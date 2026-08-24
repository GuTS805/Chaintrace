"""Live 'trace any wallet' ingestion (offline; Blockscout fetch monkeypatched)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.ingest.live as live
from app.auth import get_current_officer
from app.db.session import get_session
from app.ingest.labels import ingest_all
from app.ingest.live import ensure_ingested
from app.main import app

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
    async def fake(address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0):
        return _payload()

    monkeypatch.setattr(live, "fetch_blockscout_txlist", fake)


async def test_ensure_ingested_fetches_then_caches(
    session: AsyncSession, _mock_fetch: None
) -> None:
    first = await ensure_ingested(session, REAL_ADDR)
    assert first.source == "blockscout"
    assert first.imported_transactions >= 10

    # Second call is served from cache — no new imports.
    second = await ensure_ingested(session, REAL_ADDR)
    assert second.source == "cache"
    assert second.imported_transactions == 0
    assert second.total_transactions == first.total_transactions


@pytest_asyncio.fixture
async def client(
    session: AsyncSession, _mock_fetch: None, test_officer
) -> AsyncIterator[AsyncClient]:
    await ingest_all(session)
    await session.commit()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_officer] = lambda: test_officer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_live_trace_endpoint_then_attribution(client: AsyncClient) -> None:
    resp = await client.post(f"/wallets/{REAL_ADDR}/live-trace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "blockscout"
    assert body["imported_transactions"] >= 10

    # The freshly imported real wallet now attributes to Kraken via the pipeline.
    attr = await client.get(f"/wallets/{REAL_ADDR}/attribution")
    assert attr.status_code == 200
    data = attr.json()
    assert data["candidates"]
    assert data["candidates"][0]["vasp_name"] == "Kraken"
