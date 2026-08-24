"""Officer login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_officer, verify_password
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
    officer = (
        await session.execute(
            select(Officer).where(Officer.username == payload.username)
        )
    ).scalar_one_or_none()
    if officer is None or not officer.is_active:
        raise _INVALID
    if not verify_password(payload.password, officer.password_hash):
        raise _INVALID
    token = create_access_token(officer.id, officer.username, officer.full_name)
    return LoginResponse(access_token=token, officer=OfficerOut.model_validate(officer))


@router.get("/me", response_model=OfficerOut)
async def me(officer: Officer = Depends(get_current_officer)) -> Officer:
    return officer
