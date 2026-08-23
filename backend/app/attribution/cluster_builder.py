"""Populate Cluster/ClusterMember for each labeled exchange hot wallet.

The many-to-one deposit-sweep grouping (`app.signals.facts.detect_sweep_cluster`)
already identifies an exchange's deposit cluster per candidate during
attribution, but only over the bounded attribution-context slice, and the
result is never persisted — the Cluster/ClusterMember tables exist since the
initial migration but nothing populates them. This runs the same detector over
each labeled hot wallet's *full* inbound history (a flat filtered query, not a
graph traversal, so it doesn't touch the "traversal is always bounded"
invariant in graph_repository.py — still capped at MAX_INBOUND_ROWS as a
safety ceiling) and writes the result, so clusters exist as first-class,
queryable entities independent of any single wallet's attribution request.

Run: python -m app.attribution.cluster_builder  (or after chain_import/live
ingestion, which trigger a rebuild for the affected VASPs automatically).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import LabelCategory
from app.models import Cluster, ClusterMember, Label, Transaction, Vasp
from app.providers.tron import is_tron_address
from app.signals.facts import detect_sweep_cluster

log = structlog.get_logger(__name__)

HEURISTIC = "deposit_sweep"
# Safety ceiling on inbound rows pulled per hot wallet.
MAX_INBOUND_ROWS = 5000


@dataclass
class ClusterBuildStats:
    vasps_processed: int = 0
    clusters_written: int = 0
    members_written: int = 0


def _chain_of(address: str) -> str:
    """Infer chain from address shape — the same discriminator used throughout
    (WalletSearch, live-trace routing): deposit clustering is inherently a
    same-chain phenomenon, so a VASP's hot wallets on different chains must
    never be merged into one cluster even though they share a VASP name."""
    return "tron" if is_tron_address(address) else "ethereum"


async def _hot_wallets_by_vasp_chain(
    session: AsyncSession, vasp_name: str | None = None
) -> dict[tuple[int, str], tuple[str, set[str]]]:
    """(vasp_id, chain) -> (vasp_name, hot addresses) for EXCHANGE-labeled VASPs."""
    stmt = (
        select(Label.vasp_id, Vasp.name, Label.address)
        .select_from(Label)
        .join(Vasp, Label.vasp_id == Vasp.id)
        .where(Label.category == LabelCategory.EXCHANGE, Label.vasp_id.is_not(None))
    )
    if vasp_name is not None:
        stmt = stmt.where(Vasp.name == vasp_name)
    rows = (await session.execute(stmt)).all()

    out: dict[tuple[int, str], tuple[str, set[str]]] = {}
    for vasp_id, name, address in rows:
        key = (vasp_id, _chain_of(address))
        _, addrs = out.setdefault(key, (name, set()))
        addrs.add(address)
    return out


async def _inbound_edges(session: AsyncSession, hot: set[str]) -> list[Transaction]:
    if not hot:
        return []
    rows = (
        await session.execute(
            select(Transaction).where(Transaction.to_address.in_(hot)).limit(MAX_INBOUND_ROWS)
        )
    ).scalars().all()
    return list(rows)


async def rebuild_cluster_for_vasp(
    session: AsyncSession, vasp_name: str, hot: set[str], *, chain: str = "ethereum"
) -> ClusterBuildStats:
    """Idempotent: replaces this VASP's (chain-scoped) deposit-sweep cluster
    with a fresh one. `hot` must be single-chain — a VASP's hot wallets on
    different chains are clustered separately (see `_chain_of`)."""
    stats = ClusterBuildStats(vasps_processed=1)
    rows = await _inbound_edges(session, hot)

    inflow: dict[str, Decimal] = {}
    for row in rows:
        if row.to_address:
            inflow[row.to_address] = inflow.get(row.to_address, Decimal(0)) + row.value_wei

    # Transaction rows carry the same from_address/to_address/value_wei/tx_hash/
    # timestamp attributes detect_sweep_cluster needs from a ProviderTx — no
    # conversion required.
    sweep = detect_sweep_cluster(hot, rows, inflow)  # type: ignore[arg-type]

    cluster_name = f"{vasp_name} deposit cluster ({chain})"
    existing = (
        await session.execute(select(Cluster).where(Cluster.name == cluster_name))
    ).scalar_one_or_none()

    if not sweep.deposit_cluster:
        if existing is not None:
            await session.execute(
                delete(ClusterMember).where(ClusterMember.cluster_id == existing.id)
            )
            await session.execute(delete(Cluster).where(Cluster.id == existing.id))
        return stats

    if existing is not None:
        await session.execute(delete(ClusterMember).where(ClusterMember.cluster_id == existing.id))
        cluster = existing
    else:
        cluster = Cluster(name=cluster_name, heuristic=HEURISTIC)
        session.add(cluster)
        await session.flush()

    for addr in sweep.deposit_cluster:
        session.add(ClusterMember(cluster_id=cluster.id, address=addr))
    await session.flush()

    stats.clusters_written = 1
    stats.members_written = len(sweep.deposit_cluster)
    return stats


async def rebuild_all_clusters(session: AsyncSession) -> ClusterBuildStats:
    total = ClusterBuildStats()
    hot_by_vasp_chain = await _hot_wallets_by_vasp_chain(session)
    for (_vasp_id, chain), (name, hot) in hot_by_vasp_chain.items():
        s = await rebuild_cluster_for_vasp(session, name, hot, chain=chain)
        total.vasps_processed += s.vasps_processed
        total.clusters_written += s.clusters_written
        total.members_written += s.members_written
    return total


async def _main() -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        stats = await rebuild_all_clusters(session)
        await session.commit()
        result = {
            "vasps_processed": stats.vasps_processed,
            "clusters_written": stats.clusters_written,
            "members_written": stats.members_written,
        }
        log.info("cluster_build_complete", **result)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
