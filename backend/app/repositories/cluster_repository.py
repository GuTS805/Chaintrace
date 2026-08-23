"""Reads over the (now-populated) Cluster/ClusterMember tables."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cluster, ClusterMember

# Cluster names are "{vasp_name} deposit cluster ({chain})" — a VASP can have
# one per chain, since deposit clustering is inherently a same-chain
# phenomenon (see app.attribution.cluster_builder._chain_of).


def _name_prefix(vasp_name: str) -> str:
    return f"{vasp_name} deposit cluster"


@dataclass
class ClusterView:
    id: int
    name: str
    heuristic: str
    members: list[str]


class ClusterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cluster_for_address(self, address: str) -> ClusterView | None:
        """The cluster (if any) a given deposit address belongs to."""
        cluster_id = (
            await self._session.execute(
                select(ClusterMember.cluster_id).where(ClusterMember.address == address)
            )
        ).scalar_one_or_none()
        if cluster_id is None:
            return None
        return await self._get(cluster_id)

    async def list_clusters_for_vasp(self, vasp_name: str) -> list[ClusterView]:
        """All of this VASP's deposit clusters — one per chain it has an
        EXCHANGE-labeled hot wallet on."""
        prefix = _name_prefix(vasp_name)
        clusters = (
            await self._session.execute(
                select(Cluster).where(Cluster.name.like(f"{prefix}%"))
            )
        ).scalars().all()
        views = [await self._get(c.id) for c in clusters]
        return [v for v in views if v is not None]

    async def _get(self, cluster_id: int) -> ClusterView | None:
        cluster = (
            await self._session.execute(select(Cluster).where(Cluster.id == cluster_id))
        ).scalar_one_or_none()
        if cluster is None:
            return None
        members = (
            (
                await self._session.execute(
                    select(ClusterMember.address).where(ClusterMember.cluster_id == cluster_id)
                )
            )
            .scalars()
            .all()
        )
        return ClusterView(
            id=cluster.id,
            name=cluster.name,
            heuristic=cluster.heuristic,
            members=list(members),
        )
