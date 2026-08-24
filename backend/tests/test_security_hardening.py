"""JWT-secret production guard, login rate limiting, security headers, and
the request body size cap."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rate_limit import LoginRateLimiter
from app.config import DEFAULT_JWT_SECRET, Settings
from app.db.session import get_session
from app.main import app


def test_production_boot_with_default_jwt_secret_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercises the real create_app() startup guard, not a reimplementation
    of it — monkeypatches app.main's get_settings so the process-wide cached
    Settings singleton (and every other test relying on it) is untouched."""
    import app.main as main_module

    insecure = Settings(env="production", jwt_secret=DEFAULT_JWT_SECRET)
    monkeypatch.setattr(main_module, "get_settings", lambda: insecure)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        main_module.create_app()


def test_production_boot_with_real_jwt_secret_is_fine() -> None:
    settings = Settings(env="production", jwt_secret="a-real-randomly-generated-secret")
    assert not (settings.env == "production" and settings.uses_default_jwt_secret)


def test_demo_env_with_default_secret_is_allowed() -> None:
    settings = Settings(env="development", jwt_secret=DEFAULT_JWT_SECRET)
    assert not (settings.env == "production" and settings.uses_default_jwt_secret)


# --------------------------------------------------------------- rate limit --


def test_rate_limiter_blocks_after_threshold_then_recovers_after_cooldown() -> None:
    limiter = LoginRateLimiter(max_failures=3, window_seconds=60, cooldown_seconds=0.05)
    key = "someone"
    for _ in range(3):
        assert limiter.seconds_until_allowed(key) == 0.0
        limiter.record_failure(key)
    assert limiter.seconds_until_allowed(key) > 0.0

    import time

    time.sleep(0.06)
    assert limiter.seconds_until_allowed(key) == 0.0  # cooldown elapsed


def test_rate_limiter_success_resets_the_counter() -> None:
    limiter = LoginRateLimiter(max_failures=2, window_seconds=60, cooldown_seconds=30)
    key = "someone"
    limiter.record_failure(key)
    limiter.record_failure(key)
    assert limiter.seconds_until_allowed(key) > 0.0
    limiter.record_success(key)
    assert limiter.seconds_until_allowed(key) == 0.0


async def test_login_endpoint_429s_after_repeated_failures(session: AsyncSession) -> None:
    from app.auth.security import hash_password
    from app.models import Officer

    officer = Officer(
        username="throttle.me", password_hash=hash_password("correct-horse"),
        full_name="Throttle Test",
    )
    session.add(officer)
    await session.flush()
    app.dependency_overrides[get_session] = lambda: session

    # Isolate this test's rate-limit state from every other test in the
    # process (the limiter is a module-level singleton by design).
    import app.api.auth as auth_module
    from app.auth.rate_limit import LoginRateLimiter

    fresh = LoginRateLimiter(max_failures=3, window_seconds=60, cooldown_seconds=30)
    auth_module.get_default_limiter = lambda: fresh  # type: ignore[assignment]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        for _ in range(3):
            resp = await c.post(
                "/auth/login", json={"username": "throttle.me", "password": "wrong"}
            )
            assert resp.status_code == 401

        resp = await c.post(
            "/auth/login", json={"username": "throttle.me", "password": "wrong"}
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

        # Even the CORRECT password is throttled during cooldown — this is a
        # cooldown on the account, not just "you keep failing".
        resp = await c.post(
            "/auth/login", json={"username": "throttle.me", "password": "correct-horse"}
        )
        assert resp.status_code == 429

    app.dependency_overrides.clear()


# ------------------------------------------------------------------ headers --


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_security_headers_present_on_every_response(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "strict-transport-security" in resp.headers


async def test_oversized_request_body_is_rejected(client: AsyncClient) -> None:
    from app.config import get_settings

    huge = "x" * (get_settings().max_request_body_bytes + 1)
    resp = await client.post(
        "/auth/login", content=huge.encode(), headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 413
