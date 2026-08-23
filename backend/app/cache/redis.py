"""Thin async Redis JSON cache.

Degrades gracefully: if Redis is unreachable, operations no-op rather than break
the request path. A cache is an optimisation, and an investigation that fails
because the optimisation is down is worse than a slow one — this also keeps the
offline demo working with no Redis running at all.
"""

from __future__ import annotations

import json
import uuid
from types import TracebackType
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


def reset_client() -> None:
    """Drop the cached client. Used by tests and after a config change."""
    global _client
    _client = None


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


async def cache_delete(key: str) -> None:
    try:
        await get_client().delete(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("cache_delete_failed", key=key, error=str(exc))


class DistributedLock:
    """Best-effort cross-process lock (SET NX PX).

    Used so that ten investigators opening the same wallet at the same moment
    produce one upstream traversal rather than ten identical ones.

    Best-effort is deliberate and load-bearing: if Redis is unreachable the lock
    is treated as *acquired* and work proceeds. The failure mode is duplicated
    work, which is wasteful; the alternative — blocking every investigation
    because the cache is down — is an outage. Never use this to guard something
    where duplication would be incorrect rather than merely wasteful.
    """

    def __init__(self, key: str, *, ttl_seconds: int = 60) -> None:
        self._key = key
        self._ttl_ms = ttl_seconds * 1000
        # A random token so we only ever release a lock we still hold, rather
        # than one that expired and was retaken by someone else.
        self._token = uuid.uuid4().hex
        self.acquired = False

    async def __aenter__(self) -> DistributedLock:
        try:
            got = await get_client().set(
                self._key, self._token, nx=True, px=self._ttl_ms
            )
            self.acquired = bool(got)
        except Exception as exc:  # noqa: BLE001
            log.warning("lock_unavailable", key=self._key, error=str(exc))
            self.acquired = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self.acquired:
            return
        try:
            client = get_client()
            # Compare-and-delete, so an expired-and-retaken lock is left alone.
            current = await client.get(self._key)
            if current == self._token:
                await client.delete(self._key)
        except Exception as exc_inner:  # noqa: BLE001
            log.warning("lock_release_failed", key=self._key, error=str(exc_inner))
