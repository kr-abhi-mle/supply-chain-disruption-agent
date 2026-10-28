"""Data contracts passed between agents. Plain Pydantic models with no logic."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Action = Literal["MONITOR", "CANCEL", "DELAY", "REROUTE"]


class DisruptionEvent(BaseModel):
    """LLM-facing. Filled by the parser, then validated and clamped in code."""
    disruption_type: Literal["weather", "strike", "infrastructure", "port_closure", "other"]
    states: List[str]
    cities: List[str]
    direction: Literal["outbound", "inbound", "both"]
    delay_days: int
    product_focus: str
    interpretation: str


class ParsedQuery(BaseModel):
    """What the parser hands the pipeline: the validated event and how it was produced."""
    event: DisruptionEvent
    source: Literal["gemini", "rules"]
    assumptions: List[str]          # every default or reading the system chose, shown to the user
    fallback_note: str = ""         # set when Gemini was asked but the rules had to take over


class AffectedItem(BaseModel):
    """One order item from the vector store. Field names follow docs/DATA_CONTRACT.md."""
    id: str
    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    customer_id: str
    order_status: str
    purchase_date: str
    promised_date: str
    baseline_eta: str
    seller_city: str
    seller_state: str
    customer_city: str
    customer_state: str
    category: str
    category_pt: str
    weight_kg: float
    volume_l: float
    is_bulky: bool
    is_time_sensitive: bool
    price: float
    freight_value: float
    focus_match: bool = False


class ItemImpact(BaseModel):
    item: AffectedItem
    buffer_days: int
    new_eta: str
    days_late: int
    severity: Severity
    reasons: List[str]


class OrderImpact(BaseModel):
    order_id: str
    customer_city: str
    customer_state: str
    promised_date: str
    baseline_eta: str
    new_eta: str
    days_late: int
    severity: Severity
    has_bulky: bool
    has_time_sensitive: bool
    focus_match: bool
    order_value: float
    freight_total: float
    items: List[ItemImpact]
    reasons: List[str]


class Decision(BaseModel):
    order_id: str
    action: Action
    rule_id: str
    resolution: str
    final_eta: Optional[str]   # None when the order is cancelled
    compensation_brl: float
    reason: str


class EmailContent(BaseModel):
    """LLM-facing email shape."""
    subject: str
    body: str


class EmailDraft(BaseModel):
    order_id: str
    action: Action
    subject: str
    body: str
    source: Literal["gemini", "template"]


class ReviewNote(BaseModel):
    """LLM-facing: why a person should look at one flagged order."""
    order_ref: str
    note: str


class Narrative(BaseModel):
    """LLM-facing: the three prose parts of the report, written in one call from computed facts."""
    executive_summary: str
    recommendations: List[str]
    review_notes: List[ReviewNote]


class ReviewItem(BaseModel):
    """An order flagged for human review. Flags and checks come from code; the note explains them."""
    order_id: str
    rule_id: str
    action: Action
    severity: Severity
    flags: List[str]
    checks: List[str]
    note: str = ""
    note_source: Literal["gemini", "template"] = "template"


class TraceStep(BaseModel):
    step: str
    detail: str
    count: int = 0
    ms: int = 0


class ImpactReport(BaseModel):
    query: str
    llm_mode: str = "offline"   # e.g. "gemini (gemini-3.6-flash)" or "offline"
    llm_notes: List[str] = Field(default_factory=list)   # which LLM steps fell back to code, and why
    event: Optional[DisruptionEvent] = None
    stopped_reason: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    stats: Dict[str, float] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_action: Dict[str, int] = Field(default_factory=dict)
    mitigation_plan: List[Dict[str, Any]] = Field(default_factory=list)   # one row per rule R0 to R4
    top_categories: List[Dict[str, Any]] = Field(default_factory=list)
    top_sellers: List[Dict[str, Any]] = Field(default_factory=list)
    priority_skus: List[Dict[str, Any]] = Field(default_factory=list)
    orders: List[OrderImpact] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    emails: List[EmailDraft] = Field(default_factory=list)
    executive_summary: str = ""
    recommendations: List[str] = Field(default_factory=list)   # next steps for the operations team
    review_queue: List[ReviewItem] = Field(default_factory=list)
    written_by: Dict[str, str] = Field(default_factory=dict)   # e.g. {"summary": "gemini"}
    trace: List[TraceStep] = Field(default_factory=list)
