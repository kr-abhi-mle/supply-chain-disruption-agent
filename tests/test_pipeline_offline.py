"""Both sample scenarios end to end in offline mode. Needs the index; no key."""
import json

import pytest

from src import config
from src.agents.customer_success import pretty_date

SP_QUERY = "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days"
RS_QUERY = "Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days"


@pytest.fixture(scope="module")
def run():
    from src.build_index import open_collection
    try:
        open_collection()
    except SystemExit:
        pytest.skip("run python -m src.build_index")
    from src import pipeline
    cache = {}
    return lambda query: cache.setdefault(query, pipeline.run(query, use_llm=False))


def test_sp_scenario_matches_the_sanity_anchors(run):
    report = run(SP_QUERY)
    assert report.stopped_reason is None and report.llm_mode == "offline"
    assert report.stats["affected_items"] == 7959
    assert report.stats["affected_orders"] == 7037
    assert report.stats["affected_sellers"] == 922
    assert report.by_severity == {"LOW": 4769, "MEDIUM": 724, "HIGH": 1186, "CRITICAL": 358}
    assert [t.step[:2] for t in report.trace] == ["1.", "2.", "3.", "4.", "5.", "6."]


def test_rs_inbound_scenario_finds_orders(run):
    report = run(RS_QUERY)
    assert report.event.direction == "inbound" and report.event.delay_days == 10
    assert report.stats["affected_items"] == 571 and report.stats["affected_orders"] == 466


@pytest.mark.parametrize("query", [SP_QUERY, RS_QUERY])
def test_one_email_per_action_type_with_its_date_or_refund(run, query):
    report = run(query)
    assert [e.action for e in report.emails] == ["CANCEL", "REROUTE", "DELAY"]
    decisions = {d.order_id: d for d in report.decisions}
    for email in report.emails:
        final = decisions[email.order_id].final_eta
        assert (pretty_date(final) if final else "refund") in email.body


def test_no_location_stops_politely(run):
    report = run("Something bad happened")
    assert report.stopped_reason and not report.orders


@pytest.mark.parametrize("query, folder", [(SP_QUERY, "sp_rain_offline"), (RS_QUERY, "rs_flood_offline")])
def test_numbers_equal_the_committed_offline_sample(run, query, folder):
    sample = config.ROOT / "samples" / folder / "report.json"
    if not sample.exists():
        pytest.skip(f"samples/{folder} not generated yet")
    saved = json.loads(sample.read_text(encoding="utf-8"))   # Windows does not default to UTF-8
    report = run(query)
    assert (report.stats, report.by_severity, report.by_action) == (
        saved["stats"], saved["by_severity"], saved["by_action"])


@pytest.mark.parametrize("query", [SP_QUERY, RS_QUERY])
def test_mitigation_plan_adds_up_to_the_headline_numbers(run, query):
    report = run(query)
    plan = report.mitigation_plan
    assert [row["rule"] for row in plan] == ["R0", "R1", "R2", "R3", "R4"]
    assert sum(row["orders"] for row in plan) == report.stats["affected_orders"]
    assert round(sum(row["cost (R$)"] for row in plan), 2) == report.stats["compensation_cost_brl"]
    reroute = next(row for row in plan if row["rule"] == "R3")
    assert reroute["avg days late after action"] < reroute["avg days late if no action"]
