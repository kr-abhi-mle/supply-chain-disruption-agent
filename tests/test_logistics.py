"""Severity bands, the bulky bump and order roll-up. The default item has a 2-day buffer."""
import pytest

from src.agents import logistics_analyst


def assess(make_item, delay_days, **item_fields):
    [order] = logistics_analyst.run([make_item(**item_fields)], delay_days)
    return order


@pytest.mark.parametrize("delay_days, days_late, severity", [
    (2, 0, "LOW"),        # the buffer absorbs the delay
    (3, 1, "MEDIUM"),
    (4, 2, "MEDIUM"),
    (5, 3, "HIGH"),
    (8, 6, "HIGH"),
    (9, 7, "CRITICAL"),
])
def test_severity_bands(make_item, delay_days, days_late, severity):
    order = assess(make_item, delay_days)
    assert (order.days_late, order.severity) == (days_late, severity)


def test_new_eta_is_baseline_plus_delay(make_item):
    assert assess(make_item, 5).new_eta == "2018-08-25"


def test_bulky_late_item_is_raised_one_level(make_item):
    order = assess(make_item, 5, is_bulky=True, weight_kg=18.2)
    assert order.severity == "CRITICAL"
    assert any("Bulky (18.2 kg" in reason for reason in order.reasons)


def test_bulky_item_on_time_stays_low(make_item):
    assert assess(make_item, 2, is_bulky=True).severity == "LOW"


def test_bulky_bump_is_capped_at_critical(make_item):
    assert assess(make_item, 12, is_bulky=True).severity == "CRITICAL"


def test_negative_buffer_is_explained(make_item):
    order = assess(make_item, 1, baseline_eta="2018-08-25")   # delivered 3 days after the promise
    assert order.days_late == 4 and order.severity == "HIGH"
    assert any("Already 3 days late before the disruption" in reason for reason in order.reasons)


def test_reasons_show_the_arithmetic(make_item):
    assert "Buffer 2 days, delay 5 days, so 3 days late: HIGH" in assess(make_item, 5).reasons


def test_order_takes_the_worst_item_and_sums_values(make_item):
    small = make_item(id="o1-1", baseline_eta="2018-08-10")             # 12-day buffer: LOW
    bulky = make_item(id="o1-2", order_item_id=2, is_bulky=True)        # 3 days late, bulky: CRITICAL
    [order] = logistics_analyst.run([small, bulky], delay_days=5)
    assert order.severity == "CRITICAL" and order.has_bulky
    assert order.order_value == 200.0 and order.freight_total == 40.0
    assert order.reasons[0].startswith("2 affected items")


def test_items_are_grouped_by_order(make_item):
    orders = logistics_analyst.run([make_item(), make_item(id="o2-1", order_id="o2")], delay_days=5)
    assert [o.order_id for o in orders] == ["o1", "o2"]
