"""Command-line interface: run one disruption scenario and print or save the report.

    python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
    python cli.py "<query>" --emails 3 --out samples/sp_rain

All logic lives in src/; this file only parses arguments and prints.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src import config, pipeline, render


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess a supply chain disruption on the Olist orders.")
    parser.add_argument("query", help="the disruption in plain English")
    parser.add_argument("--offline", action="store_true", help="rule-based parser and templates, no Gemini calls")
    parser.add_argument("--emails", type=int, default=config.SAMPLE_EMAILS, help="sample emails to write (default 3)")
    parser.add_argument("--out", type=Path, help="folder for report.md, report.json and orders.csv")
    args = parser.parse_args()

    report = pipeline.run(args.query, n_emails=args.emails, use_llm=False if args.offline else None)
    print(f"Run mode: {report.llm_mode}\n")
    if report.event:
        print(f"Understood as: {report.event.interpretation}")
        for assumption in report.assumptions:
            print(f"  - {assumption}")
    if report.stopped_reason:
        print(f"\nStopped: {report.stopped_reason}")
        return
    s = report.stats
    print(f"\nAffected: {s['affected_orders']:,.0f} orders, {s['affected_items']:,.0f} items, "
          f"{s['affected_sellers']:,.0f} sellers")
    print(f"Late: {s['late_orders']:,.0f} orders ({s['pct_late_orders']}%), on average {s['avg_days_late']} days")
    print(f"Value at risk: R$ {s['value_at_risk_brl']:,.2f}   Compensation: R$ {s['compensation_cost_brl']:,.2f}")
    print("By severity: " + ", ".join(f"{k} {v:,}" for k, v in report.by_severity.items()))
    print("\nMitigation plan (first matching rule wins):")
    for row in report.mitigation_plan:
        after = "cancelled" if row["avg days late after action"] is None else row["avg days late after action"]
        print(f"  {row['rule']} {row['action']:8} {row['orders']:>6,} orders | {row['customer offer']} | "
              f"days late {row['avg days late if no action']} -> {after} | "
              f"cost R$ {row['cost (R$)']:,.2f}")
    print(f"\nSummary: {report.executive_summary}")
    print("\nNext steps for operations:")
    for step in report.recommendations:
        print(f"  - {step}")
    print(f"\nFlagged for human review: {report.stats['orders_flagged_for_review']:,.0f} orders. Top one:")
    if report.review_queue:
        top = report.review_queue[0]
        print(f"  {top.order_id[:8]} {top.rule_id} {top.action}: {top.note}")
    if report.emails:
        email = report.emails[0]
        print(f"\n--- First email ({email.action}, written by {email.source}) ---\nSubject: {email.subject}\n\n{email.body}")
    for note in report.llm_notes:
        print(f"\nNote: {note}")
    if args.out:
        paths = render.write_all(report, args.out)
        print("\nSaved " + ", ".join(str(p) for p in paths))


if __name__ == "__main__":
    main()
