"""Polygon: same Blockscout-compatible schema as Ethereum, routed through the
same fetch/parse code with a different base URL + native asset. (BNB Smart
Chain was evaluated but has no free keyless explorer API — BscScan's V1
endpoint is deprecated and there's no public Blockscout instance for it — so
it isn't offered.)"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.ingest.live as live
from app.ingest.live import ensure_ingested
from app.models import Wallet

REAL = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "realchain"
    / "kraken_depositor_216b7523.json"
)
REAL_ADDR = "0x216b75231dfec0a4716b602ab00669fa568ad09b"


def _payload() -> dict[str, Any]:
    return json.loads(REAL.read_text(encoding="utf-8"))


@pytest.fixture
def _mock_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_txlist(address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0):
        return _payload()

    async def fake_tokentx(address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0):
        return {"result": []}

    monkeypatch.setattr(live, "fetch_blockscout_txlist", fake_txlist)
    monkeypatch.setattr(live, "fetch_blockscout_tokentx", fake_tokentx)


@pytest.mark.parametrize("chain,native_asset", [("polygon", "POL")])
async def test_ensure_ingested_routes_evm_chain(
    session: AsyncSession, _mock_fetch: None, chain: str, native_asset: str
) -> None:
    result = await ensure_ingested(session, REAL_ADDR, chain=chain)
    assert result.source == "blockscout"
    assert result.chain == chain
    assert result.imported_transactions >= 10

    wallet = (
        await session.execute(select(Wallet).where(Wallet.address == REAL_ADDR))
    ).scalar_one()
    assert wallet.chain == chain

    native_txs = (
        await session.execute(
            select(live.Transaction).where(live.Transaction.asset == native_asset)
        )
    ).scalars().all()
    assert native_txs, f"expected native {native_asset} transactions"

    # Cached on the second call regardless of chain arg.
    second = await ensure_ingested(session, REAL_ADDR, chain=chain)
    assert second.source == "cache"


async def test_ensure_ingested_rejects_unknown_chain(session: AsyncSession) -> None:
    with pytest.raises(ValueError):
        await ensure_ingested(session, REAL_ADDR, chain="bnb")
