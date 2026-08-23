"""GraphRepository interface.

Traversal logic lives behind this interface so the Postgres recursive-CTE
implementation (Phase 3) can be swapped for Neo4j later without touching the
attribution engine. Bounds are mandatory — there is no unbounded BFS entry point.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.chains import DEFAULT_CHAIN
from app.schemas.graph import GraphResult


class Direction(StrEnum):
    """Edge direction to expand.

    REVERSE is required for deposit-sweep detection, which examines the inbound
    (consolidation) edges of a candidate hot wallet, not the unknown wallet.
    """

    FORWARD = "FORWARD"
    REVERSE = "REVERSE"
    BOTH = "BOTH"


@dataclass(frozen=True)
class TraversalBounds:
    """Hard bounds applied to every traversal (HARD REQUIREMENT #5).

    ``chain`` is a bound like any other: a traversal never crosses chains. Funds
    that move between chains do so through a bridge, which is a labeled endpoint
    on both sides — following the address across would fabricate an edge that
    does not exist on either ledger.
    """

    max_hops: int = 4
    min_value_wei: Decimal = Decimal(0)
    since: datetime | None = None
    until: datetime | None = None
    max_nodes: int = 500
    direction: Direction = Direction.FORWARD
    chain: str = DEFAULT_CHAIN.value


class GraphRepository(ABC):
    """Bounded graph traversal over the transaction store."""

    @abstractmethod
    async def traverse(self, root: str, bounds: TraversalBounds) -> GraphResult:
        """Expand outward from `root` within `bounds`, reporting prune metadata."""
        raise NotImplementedError

    @abstractmethod
    async def shortest_paths(
        self, source: str, target: str, bounds: TraversalBounds, limit: int = 5
    ) -> list[list[str]]:
        """Return up to `limit` bounded paths (address sequences) source->target."""
        raise NotImplementedError
