"""Investigation snapshot API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.attribution import AttributionResult
from app.schemas.graph import GraphResult
from app.schemas.risk import RiskResult


class InvestigationOut(BaseModel):
    """The full frozen record — never recomputed on read."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_address: str
    chain: str
    officer_id: int
    model_version: str
    provider_source: str
    traversal_max_hops: int
    traversal_max_nodes: int
    traversal_min_value_wei: Decimal
    attribution: AttributionResult
    risk: RiskResult
    graph: GraphResult | None
    created_at: datetime


class InvestigationSummary(BaseModel):
    """A quick-glance row for listing — the verdict without the full payload."""

    id: int
    wallet_address: str
    chain: str
    officer_id: int
    model_version: str
    created_at: datetime
    top_vasp: str | None = None
    top_probability: float | None = None
    insufficient_evidence: bool = False
    risk_level: str | None = None
    flagged: bool = False
