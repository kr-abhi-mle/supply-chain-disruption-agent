"""Offline outputs: every template email and the template summary. No key needed."""
import pytest

from src.agents import customer_success, logistics_analyst, mitigation_agent, report_narrative, report_writer
from src.models import DisruptionEvent, ImpactReport, Narrative

EVENT = DisruptionEvent(disruption_type="weather", states=["SP"], cities=[], direction="outbound",
                        delay_days=5, product_focus="furniture",
                        interpretation="A weather disruption delays freight leaving the state of Sao Paulo (SP) by 5 days.")

CASES = {   # rule -> (delay_days, item fields); the default item has a 2-day buffer
    "R1": (5, dict(is_time_sensitive=True, category="party_supplies")),
    "R2": (3, dict(is_bulky=True, weight_kg=18.0)),
    "R3": (5, dict()),
    "R4": (3, dict()),
}


def order_and_decision(make_item, rule_id):
    delay, fields = CASES[rule_id]
    [order] = logistics_analyst.run([make_item(**fields)], delay)
    [decision] = mitigation_agent.run([order], delay)
    assert decision.rule_id == rule_id
    return order, decision


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_template_states_date_or_refund_and_the_offer(make_item, rule_id):
    order, decision = order_and_decision(make_item, rule_id)
    email, note = customer_success.run(order, decision, EVENT, use_llm=False)
    assert email.source == "template" and note == ""
    if decision.final_eta:
        assert customer_success.pretty_date(decision.final_eta) in email.body
    else:
        assert "refund" in email.body
    if rule_id != "R3":   # a reroute's cost is ours (expedited freight), not an amount offered to the customer
        assert f"R$ {decision.compensation_brl:.2f}" in email.body
    assert email.body.startswith("Hello,") and "Sao Paulo" in email.body and "{" not in email.body


def test_city_names_keep_small_words_lowercase():
    assert customer_success.city_name("caxias do sul") == "Caxias do Sul"


def small_report(make_item):
    """Two orders, one bulky, both 3 days late, with numbers, tables and the review queue computed."""
    orders = logistics_analyst.run([make_item(id="o1-1"), make_item(id="o2-1", order_id="o2", is_bulky=True)], 5)
    report = ImpactReport(query="q", event=EVENT, orders=orders, decisions=mitigation_agent.run(orders, 5))
    return report, [i.item for o in orders for i in o.items]


def test_template_narrative_uses_only_the_reports_numbers(make_item):
    report, items = small_report(make_item)
    report, notes = report_writer.run(report, items, use_llm=False)
    assert notes == [] and set(report.written_by.values()) == {"template"}
    facts = report_narrative.narrative_facts(report, int(report.stats["orders_flagged_for_review"]))
    written = report.executive_summary + " ".join(report.recommendations)
    assert report_narrative.numbers_in(written) <= report_narrative.numbers_in(facts)
    assert any("reroute" in step for step in report.recommendations)


def test_gemini_parts_with_invented_numbers_fall_back_one_by_one(make_item, monkeypatch):
    report, items = small_report(make_item)
    draft = Narrative(executive_summary="About 9,999 orders are late.",
                      recommendations=["Contact seller s1 about pickups."], review_notes=[])
    monkeypatch.setattr(report_narrative.llm, "parse", lambda *args, **kwargs: draft)
    report, notes = report_writer.run(report, items, use_llm=True)
    assert "9,999" not in report.executive_summary and any("9999" in n for n in notes)
    assert report.recommendations == ["Contact seller s1 about pickups."]
    assert report.written_by["summary"] == "template" and report.written_by["recommendations"] == "gemini"
