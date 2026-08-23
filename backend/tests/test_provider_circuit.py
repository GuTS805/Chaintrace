"""Circuit breaker state machine.

Time is injected, so cooldown behaviour is asserted rather than waited for.
"""

from __future__ import annotations

from app.providers.circuit import CircuitBreaker, CircuitState
from app.providers.errors import ProviderUnavailable


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def breaker(clock: Clock, **kw: object) -> CircuitBreaker:
    return CircuitBreaker(
        provider="test", failure_threshold=3, recovery_seconds=30.0, clock=clock, **kw
    )


def boom(msg: str = "down") -> ProviderUnavailable:
    return ProviderUnavailable("test", msg)


def test_starts_closed_and_allows_requests() -> None:
    cb = breaker(Clock())
    assert cb.state is CircuitState.CLOSED
    assert cb.allows_request()


def test_opens_only_at_the_threshold() -> None:
    cb = breaker(Clock())
    cb.record_failure(boom())
    cb.record_failure(boom())
    assert cb.state is CircuitState.CLOSED, "should tolerate a blip below threshold"
    cb.record_failure(boom())
    assert cb.state is CircuitState.OPEN
    assert not cb.allows_request()


def test_success_resets_the_failure_run() -> None:
    """Intermittent failures must not accumulate into an outage."""
    cb = breaker(Clock())
    cb.record_failure(boom())
    cb.record_failure(boom())
    cb.record_success()
    cb.record_failure(boom())
    cb.record_failure(boom())
    assert cb.state is CircuitState.CLOSED


def test_half_opens_after_cooldown_and_allows_one_probe() -> None:
    clock = Clock()
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure(boom())
    assert not cb.allows_request()

    clock.advance(29)
    assert cb.state is CircuitState.OPEN

    clock.advance(2)
    assert cb.state is CircuitState.HALF_OPEN
    assert cb.allows_request(), "first probe should be let through"
    assert not cb.allows_request(), "only one probe at a time"


def test_successful_probe_closes_the_circuit() -> None:
    clock = Clock()
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure(boom())
    clock.advance(31)
    assert cb.allows_request()
    cb.record_success()
    assert cb.state is CircuitState.CLOSED
    assert cb.allows_request()


def test_failed_probe_reopens_immediately() -> None:
    """A failed probe proves the cooldown was too short; do not keep probing."""
    clock = Clock()
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure(boom())
    clock.advance(31)
    assert cb.allows_request()

    cb.record_failure(boom("still down"))
    assert cb.state is CircuitState.OPEN
    assert not cb.allows_request()

    # And the new cooldown is measured from the failed probe, not the original.
    clock.advance(31)
    assert cb.state is CircuitState.HALF_OPEN


def test_health_reports_counters_and_last_error() -> None:
    cb = breaker(Clock())
    cb.record_success()
    cb.record_failure(boom("upstream 503"))
    h = cb.health()
    assert h.provider == "test"
    assert h.total_successes == 1
    assert h.total_failures == 1
    assert h.consecutive_failures == 1
    assert h.last_error is not None and "upstream 503" in h.last_error


def test_health_clears_last_error_on_recovery() -> None:
    cb = breaker(Clock())
    cb.record_failure(boom("blip"))
    cb.record_success()
    assert cb.health().last_error is None
