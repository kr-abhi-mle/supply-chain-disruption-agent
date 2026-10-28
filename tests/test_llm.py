"""The Gemini layer, tested with a mocked HTTP transport: no key and no network needed."""
import httpx
import pytest

from src import config, llm
from src.models import EmailContent

GOOD_REPLY = {
    "candidates": [{"content": {"parts": [
        {"text": "thinking...", "thought": True},
        {"text": '{"subject": "Your order", "body": "Hello"}'},
    ]}}],
    "usageMetadata": {"totalTokenCount": 42},
}
BUSY = (503, {"error": "high demand"})
QUOTA = (429, {"error": "quota exceeded"})
OK = (200, GOOD_REPLY)


@pytest.fixture
def gemini(monkeypatch):
    """Pretend a key is set, record the backoff waits, and serve replies per model from lists."""
    monkeypatch.setattr(config, "LLM_MODE", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "main")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ["backup"])
    waits = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    llm.reset()
    calls = []

    def serve(**replies_by_model):
        def handler(request):
            model = request.url.path.split("/")[-1].split(":")[0]
            calls.append((model, request))
            replies = replies_by_model[model]
            status, body = replies[min(sum(m == model for m, _ in calls), len(replies)) - 1]
            return httpx.Response(status, json=body)
        monkeypatch.setattr(llm, "_client", httpx.Client(transport=httpx.MockTransport(handler)))
        return calls, waits
    return serve


def models(calls):
    return [model for model, _ in calls]


def test_retries_a_503_with_backoff_then_returns_the_parsed_model(gemini):
    calls, waits = gemini(main=[BUSY, OK])
    assert llm.parse("system", "user", EmailContent) == EmailContent(subject="Your order", body="Hello")
    assert models(calls) == ["main", "main"] and waits == [2]
    request = calls[0][1]
    assert request.headers["x-goog-api-key"] == "test-key" and "test-key" not in str(request.url)


def test_a_429_switches_to_the_fallback_model_at_once(gemini):
    calls, waits = gemini(main=[QUOTA], backup=[OK])
    llm.text("system", "user")
    assert models(calls) == ["main", "backup"] and waits == []
    assert llm.MODELS_USED == {"backup": 1}
    assert "main was unavailable (main: HTTP 429), so backup answered" in llm.NOTES[0]


def test_a_rate_limited_model_is_skipped_for_the_rest_of_the_run(gemini):
    calls, _ = gemini(main=[QUOTA], backup=[OK])
    llm.text("system", "user")
    llm.text("system", "user")
    assert models(calls) == ["main", "backup", "backup"]


def test_repeated_503s_back_off_then_try_the_next_model(gemini):
    calls, waits = gemini(main=[BUSY], backup=[OK])
    llm.text("system", "user")
    assert models(calls) == ["main"] * config.LLM_MAX_ATTEMPTS + ["backup"]
    assert waits == [2, 4]


def test_every_model_failing_raises_llm_error(gemini):
    calls, _ = gemini(main=[QUOTA], backup=[BUSY])
    with pytest.raises(llm.LLMError, match="every model"):
        llm.text("system", "user")
    assert models(calls) == ["main"] + ["backup"] * config.LLM_MAX_ATTEMPTS


def test_bad_key_is_not_retried_on_any_model(gemini):
    calls, _ = gemini(main=[(403, {"error": "bad key"})], backup=[OK])
    with pytest.raises(llm.LLMError):
        llm.text("system", "user")
    assert models(calls) == ["main"]


def test_invalid_json_raises_llm_error(gemini):
    bad = {"candidates": [{"content": {"parts": [{"text": "Sure! Here is the email: ..."}]}}]}
    gemini(main=[(200, bad)])
    with pytest.raises(llm.LLMError):
        llm.parse("system", "user", EmailContent)


def test_offline_mode_never_calls_the_transport(gemini, monkeypatch):
    calls, _ = gemini(main=[OK])
    monkeypatch.setattr(config, "LLM_MODE", "offline")
    with pytest.raises(llm.LLMError):
        llm.text("system", "user")
    assert calls == []
