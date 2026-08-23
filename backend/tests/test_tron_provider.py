"""Tron/TRC20 provider: real-chain (TronGrid-schema) import through the same
pipeline, plus 'trace any wallet' routing to Tron by address shape."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.ingest.live as live
from app.ingest.chain_import import import_provider_txs
from app.ingest.labels import ingest_all
from app.ingest.live import ensure_ingested
from app.models import Wallet
from app.providers.base import normalize_address
from app.providers.tron import is_tron_address, parse_trongrid_trc20
from app.repositories.graph_repository import TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository

_REALCHAIN = Path(__file__).resolve().parents[1] / "data" / "realchain"
REAL = _REALCHAIN / "tron_kraken_depositor_TVYuaXdh.json"
REAL_ADDR = "TVYuaXdhEHBvmk8284pSdtyRZwxE5oZ9yQ"
KRAKEN_HOT_TRON = "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76"


def _payload() -> dict[str, Any]:
    return json.loads(REAL.read_text(encoding="utf-8"))


def test_is_tron_address() -> None:
    assert is_tron_address(REAL_ADDR) is True
    assert is_tron_address("0x216b75231dfec0a4716b602ab00669fa568ad09b") is False


def test_normalize_address_preserves_tron_case() -> None:
    # Base58 is case-sensitive/checksummed — must not be lowercased.
    assert normalize_address(REAL_ADDR) == REAL_ADDR
    assert normalize_address("0xABCDEF") == "0xabcdef"


def test_parse_trongrid_trc20_schema() -> None:
    txs = parse_trongrid_trc20(_payload())
    assert len(txs) == 16
    first = txs[0]
    assert first.asset == "USDT"
    assert first.value_wei == Decimal("493000000")
    assert first.from_address == REAL_ADDR
    assert first.to_address == KRAKEN_HOT_TRON  # unchanged case, base58


async def test_committed_real_tron_snapshot_reaches_kraken(session: AsyncSession) -> None:
    """The genuine TronGrid snapshot flows through the same pipeline to Kraken."""
    await ingest_all(session)
    txs = parse_trongrid_trc20(_payload())
    assert len(txs) >= 10  # real low-degree wallet
    stats = await import_provider_txs(session, txs, chain="tron")
    await session.commit()
    assert stats.transactions == 16

    wallet = (
        await session.execute(select(Wallet).where(Wallet.address == REAL_ADDR))
    ).scalar_one()
    assert wallet.chain == "tron"

    repo = SqlGraphRepository(session)
    graph = await repo.traverse(REAL_ADDR, TraversalBounds(max_hops=4))
    kraken = next((n for n in graph.nodes if n.address == KRAKEN_HOT_TRON), None)
    assert kraken is not None
    assert kraken.is_labeled is True
    assert kraken.vasp_name == "Kraken"


@pytest.fixture
def _mock_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0):
        return _payload()

    monkeypatch.setattr(live, "fetch_trongrid_trc20", fake)


async def test_ensure_ingested_routes_tron_by_address_shape(
    session: AsyncSession, _mock_fetch: None
) -> None:
    first = await ensure_ingested(session, REAL_ADDR)
    assert first.source == "trongrid"
    assert first.imported_transactions == 16

    second = await ensure_ingested(session, REAL_ADDR)
    assert second.source == "cache"
    assert second.imported_transactions == 0
