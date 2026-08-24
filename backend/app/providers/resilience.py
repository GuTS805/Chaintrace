"""Provider resilience: retry, circuit breaker, and a hard distinction between
"the provider/network failed" and "the provider answered and there's no
evidence" — the two must never be conflated, especially anywhere near an
attribution or risk verdict. A confidently-wrong "insufficient evidence"
because Blockscout was down for a few seconds is worse for a law-enforcement
tool than a clear "try again" error.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

import structlog

log = structlog.get_logger(__name__)

T = TypeVar("T")


class ProviderError(Exception):
    """Base for a classified provider-call failure."""


class ProviderUnavailable(ProviderError):
    """Transient: timeout, connection error, 5xx, or rate-limited (429).
    Retry-eligible, and counts toward the circuit breaker."""


class ProviderBadRequest(ProviderError):
    """Permanent for this input: a 4xx other than 429 (e.g. an address the
    provider itself rejects). Not retried, and does not count as a provider
    health failure — the provider answered fine, the request was bad."""


class ProviderCircuitOpen(ProviderUnavailable):
    """The circuit breaker is open for this provider — failing fast without
    even attempting a call, because recent calls have already shown it's down."""


# --------------------------------------------------------------- circuit breaker --


class _CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _Circuit:
    state: _CircuitState = _CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: float = 0.0


@dataclass
class CircuitBreaker:
    """One breaker instance per provider (module-level singleton in practice,
    so state persists across requests within the process — a breaker that
    resets every request would never actually trip)."""

    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    _circuits: dict[str, _Circuit] = field(default_factory=dict)

    def _get(self, key: str) -> _Circuit:
        return self._circuits.setdefault(key, _Circuit())

    def allow(self, key: str) -> bool:
        c = self._get(key)
        if c.state is _CircuitState.CLOSED:
            return True
        if c.state is _CircuitState.OPEN:
            if time.monotonic() - c.opened_at >= self.cooldown_seconds:
                c.state = _CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: allow exactly one probe through

    def record_success(self, key: str) -> None:
        c = self._get(key)
        if c.state is not _CircuitState.CLOSED:
            log.info("circuit_closed", provider=key)
        c.state = _CircuitState.CLOSED
        c.consecutive_failures = 0

    def record_failure(self, key: str) -> None:
        c = self._get(key)
        c.consecutive_failures += 1
        if c.state is _CircuitState.HALF_OPEN or c.consecutive_failures >= self.failure_threshold:
            if c.state is not _CircuitState.OPEN:
                log.warning(
                    "circuit_opened", provider=key, consecutive_failures=c.consecutive_failures
                )
            c.state = _CircuitState.OPEN
            c.opened_at = time.monotonic()

    def status(self, key: str) -> str:
        return self._get(key).state.value


# One breaker per (chain, provider) pair, shared across requests for the life
# of the process. A single global instance keeps the whole app's view of
# "is this provider currently healthy" consistent.
def _build_default_breaker() -> CircuitBreaker:
    from app.config import get_settings

    settings = get_settings()
    return CircuitBreaker(
        failure_threshold=settings.provider_circuit_failure_threshold,
        cooldown_seconds=settings.provider_circuit_cooldown_seconds,
    )


_default_breaker = _build_default_breaker()


def get_default_breaker() -> CircuitBreaker:
    return _default_breaker


# --------------------------------------------------------------------- retry --


async def resilient_call(
    fn: Callable[[], Awaitable[T]],
    *,
    key: str,
    breaker: CircuitBreaker | None = None,
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 4.0,
) -> T:
    """Run `fn` with retry + circuit breaker for the named provider `key`.

    - `ProviderBadRequest` is never retried and never trips the breaker — the
      provider is healthy, the input was bad.
    - `ProviderUnavailable` is retried with exponential backoff + jitter, up
      to `max_retries` extra attempts, and counts toward the breaker.
    - If the breaker is open for `key`, fails immediately as
      `ProviderCircuitOpen` without attempting a call at all.
    """
    breaker = breaker or _default_breaker
    if not breaker.allow(key):
        raise ProviderCircuitOpen(f"{key}: circuit open, provider recently failed repeatedly")

    attempt = 0
    last_exc: ProviderUnavailable | None = None
    while attempt <= max_retries:
        try:
            result = await fn()
        except ProviderBadRequest:
            raise  # not a provider-health issue — surface immediately, no retry
        except ProviderUnavailable as exc:
            last_exc = exc
            breaker.record_failure(key)
            if attempt == max_retries:
                break
            delay = min(max_delay, base_delay * (2**attempt)) * (0.5 + random.random())
            log.warning(
                "provider_retry", provider=key, attempt=attempt + 1, delay_s=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)
            attempt += 1
            continue
        else:
            breaker.record_success(key)
            return result
    assert last_exc is not None  # loop only exits via break after a failure
    raise last_exc


def classify_httpx_error(exc: Exception) -> ProviderError:
    """Map an httpx exception to a retry-eligible vs. permanent provider error.

    Every provider adapter's raw ``httpx`` call funnels through this so the
    classification (and therefore the retry/circuit-breaker behavior) is
    identical across Blockscout, TronGrid, and any future provider.
    """
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429 or status >= 500:
            return ProviderUnavailable(f"HTTP {status}: {exc}")
        return ProviderBadRequest(f"HTTP {status}: {exc}")
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError | httpx.NetworkError):
        return ProviderUnavailable(str(exc))
    return ProviderUnavailable(str(exc))
