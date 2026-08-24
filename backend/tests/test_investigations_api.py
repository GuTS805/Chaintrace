"""Investigation snapshots: create freezes a result immutably; re-reading it
must never change even if the live pipeline would now answer differently."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder
from app.attribution.context_builder import ContextBuilder
from app.attribution.model import DEFAULT_MODEL_PATH
from app.auth import get_current_officer
from app.db.session import get_session
from app.main import app
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)

SCN = {s.key: s for s in build_all_scenarios()}


@pytest_asyncio.fixture
async def client(session: AsyncSession, test_officer) -> AsyncIterator[AsyncClient]:
    await seed_demo(session)
    await session.commit()
    app.dependency_overrides[get_context_builder] = lambda: ContextBuilder(session)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_officer] = lambda: test_officer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_create_investigation_freezes_the_verdict(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    resp = await client.post(f"/wallets/{addr}/investigations")
    assert resp.status_code == 201
    body = resp.json()
    assert body["wallet_address"] == addr
    assert body["attribution"]["candidates"][0]["vasp_name"] == "Binance"
    assert body["model_version"].startswith("phase4-")
    assert body["provider_source"] == "cache"  # already seeded, no live fetch needed
    assert body["traversal_max_hops"] > 0
    assert body["traversal_max_nodes"] > 0
    assert body["graph"] is not None
    assert body["risk"]["level"]


async def test_get_investigation_returns_the_frozen_record_unchanged(
    client: AsyncClient,
) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    created = (await client.post(f"/wallets/{addr}/investigations")).json()

    resp = await client.get(f"/investigations/{created['id']}")
    assert resp.status_code == 200
    fetched = resp.json()
    assert fetched["attribution"] == created["attribution"]
    assert fetched["risk"] == created["risk"]
    assert fetched["model_version"] == created["model_version"]


async def test_get_investigation_404_for_unknown_id(client: AsyncClient) -> None:
    resp = await client.get("/investigations/999999")
    assert resp.status_code == 404


async def test_list_investigations_for_wallet(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    await client.post(f"/wallets/{addr}/investigations")
    await client.post(f"/wallets/{addr}/investigations")

    resp = await client.get(f"/wallets/{addr}/investigations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["top_vasp"] == "Binance"
    assert body[0]["insufficient_evidence"] is False


async def test_investigation_report_pdf(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    created = (await client.post(f"/wallets/{addr}/investigations")).json()

    resp = await client.get(f"/investigations/{created['id']}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


async def test_investigation_disclosure_request_pdf(client: AsyncClient) -> None:
    addr = SCN["ransomware_to_exchange"].unknown_wallet
    created = (await client.post(f"/wallets/{addr}/investigations")).json()

    resp = await client.get(f"/investigations/{created['id']}/disclosure-request")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


async def test_frozen_investigation_survives_underlying_data_changing(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The exact scenario this feature exists for: an officer's investigation
    from two weeks ago must read back identically today, even though the live
    /attribution endpoint on the same wallet would now answer differently."""
    from sqlalchemy import delete

    from app.models import Transaction

    addr = SCN["ransomware_to_exchange"].unknown_wallet
    created = (await client.post(f"/wallets/{addr}/investigations")).json()
    assert created["attribution"]["candidates"][0]["vasp_name"] == "Binance"

    # Simulate the chain data changing later — delete the transactions that
    # actually carried this wallet to Binance, which would flip a fresh live
    # attribution call to insufficient_evidence.
    await session.execute(delete(Transaction).where(Transaction.from_address == addr))
    await session.commit()

    live_resp = await client.get(f"/wallets/{addr}/attribution")
    assert live_resp.json()["insufficient_evidence"] is True  # live view did change

    frozen_resp = await client.get(f"/investigations/{created['id']}")
    frozen = frozen_resp.json()
    assert frozen["attribution"] == created["attribution"]  # snapshot did not
    assert frozen["attribution"]["candidates"][0]["vasp_name"] == "Binance"


async def test_disclosure_request_409_for_insufficient_evidence(client: AsyncClient) -> None:
    addr = SCN["dead_end"].unknown_wallet
    created = (await client.post(f"/wallets/{addr}/investigations")).json()
    assert created["attribution"]["insufficient_evidence"] is True

    resp = await client.get(f"/investigations/{created['id']}/disclosure-request")
    assert resp.status_code == 409
