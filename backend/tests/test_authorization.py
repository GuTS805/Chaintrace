"""Cross-officer authorization: the classic IDOR check — can Officer A reach
Officer B's case or investigation by guessing/incrementing an ID?

This is deliberately its own file: every other test file in this suite uses
exactly one officer identity per client, so none of them could ever catch
this class of bug even if it existed (confirmed by design, not oversight —
see the fixtures below for the two-officer pattern the rest of the suite
doesn't use)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.model import DEFAULT_MODEL_PATH
from app.auth import get_current_officer
from app.auth.security import hash_password
from app.db.session import get_session
from app.main import app
from app.models import Officer

import pytest

pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)


@pytest_asyncio.fixture
async def officer_a(session: AsyncSession) -> Officer:
    o = Officer(
        username="officer.a",
        password_hash=hash_password("pw-a"),
        full_name="Officer A",
        badge_no="A-01",
        department="Cyber Cell A",
    )
    session.add(o)
    await session.flush()
    return o


@pytest_asyncio.fixture
async def officer_b(session: AsyncSession) -> Officer:
    o = Officer(
        username="officer.b",
        password_hash=hash_password("pw-b"),
        full_name="Officer B",
        badge_no="B-01",
        department="Cyber Cell B",
    )
    session.add(o)
    await session.flush()
    return o


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    from app.api.attribution import get_context_builder
    from app.attribution.context_builder import ContextBuilder

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_context_builder] = lambda: ContextBuilder(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _as(officer: Officer) -> None:
    """Switch which officer the next request(s) on `client` authenticate as."""
    app.dependency_overrides[get_current_officer] = lambda: officer


async def test_officer_a_cannot_read_officer_bs_case(
    client: AsyncClient, officer_a: Officer, officer_b: Officer
) -> None:
    _as(officer_b)
    created = (
        await client.post("/cases", json={"name": "Officer B's private case"})
    ).json()

    _as(officer_a)
    resp = await client.get(f"/cases/{created['id']}")
    assert resp.status_code == 404  # not 403 — existence itself isn't disclosed

    resp = await client.get("/cases")
    assert all(c["id"] != created["id"] for c in resp.json())  # not in A's list either


async def test_officer_a_cannot_delete_officer_bs_case(
    client: AsyncClient, officer_a: Officer, officer_b: Officer
) -> None:
    _as(officer_b)
    created = (
        await client.post("/cases", json={"name": "Officer B's case"})
    ).json()

    _as(officer_a)
    resp = await client.delete(f"/cases/{created['id']}")
    assert resp.status_code == 404

    _as(officer_b)
    resp = await client.get(f"/cases/{created['id']}")
    assert resp.status_code == 200  # still there — A's attempt did nothing


async def test_officer_a_cannot_add_findings_to_officer_bs_case(
    client: AsyncClient, officer_a: Officer, officer_b: Officer
) -> None:
    _as(officer_b)
    created = (
        await client.post("/cases", json={"name": "Officer B's case"})
    ).json()

    _as(officer_a)
    resp = await client.post(
        f"/cases/{created['id']}/findings", json={"title": "planted by A"}
    )
    assert resp.status_code == 404

    resp = await client.get(f"/cases/{created['id']}/findings")
    assert resp.status_code == 404


async def test_officer_a_cannot_read_officer_bs_investigation(
    client: AsyncClient, officer_a: Officer, officer_b: Officer, session: AsyncSession
) -> None:
    from app.synthetic.seed import seed_demo
    from app.synthetic import build_all_scenarios

    await seed_demo(session)
    await session.commit()
    addr = {s.key: s for s in build_all_scenarios()}["ransomware_to_exchange"].unknown_wallet

    _as(officer_b)
    created = (await client.post(f"/wallets/{addr}/investigations")).json()

    _as(officer_a)
    resp = await client.get(f"/investigations/{created['id']}")
    assert resp.status_code == 404

    resp = await client.get(f"/investigations/{created['id']}/report")
    assert resp.status_code == 404

    resp = await client.get(f"/investigations/{created['id']}/disclosure-request")
    assert resp.status_code == 404

    # A's own list for the same wallet must not surface B's investigation.
    resp = await client.get(f"/wallets/{addr}/investigations")
    assert resp.json() == []
