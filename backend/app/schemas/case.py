"""Case / finding API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.enums import CaseStatus, FindingSeverity


class CaseCreate(BaseModel):
    name: str
    description: str | None = None
    investigator: str | None = None


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: CaseStatus
    investigator: str | None
    officer_id: int | None
    created_at: datetime


class FindingCreate(BaseModel):
    title: str
    description: str | None = None
    severity: FindingSeverity = FindingSeverity.INFO
    wallet_address: str | None = None
    evidence: dict[str, Any] | None = None


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    title: str
    description: str | None
    severity: FindingSeverity
    wallet_address: str | None
    evidence: dict[str, Any] | None
    created_at: datetime


class CaseDetail(CaseOut):
    findings: list[FindingOut] = Field(default_factory=list)
