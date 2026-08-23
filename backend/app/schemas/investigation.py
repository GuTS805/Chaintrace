"""Investigation API contracts.

An investigation is requested, not computed inline: ``POST /investigations``
accepts the subject and bounds and returns immediately with an id. The client
polls that id for progress and then reads the result sub-resources, all of which
are served from the frozen snapshot rather than recomputed.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.chains import Chain, is_evm, normalize_address
from app.enums import InvestigationStatus
from app.schemas.attribution import AttributionResult
from app.schemas.graph import GraphResult
from app.schemas.risk import RiskResult

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
# Base58 and Bech32 alphabets, loosely bounded. Deliberately permissive: this is
# an input-shape guard against injection and junk, not an address checksum.
_NON_EVM_ADDRESS = re.compile(r"^[a-zA-Z0-9]{16,64}$")


class InvestigationCreate(BaseModel):
    """Request to open an investigation."""

    chain: Chain = Chain.ETHEREUM
    address: str = Field(..., min_length=4, max_length=64)
    depth: int = Field(default=6, ge=1, le=8)
    min_value_wei: int = Field(default=0, ge=0)
    max_nodes: int = Field(default=2000, ge=1, le=5000)
    case_id: int | None = None
    requested_by: str | None = Field(default=None, max_length=128)

    @field_validator("address")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _check_address_shape(self) -> InvestigationCreate:
        """Reject addresses that cannot exist on the requested chain.

        Catching this here means a bad address fails fast with a 422 instead of
        becoming an investigation that traverses nothing and reports
        'insufficient evidence' — an answer that would look like a finding.
        """
        pattern = _EVM_ADDRESS if is_evm(self.chain) else _NON_EVM_ADDRESS
        if not pattern.match(self.address):
            raise ValueError(
                f"{self.address!r} is not a valid address for chain {self.chain.value}"
            )
        # Normalize once, at the boundary, so nothing downstream has to remember.
        self.address = normalize_address(self.address, self.chain)
        return self


class InvestigationOut(BaseModel):
    """Status view of an investigation. Cheap to poll."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Public reference, e.g. INV-2026-00142.")
    chain: str
    address: str
    status: InvestigationStatus
    depth: int
    max_nodes: int
    requested_by: str | None = None
    case_id: int | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    has_result: bool = False


class Methodology(BaseModel):
    """How a conclusion was produced — required for the report to be defensible."""

    model_version: str
    provider: str
    confidence_threshold: float
    traversal_bounds: dict[str, Any] = Field(default_factory=dict)
    data_timestamp: datetime | None = None
    evidence_hash: str
    snapshot_created_at: datetime


class EvidenceBundle(BaseModel):
    """The flat evidence records plus the hash that seals them."""

    investigation_id: str
    evidence_hash: str
    record_count: int
    records: list[dict[str, Any]] = Field(default_factory=list)


class InvestigationDetail(InvestigationOut):
    """Full investigation view: status plus, once complete, the frozen result."""

    attribution: AttributionResult | None = None
    risk: RiskResult | None = None
    methodology: Methodology | None = None


class InvestigationGraph(BaseModel):
    investigation_id: str
    graph: GraphResult
