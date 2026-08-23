"""Graph traversal contract (HARD REQUIREMENT #5: bounded traversal).

Every traversal reports whether it was pruned and why — never silent truncation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class PruneReason(StrEnum):
    MAX_HOPS = "MAX_HOPS"
    MAX_NODES = "MAX_NODES"
    MIN_VALUE = "MIN_VALUE"
    TIME_WINDOW = "TIME_WINDOW"


class PruneInfo(BaseModel):
    """Why (and whether) a bounded traversal stopped short of full expansion."""

    pruned: bool = False
    reasons: list[PruneReason] = Field(default_factory=list)
    nodes_visited: int = 0
    max_depth_reached: int = 0


class GraphNode(BaseModel):
    address: str
    depth: int
    is_labeled: bool = False
    label_name: str | None = None
    vasp_name: str | None = None
    is_contract: bool = False


class GraphEdge(BaseModel):
    tx_hash: str
    from_address: str
    to_address: str
    value_wei: Decimal
    timestamp: datetime
    asset: str = "ETH"


class GraphResult(BaseModel):
    """Nodes + edges of a bounded expansion, with prune metadata."""

    root: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    prune: PruneInfo = Field(default_factory=PruneInfo)


class LabeledPath(BaseModel):
    """Bounded paths from an unknown wallet to a specific labeled wallet."""

    target: str
    label_name: str | None = None
    vasp_name: str | None = None
    shortest_hops: int
    paths: list[list[str]] = Field(default_factory=list)
