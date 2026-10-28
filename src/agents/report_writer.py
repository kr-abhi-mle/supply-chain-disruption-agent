"""Report Writer (step 6): every statistic and table in code, then the narrative.

The numbers, tables and mitigation plan are computed here. review_queue.py flags unusual orders for a
person, and report_narrative.py writes the summary, next steps and review notes (Gemini or templates).
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, List, Tuple

from src import config
from src.agents import report_narrative, review_queue
from src.agents.mitigation_agent import RULES
from src.models import AffectedItem, ImpactReport


def run(report: ImpactReport, items: List[AffectedItem], use_llm: bool) -> Tuple[ImpactReport, List[str]]:
    """Fill in the numbers, tables and review queue, then the narrative. Returns the report and fallback notes."""
    report = report.model_copy(update=compute(report, items))
    flagged_total, queue = review_queue.run(report)
    report.stats["orders_flagged_for_review"] = flagged_total
    report = report.model_copy(update={"review_queue": queue})
    return report_narrative.run(report, flagged_total, use_llm)


def compute(report: ImpactReport, items: List[AffectedItem]) -> Dict[str, Any]:
    late = [o for o in report.orders if o.days_late > 0]
    stats = {
        "affected_items": len(items),
        "affected_orders": len(report.orders),
        "affected_sellers": len({i.seller_id for i in items}),
        "affected_customers": len({i.customer_id for i in items}),
        "late_orders": len(late),
        "pct_late_orders": round(100 * len(late) / max(len(report.orders), 1), 1),
        "avg_days_late": round(sum(o.days_late for o in late) / max(len(late), 1), 1),
        "value_at_risk_brl": round(sum(o.order_value for o in late), 2),
        "compensation_cost_brl": round(sum(d.compensation_brl for d in report.decisions), 2),
    }
    by_severity = Counter(o.severity for o in report.orders)
    by_rule = Counter(f"{d.rule_id} {d.action}" for d in report.decisions)
    return {
        "stats": stats,
        "by_severity": {level: by_severity.get(level, 0) for level in config.SEVERITY_ORDER},
        "by_action": dict(sorted(by_rule.items())),
        "mitigation_plan": mitigation_plan(report),
        "top_categories": top_categories(report),
        "top_sellers": top_sellers(items),
        "priority_skus": priority_skus(report),
    }


def mitigation_plan(report: ImpactReport) -> List[Dict[str, Any]]:
    """Per rule: what triggers it, what the customer gets, how many orders, and how much it helps."""
    rows = []
    for rule_id, rule in RULES.items():
        pairs = [(o, d) for o, d in zip(report.orders, report.decisions) if d.rule_id == rule_id]
        before = [o.days_late for o, _ in pairs]
        after = [max(0, (date.fromisoformat(d.final_eta) - date.fromisoformat(o.promised_date)).days)
                 for o, d in pairs if d.final_eta]
        rows.append({
            "rule": rule_id, "action": rule["action"], "when": rule["when"], "customer offer": rule["offer"],
            "orders": len(pairs),
            "avg days late if no action": round(sum(before) / len(before), 1) if before else 0,
            # None for R1: a cancelled order is refunded, not delivered late
            "avg days late after action": None if rule_id == "R1" else round(sum(after) / len(after), 1) if after else 0,
            "cost (R$)": round(sum(d.compensation_brl for _, d in pairs), 2),
        })
    return rows


def top_categories(report: ImpactReport, n: int = 5) -> List[Dict[str, Any]]:
    impacts = [i for o in report.orders for i in o.items]
    counts = Counter(i.item.category for i in impacts)
    late = Counter(i.item.category for i in impacts if i.days_late > 0)
    return [{"category": c, "items": k, "late_items": late[c]} for c, k in counts.most_common(n)]


def top_sellers(items: List[AffectedItem], n: int = 5) -> List[Dict[str, Any]]:
    counts = Counter(i.seller_id for i in items)
    where = {i.seller_id: f"{i.seller_city}, {i.seller_state}" for i in items}
    orders = {s: len({i.order_id for i in items if i.seller_id == s}) for s, _ in counts.most_common(n)}
    return [{"seller": s[:8], "location": where[s], "items": k, "orders": orders[s]} for s, k in counts.most_common(n)]


def priority_skus(report: ImpactReport, n_each: int = 8) -> List[Dict[str, Any]]:
    """Late bulky items (hardest to move) and the best semantic matches for the product focus."""
    rank = {level: i for i, level in enumerate(config.SEVERITY_ORDER)}
    impacts = sorted((i for o in report.orders for i in o.items),
                     key=lambda i: (-rank[i.severity], -i.days_late, i.item.id))
    bulky = [i for i in impacts if i.item.is_bulky and i.days_late > 0][:n_each]
    focus = [i for i in impacts if i.item.focus_match and i not in bulky][:n_each]
    rows, seen = [], set()
    for i in bulky + focus:
        if i.item.product_id in seen:
            continue
        seen.add(i.item.product_id)
        why = [f"bulky and {i.days_late} days late"] if i.item.is_bulky and i.days_late else []
        why += ["matches the product focus"] if i.item.focus_match else []
        rows.append({"product": i.item.product_id[:8], "category": i.item.category,
                     "weight_kg": round(i.item.weight_kg, 1), "volume_l": round(i.item.volume_l),
                     "severity": i.severity, "why": "; ".join(why)})
    return rows
