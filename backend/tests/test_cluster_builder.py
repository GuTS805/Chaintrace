"""Exchange clustering: activates the previously-unused Cluster/ClusterMember
tables from a hot wallet's full inbound history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.cluster_builder import rebuild_all_clusters, rebuild_cluster_for_vasp
from app.ingest.chain_import import import_provider_txs
from app.ingest.labels import ingest_all
from app.models import Transaction
from app.providers.base import ProviderTx
from app.repositories.cluster_repository import ClusterRepository

BINANCE_HOT = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
BASE = datetime(2024, 5, 1, tzinfo=UTC)


def _sweep_txs() -> list[ProviderTx]:
    """8 deposit addresses, each sweeping a near-full balance into Binance's hot wallet."""
    txs: list[ProviderTx] = []
    n = 0
    for i in range(8):
        n += 1
        txs.append(
            ProviderTx(
                tx_hash=f"0xfund{i:062x}",
                timestamp=BASE + timedelta(hours=n),
                from_address=f"0xsrc{i}",
                to_address=f"0xdep{i}",
                value_wei=Decimal(10 * 10**18),
            )
        )
    for i in range(8):
        n += 1
        txs.append(
            ProviderTx(
                tx_hash=f"0xsweep{i:060x}",
                timestamp=BASE + timedelta(hours=n),
                from_address=f"0xdep{i}",
                to_address=BINANCE_HOT,
                value_wei=Decimal(int(9.99 * 10**18)),
            )
        )
    return txs


async def test_rebuild_cluster_for_vasp_persists_members(session: AsyncSession) -> None:
    await ingest_all(session)
    await import_provider_txs(session, _sweep_txs())
    await session.commit()

    stats = await rebuild_cluster_for_vasp(session, "Binance", {BINANCE_HOT}, chain="ethereum")
    await session.commit()

    assert stats.clusters_written == 1
    assert stats.members_written == 8

    repo = ClusterRepository(session)
    clusters = await repo.list_clusters_for_vasp("Binance")
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.heuristic == "deposit_sweep"
    assert "(ethereum)" in cluster.name
    assert set(cluster.members) == {f"0xdep{i}" for i in range(8)}

    member_view = await repo.get_cluster_for_address("0xdep3")
    assert member_view is not None
    assert member_view.id == cluster.id


async def test_rebuild_is_idempotent(session: AsyncSession) -> None:
    await ingest_all(session)
    await import_provider_txs(session, _sweep_txs())
    await session.commit()

    first = await rebuild_cluster_for_vasp(session, "Binance", {BINANCE_HOT})
    await session.commit()
    second = await rebuild_cluster_for_vasp(session, "Binance", {BINANCE_HOT})
    await session.commit()

    assert first.members_written == second.members_written == 8

    repo = ClusterRepository(session)
    clusters = await repo.list_clusters_for_vasp("Binance")
    assert len(clusters) == 1
    assert len(clusters[0].members) == 8  # not doubled by the rebuild


async def test_rebuild_all_clusters_covers_every_labeled_exchange(
    session: AsyncSession,
) -> None:
    await ingest_all(session)
    await import_provider_txs(session, _sweep_txs())
    await session.commit()

    total = await rebuild_all_clusters(session)
    await session.commit()

    assert total.clusters_written >= 1  # Binance's cluster; others have no inbound data
    repo = ClusterRepository(session)
    assert await repo.list_clusters_for_vasp("Binance") != []
    assert await repo.list_clusters_for_vasp("Coinbase") == []  # no sweep -> no cluster


async def test_no_sweep_no_cluster(session: AsyncSession) -> None:
    """A hot wallet with only a lone deposit (below MIN_SWEEP_CLUSTER) gets no cluster."""
    await ingest_all(session)
    session.add(
        Transaction(
            tx_hash="0x" + "1" * 64,
            timestamp=BASE,
            from_address="0xlonedep",
            to_address=BINANCE_HOT,
            value_wei=Decimal(1 * 10**18),
        )
    )
    await session.commit()

    stats = await rebuild_cluster_for_vasp(session, "Binance", {BINANCE_HOT})
    await session.commit()
    assert stats.clusters_written == 0

    repo = ClusterRepository(session)
    assert await repo.list_clusters_for_vasp("Binance") == []


async def test_hot_wallets_on_different_chains_never_merge_into_one_cluster(
    session: AsyncSession,
) -> None:
    """A Tron depositor and an Ethereum depositor for the *same* VASP name must
    not end up in the same cluster — deposit clustering is a same-chain
    phenomenon (regression for the cross-chain merge bug)."""
    from sqlalchemy import select as sa_select

    from app.enums import LabelCategory, LabelSource
    from app.models import Label, Vasp

    await ingest_all(session)
    vasp_id = (
        await session.execute(sa_select(Vasp.id).where(Vasp.name == "Binance"))
    ).scalar_one()

    tron_hot = "TFakeHotWalletAddress1234567890ABC"
    session.add(
        Label(
            address=tron_hot,
            name="Binance Tron Hot",
            category=LabelCategory.EXCHANGE,
            source=LabelSource.MANUAL,
            vasp_id=vasp_id,
        )
    )
    await session.commit()

    # One Ethereum-side sweep (BINANCE_HOT) and one Tron-side sweep (tron_hot),
    # each with its own 2+ depositors.
    txs = _sweep_txs()
    tron_txs = [
        ProviderTx(
            tx_hash=f"0xtronfund{i:057x}",
            timestamp=BASE + timedelta(hours=100 + i),
            from_address=f"Tsrc{i}",
            to_address=f"Tdep{i}",
            value_wei=Decimal(10_000_000),
        )
        for i in range(2)
    ] + [
        ProviderTx(
            tx_hash=f"0xtronsweep{i:055x}",
            timestamp=BASE + timedelta(hours=200 + i),
            from_address=f"Tdep{i}",
            to_address=tron_hot,
            value_wei=Decimal(9_990_000),
        )
        for i in range(2)
    ]
    await import_provider_txs(session, txs + tron_txs)
    await session.commit()

    total = await rebuild_all_clusters(session)
    await session.commit()

    repo = ClusterRepository(session)
    clusters = await repo.list_clusters_for_vasp("Binance")
    assert len(clusters) == 2  # one per chain, never merged
    by_chain = {("(tron)" if "(tron)" in c.name else "(ethereum)"): c for c in clusters}
    assert set(by_chain["(ethereum)"].members) == {f"0xdep{i}" for i in range(8)}
    assert set(by_chain["(tron)"].members) == {"Tdep0", "Tdep1"}
    assert total.clusters_written >= 2
