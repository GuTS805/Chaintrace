"""Graph traversal + path-extraction endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_graph_repository
from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository
from app.schemas.graph import GraphResult, LabeledPath

router = APIRouter(prefix="/wallets", tags=["graph"])


def _bounds(
    depth: int,
    min_value: int,
    since: datetime | None,
    until: datetime | None,
    direction: Direction,
    max_nodes: int,
) -> TraversalBounds:
    return TraversalBounds(
        max_hops=depth,
        min_value_wei=Decimal(min_value),
        since=since,
        until=until,
        max_nodes=max_nodes,
        direction=direction,
    )


@router.get("/{address}/graph", response_model=GraphResult)
async def wallet_graph(
    address: str,
    depth: int = Query(4, ge=1, le=8, description="Max hops from the root wallet."),
    min_value: int = Query(0, ge=0, description="Minimum edge value in wei."),
    since: datetime | None = Query(None, description="Only edges at/after this time."),
    until: datetime | None = Query(None, description="Only edges at/before this time."),
    direction: Direction = Query(Direction.FORWARD),
    max_nodes: int = Query(500, ge=1, le=5000),
    repo: SqlGraphRepository = Depends(get_graph_repository),
) -> GraphResult:
    """Bounded neighborhood of a wallet with node/edge and prune metadata."""
    bounds = _bounds(depth, min_value, since, until, direction, max_nodes)
    return await repo.traverse(address, bounds)


@router.get("/{address}/paths-to-labeled", response_model=list[LabeledPath])
async def paths_to_labeled(
    address: str,
    depth: int = Query(5, ge=1, le=8),
    min_value: int = Query(0, ge=0),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    direction: Direction = Query(Direction.FORWARD),
    max_nodes: int = Query(500, ge=1, le=5000),
    limit_per_target: int = Query(3, ge=1, le=20),
    repo: SqlGraphRepository = Depends(get_graph_repository),
) -> list[LabeledPath]:
    """Extract bounded paths from an unknown wallet to each reachable labeled wallet."""
    bounds = _bounds(depth, min_value, since, until, direction, max_nodes)
    graph = await repo.traverse(address, bounds)

    results: list[LabeledPath] = []
    for node in graph.nodes:
        if not node.is_labeled or node.depth == 0:
            continue
        paths = await repo.shortest_paths(
            address, node.address, bounds, limit=limit_per_target
        )
        if not paths:
            continue
        results.append(
            LabeledPath(
                target=node.address,
                label_name=node.label_name,
                vasp_name=node.vasp_name,
                shortest_hops=min(len(p) - 1 for p in paths),
                paths=paths,
            )
        )
    results.sort(key=lambda r: r.shortest_hops)
    return results
