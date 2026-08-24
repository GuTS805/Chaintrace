"""Officer authentication: password hashing, JWT issuance/verification, and the
FastAPI dependency that protects routes."""

from app.auth import audit
from app.auth.deps import get_current_officer, get_optional_officer
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "audit",
    "create_access_token",
    "decode_access_token",
    "get_current_officer",
    "get_optional_officer",
    "hash_password",
    "verify_password",
]
