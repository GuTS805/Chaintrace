"""HTTP tests for the cases API."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_officer
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def client(session: AsyncSession, test_officer) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_officer] = lambda: test_officer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_case_lifecycle(client: AsyncClient) -> None:
    # Create.
    resp = await client.post(
        "/cases", json={"name": "Ransomware trace", "investigator": "analyst-1"}
    )
    assert resp.status_code == 201
    case = resp.json()
    case_id = case["id"]
    assert case["status"] == "OPEN"

    # List.
    resp = await client.get("/cases")
    assert resp.status_code == 200
    assert any(c["id"] == case_id for c in resp.json())

    # Add a finding (attach a wallet + evidence).
    resp = await client.post(
        f"/cases/{case_id}/findings",
        json={
            "title": "Deposit sweep into Binance",
            "severity": "HIGH",
            "wallet_address": "0xabc",
            "evidence": {"signal_type": "DEPOSIT_SWEEP", "weight": 0.4},
        },
    )
    assert resp.status_code == 201
    assert resp.json()["severity"] == "HIGH"

    # Detail includes the finding.
    resp = await client.get(f"/cases/{case_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["wallet_address"] == "0xabc"

    # Delete.
    resp = await client.delete(f"/cases/{case_id}")
    assert resp.status_code == 204
    resp = await client.get(f"/cases/{case_id}")
    assert resp.status_code == 404


async def test_finding_on_missing_case_is_404(client: AsyncClient) -> None:
    resp = await client.post("/cases/9999/findings", json={"title": "x"})
    assert resp.status_code == 404
