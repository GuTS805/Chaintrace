"""Exchange deposit-cluster schema (co-spend / behavioral grouping)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClusterOut(BaseModel):
    id: int
    name: str
    heuristic: str
    members: list[str] = Field(default_factory=list)
    size: int = 0
