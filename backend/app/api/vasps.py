"""VASP-scoped endpoints (deposit clusters)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_officer
from app.db.session import get_session
from app.repositories.cluster_repository import ClusterRepository
from app.schemas.cluster import ClusterOut

router = APIRouter(
    prefix="/vasps", tags=["clusters"], dependencies=[Depends(get_current_officer)]
)


async def get_cluster_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[ClusterRepository]:
    yield ClusterRepository(session)


@router.get("/{name}/cluster", response_model=list[ClusterOut])
async def vasp_cluster(
    name: str,
    repo: ClusterRepository = Depends(get_cluster_repository),
) -> list[ClusterOut]:
    """The VASP's deposit-sweep cluster(s) — one per chain it has an
    EXCHANGE-labeled hot wallet on (populated by `app.attribution.cluster_builder`)."""
    clusters = await repo.list_clusters_for_vasp(name)
    if not clusters:
        raise HTTPException(
            status_code=404,
            detail=f"No deposit cluster for '{name}' — run cluster_builder after ingestion.",
        )
    return [
        ClusterOut(
            id=c.id, name=c.name, heuristic=c.heuristic, members=c.members, size=len(c.members)
        )
        for c in clusters
    ]
