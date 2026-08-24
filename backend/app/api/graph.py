"""Graph traversal + path-extraction endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_graph_repository
from app.auth import get_current_officer
from app.config import get_settings
from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository
from app.schemas.graph import GraphResult, LabeledPath

router = APIRouter(
    prefix="/wallets", tags=["graph"], dependencies=[Depends(get_current_officer)]
)

_settings = get_settings()
# Default matches the visualization's own bound (smaller than the attribution
# pipeline's default — a graph view is for a human to look at); the ceiling
# is the same server-side absolute cap everywhere else in the app uses.
_MAX_NODES_DEFAULT = min(500, _settings.traversal_max_nodes_ceiling)
_MAX_NODES_CEILING = _settings.traversal_max_nodes_ceiling


async def _traverse_or_504(repo: SqlGraphRepository, address: str, bounds: TraversalBounds) -> GraphResult:
    try:
        return await asyncio.wait_for(
            repo.traverse(address, bounds), timeout=_settings.traversal_timeout_seconds
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "The graph query took too long to complete and was aborted — "
                "narrow the depth or max_nodes and retry."
            ),
        ) from exc


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
    max_nodes: int = Query(_MAX_NODES_DEFAULT, ge=1, le=_MAX_NODES_CEILING),
    repo: SqlGraphRepository = Depends(get_graph_repository),
) -> GraphResult:
    """Bounded neighborhood of a wallet with node/edge and prune metadata."""
    bounds = _bounds(depth, min_value, since, until, direction, max_nodes)
    return await _traverse_or_504(repo, address, bounds)


@router.get("/{address}/paths-to-labeled", response_model=list[LabeledPath])
async def paths_to_labeled(
    address: str,
    depth: int = Query(5, ge=1, le=8),
    min_value: int = Query(0, ge=0),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    direction: Direction = Query(Direction.FORWARD),
    max_nodes: int = Query(_MAX_NODES_DEFAULT, ge=1, le=_MAX_NODES_CEILING),
    limit_per_target: int = Query(3, ge=1, le=20),
    repo: SqlGraphRepository = Depends(get_graph_repository),
) -> list[LabeledPath]:
    """Extract bounded paths from an unknown wallet to each reachable labeled wallet."""
    bounds = _bounds(depth, min_value, since, until, direction, max_nodes)
    graph = await _traverse_or_504(repo, address, bounds)

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
