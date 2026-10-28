"""Streamlit app: type a disruption, see how the system understood it, the impact and sample emails.

    streamlit run app.py

A thin layout over src/pipeline.py and src/render.py, so the app and the CLI always agree.
Works with no .env file: the Gemini toggle is then off and disabled.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import config, pipeline, render
from src.models import ImpactReport

EXAMPLES = {
    "Sao Paulo rain (outbound, 5 days)": "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days",
    "Rio Grande do Sul flood (inbound, 10 days)":
        "Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days",
}


def sidebar_and_input():
    st.title("Supply chain disruption response")
    has_key = config.LLM_MODE == "gemini"
    use_llm = st.toggle("Use Gemini", value=has_key, disabled=not has_key,
                        help=None if has_key else "No GEMINI_API_KEY found, so the app runs offline.")
    st.badge(f"Gemini ({config.GEMINI_MODEL})" if use_llm else "Offline: rule-based parser and templates",
             color="blue" if use_llm else "gray")
    columns = st.columns(len(EXAMPLES))
    for column, (label, text) in zip(columns, EXAMPLES.items()):
        if column.button(label, width="stretch"):
            st.session_state["query"] = text
    query = st.text_area("Describe the disruption", key="query", height=80,
                         placeholder="e.g. Truckers' strike in Curitiba, shipments out of the city stuck for a week")
    return query.strip(), use_llm, st.button("Assess impact", type="primary")


def understanding(report: ImpactReport) -> None:
    with st.container(border=True):
        st.subheader("How the system understood this")
        st.write(report.event.interpretation)
        e = report.event
        st.dataframe(pd.DataFrame([{"type": e.disruption_type, "place": ", ".join(e.cities or e.states),
                                    "direction": e.direction, "delay days": e.delay_days,
                                    "product focus": e.product_focus}]), hide_index=True)
        for assumption in report.assumptions:
            st.caption(f"Assumption: {assumption}")


def impact(report: ImpactReport) -> None:
    s = report.stats
    cards = st.columns(5)
    cards[0].metric("Affected orders", f"{s['affected_orders']:,.0f}")
    cards[1].metric("Sellers", f"{s['affected_sellers']:,.0f}")
    cards[2].metric("Late", f"{s['pct_late_orders']}%")
    cards[3].metric("Value at risk", f"R$ {s['value_at_risk_brl']:,.0f}")
    cards[4].metric("Compensation", f"R$ {s['compensation_cost_brl']:,.0f}")
    st.subheader("Executive summary")
    st.caption(f"Written by {written_by(report, 'summary')}")
    st.write(report.executive_summary)
    st.subheader("Recommended next steps")
    st.caption(f"For the operations team · written by {written_by(report, 'recommendations')}")
    st.markdown("\n".join(f"- {step}" for step in report.recommendations))
    left, right = st.columns(2)
    left.write("**Orders by severity**")
    left.dataframe(pd.DataFrame(report.by_severity.items(), columns=["severity", "orders"]), hide_index=True)
    right.write("**Orders by rule and action**")
    right.dataframe(pd.DataFrame(report.by_action.items(), columns=["rule and action", "orders"]), hide_index=True)
    actions_and_review(report)
    left, right = st.columns(2)
    left.write("**Most affected categories**")
    left.dataframe(pd.DataFrame(report.top_categories), hide_index=True)
    right.write("**Most affected sellers**")
    right.dataframe(pd.DataFrame(report.top_sellers), hide_index=True)
    st.write("**Priority products** (late bulky items and the best matches for the product focus)")
    st.dataframe(pd.DataFrame(report.priority_skus), hide_index=True, width="stretch")


def written_by(report: ImpactReport, part: str) -> str:
    return {"gemini": "Gemini", "mixed": "Gemini, some templates"}.get(report.written_by.get(part), "Template")


def actions_and_review(report: ImpactReport) -> None:
    st.subheader("Mitigation plan")
    st.caption("Rules are checked in order R0 to R4; the first match decides each order's action.")
    st.dataframe(pd.DataFrame(report.mitigation_plan), hide_index=True, width="stretch")
    st.subheader("Orders flagged for human review")
    st.caption(f"{report.stats['orders_flagged_for_review']:,.0f} orders flagged by code; the most important are "
               f"below. Flags never change a decision · notes written by {written_by(report, 'review_notes')}")
    st.dataframe(pd.DataFrame([{"order": r.order_id[:8], "rule": r.rule_id, "action": r.action,
                                "severity": r.severity, "note": r.note, "written by": r.note_source}
                               for r in report.review_queue]), hide_index=True, width="stretch")


def emails_and_trace(report: ImpactReport) -> None:
    st.subheader("Sample customer emails")
    for email in report.emails:
        with st.container(border=True):
            st.caption(f"{email.action} · written by {'Gemini' if email.source == 'gemini' else 'Template'}")
            st.write(f"**{email.subject}**")
            st.text(email.body)
    trace = render.traced_order(report)
    if trace:
        with st.expander("One order traced end to end", expanded=True):
            st.json(trace)
    with st.expander("Step trace"):
        st.dataframe(pd.DataFrame([t.model_dump() for t in report.trace]), hide_index=True, width="stretch")
    with st.expander("Every affected order, with its reasons"):
        st.dataframe(pd.DataFrame(render.order_rows(report)), hide_index=True, width="stretch")
    files = st.columns(3)
    files[0].download_button("report.md", render.to_markdown(report), "report.md")
    files[1].download_button("report.json", render.to_json(report), "report.json")
    files[2].download_button("orders.csv", render.to_csv(report), "orders.csv")
    saved_to = st.session_state.get("saved_to")
    if saved_to:
        st.caption(f"Also saved to {saved_to.relative_to(config.ROOT)}/")


def main() -> None:
    st.set_page_config(page_title="Disruption response", layout="wide")
    query, use_llm, clicked = sidebar_and_input()
    if clicked and query:
        with st.spinner("Assessing the disruption..."):
            # Kept in the session, not a cache: a download click reruns the page without spending
            # Gemini quota, and clicking "Assess impact" again always makes a fresh attempt.
            report = pipeline.run(query, n_emails=config.SAMPLE_EMAILS, use_llm=use_llm)
            folder = render.run_folder(report, config.OUTPUT_DIR)
            render.write_all(report, folder)   # saved on disk too, so a run is never lost
            st.session_state["report"], st.session_state["saved_to"] = report, folder
    report = st.session_state.get("report")
    if report is None:
        return
    for note in report.llm_notes:
        st.warning(note)
    if report.event:
        understanding(report)
    if report.stopped_reason:
        st.error(report.stopped_reason)
        return
    impact(report)
    emails_and_trace(report)


main()
