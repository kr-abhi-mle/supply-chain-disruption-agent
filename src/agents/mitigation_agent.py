"""Mitigation Agent (step 4): picks one action per order with a fixed rule table.

Rules are checked top to bottom and the first match wins (see RULES). No LLM: the decision must
be auditable, so every Decision names its rule and gives a one-line reason.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from src import config
from src.models import Decision, OrderImpact

SEVERE = ("HIGH", "CRITICAL")

# The policy in one readable table. decide() implements it; the report shows it as the mitigation plan.
RULES = {
    "R0": {"action": "MONITOR", "when": "Severity LOW: the delivery buffer absorbs the delay",
           "offer": "None needed, no email"},
    "R1": {"action": "CANCEL", "when": "Time-sensitive item and severity HIGH or CRITICAL",
           "offer": "Free cancellation with a full refund"},
    "R2": {"action": "DELAY", "when": "Bulky item (expensive and slow to reroute)",
           "offer": "Freight charge refunded"},
    "R3": {"action": "REROUTE", "when": "Severity HIGH or CRITICAL, small item",
           "offer": f"Free expedited shipping, {config.REROUTE_EXTRA_DAYS} extra days instead of the full delay"},
    "R4": {"action": "DELAY", "when": "Anything else (severity MEDIUM)",
           "offer": f"{config.VOUCHER_PCT}% voucher for the next order"},
}


def run(order_impacts: List[OrderImpact], delay_days: int) -> List[Decision]:
    return [decide(order, delay_days) for order in order_impacts]


def decide(order: OrderImpact, delay_days: int) -> Decision:
    def decision(action, rule_id, resolution, final_eta, compensation, reason):
        return Decision(order_id=order.order_id, action=action, rule_id=rule_id, resolution=resolution,
                        final_eta=final_eta, compensation_brl=round(compensation, 2), reason=reason)

    if order.severity == "LOW":
        return decision("MONITOR", "R0", "No action needed", order.new_eta, 0.0,
                        f"Still arrives by the promised date ({order.promised_date}) despite the {delay_days}-day delay")
    if order.has_time_sensitive and order.severity in SEVERE:
        refund = order.order_value + order.freight_total
        return decision("CANCEL", "R1", f"Free cancellation with a full refund of R$ {refund:.2f}", None, refund,
                        f"Time-sensitive goods lose their value when {order.days_late} days late, so refund instead")
    if order.has_bulky:
        return decision("DELAY", "R2", f"Delivery delayed, freight charge of R$ {order.freight_total:.2f} refunded",
                        order.new_eta, order.freight_total,
                        "Bulky goods are expensive and slow to reroute, so waiting is cheaper")
    if order.severity in SEVERE:
        rerouted = date.fromisoformat(order.baseline_eta) + timedelta(days=config.REROUTE_EXTRA_DAYS)
        return decision("REROUTE", "R3", "Free expedited shipping through an unaffected route", rerouted.isoformat(),
                        order.freight_total * config.REROUTE_COST_FACTOR,
                        f"Small goods move easily by another carrier: {config.REROUTE_EXTRA_DAYS} extra days "
                        f"instead of {delay_days}")
    voucher = order.order_value * config.VOUCHER_PCT / 100
    return decision("DELAY", "R4", f"Delivery delayed, {config.VOUCHER_PCT}% voucher (R$ {voucher:.2f}) for the next order",
                    order.new_eta, voucher, f"Only {order.days_late} days late, so a goodwill voucher is enough")
