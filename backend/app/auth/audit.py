"""Write an AuditLog row for an officer action. Best-effort: a logging failure
must never break the request it is logging."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Officer

log = structlog.get_logger(__name__)


async def record(
    session: AsyncSession,
    officer: Officer,
    action: str,
    *,
    target: str | None = None,
    detail: str | None = None,
) -> None:
    try:
        session.add(
            AuditLog(officer_id=officer.id, action=action, target=target, detail=detail)
        )
        await session.flush()
    except Exception as exc:  # noqa: BLE001
        log.warning("audit_log_failed", action=action, error=str(exc))
