"""Login request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class OfficerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    badge_no: str | None
    department: str | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    officer: OfficerOut
