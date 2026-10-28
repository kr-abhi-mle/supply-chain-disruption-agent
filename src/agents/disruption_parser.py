"""Disruption Parser (step 1): turns a plain-English query into a validated DisruptionEvent.

Gemini reads the query when it is available. The rule-based parser (rule_parser.py) is used offline
and whenever Gemini fails. Both results then go through the same validation in code, which also
records every default the system applied and writes the interpretation sentence shown to the user.
"""
from __future__ import annotations

from typing import List, Tuple

from src import config, llm
from src.agents import rule_parser
from src.data_prep import normalize_city
from src.models import DisruptionEvent, ParsedQuery

SYSTEM_PROMPT = f"""You read reports of freight disruptions in Brazil and extract structured fields.

Rules:
- states: two-letter Brazilian state codes, for example "SP" for Sao Paulo or "RS" for Rio Grande do Sul.
- cities: only when the text names a specific city, for example "curitiba". Leave it empty for a whole state.
- "Sao Paulo" and "Rio de Janeiro" are both a city and a state. Read them as the STATE (put the code in
  states, leave cities empty) unless the text explicitly says "city".
- direction: "outbound" for freight leaving the area, "inbound" for deliveries arriving into it,
  "both" when both ways are affected. If the text does not say, use "outbound".
- delay_days: the duration in days ("a week" is 7, "48 hours" is 2). If no duration is given, use
  {config.DEFAULT_DELAY_DAYS}.
- product_focus: the kinds of products the text is concerned about. If it names none (for example it
  says "all freight"), use exactly: "{config.DEFAULT_PRODUCT_FOCUS}".
- interpretation: one sentence saying how you understood the query.
- If no Brazilian place is named, return empty states and cities. Never guess a location."""


def run(query: str, use_llm: bool) -> ParsedQuery:
    source, note = "rules", ""
    if use_llm:
        try:
            event = llm.parse(SYSTEM_PROMPT, query, DisruptionEvent, temperature=0.0)
            source = "gemini"
        except llm.LLMError as error:
            note = f"Parser fell back to rules: {error}"
    if source == "rules":
        event = rule_parser.parse_with_rules(query)
    event, assumptions = validate(event, query)
    return ParsedQuery(event=event, source=source, assumptions=assumptions, fallback_note=note)


def validate(event: DisruptionEvent, query: str) -> Tuple[DisruptionEvent, List[str]]:
    """Shared by both paths: clean the fields, then list every default and reading that was applied."""
    text = normalize_city(query)
    assumptions: List[str] = []
    states = list(dict.fromkeys(s.strip().upper() for s in event.states))
    dropped = [s for s in states if s not in config.BRAZIL_STATES]
    if dropped:
        assumptions.append(f"Ignored unknown state codes: {', '.join(dropped)}")
    states = [s for s in states if s in config.BRAZIL_STATES]
    cities = list(dict.fromkeys(normalize_city(c) for c in event.cities if c.strip()))
    # A city that is just the name of a chosen state ("sao paulo" next to SP) is the state, not a city.
    state_names = {config.BRAZIL_STATES[s].lower() for s in states}
    cities = [c for c in cities if c not in state_names or rule_parser.says_city(text, c)]
    if cities:
        states = []   # retrieval filters on cities when any are given, so keep one place list
    for code in states:
        name = config.BRAZIL_STATES[code]
        if code in config.CITY_STATE_NAMES and name.lower() in text and not cities:
            assumptions.append(f"'{name}' read as the state {code}. Say 'city of {name}' to mean the city.")
    days = min(max(event.delay_days, 1), config.MAX_DELAY_DAYS)
    if days != event.delay_days:
        assumptions.append(f"Delay of {event.delay_days} days clamped to {days} (allowed 1 to {config.MAX_DELAY_DAYS})")
    if states or cities:   # without a place the run stops, so defaults would only be noise
        assumptions += _defaults_applied(event, text, days)
    clean = event.model_copy(update={"states": states, "cities": cities, "delay_days": days})
    return clean.model_copy(update={"interpretation": interpretation(clean)}), assumptions


def _defaults_applied(event: DisruptionEvent, text: str, days: int) -> List[str]:
    """Checked in code against the query text, so a note appears only when a default was really used."""
    notes = []
    if rule_parser.find_days(text) is None:
        if days == config.DEFAULT_DELAY_DAYS:
            notes.append(f"No duration given: assumed {config.DEFAULT_DELAY_DAYS} days")
        else:   # e.g. "until next Friday": the LLM estimated a number the query does not state
            notes.append(f"No exact duration in the query: Gemini estimated {days} days")
    if event.direction == "outbound" and rule_parser.find_direction(text) is None:
        notes.append("No direction given: assumed freight leaving the area (outbound)")
    if event.product_focus == config.DEFAULT_PRODUCT_FOCUS:
        notes.append(f"No product focus given: ranked '{config.DEFAULT_PRODUCT_FOCUS}' first")
    return notes


def interpretation(event: DisruptionEvent) -> str:
    """Built from the validated fields, so it always describes exactly what retrieval will search."""
    if event.cities:
        place = "the city of " + ", ".join(c.title() for c in event.cities)
    elif event.states:
        place = "the state of " + ", ".join(f"{config.BRAZIL_STATES[s]} ({s})" for s in event.states)
    else:
        return "No Brazilian city or state was found in the query."
    flow = {"outbound": "freight leaving", "inbound": "deliveries into",
            "both": "freight leaving and deliveries into"}[event.direction]
    kind = event.disruption_type.replace("_", " ")
    article = "An" if kind[0] in "aeiou" else "A"
    return f"{article} {kind} disruption delays {flow} {place} by {event.delay_days} days."
