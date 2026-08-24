"""Password hashing (stdlib PBKDF2, no extra native dependency) and JWT
issuance/verification for officer sessions."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import jwt

from app.config import get_settings

_PBKDF2_ITERATIONS = 260_000
_ALGO_TAG = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    )
    return f"{_ALGO_TAG}${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iterations_s, salt, expected_hex = password_hash.split("$")
    except ValueError:
        return False
    if algo != _ALGO_TAG:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations_s)
    )
    return hmac.compare_digest(digest.hex(), expected_hex)


class TokenPayload(TypedDict):
    sub: str  # officer id, as a string (JWT convention)
    username: str
    full_name: str
    exp: int


def create_access_token(officer_id: int, username: str, full_name: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(officer_id),
        "username": username,
        "full_name": full_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
    return payload  # type: ignore[return-value]
