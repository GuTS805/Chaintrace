"""Resilient HTTP transport shared by every remote provider.

Retry policy, in one place, because getting it subtly different per provider is
how one upstream ends up hammering a rate limit while another gives up too early.

What is retried, and why:
- transport errors and timeouts -- the request may never have arrived;
- 5xx -- the upstream is having a bad moment;
- 429 -- explicitly asked to slow down, and its ``Retry-After`` is honoured over
  our own backoff curve, since the server knows its state and we are guessing.

What is not retried: 4xx other than 429. A malformed request or a bad API key
returns the same answer however many times it is sent, so retrying only delays
the failover that was always going to happen.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import structlog

from app.providers.errors import (
    ProviderBadResponse,
    ProviderRateLimited,
    ProviderUnavailable,
)

log = structlog.get_logger(__name__)

SleepFn = Callable[[float], Awaitable[None]]

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _parse_retry_after(value: str | None) -> float | None:
    """Read a ``Retry-After`` header, seconds form only.

    The HTTP-date form is deliberately ignored: acting on a clock difference
    between us and the upstream is worse than falling back to our own backoff.
    """
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


class ResilientHttp:
    """An HTTP caller with bounded retries, backoff, and typed failures."""

    def __init__(
        self,
        provider: str,
        *,
        timeout: float = 15.0,
        max_attempts: int = 3,
        base_backoff: float = 0.5,
        max_backoff: float = 8.0,
        max_retry_after: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: SleepFn | None = None,
        jitter: Callable[[], float] | None = None,
    ) -> None:
        self._provider = provider
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._base_backoff = base_backoff
        self._max_backoff = max_backoff
        # A server may ask us to wait for minutes. Beyond this we would rather
        # fail over to another provider than hold an investigation open.
        self._max_retry_after = max_retry_after
        self._transport = transport
        self._sleep: SleepFn = sleep or asyncio.sleep
        # Full jitter: without it, several callers rate-limited at the same
        # moment retry in lockstep and rebuild the spike that limited them.
        self._jitter = jitter or random.random

    def _backoff(self, attempt: int) -> float:
        window = min(self._base_backoff * (2**attempt), self._max_backoff)
        return float(window * self._jitter())

    async def get_json(
        self, url: str, *, params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request("GET", url, params=params, headers=headers)

    async def post_json(
        self, url: str, *, json: dict[str, Any], headers: dict[str, str] | None = None
    ) -> Any:
        return await self._request("POST", url, json=json, headers=headers)

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        last: Exception | None = None

        for attempt in range(self._max_attempts):
            try:
                return await self._attempt(method, url, **kwargs)
            except ProviderRateLimited as exc:
                last = exc
                delay = exc.retry_after
                if delay is not None and delay > self._max_retry_after:
                    # Longer than we are willing to hold the caller for.
                    raise
                wait = delay if delay is not None else self._backoff(attempt)
            except ProviderUnavailable as exc:
                last = exc
                wait = self._backoff(attempt)
            # ProviderBadResponse deliberately not caught: identical request,
            # identical garbage.

            if attempt + 1 >= self._max_attempts:
                break
            log.warning(
                "provider_retry",
                provider=self._provider,
                url=url,
                attempt=attempt + 1,
                wait_seconds=round(wait, 3),
                error=str(last),
            )
            await self._sleep(wait)

        assert last is not None
        raise last

    async def _attempt(self, method: str, url: str, **kwargs: Any) -> Any:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(self._provider, f"timeout after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(self._provider, f"transport error: {exc}") from exc

        if resp.status_code == 429:
            raise ProviderRateLimited(
                self._provider,
                "rate limited",
                retry_after=_parse_retry_after(resp.headers.get("Retry-After")),
            )
        if resp.status_code in RETRYABLE_STATUS:
            raise ProviderUnavailable(self._provider, f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise ProviderBadResponse(
                self._provider, f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise ProviderBadResponse(
                self._provider, f"response was not JSON: {resp.text[:200]}"
            ) from exc
