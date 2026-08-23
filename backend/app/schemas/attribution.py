"""Attribution result contract (HARD REQUIREMENT #1 and #2).

Every attribution returns structured, human-readable evidence — never a bare
number — and the system can explicitly decline to attribute a wallet.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import SignalType


class Evidence(BaseModel):
    """One concrete, traceable piece of on-chain evidence for a candidate."""

    model_config = ConfigDict(from_attributes=True)

    signal_type: SignalType
    description: str = Field(
        ..., description="Human-readable; shown verbatim in the UI."
    )
    weight: float = Field(..., description="Contribution of this signal to the score.")
    tx_hashes: list[str] = Field(default_factory=list)
    timestamps: list[datetime] = Field(default_factory=list)


class VaspCandidate(BaseModel):
    """A candidate VASP with its calibrated probability and evidence chain."""

    vasp_name: str
    probability: float = Field(..., ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)


class AttributionResult(BaseModel):
    """Top-level attribution response.

    - `insufficient_evidence=True` -> no candidate cleared the confidence floor;
      `explanation` says why. This is a first-class, expected outcome.
    - `ambiguous=True` -> multiple candidates are credible but no single one
      dominates (distinct from insufficient evidence; see design note in README).
    """

    candidates: list[VaspCandidate] = Field(default_factory=list)
    insufficient_evidence: bool = False
    ambiguous: bool = False
    explanation: str | None = None
    confidence_threshold: float
    model_version: str
