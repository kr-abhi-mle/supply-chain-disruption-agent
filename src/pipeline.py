"""Orchestrator: runs the six agents in a fixed order and records a trace of each step.

  1. disruption_parser   query -> DisruptionEvent         (Gemini, or rules offline)
  2. retrieval_agent     event -> affected items          (Chroma filter + local semantic ranking)
  3. logistics_analyst   items -> order impacts           (code)
  4. mitigation_agent    impacts -> decisions             (code, rules R0 to R4)
  5. customer_success    sample orders -> emails          (Gemini, or templates offline)
  6. report_writer       everything -> ImpactReport       (code, plus a Gemini or template summary)

Once any Gemini step falls back, later steps skip Gemini, so an outage costs one retry cycle, not five.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from src import config, llm
from src.agents import (customer_success, disruption_parser, logistics_analyst,
                        mitigation_agent, report_writer, retrieval_agent)
from src.models import Decision, DisruptionEvent, EmailDraft, ImpactReport, OrderImpact, TraceStep

EMAIL_ACTIONS = ["CANCEL", "REROUTE", "DELAY"]   # one sample email per action type, in this order


def run(query: str, n_emails: int = config.SAMPLE_EMAILS, use_llm: Optional[bool] = None) -> ImpactReport:
    use_llm = config.LLM_MODE == "gemini" if use_llm is None else use_llm
    llm.reset()
    report = ImpactReport(query=query, llm_mode=f"gemini ({config.GEMINI_MODEL})" if use_llm else "offline")

    def step(name: str, started: float, detail: str, count: int = 0) -> float:   # returns the next start time
        report.trace.append(TraceStep(step=name, detail=detail, count=count, ms=int((time.time() - started) * 1000)))
        return time.time()

    def fell_back(*notes: str) -> None:
        nonlocal use_llm
        for note in filter(None, notes):
            report.llm_notes.append(note)
            use_llm = False   # Gemini is struggling: skip it for the rest of the run

    started = time.time()
    parsed = disruption_parser.run(query, use_llm)
    fell_back(parsed.fallback_note)
    report.event, report.assumptions = parsed.event, parsed.assumptions
    started = step("1. Parse disruption", started, f"{parsed.event.interpretation} (parsed by {parsed.source})")
    if not parsed.event.states and not parsed.event.cities:
        report.stopped_reason = "No Brazilian city or state was found in the query. Name a state or city and try again."
        return report

    items = retrieval_agent.run(parsed.event)
    started = step("2. Retrieve affected items", started, f"filter {retrieval_agent.build_where(parsed.event)}; "
                   f"{sum(i.focus_match for i in items)} best matches for '{parsed.event.product_focus}'", len(items))
    if not items:
        report.stopped_reason = "No orders in the data ship through the affected area."
        return report

    report.orders = logistics_analyst.run(items, parsed.event.delay_days)
    late = sum(o.days_late > 0 for o in report.orders)
    started = step("3. Analyse impact", started, f"{late} of {len(report.orders)} orders become late", len(report.orders))

    report.decisions = mitigation_agent.run(report.orders, parsed.event.delay_days)
    started = step("4. Decide actions", started, "rules R0 to R4, first match wins", len(report.decisions))

    report.emails, notes = write_emails(report, parsed.event, n_emails, use_llm)
    fell_back(*notes)
    sources = ", ".join(sorted({e.source for e in report.emails})) or "none"
    started = step("5. Write customer emails", started, f"written by {sources}", len(report.emails))

    report, notes = report_writer.run(report, items, use_llm)
    fell_back(*notes)
    step("6. Write report", started, f"Gemini calls {llm.USAGE['calls']}, tokens {llm.USAGE['tokens']}")
    if llm.MODELS_USED:   # name the models that really answered, which may include a fallback model
        report.llm_mode = f"gemini ({', '.join(llm.MODELS_USED)})"
    report.llm_notes = llm.NOTES + report.llm_notes
    return report


def write_emails(report: ImpactReport, event: DisruptionEvent, n_emails: int,
                 use_llm: bool) -> Tuple[List[EmailDraft], List[str]]:
    """Sample emails; after the first fallback the rest use templates without calling Gemini."""
    emails, notes = [], []
    for order, decision in pick_email_orders(report.orders, report.decisions, n_emails):
        email, note = customer_success.run(order, decision, event, use_llm and not notes)
        emails.append(email)
        if note:
            notes.append(note)
    return emails, notes


def pick_email_orders(orders: List[OrderImpact], decisions: List[Decision], n: int):
    """The most severe order of each action type, ties broken by order ID, so samples are repeatable.

    Orders that were on time before the disruption come first: an order already weeks late in the
    real data is not a fair example of what this disruption does.
    """
    rank = {level: i for i, level in enumerate(config.SEVERITY_ORDER)}

    def priority(pair):
        order = pair[0]
        already_late = any(i.buffer_days < 0 for i in order.items)
        return already_late, -rank[order.severity], -order.days_late, order.order_id

    picked = []
    for action in EMAIL_ACTIONS:
        pairs = [(o, d) for o, d in zip(orders, decisions) if d.action == action]
        if pairs:
            picked.append(min(pairs, key=priority))
    return picked[:n]
