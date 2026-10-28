"""Retrieval Agent (step 2): finds every order item the disruption touches, then ranks them by meaning.

Two searches on the same Chroma collection and the same filter:
  A. collection.get(where=...)  returns EVERY matching item, so counts are complete.
  B. collection.query(...)      ranks those items against the product focus and marks the top matches.
No LLM: the filter is built in code and the embeddings run locally.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src import config
from src.build_index import open_collection
from src.models import AffectedItem, DisruptionEvent

SIDES = {"outbound": ["seller"], "inbound": ["customer"], "both": ["seller", "customer"]}


def run(event: DisruptionEvent) -> List[AffectedItem]:
    collection = open_collection()
    where = build_where(event)
    found = collection.get(where=where, include=["metadatas"])
    items = [AffectedItem(id=item_id, **meta) for item_id, meta in zip(found["ids"], found["metadatas"])]
    if items:
        hits = collection.query(
            query_texts=[event.product_focus],
            where=where,   # rank only inside the affected set
            n_results=min(config.FOCUS_TOP_K, len(items)),
            include=[],
        )
        focus_ids = set(hits["ids"][0])
        for item in items:
            item.focus_match = item.id in focus_ids
    return sorted(items, key=lambda item: item.id)   # fixed order, so runs are repeatable


def build_where(event: DisruptionEvent) -> Dict[str, Any]:
    """Outbound filters on where the seller is, inbound on where the customer is, both on either.

    Cities are used instead of states when the event names any.
    """
    field, values = ("city", event.cities) if event.cities else ("state", event.states)
    clauses = [{f"{side}_{field}": {"$in": values}} for side in SIDES[event.direction]]
    return clauses[0] if len(clauses) == 1 else {"$or": clauses}
