"""Rule-based disruption parser: the offline path of step 1, and the fallback when Gemini fails.

It reads the same fields Gemini does, using keyword tables and the city names in the order data.
disruption_parser.py validates both paths with the same code, so they produce the same event.
"""
from __future__ import annotations

import csv
import math
import re
from functools import lru_cache
from typing import FrozenSet, List, Optional, Tuple

from src import config
from src.data_prep import normalize_city
from src.models import DisruptionEvent

TYPE_KEYWORDS = [   # checked in order, first match wins; each word matches from the start of a word
    ("weather", ["rain", "flood", "storm", "hurricane", "snow", "landslide", "weather"]),
    ("strike", ["strike", "protest", "walkout"]),
    ("port_closure", [r"ports?\b", "harbor", "harbour"]),   # whole word, so "Porto Alegre" is not a port
    ("infrastructure", ["road", "bridge", "highway", "tunnel", "rail"]),
]
BOTH_PHRASES = ["both ways", "both directions", "in and out", "to and from", "inbound and outbound"]
OUTBOUND_WORDS = ["leaving", "out of", "from", "departing", "outbound", "outgoing"]
INBOUND_WORDS = ["into", "arriving", "deliveries to", "inbound", "incoming"]
NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30,
}
DURATION = re.compile(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")[\s-]+(hour|day|week)s?\b")


def parse_with_rules(query: str) -> DisruptionEvent:
    text = normalize_city(query)   # lowercase, no accents: "São Paulo" -> "sao paulo"
    states, cities = find_places(query, text)
    return DisruptionEvent(
        disruption_type=find_type(text),
        states=states,
        cities=cities,
        direction=find_direction(text) or "outbound",
        delay_days=find_days(text) or config.DEFAULT_DELAY_DAYS,
        product_focus=config.DEFAULT_PRODUCT_FOCUS,
        interpretation="",   # written by disruption_parser for both paths
    )


def find_type(text: str) -> str:
    for disruption_type, words in TYPE_KEYWORDS:
        if any(re.search(rf"\b{word}", text) for word in words):
            return disruption_type
    return "other"


def find_direction(text: str) -> Optional[str]:
    """None when the query gives no direction, so the caller can record the default."""
    if any(phrase in text for phrase in BOTH_PHRASES):
        return "both"
    outbound = any(re.search(rf"\b{word}\b", text) for word in OUTBOUND_WORDS)
    inbound = any(re.search(rf"\b{word}\b", text) for word in INBOUND_WORDS)
    if outbound and inbound:
        return "both"   # "from X into Y" names both ends; over-notifying beats missing customers
    return "outbound" if outbound else "inbound" if inbound else None


def find_days(text: str) -> Optional[int]:
    match = DURATION.search(text)
    if not match:
        return None
    amount = int(match.group(1)) if match.group(1).isdigit() else NUMBER_WORDS[match.group(1)]
    unit = match.group(2)
    if unit == "hour":
        return max(1, math.ceil(amount / 24))
    return amount * 7 if unit == "week" else amount


def find_places(query: str, text: str) -> Tuple[List[str], List[str]]:
    """States first, then cities in what is left, so "Rio Grande do Sul" is never the city rio grande."""
    states, cities = [], []
    for code, name in sorted(config.BRAZIL_STATES.items(), key=lambda kv: -len(kv[1])):
        name = name.lower()
        if not re.search(rf"\b{name}\b", text):
            continue
        if name in known_cities() and says_city(text, name):
            cities.append(name)   # "city of Sao Paulo" or "Sao Paulo city" means the city
        else:
            states.append(code)
        text = re.sub(rf"\b{name}\b", " ", text)
    # Codes count only as uppercase whole words, so the words "to" or "es" are not read as states.
    for code in re.findall(r"\b[A-Z]{2}\b", query):
        if code in config.BRAZIL_STATES and code not in states:
            states.append(code)
        text = re.sub(rf"\b{code.lower()}\b", " ", text)
    for city in sorted(known_cities(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", text):
            cities.append(city)
            text = re.sub(rf"\b{re.escape(city)}\b", " ", text)
    return states, cities


def says_city(text: str, name: str) -> bool:
    return bool(re.search(rf"\bcity of {name}\b|\b{name} city\b", text))


@lru_cache(maxsize=1)
def known_cities() -> FrozenSet[str]:
    """Seller and customer city names from the order data (already lowercase, no accents)."""
    with open(config.PROCESSED_CSV, newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        names = {row[col] for row in rows for col in ("seller_city", "customer_city")}
    return frozenset(name for name in names if len(name) > 2)   # drops junk like "sp"
