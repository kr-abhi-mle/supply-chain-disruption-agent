"""Each rule R0 to R4, the rule order and the final ETA per action. Default buffer is 2 days."""
from src.agents import logistics_analyst, mitigation_agent


def decide(make_item, delay_days, **item_fields):
    orders = logistics_analyst.run([make_item(**item_fields)], delay_days)
    [decision] = mitigation_agent.run(orders, delay_days)
    return decision


def test_r0_low_severity_is_monitored(make_item):
    decision = decide(make_item, 2)
    assert (decision.action, decision.rule_id, decision.compensation_brl) == ("MONITOR", "R0", 0.0)


def test_r1_time_sensitive_and_severe_is_cancelled_with_full_refund(make_item):
    decision = decide(make_item, 5, is_time_sensitive=True, category="party_supplies")
    assert (decision.action, decision.rule_id) == ("CANCEL", "R1")
    assert decision.final_eta is None and decision.compensation_brl == 120.0
    assert "refund" in decision.resolution


def test_r1_wins_over_r2_for_time_sensitive_bulky_items(make_item):
    assert decide(make_item, 5, is_time_sensitive=True, is_bulky=True).rule_id == "R1"


def test_time_sensitive_but_only_medium_is_not_cancelled(make_item):
    assert decide(make_item, 3, is_time_sensitive=True).rule_id == "R4"


def test_r2_bulky_is_delayed_with_freight_refund(make_item):
    decision = decide(make_item, 3, is_bulky=True)
    assert (decision.action, decision.rule_id) == ("DELAY", "R2")
    assert decision.final_eta == "2018-08-23" and decision.compensation_brl == 20.0


def test_r2_wins_over_r3_for_severe_bulky_items(make_item):
    assert decide(make_item, 9, is_bulky=True).rule_id == "R2"


def test_r3_severe_small_item_is_rerouted(make_item):
    decision = decide(make_item, 5)
    assert (decision.action, decision.rule_id) == ("REROUTE", "R3")
    assert decision.final_eta == "2018-08-22"   # baseline 20 Aug + 2 reroute days, instead of 25 Aug


def test_r4_medium_small_item_gets_a_voucher(make_item):
    decision = decide(make_item, 3)
    assert (decision.action, decision.rule_id) == ("DELAY", "R4")
    assert decision.final_eta == "2018-08-23" and decision.compensation_brl == 10.0
    assert "10% voucher" in decision.resolution


def test_every_decision_explains_itself(make_item):
    for delay in (2, 3, 5, 9):
        decision = decide(make_item, delay)
        assert decision.rule_id and decision.reason
