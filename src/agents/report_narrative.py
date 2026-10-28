"""Report narrative (part of step 6): the executive summary, next steps for operations, and a note per
order flagged for human review.

One Gemini call writes all three from facts computed in code, which keeps a run at five calls. Each part
is checked on its own: if it contains a number the facts did not give it, that part uses its template.
Offline, every part uses its template, built from the same facts.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from src import llm
from src.models import ImpactReport, Narrative, ReviewItem

SYSTEM_PROMPT = """You write the narrative parts of a supply chain disruption report for an operations team.
Use ONLY the facts given. Every number you write must appear in the facts exactly as written.
Do not calculate, round or invent any number, date, percentage, name or order reference.

Return three parts:
- executive_summary: 4 to 6 plain sentences in one paragraph: what happened, how many orders and sellers
  are hit, how many orders will be late and how badly, what the rules decided, and the estimated cost.
- recommendations: 3 to 5 concrete next steps for the operations team, each one sentence starting with a
  verb. Do NOT restate the mitigation plan rule by rule; the report already shows it. Say what people
  should do that the rules do not: which sellers to contact first (by their reference), where to book
  extra carrier capacity and why, what to prepare for refunds and cancellations, and the review queue.
- review_notes: one note per order listed under "Orders flagged for human review", with order_ref set to
  its 8-character reference. In one or two sentences, explain the specific risk in plain words by
  connecting its flags (for example, a customer who already waited and has a high-value order), then
  say what to check first. Never change, question or override the decided action."""

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def run(report: ImpactReport, flagged_total: int, use_llm: bool) -> Tuple[ImpactReport, List[str]]:
    """Returns the report with its narrative filled in, and notes on any part that used its template."""
    summary, recommendations = template_summary(report), template_recommendations(report, flagged_total)
    queue = [r.model_copy(update={"note": template_note(r)}) for r in report.review_queue]
    sources = {"summary": "template", "recommendations": "template", "review_notes": "template"}
    notes: List[str] = []
    if use_llm:
        facts = narrative_facts(report, flagged_total)
        allowed = numbers_in(facts)
        try:
            draft = llm.parse(SYSTEM_PROMPT, facts, Narrative, temperature=0.2)
        except llm.LLMError as error:
            draft, notes = None, [f"Summary, next steps and review notes used templates: {error}"]
        if draft:
            summary, ok = _checked(draft.executive_summary, summary, allowed, "Summary", notes)
            sources["summary"] = "gemini" if ok else "template"
            joined = "\n".join(draft.recommendations)
            if draft.recommendations and _checked(joined, "", allowed, "Next steps", notes)[1]:
                recommendations, sources["recommendations"] = [r.strip() for r in draft.recommendations], "gemini"
            queue, sources["review_notes"] = _merge_notes(queue, draft, allowed, notes)
    update = {"executive_summary": summary, "recommendations": recommendations, "review_queue": queue,
              "written_by": sources}
    return report.model_copy(update=update), notes


def _checked(text: str, fallback: str, allowed: set, part: str, notes: List[str]) -> Tuple[str, bool]:
    invented = numbers_in(text) - allowed
    if invented or not text.strip():
        notes.append(f"{part} used the template: Gemini wrote numbers not in the facts "
                     f"({', '.join(sorted(invented)) or 'empty answer'})")
        return fallback, False
    return text.strip(), True


def _merge_notes(queue: List[ReviewItem], draft: Narrative, allowed: set, notes: List[str]):
    """Match Gemini's notes to flagged orders by reference; any missing or failing note keeps its template."""
    merged, used = [], 0
    for item in queue:
        # Gemini may write "f92d5a62" or "order f92d5a62", so look for the reference inside the field.
        note = next((n.note.strip() for n in draft.review_notes if item.order_id[:8] in n.order_ref.lower()), "")
        if note and not (numbers_in(note) - allowed):
            item, used = item.model_copy(update={"note": note, "note_source": "gemini"}), used + 1
        merged.append(item)
    if used < len(queue):
        notes.append(f"{len(queue) - used} of {len(queue)} review notes used the template")
    source = "gemini" if used == len(queue) else "template" if used == 0 else "mixed"
    return merged, source


def narrative_facts(report: ImpactReport, flagged_total: int) -> str:
    lines = [summary_facts(report), "Mitigation plan (rules decided every order):"]
    for row in report.mitigation_plan:
        if row["orders"]:
            after = "cancelled" if row["avg days late after action"] is None else row["avg days late after action"]
            lines.append(f"- {row['rule']} {row['action']}: {row['orders']:,} orders; offer: {row['customer offer']}; "
                         f"average days late {row['avg days late if no action']} without action, {after} with it; "
                         f"cost R$ {row['cost (R$)']:,.2f}")
    lines.append("Most affected sellers:")
    lines += [f"- seller {s['seller']} in {s['location']}: {s['orders']:,} orders, {s['items']:,} items"
              for s in report.top_sellers[:3]]
    lines.append(f"Orders flagged for human review: {flagged_total:,} in total. The most important:")
    lines += [f"- order {r.order_id[:8]}: {r.rule_id} {r.action}, severity {r.severity}; flags: "
              f"{'; '.join(r.flags)}; check: {'; '.join(r.checks)}" for r in report.review_queue]
    return "\n".join(lines)


def summary_facts(report: ImpactReport) -> str:
    s = report.stats
    return "\n".join([
        f"Disruption: {report.event.interpretation}",
        f"Affected: {s['affected_orders']:,.0f} orders, {s['affected_items']:,.0f} items, "
        f"{s['affected_sellers']:,.0f} sellers, {s['affected_customers']:,.0f} customers",
        f"Late orders: {s['late_orders']:,.0f} ({s['pct_late_orders']}%), on average {s['avg_days_late']} days late",
        "Orders by severity: " + ", ".join(f"{k} {v:,}" for k, v in report.by_severity.items()),
        "Decisions by rule: " + ", ".join(f"{k} {v:,}" for k, v in report.by_action.items()),
        "Decisions by action: " + ", ".join(f"{k} {v:,}" for k, v in action_totals(report).items()),
        f"Value of late orders: R$ {s['value_at_risk_brl']:,.2f}",
        f"Estimated compensation cost: R$ {s['compensation_cost_brl']:,.2f}",
        "Most affected categories: " + ", ".join(c["category"].replace("_", " ") for c in report.top_categories[:3]),
    ])


def template_summary(report: ImpactReport) -> str:
    s, sev, actions = report.stats, report.by_severity, action_totals(report)
    return (f"{report.event.interpretation} It affects {s['affected_orders']:,.0f} orders "
            f"({s['affected_items']:,.0f} items) from {s['affected_sellers']:,.0f} sellers. "
            f"{s['late_orders']:,.0f} orders ({s['pct_late_orders']}%) will now miss their promised date, "
            f"on average by {s['avg_days_late']} days; {sev['CRITICAL']:,} are CRITICAL and {sev['HIGH']:,} HIGH. "
            f"The rules reroute {actions['REROUTE']:,} orders, delay {actions['DELAY']:,} with compensation and "
            f"offer cancellation on {actions['CANCEL']:,}, while {actions['MONITOR']:,} need no action. "
            f"Late orders are worth R$ {s['value_at_risk_brl']:,.2f}, and the estimated compensation cost is "
            f"R$ {s['compensation_cost_brl']:,.2f}. The most affected categories are "
            f"{', '.join(c['category'].replace('_', ' ') for c in report.top_categories[:3])}.")


def template_recommendations(report: ImpactReport, flagged_total: int) -> List[str]:
    plan = {row["rule"]: row for row in report.mitigation_plan}
    steps = []
    if report.top_sellers:
        names = ", ".join(f"seller {s['seller']} in {s['location']} ({s['orders']:,} orders)" for s in report.top_sellers[:3])
        steps.append(f"Contact the most affected sellers first about pickups and stock: {names}.")
    if plan["R3"]["orders"]:
        r = plan["R3"]
        steps.append(f"Book expedited capacity on unaffected routes for {r['orders']:,} reroutes, which cuts their "
                     f"average delay from {r['avg days late if no action']} to {r['avg days late after action']} days "
                     f"at an estimated R$ {r['cost (R$)']:,.2f}.")
    if plan["R2"]["orders"]:
        steps.append(f"Arrange special carriers for {plan['R2']['orders']:,} bulky orders that will wait, and refund "
                     f"their freight (R$ {plan['R2']['cost (R$)']:,.2f} in total).")
    if plan["R1"]["orders"]:
        steps.append(f"Confirm the {plan['R1']['orders']:,} cancellations with customers; full refunds total "
                     f"R$ {plan['R1']['cost (R$)']:,.2f}.")
    if flagged_total:
        steps.append(f"Review the {flagged_total:,} orders flagged for human review before their emails go out.")
    return steps


def template_note(item: ReviewItem) -> str:
    flags = "; ".join(item.flags)
    checks = item.checks[0] if len(item.checks) == 1 else ", ".join(item.checks[:-1]) + " and " + item.checks[-1]
    return f"{flags[0].upper()}{flags[1:]}. The {item.rule_id} {item.action} decision stands. Check {checks}."


def action_totals(report: ImpactReport) -> Dict[str, int]:
    """'R2 DELAY' and 'R4 DELAY' both count as DELAY."""
    totals = {"REROUTE": 0, "DELAY": 0, "CANCEL": 0, "MONITOR": 0}
    for key, count in report.by_action.items():
        totals[key.split()[1]] += count
    return totals


def numbers_in(text: str) -> set:
    return {n.replace(",", "") for n in NUMBER.findall(text)}
