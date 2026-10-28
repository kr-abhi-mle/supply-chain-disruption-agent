"""Customer Success Agent (step 5): one empathetic email for an affected order.

Gemini only handles tone. Every fact comes from code, and a check confirms the email states the
final date (or the refund). Offline, or if Gemini fails twice, a hand-written template with the
same facts is used. Offline reviewers see only templates, so they read as finished emails.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, Tuple

from src import config, llm
from src.models import Decision, DisruptionEvent, EmailContent, EmailDraft, OrderImpact

SYSTEM_PROMPT = """You write short, empathetic emails to customers of a Brazilian online marketplace.
Use ONLY the facts provided. Never invent dates, amounts, offers, names, links or phone numbers.
Copy dates and amounts exactly as they are written in the facts.
Structure: a brief apology, the cause in one sentence, the new delivery date or the refund, the
resolution we offer, and the one next step given in the facts. Under 150 words, in English.
Start with "Hello," on its own line, because we do not know the customer's name.
Write two or three short paragraphs separated by blank lines.
End with "Thank you for your patience," and then "Customer Care Team", each on its own line."""

CAUSES = {
    "weather": "severe weather", "strike": "a transport strike", "port_closure": "a port disruption",
    "infrastructure": "a road and bridge closure", "other": "a transport disruption",
}
NEXT_STEPS = {
    "R1": "Reply to this email to confirm the cancellation, or to keep the order if you still want it.",
    "R2": "You do not need to do anything. The refund is automatic.",
    "R3": "You do not need to do anything. The new route is already booked.",
    "R4": "You do not need to do anything. The voucher is already in your account.",
}


def run(order: OrderImpact, decision: Decision, event: DisruptionEvent, use_llm: bool) -> Tuple[EmailDraft, str]:
    """Returns the email and a note for the report ("" when nothing fell back)."""
    facts = order_facts(order, decision, event)
    if not use_llm:
        return template(decision, facts), ""
    must_contain = facts["final_date"] if decision.final_eta else "refund"
    for _attempt in (1, 2):
        try:
            email = llm.parse(SYSTEM_PROMPT, facts_text(facts), EmailContent, temperature=0.4)
        except llm.LLMError as error:   # Gemini is down: retrying here would only repeat the wait
            return template(decision, facts), f"Email for order {facts['ref']} used the template: {error}"
        if must_contain.lower() in email.body.lower():
            return EmailDraft(order_id=order.order_id, action=decision.action, subject=email.subject,
                              body=email.body.strip(), source="gemini"), ""
    return template(decision, facts), f"Email for order {facts['ref']} missed '{must_contain}' twice, used the template"


def city_name(city: str) -> str:
    """'caxias do sul' -> 'Caxias do Sul'. Olist stores cities lowercase."""
    small = {"do", "da", "de", "dos", "das", "e"}
    return " ".join(w if w in small else w.capitalize() for w in city.split())


def pretty_date(iso: str) -> str:
    day = date.fromisoformat(iso)
    return f"{day.day} {day.strftime('%B %Y')}"


def order_facts(order: OrderImpact, decision: Decision, event: DisruptionEvent) -> Dict[str, str]:
    categories = sorted({i.item.category.replace("_", " ") for i in order.items})
    place = ", ".join(city_name(c) for c in event.cities) or ", ".join(config.BRAZIL_STATES[s] for s in event.states)
    side = {"outbound": "freight leaving", "inbound": "deliveries into", "both": "freight in and out of"}
    return {
        "order_id": order.order_id, "ref": order.order_id[:8], "action": decision.action,
        "city": f"{city_name(order.customer_city)}, {order.customer_state}",
        "items": " and ".join(categories),
        "purchase_date": pretty_date(order.items[0].item.purchase_date),
        "promised_date": pretty_date(order.promised_date),
        "final_date": pretty_date(decision.final_eta) if decision.final_eta else "",
        "cause": f"{CAUSES[event.disruption_type]} affecting {side[event.direction]} {place}",
        "resolution": decision.resolution, "amount": f"R$ {decision.compensation_brl:.2f}",
        "rule_id": decision.rule_id, "next_step": NEXT_STEPS.get(decision.rule_id, ""),
    }


def facts_text(f: Dict[str, str]) -> str:
    # A cancelled order has no new date; saying so as an instruction keeps it out of the email text.
    final = (f"New delivery date: {f['final_date']}\n" if f["final_date"]
             else "Instruction: the order will not be delivered late; do not mention any new delivery date.\n")
    return (f"Order reference: {f['ref']}\nCustomer city: {f['city']}\nItems: {f['items']}\n"
            f"Purchased on: {f['purchase_date']}\nOriginally promised delivery: {f['promised_date']}\n"
            f"Cause: {f['cause']}\nWhat we are doing: {f['resolution']}\n{final}"
            f"Next step for the customer: {f['next_step']}")


TEMPLATES = {
    "R1": ("Your order {ref}: free cancellation and full refund",
           "Because of {cause}, your order {ref} ({items}, bought on {purchase_date}) cannot reach {city} "
           "in time. These items lose their value when they arrive late, so we would rather not keep you "
           "waiting.\n\nYou can cancel at no cost and receive a full refund of {amount}."),
    "R2": ("Your order {ref} is delayed, and your freight is refunded",
           "Because of {cause}, your order {ref} ({items}, bought on {purchase_date}) will miss its promised "
           "date of {promised_date}. Large items like yours need special carriers, so we are keeping it on "
           "its current route.\n\nIt should now arrive in {city} by {final_date}. To make up for the wait, "
           "we have refunded your freight charge of {amount}."),
    "R3": ("Your order {ref} is on a faster route",
           "Because of {cause}, your order {ref} ({items}, bought on {purchase_date}) was at risk of missing "
           "its promised date of {promised_date}.\n\nWe have moved it to an unaffected route with free "
           "expedited shipping, at no cost to you. It should now arrive in {city} by {final_date}."),
    "R4": ("Your order {ref} is running a little late",
           "Because of {cause}, your order {ref} ({items}, bought on {purchase_date}) will arrive a little "
           "after its promised date of {promised_date}. It should now reach {city} by {final_date}.\n\n"
           "As a thank you for your patience, we have added a voucher of {amount} to your account for your "
           "next order."),
}


def template(decision: Decision, f: Dict[str, str]) -> EmailDraft:
    subject, middle = TEMPLATES[decision.rule_id]
    body = (f"Hello,\n\nWe are sorry for the trouble with your order. {middle.format(**f)}\n\n"
            f"{f['next_step']}\n\nThank you for your patience,\nCustomer Care Team")
    return EmailDraft(order_id=f["order_id"], action=decision.action, subject=subject.format(**f),
                      body=body, source="template")
