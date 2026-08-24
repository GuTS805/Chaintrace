"""Officer authentication: password hashing, JWT, login flow, and route
protection (offline)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.model import DEFAULT_MODEL_PATH
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_session
from app.main import app
from app.models import AuditLog
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo


def test_password_hash_roundtrip() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h) is True
    assert verify_password("wrong password", h) is False


def test_password_hash_is_salted() -> None:
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2  # different salt each time
    assert verify_password("same-password", h1)
    assert verify_password("same-password", h2)


def test_jwt_roundtrip() -> None:
    token = create_access_token(7, "officer1", "Officer One")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["username"] == "officer1"


def test_jwt_rejects_garbage() -> None:
    assert decode_access_token("not-a-real-token") is None


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_officer(session: AsyncSession) -> None:
    from app.models import Officer

    session.add(
        Officer(
            username="officer1",
            password_hash=hash_password("secret-pass"),
            full_name="Officer One",
            badge_no="BADGE-1",
            department="Test Dept",
        )
    )
    await session.commit()


async def test_login_success(client: AsyncClient, session: AsyncSession) -> None:
    await _create_officer(session)
    resp = await client.post(
        "/auth/login", json={"username": "officer1", "password": "secret-pass"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["officer"]["username"] == "officer1"
    assert body["officer"]["full_name"] == "Officer One"


async def test_login_wrong_password(client: AsyncClient, session: AsyncSession) -> None:
    await _create_officer(session)
    resp = await client.post(
        "/auth/login", json={"username": "officer1", "password": "nope"}
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/login", json={"username": "ghost", "password": "x"}
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_valid_token(client: AsyncClient, session: AsyncSession) -> None:
    await _create_officer(session)
    login = await client.post(
        "/auth/login", json={"username": "officer1", "password": "secret-pass"}
    )
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "officer1"


async def test_protected_wallet_route_401_without_token(client: AsyncClient) -> None:
    resp = await client.get("/wallets/0xabc/graph")
    assert resp.status_code == 401


async def test_protected_wallet_route_works_with_real_login(
    client: AsyncClient, session: AsyncSession
) -> None:
    await _create_officer(session)
    await seed_demo(session)
    await session.commit()

    login = await client.post(
        "/auth/login", json={"username": "officer1", "password": "secret-pass"}
    )
    token = login.json()["access_token"]

    addr = next(
        s.unknown_wallet
        for s in build_all_scenarios()
        if s.key == "ransomware_to_exchange"
    )
    resp = await client.get(
        f"/wallets/{addr}/graph", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["root"] == addr


async def test_cases_route_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/cases")
    assert resp.status_code == 401


@pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)
async def test_wallet_query_writes_audit_log(
    client: AsyncClient, session: AsyncSession
) -> None:
    await _create_officer(session)
    await seed_demo(session)
    await session.commit()

    login = await client.post(
        "/auth/login", json={"username": "officer1", "password": "secret-pass"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    addr = next(
        s.unknown_wallet
        for s in build_all_scenarios()
        if s.key == "ransomware_to_exchange"
    )
    resp = await client.get(f"/wallets/{addr}/attribution", headers=headers)
    assert resp.status_code == 200

    rows = (await session.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "WALLET_QUERY"
    assert rows[0].target == addr
