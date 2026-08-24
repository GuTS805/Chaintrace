"""Test fixtures — offline, in-memory SQLite (no docker, no network)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Import models so metadata is fully populated before create_all.
import app.models  # noqa: F401
from app.db.base import Base


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """A fresh in-memory database and session for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def test_officer(session: AsyncSession):
    """A persisted Officer for tests that exercise protected endpoints —
    persisted (not just constructed) so FK-backed audit logging has a real row
    to reference."""
    from app.auth.security import hash_password
    from app.models import Officer

    officer = Officer(
        username="test.officer",
        password_hash=hash_password("test-password"),
        full_name="Test Officer",
        badge_no="TEST-01",
        department="Test Department",
    )
    session.add(officer)
    await session.flush()
    return officer
