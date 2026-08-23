"""HTTP-level test for the /vasps/{name}/cluster endpoint and the graph's
cluster_id passthrough."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.cluster_builder import rebuild_cluster_for_vasp
from app.db.session import get_session
from app.ingest.chain_import import import_provider_txs
from app.ingest.labels import ingest_all
from app.main import app
from app.providers.base import ProviderTx

BINANCE_HOT = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
BASE = datetime(2024, 5, 1, tzinfo=UTC)


def _sweep_txs() -> list[ProviderTx]:
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


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    await ingest_all(session)
    await import_provider_txs(session, _sweep_txs())
    await session.commit()
    await rebuild_cluster_for_vasp(session, "Binance", {BINANCE_HOT})
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_vasp_cluster_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/vasps/Binance/cluster")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    cluster = data[0]
    assert cluster["heuristic"] == "deposit_sweep"
    assert cluster["size"] == 8
    assert set(cluster["members"]) == {f"0xdep{i}" for i in range(8)}


async def test_vasp_cluster_endpoint_404_when_absent(client: AsyncClient) -> None:
    resp = await client.get("/vasps/Coinbase/cluster")
    assert resp.status_code == 404


async def test_graph_endpoint_reports_cluster_id_on_deposit_nodes(
    client: AsyncClient,
) -> None:
    resp = await client.get(f"/wallets/{BINANCE_HOT}/graph", params={"direction": "REVERSE"})
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    dep0 = next(n for n in nodes if n["address"] == "0xdep0")
    assert dep0["cluster_id"] is not None
