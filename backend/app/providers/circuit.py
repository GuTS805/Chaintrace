"""Circuit breaker and health tracking per provider.

Retries help when an upstream is briefly unwell. They actively hurt when it is
down: every request pays the full retry budget before failing over, so a dead
provider makes each investigation slower than having no provider at all. The
breaker converts "this is failing" into "stop asking for a while".

States:
    CLOSED    -- normal.
    OPEN      -- refuse immediately; fail over without touching the network.
    HALF_OPEN -- after the cooldown, let exactly one probe through. Success
                 closes the circuit; failure re-opens it for another cooldown.

Only transient failures count. A ``ProviderNotCapable`` is a routing fact, not an
outage, and a ``ProviderBadResponse`` for one malformed address should not take a
healthy provider offline for every other caller.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

log = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class ProviderHealth:
    """Point-in-time view of one provider, for /ready and for operators."""

    provider: str
    state: CircuitState
    consecutive_failures: int
    total_failures: int
    total_successes: int
    last_error: str | None
    opened_at: float | None

    @property
    def healthy(self) -> bool:
        return self.state is not CircuitState.CLOSED or self.consecutive_failures == 0


@dataclass
class CircuitBreaker:
    """Per-provider breaker. Not shared across providers by design."""

    provider: str
    failure_threshold: int = 3
    recovery_seconds: float = 30.0
    clock: Callable[[], float] = time.monotonic

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _consecutive: int = field(default=0, init=False)
    _total_failures: int = field(default=0, init=False)
    _total_successes: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)
    _last_error: str | None = field(default=None, init=False)
    # Ensures only one probe is in flight while half-open.
    _probe_taken: bool = field(default=False, init=False)

    @property
    def state(self) -> CircuitState:
        self._maybe_half_open()
        return self._state

    def _maybe_half_open(self) -> None:
        if self._state is not CircuitState.OPEN or self._opened_at is None:
            return
        if self.clock() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            self._probe_taken = False
            log.info("circuit_half_open", provider=self.provider)

    def allows_request(self) -> bool:
        """True when a call may proceed right now."""
        state = self.state
        if state is CircuitState.CLOSED:
            return True
        if state is CircuitState.HALF_OPEN and not self._probe_taken:
            self._probe_taken = True
            return True
        return False

    def record_success(self) -> None:
        self._total_successes += 1
        self._consecutive = 0
        self._last_error = None
        if self._state is not CircuitState.CLOSED:
            log.info("circuit_closed", provider=self.provider)
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._probe_taken = False

    def record_failure(self, error: Exception) -> None:
        self._total_failures += 1
        self._consecutive += 1
        self._last_error = str(error)

        # A failed probe re-opens immediately: the cooldown just proved too short.
        if self._state is CircuitState.HALF_OPEN:
            self._open()
            return
        if self._consecutive >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        already = self._state is CircuitState.OPEN
        self._state = CircuitState.OPEN
        self._opened_at = self.clock()
        self._probe_taken = False
        if not already:
            log.warning(
                "circuit_opened",
                provider=self.provider,
                consecutive_failures=self._consecutive,
                error=self._last_error,
            )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider,
            state=self.state,
            consecutive_failures=self._consecutive,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
            last_error=self._last_error,
            opened_at=self._opened_at,
        )
