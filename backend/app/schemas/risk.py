"""Risk schema. Risk and VASP attribution are separate, independently computed
values (conflating them is a correctness bug) — this is NOT part of
AttributionResult."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskIndicator(BaseModel):
    category: str
    description: str
    address: str
    hops: int
    contribution: float


class RiskResult(BaseModel):
    wallet: str
    score: float = Field(..., ge=0.0, le=1.0)
    level: RiskLevel
    indicators: list[RiskIndicator] = Field(default_factory=list)
