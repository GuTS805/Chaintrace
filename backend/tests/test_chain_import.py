"""Real-chain (Etherscan-schema) import → same pipeline runs on it."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.chain_import import import_provider_txs
from app.ingest.labels import ingest_all
from app.models import Transaction
from app.providers.etherscan import parse_etherscan_txlist
from app.repositories.graph_repository import TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository

_REALCHAIN = Path(__file__).resolve().parents[1] / "data" / "realchain"
SAMPLE = _REALCHAIN / "sample_etherscan_txlist.json"
REAL = _REALCHAIN / "kraken_depositor_216b7523.json"
BINANCE_HOT = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
KRAKEN_HOT = "0x2910543af39aba0cd09dbb2d50200b3e800a63d2"
SRC = "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1"
REAL_ADDR = "0x216b75231dfec0a4716b602ab00669fa568ad09b"


def test_parse_etherscan_schema() -> None:
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    txs = parse_etherscan_txlist(payload)
    assert len(txs) == 2
    first = txs[0]
    assert first.from_address == SRC
    assert first.value_wei == Decimal("5000000000000000000")
    assert first.tx_hash.startswith("0xaa01")


async def test_import_feeds_the_same_pipeline(session: AsyncSession) -> None:
    # Real-chain labels + imported real-schema transactions.
    await ingest_all(session)
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    txs = parse_etherscan_txlist(payload)
    stats = await import_provider_txs(session, txs)
    await session.commit()

    assert stats.transactions == 2
    assert stats.wallets == 3  # src, deposit, binance hot

    # The unchanged traversal reaches the labeled Binance hot wallet.
    repo = SqlGraphRepository(session)
    graph = await repo.traverse(SRC, TraversalBounds(max_hops=4))
    hot = next((n for n in graph.nodes if n.address == BINANCE_HOT), None)
    assert hot is not None
    assert hot.is_labeled is True
    assert hot.vasp_name == "Binance"


async def test_committed_real_snapshot_reaches_kraken(session: AsyncSession) -> None:
    """The genuine Blockscout snapshot flows through the same pipeline to Kraken."""
    await ingest_all(session)
    payload = json.loads(REAL.read_text(encoding="utf-8"))
    txs = parse_etherscan_txlist(payload)
    assert len(txs) >= 10  # real low-degree wallet
    await import_provider_txs(session, txs)
    await session.commit()

    repo = SqlGraphRepository(session)
    graph = await repo.traverse(REAL_ADDR, TraversalBounds(max_hops=4))
    kraken = next((n for n in graph.nodes if n.address == KRAKEN_HOT), None)
    assert kraken is not None
    assert kraken.is_labeled is True
    assert kraken.vasp_name == "Kraken"


async def test_import_is_idempotent(session: AsyncSession) -> None:
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    txs = parse_etherscan_txlist(payload)
    await import_provider_txs(session, txs)
    await session.commit()
    second = await import_provider_txs(session, txs)
    await session.commit()

    assert second.transactions == 0
    assert second.skipped == 2
    total = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()
    assert total == 2
