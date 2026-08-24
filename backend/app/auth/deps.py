"""FastAPI dependency that resolves the authenticated Officer from a Bearer token."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.db.session import get_session
from app.models import Officer

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Log in via POST /auth/login.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_officer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Officer:
    if credentials is None:
        raise _CREDENTIALS_ERROR
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise _CREDENTIALS_ERROR
    officer = await session.get(Officer, int(payload["sub"]))
    if officer is None or not officer.is_active:
        raise _CREDENTIALS_ERROR
    return officer


async def get_optional_officer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Officer | None:
    """Like get_current_officer, but returns None instead of raising 401.

    Used only where an endpoint stays reachable without login but still wants
    to attribute the action to an officer when one is present.
    """
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    officer = await session.get(Officer, int(payload["sub"]))
    if officer is None or not officer.is_active:
        return None
    return officer
