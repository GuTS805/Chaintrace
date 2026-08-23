"""HTTP-level tests for /attribution and /risk."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder
from app.attribution.context_builder import ContextBuilder
from app.attribution.model import DEFAULT_MODEL_PATH
from app.main import app
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)

SCN = {s.key: s for s in build_all_scenarios()}


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    await seed_demo(session)
    await session.commit()
    app.dependency_overrides[get_context_builder] = lambda: ContextBuilder(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_attribution_endpoint_ransomware(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    resp = await client.get(f"/wallets/{addr}/attribution")
    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is False
    assert body["candidates"][0]["vasp_name"] == "Binance"
    assert body["candidates"][0]["evidence"]
    assert body["model_version"].startswith("phase4-")


async def test_attribution_endpoint_dead_end(client: AsyncClient) -> None:
    addr = SCN["dead_end"].unknown_wallet
    resp = await client.get(f"/wallets/{addr}/attribution")
    assert resp.status_code == 200
    assert resp.json()["insufficient_evidence"] is True


async def test_risk_endpoint_flags_mixer(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    resp = await client.get(f"/wallets/{addr}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] in {"MEDIUM", "HIGH", "CRITICAL"}
    assert any(i["category"] == "SANCTIONED" for i in body["indicators"])
