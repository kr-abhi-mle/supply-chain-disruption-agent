"""Logistics Analyst (step 3): the impact of the disruption on each order if we do nothing.

Pure Python, no LLM: dates and severity must be exact, repeatable and unit tested.
Every result carries plain-English reasons, so a reviewer can check any number by hand.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from src import config
from src.models import AffectedItem, ItemImpact, OrderImpact


def run(items: List[AffectedItem], delay_days: int) -> List[OrderImpact]:
    by_order: Dict[str, List[ItemImpact]] = {}
    for item in items:
        by_order.setdefault(item.order_id, []).append(assess_item(item, delay_days))
    return [summarize_order(impacts) for impacts in by_order.values()]


def severity_for(days_late: int) -> str:
    if days_late >= config.CRITICAL_FROM_DAYS:
        return "CRITICAL"
    if days_late >= config.HIGH_FROM_DAYS:
        return "HIGH"
    if days_late >= config.MEDIUM_FROM_DAYS:
        return "MEDIUM"
    return "LOW"


def bump(severity: str) -> str:
    levels = config.SEVERITY_ORDER
    return levels[min(levels.index(severity) + 1, len(levels) - 1)]


def assess_item(item: AffectedItem, delay_days: int) -> ItemImpact:
    promised = date.fromisoformat(item.promised_date)
    baseline = date.fromisoformat(item.baseline_eta)
    buffer_days = (promised - baseline).days
    new_eta = baseline + timedelta(days=delay_days)
    days_late = max(0, (new_eta - promised).days)
    severity = severity_for(days_late)
    reasons = []
    if buffer_days < 0:
        reasons.append(f"Already {-buffer_days} days late before the disruption "
                       f"(delivered {item.baseline_eta}, promised {item.promised_date})")
    if days_late == 0:
        reasons.append(f"Buffer {buffer_days} days absorbs the {delay_days}-day delay: LOW")
    else:
        reasons.append(f"Buffer {buffer_days} days, delay {delay_days} days, so {days_late} days late: {severity}")
    if item.is_bulky and days_late > 0:
        # Heavy freight needs special carriers, and its backlog clears more slowly.
        raised = bump(severity)
        if raised != severity:
            reasons.append(f"Bulky ({item.weight_kg:.1f} kg, {item.volume_l:.0f} L): raised to {raised}")
        severity = raised
    return ItemImpact(item=item, buffer_days=buffer_days, new_eta=new_eta.isoformat(),
                      days_late=days_late, severity=severity, reasons=reasons)


def summarize_order(impacts: List[ItemImpact]) -> OrderImpact:
    """An order is as severe as its worst affected item."""
    worst = max(impacts, key=lambda i: (config.SEVERITY_ORDER.index(i.severity), i.days_late))
    first = impacts[0].item
    reasons = list(worst.reasons)
    if len(impacts) > 1:
        reasons.insert(0, f"{len(impacts)} affected items; the worst ({worst.item.category}) sets the order severity")
    return OrderImpact(
        order_id=first.order_id,
        customer_city=first.customer_city,
        customer_state=first.customer_state,
        promised_date=first.promised_date,
        baseline_eta=first.baseline_eta,
        new_eta=max(i.new_eta for i in impacts),
        days_late=max(i.days_late for i in impacts),
        severity=worst.severity,
        has_bulky=any(i.item.is_bulky for i in impacts),
        has_time_sensitive=any(i.item.is_time_sensitive for i in impacts),
        focus_match=any(i.item.focus_match for i in impacts),
        order_value=round(sum(i.item.price for i in impacts), 2),
        freight_total=round(sum(i.item.freight_value for i in impacts), 2),
        items=impacts,
        reasons=reasons,
    )
