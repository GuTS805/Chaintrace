"""HTTP-level tests for the graph endpoints (offline, in-loop AsyncClient)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_graph_repository
from app.auth import get_current_officer
from app.main import app
from app.repositories.sql_graph_repository import SqlGraphRepository
from app.synthetic import build_all_scenarios
from app.synthetic.scenarios import BINANCE_HOT
from app.synthetic.seed import seed_demo

RANSOM = next(
    s.unknown_wallet for s in build_all_scenarios() if s.key == "ransomware_to_exchange"
)


@pytest_asyncio.fixture
async def client(session: AsyncSession, test_officer) -> AsyncIterator[AsyncClient]:
    await seed_demo(session)
    await session.commit()
    app.dependency_overrides[get_graph_repository] = lambda: SqlGraphRepository(session)
    app.dependency_overrides[get_current_officer] = lambda: test_officer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_graph_endpoint_returns_nodes_edges_prune(client: AsyncClient) -> None:
    resp = await client.get(f"/wallets/{RANSOM}/graph", params={"depth": 4})
    assert resp.status_code == 200
    data = resp.json()
    assert data["root"] == RANSOM
    assert any(n["address"] == BINANCE_HOT and n["is_labeled"] for n in data["nodes"])
    assert "prune" in data and "pruned" in data["prune"]
    assert data["edges"]


async def test_graph_endpoint_reports_prune_at_shallow_depth(
    client: AsyncClient,
) -> None:
    resp = await client.get(f"/wallets/{RANSOM}/graph", params={"depth": 1})
    assert resp.status_code == 200
    prune = resp.json()["prune"]
    assert prune["pruned"] is True
    assert "MAX_HOPS" in prune["reasons"]


async def test_paths_to_labeled_endpoint(client: AsyncClient) -> None:
    resp = await client.get(f"/wallets/{RANSOM}/paths-to-labeled", params={"depth": 4})
    assert resp.status_code == 200
    paths = resp.json()
    assert any(p["vasp_name"] == "Binance" for p in paths)
    binance = next(p for p in paths if p["vasp_name"] == "Binance")
    assert binance["shortest_hops"] == 2
    assert binance["paths"][0][0] == RANSOM
    assert binance["paths"][0][-1] == BINANCE_HOT
