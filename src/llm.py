"""The only module that talks to an LLM (Gemini, over its REST API). Agents call parse() and text().

Every failure, including offline mode, surfaces as LLMError. Callers catch only that error and
switch to their offline counterpart: the rule-based parser or a template. Switching to another
provider means rewriting this one file.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src import config

T = TypeVar("T", bound=BaseModel)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRY_STATUSES = {500, 502, 503, 504}   # worth retrying on the same model

# Per-run state, cleared by reset() and shown in the report, so cost and model switches are visible.
USAGE: Dict[str, int] = {"calls": 0, "tokens": 0}
MODELS_USED: Dict[str, int] = {}   # model name -> successful calls
NOTES: List[str] = []              # e.g. "gemini-3.6-flash was unavailable (HTTP 429), so ... answered"
_RATE_LIMITED: Set[str] = set()    # models that answered 429 in this run; not asked again

_client: Optional[httpx.Client] = None   # tests replace this with a mocked transport


class LLMError(Exception):
    """Gemini could not give a usable answer: offline, network, quota, or a malformed reply."""


def parse(system: str, user: str, schema: Type[T], temperature: float = 0.0) -> T:
    """Ask Gemini for JSON that matches a Pydantic model (structured output)."""
    extra = {"responseMimeType": "application/json", "responseJsonSchema": schema.model_json_schema()}
    reply = _generate(system, user, temperature, extra)
    try:
        return schema.model_validate_json(reply)
    except ValidationError as error:
        raise LLMError(f"Gemini returned JSON that does not match {schema.__name__}") from error


def text(system: str, user: str, temperature: float = 0.2) -> str:
    """Ask Gemini for plain text."""
    return _generate(system, user, temperature, {}).strip()


def _generate(system: str, user: str, temperature: float, extra: Dict[str, Any]) -> str:
    if config.LLM_MODE == "offline":
        raise LLMError("offline mode")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "thinkingConfig": {"thinkingLevel": config.GEMINI_THINKING_LEVEL},
            **extra,
        },
    }
    data = _post_with_retries(body)
    USAGE["calls"] += 1
    USAGE["tokens"] += data.get("usageMetadata", {}).get("totalTokenCount", 0)
    return _reply_text(data)


def _post_with_retries(body: Dict[str, Any]) -> Dict[str, Any]:
    """Try the main model, then each fallback model, until one answers."""
    problems = []
    for model in _models():
        data, problem = _try_model(model, body)
        if data is not None:
            MODELS_USED[model] = MODELS_USED.get(model, 0) + 1
            if model != config.GEMINI_MODEL and not any(model in n for n in NOTES):
                NOTES.append(f"{config.GEMINI_MODEL} was unavailable ({'; '.join(problems)}), so {model} answered")
            return data
        problems.append(f"{model}: {problem}")
        if problem in ("HTTP 400", "HTTP 401", "HTTP 403"):
            break   # a bad request or a bad key fails on every model, so stop here
    raise LLMError("Gemini failed on every model: " + "; ".join(problems))


def _try_model(model: str, body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """One model with exponential backoff. Returns (reply, "") or (None, what went wrong).

    A 429 means this model's quota is spent (per minute or per day), so waiting a few seconds will
    not help: skip it for the rest of the run. 503s and timeouts are often brief, so back off and retry.
    """
    url = API_URL.format(model=model)
    headers = {"x-goog-api-key": config.GEMINI_API_KEY}   # a header, so the key never appears in a URL or log
    problem = ""
    for attempt in range(config.LLM_MAX_ATTEMPTS):
        if attempt > 0:
            time.sleep(config.LLM_RETRY_WAITS_S[min(attempt - 1, len(config.LLM_RETRY_WAITS_S) - 1)])
        try:
            response = _get_client().post(url, json=body, headers=headers)
        except httpx.TransportError as error:
            problem = f"network error ({type(error).__name__})"
            continue
        if response.status_code == 200:
            return response.json(), ""
        problem = f"HTTP {response.status_code}"
        if response.status_code == 429:
            _RATE_LIMITED.add(model)
            break
        if response.status_code not in RETRY_STATUSES:
            break   # e.g. 404 for a retired model: try the next model instead
    return None, problem


def _models() -> List[str]:
    models = [config.GEMINI_MODEL] + [m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL]
    return [m for m in models if m not in _RATE_LIMITED]


def reset() -> None:
    """Called at the start of every pipeline run."""
    USAGE.update(calls=0, tokens=0)
    MODELS_USED.clear()
    NOTES.clear()
    _RATE_LIMITED.clear()


def _reply_text(data: Dict[str, Any]) -> str:
    """Join the answer parts, skipping Gemini's internal thought parts."""
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        reason = (data.get("candidates") or [{}])[0].get("finishReason", "no candidates")
        raise LLMError(f"Gemini returned no answer ({reason})")
    reply = "".join(part.get("text", "") for part in parts if not part.get("thought"))
    if not reply.strip():
        raise LLMError("Gemini returned an empty answer")
    return reply


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=config.LLM_TIMEOUT_S)
    return _client

