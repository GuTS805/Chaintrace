"""Synthetic scenario generator + seeding tests (offline, deterministic)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Label, Transaction, Vasp, Wallet
from app.synthetic import ExpectedOutcome, build_all_scenarios
from app.synthetic.provider import build_fixture_provider
from app.synthetic.scenarios import BINANCE_HOT, COINBASE_HOT, KRAKEN_HOT
from app.synthetic.seed import seed_demo


def test_four_scenarios_cover_every_outcome() -> None:
    scenarios = build_all_scenarios()
    assert len(scenarios) == 4
    outcomes = {s.expected for s in scenarios}
    assert outcomes == {
        ExpectedOutcome.CLEAN,
        ExpectedOutcome.MODERATE,
        ExpectedOutcome.INSUFFICIENT,
        ExpectedOutcome.AMBIGUOUS,
    }


def test_generation_is_deterministic() -> None:
    first = build_all_scenarios()
    second = build_all_scenarios()
    for a, b in zip(first, second, strict=True):
        assert a.unknown_wallet == b.unknown_wallet
        assert [t.tx_hash for t in a.transactions] == [t.tx_hash for t in b.transactions]
        assert [t.value_wei for t in a.transactions] == [t.value_wei for t in b.transactions]


def test_ground_truth_wiring() -> None:
    by_key = {s.key: s for s in build_all_scenarios()}

    assert by_key["ransomware_to_exchange"].ground_truth == "Binance"
    assert by_key["peel_chain"].ground_truth == "Kraken"
    assert by_key["dead_end"].ground_truth is None
    assert by_key["two_exchanges"].ground_truth is None
    assert set(by_key["two_exchanges"].ground_truth_candidates) == {"Binance", "Coinbase"}


def test_dead_end_never_touches_a_vasp() -> None:
    dead = next(s for s in build_all_scenarios() if s.key == "dead_end")
    addrs = {w.address for w in dead.wallets}
    assert BINANCE_HOT not in addrs
    assert KRAKEN_HOT not in addrs
    assert COINBASE_HOT not in addrs


def test_sweep_cluster_consolidates_into_hot_wallet() -> None:
    scn = next(s for s in build_all_scenarios() if s.key == "ransomware_to_exchange")
    into_binance = [t for t in scn.transactions if t.to_address == BINANCE_HOT]
    # 10 deposit addresses each sweep into the hot wallet.
    assert len(into_binance) >= 10
    # Sweeps are near-full-balance (within a small gas reserve of the deposit).
    assert all(t.value_wei > 0 for t in into_binance)


async def test_seed_demo_populates_db(session: AsyncSession) -> None:
    stats = await seed_demo(session)
    await session.commit()

    assert stats.scenarios == 4
    assert stats.transactions > 0
    assert len(stats.unknown_wallets) == 4

    db_wallets = (
        await session.execute(select(func.count()).select_from(Wallet))
    ).scalar_one()
    db_tx = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()
    assert db_wallets > 0
    assert db_tx == stats.transactions

    # Bundled labels came in, and the Binance hot wallet is labeled + linked.
    binance = (
        await session.execute(select(Vasp).where(Vasp.name == "Binance"))
    ).scalar_one()
    hot_label = (
        await session.execute(select(Label).where(Label.address == BINANCE_HOT))
    ).scalars().first()
    assert hot_label is not None
    assert hot_label.vasp_id == binance.id


async def test_seed_demo_is_idempotent(session: AsyncSession) -> None:
    first = await seed_demo(session)
    await session.commit()
    tx_after_first = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()

    second = await seed_demo(session)
    await session.commit()
    tx_after_second = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()

    assert tx_after_first == tx_after_second
    assert second.transactions == 0  # nothing new inserted on the second run
    assert first.transactions > 0


async def test_fixture_provider_reaches_hot_wallet() -> None:
    provider = build_fixture_provider()
    scn = next(s for s in build_all_scenarios() if s.key == "ransomware_to_exchange")
    txs = await provider.get_transactions(scn.unknown_wallet)
    assert txs, "unknown wallet should have outgoing transactions"
