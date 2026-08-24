"""Officer login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_officer, verify_password
from app.auth.rate_limit import get_default_limiter
from app.db.session import get_session
from app.models import Officer
from app.schemas.auth import LoginRequest, LoginResponse, OfficerOut

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password."
)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    limiter = get_default_limiter()
    # Keyed by username (case-insensitive), not IP: the threat this defends
    # against is guessing one account's password, which a rotating IP doesn't
    # help an attacker escape. It's a cooldown, not a lockout, so it can't be
    # used to deny a real officer service by deliberately failing their name.
    key = payload.username.strip().lower()
    wait = limiter.seconds_until_allowed(key)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again shortly.",
            headers={"Retry-After": str(int(wait) + 1)},
        )

    officer = (
        await session.execute(
            select(Officer).where(Officer.username == payload.username)
        )
    ).scalar_one_or_none()
    if officer is None or not officer.is_active or not verify_password(
        payload.password, officer.password_hash
    ):
        limiter.record_failure(key)
        raise _INVALID
    limiter.record_success(key)
    token = create_access_token(officer.id, officer.username, officer.full_name)
    return LoginResponse(access_token=token, officer=OfficerOut.model_validate(officer))


@router.get("/me", response_model=OfficerOut)
async def me(officer: Officer = Depends(get_current_officer)) -> Officer:
    return officer
