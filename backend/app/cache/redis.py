"""Thin async Redis JSON cache.

Degrades gracefully: if Redis is unreachable, operations no-op rather than break
the request path (important for offline demo reliability).
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            get_settings().redis_url, encoding="utf-8", decode_responses=True
        )
    return _client


async def cache_get(key: str) -> Any | None:
    try:
        raw = await get_client().get(key)
    except Exception as exc:  # noqa: BLE001 - cache must never break the request
        log.warning("cache_get_failed", key=key, error=str(exc))
        return None
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    try:
        await get_client().set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        log.warning("cache_set_failed", key=key, error=str(exc))
