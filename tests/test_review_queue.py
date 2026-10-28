"""Flags for human review come from code and never change a decision. No key needed."""
from src.agents import logistics_analyst, mitigation_agent, review_queue
from src.models import ImpactReport, Narrative, ReviewNote
from src.agents import report_narrative


def queue_for(items, delay_days=5):
    orders = logistics_analyst.run(items, delay_days)
    decisions = mitigation_agent.run(orders, delay_days)
    report = ImpactReport(query="q", orders=orders, decisions=decisions)
    return review_queue.run(report), decisions


def test_an_order_already_late_before_the_disruption_is_flagged(make_item):
    (total, queue), _ = queue_for([make_item(baseline_eta="2018-08-26")])   # 4 days late already
    assert total == 1 and "already 4 days late before the disruption" in queue[0].flags
    assert "still 6 days late after rerouting" in queue[0].flags


def test_an_ordinary_late_order_is_not_flagged(make_item):
    (total, queue), decisions = queue_for([make_item()])   # 3 days late, rerouted, then on time
    assert decisions[0].action == "REROUTE" and total == 0 and queue == []


def test_monitor_orders_are_never_flagged(make_item):
    (total, _), _ = queue_for([make_item(price=900.0, baseline_eta="2018-08-10")])
    assert total == 0


def test_high_value_split_and_bulky_time_sensitive_flags(make_item):
    items = [make_item(id="o1-1", price=450.0, is_bulky=True, is_time_sensitive=True),
             make_item(id="o1-2", order_item_id=2, seller_id="s2", price=100.0)]
    (total, [item]), decisions = queue_for(items)
    text = " ".join(item.flags)
    assert "high-value order (R$ 550.00)" in text and "2 affected items from 2 sellers" in text
    assert "R1 took priority over R2" in text
    assert item.action == decisions[0].action == "CANCEL"   # the flag explains, it does not decide


def test_gemini_note_is_matched_by_reference_and_checked(make_item, monkeypatch):
    (total, queue), decisions = queue_for([make_item(baseline_eta="2018-08-26")])
    orders = logistics_analyst.run([make_item(baseline_eta="2018-08-26")], 5)
    report = ImpactReport(query="q", orders=orders, decisions=decisions, review_queue=queue)
    good = ReviewNote(order_ref="o1", note="The customer already waited 4 days; check for complaints.")
    draft = Narrative(executive_summary="", recommendations=[], review_notes=[good])
    merged, source = report_narrative._merge_notes(
        [q.model_copy(update={"note": "template"}) for q in queue], draft, {"4"}, [])
    assert merged[0].note == good.note and merged[0].note_source == "gemini" and source == "gemini"
    bad = Narrative(executive_summary="", recommendations=[],
                    review_notes=[ReviewNote(order_ref="o1", note="Refund R$ 999 now.")])
    merged, source = report_narrative._merge_notes(
        [q.model_copy(update={"note": "template"}) for q in queue], bad, {"4"}, [])
    assert merged[0].note == "template" and source == "template"
