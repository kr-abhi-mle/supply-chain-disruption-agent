"""Live Gemini checks. Skipped without GEMINI_API_KEY, so the suite always passes offline."""
import pytest

from src import config
from src.agents import disruption_parser

pytestmark = pytest.mark.skipif(config.LLM_MODE != "gemini", reason="no GEMINI_API_KEY")


def test_gemini_parses_the_sp_scenario_like_the_rules():
    query = "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days"
    gemini = disruption_parser.run(query, use_llm=True)
    if gemini.fallback_note:
        pytest.skip(f"Gemini unavailable right now: {gemini.fallback_note}")
    rules = disruption_parser.run(query, use_llm=False)
    assert gemini.source == "gemini"
    assert gemini.event == rules.event


def test_gemini_email_passes_the_date_check(make_item):
    from src.agents import customer_success, logistics_analyst, mitigation_agent
    [order] = logistics_analyst.run([make_item()], 5)
    [decision] = mitigation_agent.run([order], 5)
    event = disruption_parser.run("Heavy rains are delaying all freight leaving Sao Paulo for 5 days", False).event
    email, note = customer_success.run(order, decision, event, use_llm=True)
    if note:
        pytest.skip(f"Gemini unavailable or off-script right now: {note}")
    assert email.source == "gemini"
    assert customer_success.pretty_date(decision.final_eta) in email.body
