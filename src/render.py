"""Turns an ImpactReport into the three output files: report.md, report.json and orders.csv.

Presentation only: every number was already computed by the agents. The CLI and the app both use
this module, so they always show the same thing.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import ImpactReport, OrderImpact

ORDER_COLUMNS = ["order_id", "customer_city", "customer_state", "categories", "promised_date", "new_eta",
                 "days_late", "severity", "action", "rule_id", "resolution", "final_eta", "compensation_brl",
                 "reasons"]


def run_folder(report: ImpactReport, root: Path) -> Path:
    """A readable, unique folder name, e.g. outputs/2026-10-29_0915_heavy-rains-are-delaying."""
    words = "".join(c if c.isalnum() else " " for c in report.query.lower()).split()[:4]
    return root / f"{datetime.now():%Y-%m-%d_%H%M%S}_{'-'.join(words) or 'run'}"


def write_all(report: ImpactReport, out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "report.md", out_dir / "report.json", out_dir / "orders.csv"]
    paths[0].write_text(to_markdown(report), encoding="utf-8")
    paths[1].write_text(to_json(report), encoding="utf-8")
    paths[2].write_text(to_csv(report), encoding="utf-8")
    return paths


def to_csv(report: ImpactReport) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=ORDER_COLUMNS)
    writer.writeheader()
    writer.writerows(order_rows(report))
    return buffer.getvalue()


def order_rows(report: ImpactReport) -> List[Dict[str, Any]]:
    rows = []
    for order, decision in zip(report.orders, report.decisions):
        rows.append({
            "order_id": order.order_id, "customer_city": order.customer_city, "customer_state": order.customer_state,
            "categories": "; ".join(sorted({i.item.category for i in order.items})),
            "promised_date": order.promised_date, "new_eta": order.new_eta, "days_late": order.days_late,
            "severity": order.severity, "action": decision.action, "rule_id": decision.rule_id,
            "resolution": decision.resolution, "final_eta": decision.final_eta or "",
            "compensation_brl": decision.compensation_brl, "reasons": " | ".join(order.reasons + [decision.reason]),
        })
    return rows


def to_json(report: ImpactReport) -> str:
    """Everything except the full order list, which goes to orders.csv (about 7,000 rows for SP)."""
    data = report.model_dump(exclude={"orders", "decisions"})
    data["traced_order"] = traced_order(report)
    return json.dumps(data, indent=2, ensure_ascii=False)


def traced_order(report: ImpactReport) -> Optional[Dict[str, Any]]:
    """One order followed from retrieval to email: the first sample email's order."""
    if not report.emails:
        return None
    order_id = report.emails[0].order_id
    index = next(i for i, o in enumerate(report.orders) if o.order_id == order_id)
    order: OrderImpact = report.orders[index]
    decision = report.decisions[index]
    return {
        "order_id": order_id,
        "items": [f"{i.item.category}, {i.item.weight_kg:.1f} kg, {i.item.volume_l:.0f} L, seller "
                  f"{i.item.seller_city}/{i.item.seller_state} to customer {i.item.customer_city}/{i.item.customer_state}"
                  + (", semantic match for the product focus" if i.item.focus_match else "") for i in order.items],
        "retrieval": report.trace[1].detail.split(";")[0] if len(report.trace) > 1 else "",
        "logistics": [f"baseline ETA {order.baseline_eta}, promised {order.promised_date}, "
                      f"new ETA {order.new_eta}"] + order.reasons,
        "decision": f"{decision.rule_id} {decision.action}: {decision.resolution}. {decision.reason}",
        "final_eta": decision.final_eta,
        "email_subject": report.emails[0].subject,
    }


def table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "_None._\n"
    head = list(rows[0])
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join("n/a" if row[h] is None else str(row[h]) for h in head) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def review_section(report: ImpactReport, written_by: str) -> str:
    return (f"## Orders flagged for human review\n\n{report.stats.get('orders_flagged_for_review', 0):,.0f} orders "
            f"were flagged by code. The most important are below. Flags never change a decision. "
            f"Notes written by: {written_by}.\n\n"
            + table([{"order": r.order_id[:8], "rule": r.rule_id, "action": r.action, "severity": r.severity,
                      "note": r.note} for r in report.review_queue]))


def to_markdown(report: ImpactReport) -> str:
    """The human-readable report, in the section order of IMPLEMENTATION_PLAN.md section 1.2."""
    out = [f"# Disruption impact report\n\n**Query:** {report.query}\n\n**Run mode:** {report.llm_mode}\n"]
    event = report.event
    if event:
        place = ", ".join(event.cities) or ", ".join(event.states)
        out.append("## How the system understood this\n\n" + f"{event.interpretation}\n\n" + table([{
            "type": event.disruption_type, "place": place, "direction": event.direction,
            "delay_days": event.delay_days, "product_focus": event.product_focus}]))
        out.append("**Assumptions:**\n\n" + "".join(f"- {a}\n" for a in report.assumptions or ["None"]))
    if report.stopped_reason:
        out.append(f"## Stopped\n\n{report.stopped_reason}\n")
        return "\n".join(out)
    s = report.stats
    by = {part: {"gemini": "Gemini", "mixed": "Gemini, some templates"}.get(src, "Template")
          for part, src in report.written_by.items()}
    out.append(f"## Executive summary\n\n_Written by: {by.get('summary', 'Template')}._\n\n{report.executive_summary}\n")
    out.append(f"## Recommended next steps\n\n_For the operations team. Written by: {by.get('recommendations', 'Template')}._\n\n"
               + "".join(f"- {step}\n" for step in report.recommendations))
    out.append("## Headline numbers\n\n" + table([{
        "affected orders": f"{s['affected_orders']:,.0f}", "items": f"{s['affected_items']:,.0f}",
        "sellers": f"{s['affected_sellers']:,.0f}", "customers": f"{s['affected_customers']:,.0f}",
        "late": f"{s['pct_late_orders']}%", "value at risk": f"R$ {s['value_at_risk_brl']:,.2f}",
        "compensation": f"R$ {s['compensation_cost_brl']:,.2f}"}]))
    out.append("## Orders by severity\n\n" + table([{"severity": k, "orders": v} for k, v in report.by_severity.items()]))
    out.append("## Mitigation plan\n\nRules are checked in order R0 to R4, and the first match decides the action. "
               "Every order's rule and reasons are in `orders.csv`.\n\n" + table(report.mitigation_plan))
    out.append(review_section(report, by.get("review_notes", "Template")))
    out.append("## Priority products\n\n" + table(report.priority_skus))
    out.append("## Most affected sellers\n\n" + table(report.top_sellers))
    out.append("## Most affected categories\n\n" + table(report.top_categories))
    out.append("## Sample customer emails\n")
    for email in report.emails:
        label = "Gemini" if email.source == "gemini" else "Template"
        out.append(f"### {email.action}: {email.subject}\n\n_Written by: {label}. Order {email.order_id}._\n\n"
                   + "\n".join(f"> {line}" if line else ">" for line in email.body.splitlines()) + "\n")
    trace = traced_order(report)
    if trace:
        out.append(f"## One order traced end to end\n\nOrder `{trace['order_id']}`\n\n"
                   + "".join(f"- **Item:** {i}\n" for i in trace["items"])
                   + f"- **Retrieval:** {trace['retrieval']}\n"
                   + "".join(f"- **Logistics:** {line}\n" for line in trace["logistics"])
                   + f"- **Decision:** {trace['decision']}\n- **Email:** {trace['email_subject']}\n")
    out.append("## Step trace\n\n" + table([{"step": t.step, "count": t.count, "ms": t.ms, "detail": t.detail}
                                            for t in report.trace]))
    out.append("**LLM notes:**\n\n" + "".join(f"- {n}\n" for n in report.llm_notes or ["No step fell back."]))
    return "\n".join(out)
