"""All settings in one place: paths, model names, thresholds and business policies.

Change behavior here, not inside the agents, so every policy is easy to find and review.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Gemini (language tasks: parsing the disruption, emails, the executive summary).
# The key is optional. Without it the system runs offline: rule-based parser and templates.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY == "your-key-here":   # the placeholder copied from .env.example is not a key
    GEMINI_API_KEY = ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# Tried in order when the main model is rate-limited or down. Free-tier quotas are per model,
# so a second model usually still has quota when the first has run out.
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",") if m.strip()]
GEMINI_THINKING_LEVEL = "low"   # extraction and short emails need little thinking; low is about 2x faster
LLM_MODE = os.getenv("LLM_MODE", "").strip().lower() or ("gemini" if GEMINI_API_KEY else "offline")
if not GEMINI_API_KEY:
    LLM_MODE = "offline"        # "gemini" without a key cannot work, so never try
LLM_TIMEOUT_S = 30
LLM_MAX_ATTEMPTS = 3            # the free tier often answers 503 "high demand", so retry
LLM_RETRY_WAITS_S = [2, 4]      # wait before attempt 2 and attempt 3

# Embeddings: Chroma's built-in all-MiniLM-L6-v2 model runs locally (no API key, no cost).
# A local model keeps the index free, needs no key and works offline.
EMBED_MODEL = "all-MiniLM-L6-v2"

# Paths
RAW_DIR = ROOT / "raw_data"
PROCESSED_CSV = ROOT / "data" / "processed" / "order_items.csv"
CHROMA_DIR = ROOT / "data" / "chroma"
OUTPUT_DIR = ROOT / "outputs"   # every app run is saved here, one folder per run
COLLECTION = "order_items"

# Data subset
SUBSET_SIZE = 10_000
EXCLUDED_STATUSES = ["canceled", "unavailable"]

# Product rules (about the top 5% of items are bulky)
BULKY_KG = 10.0
BULKY_L = 60.0
TIME_SENSITIVE_CATEGORIES = [
    "flowers", "food", "food_drink", "drinks", "party_supplies", "christmas_supplies",
]

# Severity: days late needed to reach each level (0 days late is LOW)
SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
MEDIUM_FROM_DAYS = 1
HIGH_FROM_DAYS = 3
CRITICAL_FROM_DAYS = 7

# Mitigation policy
REROUTE_EXTRA_DAYS = 2   # an alternate route adds 2 days instead of the full delay
VOUCHER_PCT = 10         # voucher for MEDIUM delays, percent of order value
REROUTE_COST_FACTOR = 1.0  # expedited shipping is estimated at the original freight, paid again

# Parser defaults
DEFAULT_DELAY_DAYS = 3
MAX_DELAY_DAYS = 30
DEFAULT_PRODUCT_FOCUS = "heavy bulky items such as furniture and home goods"
# States whose name is also a big city. They are read as the state unless the query says "city".
CITY_STATE_NAMES = ["SP", "RJ"]
BRAZIL_STATES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapa", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceara", "DF": "Distrito Federal", "ES": "Espirito Santo", "GO": "Goias",
    "MA": "Maranhao", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Para", "PB": "Paraiba", "PR": "Parana", "PE": "Pernambuco", "PI": "Piaui",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondonia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "Sao Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

# Human review: unusual orders are flagged for a person to check. Flags never change an action.
REVIEW_HIGH_VALUE_BRL = 500   # about the top 2% of late orders by value
REVIEW_LATE_DAYS = 3          # flag orders this late before the disruption, or still this late after a reroute
REVIEW_QUEUE_SIZE = 5         # flagged orders shown with a note in the report

# Output
SAMPLE_EMAILS = 3
FOCUS_TOP_K = 50
