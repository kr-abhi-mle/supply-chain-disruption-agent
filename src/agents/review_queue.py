"""Review queue (part of step 6): flags unusual orders for a person to check before emails go out.

Pure code. A flag never changes an order's action; it only says what a person should look at.
report_narrative.py then writes a short note per flagged order (Gemini or a template).
"""
from __future__ import annotations

from datetime import date
from typing import List, Set, Tuple

from src import config
from src.models import Decision, ImpactReport, OrderImpact, ReviewItem


def run(report: ImpactReport) -> Tuple[int, List[ReviewItem]]:
    """Returns how many orders were flagged, and a short list that covers each kind of flag."""
    flagged = []   # (kinds, item)
    for order, decision in zip(report.orders, report.decisions):
        if decision.action == "MONITOR":
            continue   # no customer action is taken, so there is nothing to review
        found = flags_for(order, decision)
        if found:
            item = ReviewItem(order_id=order.order_id, rule_id=decision.rule_id, action=decision.action,
                              severity=order.severity, flags=[f for _, f, _ in found], checks=[c for _, _, c in found])
            flagged.append(({kind for kind, _, _ in found}, item))
    rank = {level: i for i, level in enumerate(config.SEVERITY_ORDER)}
    days_late = {o.order_id: o.days_late for o in report.orders}
    flagged.sort(key=lambda pair: (-len(pair[1].flags), -rank[pair[1].severity],
                                   -days_late[pair[1].order_id], pair[1].order_id))
    # The best example of each kind of flag first, so the short list shows different risks.
    picked: List[ReviewItem] = []
    covered: Set[str] = set()
    for kind in KINDS:
        best = next(((kinds, item) for kinds, item in flagged if kind in kinds), None)
        if best and kind not in covered:
            picked.append(best[1])
            covered |= best[0]
    picked += [item for _, item in flagged if item not in picked]
    return len(flagged), picked[:config.REVIEW_QUEUE_SIZE]


KINDS = ["already_late", "still_late", "high_value", "split_order", "bulky_time_sensitive"]


def flags_for(order: OrderImpact, decision: Decision) -> List[Tuple[str, str, str]]:
    """Each flag is (kind, fact, what a person should check)."""
    found = []
    worst_buffer = min(i.buffer_days for i in order.items)
    if -worst_buffer >= config.REVIEW_LATE_DAYS:
        found.append(("already_late", f"already {-worst_buffer} days late before the disruption",
                      "whether the customer has already complained or been compensated"))
    if decision.action == "REROUTE":
        still_late = (date.fromisoformat(decision.final_eta) - date.fromisoformat(order.promised_date)).days
        if still_late >= config.REVIEW_LATE_DAYS:
            found.append(("still_late", f"still {still_late} days late after rerouting",
                          "whether a faster carrier is available"))
    if order.order_value >= config.REVIEW_HIGH_VALUE_BRL:
        found.append(("high_value", f"high-value order (R$ {order.order_value:,.2f})",
                      "that the standard compensation is enough for this customer"))
    sellers = {i.item.seller_id for i in order.items}
    if len(sellers) > 1:
        found.append(("split_order", f"{len(order.items)} affected items from {len(sellers)} sellers",
                      "whether the items should ship separately"))
    if order.has_bulky and order.has_time_sensitive:
        found.append(("bulky_time_sensitive", "both bulky and time-sensitive, so the cancellation rule R1 "
                      "took priority over R2", "that cancelling is better than a late delivery"))
    return found
