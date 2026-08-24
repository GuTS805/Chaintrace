"""Seed a demo officer account (offline, idempotent).

`run.ps1` / `make seed-demo` calls this so the demo has a login-ready account out
of the box. Credentials are intentionally simple and printed to the console —
this is a hackathon demo fixture, not a production credential.
"""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models import Officer

log = structlog.get_logger(__name__)

DEMO_USERNAME = "i4c.analyst"
DEMO_PASSWORD = "Chain@2026"  # noqa: S105 - intentional demo-only fixture credential
DEMO_FULL_NAME = "Demo Investigating Officer"
DEMO_BADGE_NO = "I4C-DEMO-01"
DEMO_DEPARTMENT = "I4C — Cyber Crime Coordination Centre, MHA"


async def ensure_demo_officer(session: AsyncSession) -> bool:
    """Create the demo officer if it doesn't exist yet. Returns True if created."""
    existing = (
        await session.execute(select(Officer).where(Officer.username == DEMO_USERNAME))
    ).scalar_one_or_none()
    if existing is not None:
        return False
    session.add(
        Officer(
            username=DEMO_USERNAME,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=DEMO_FULL_NAME,
            badge_no=DEMO_BADGE_NO,
            department=DEMO_DEPARTMENT,
        )
    )
    await session.flush()
    return True


async def _main() -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        created = await ensure_demo_officer(session)
        await session.commit()
        if created:
            log.info("demo_officer_created", username=DEMO_USERNAME)
            print(f"Created demo officer: {DEMO_USERNAME} / {DEMO_PASSWORD}")
        else:
            print(f"Demo officer already exists: {DEMO_USERNAME}")


if __name__ == "__main__":
    asyncio.run(_main())
