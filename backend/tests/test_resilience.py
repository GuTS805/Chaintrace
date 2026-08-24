"""Provider resilience: retry, circuit breaker, and the classification that
keeps a provider failure from ever being mistaken for an attribution result."""

from __future__ import annotations

import pytest

from app.providers.resilience import (
    CircuitBreaker,
    ProviderBadRequest,
    ProviderCircuitOpen,
    ProviderUnavailable,
    classify_httpx_error,
    resilient_call,
)


async def test_transient_failure_retries_then_succeeds() -> None:
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderUnavailable("simulated 503")
        return "ok"

    result = await resilient_call(
        flaky, key="test:flaky", breaker=CircuitBreaker(), max_retries=3, base_delay=0.001
    )
    assert result == "ok"
    assert attempts == 3


async def test_transient_failure_exhausts_retries_and_raises() -> None:
    async def always_fails() -> str:
        raise ProviderUnavailable("simulated timeout")

    with pytest.raises(ProviderUnavailable):
        await resilient_call(
            always_fails, key="test:always-fails", breaker=CircuitBreaker(),
            max_retries=2, base_delay=0.001,
        )


async def test_bad_request_is_never_retried() -> None:
    attempts = 0

    async def bad_request() -> str:
        nonlocal attempts
        attempts += 1
        raise ProviderBadRequest("simulated 400")

    with pytest.raises(ProviderBadRequest):
        await resilient_call(
            bad_request, key="test:bad-request", breaker=CircuitBreaker(),
            max_retries=5, base_delay=0.001,
        )
    assert attempts == 1  # no retry at all


async def test_circuit_opens_after_threshold_and_fails_fast() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)

    async def always_fails() -> str:
        raise ProviderUnavailable("down")

    # Two calls, each exhausting its own retries — trips the breaker.
    for _ in range(2):
        with pytest.raises(ProviderUnavailable):
            await resilient_call(
                always_fails, key="test:circuit", breaker=breaker, max_retries=0, base_delay=0.001
            )

    assert breaker.status("test:circuit") == "open"

    # A third call must fail immediately as ProviderCircuitOpen — no attempt
    # at all, not even a network round trip.
    attempted = False

    async def would_succeed() -> str:
        nonlocal attempted
        attempted = True
        return "should not run"

    with pytest.raises(ProviderCircuitOpen):
        await resilient_call(would_succeed, key="test:circuit", breaker=breaker)
    assert attempted is False


async def test_circuit_half_opens_after_cooldown_and_closes_on_success() -> None:
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.0)  # cooldown elapses instantly

    async def fails_once() -> str:
        raise ProviderUnavailable("down")

    with pytest.raises(ProviderUnavailable):
        await resilient_call(
            fails_once, key="test:half-open", breaker=breaker, max_retries=0, base_delay=0.001
        )
    assert breaker.status("test:half-open") == "open"

    async def succeeds() -> str:
        return "recovered"

    result = await resilient_call(succeeds, key="test:half-open", breaker=breaker)
    assert result == "recovered"
    assert breaker.status("test:half-open") == "closed"


def test_classify_httpx_status_errors() -> None:
    import httpx

    def _status_error(status: int) -> httpx.HTTPStatusError:
        request = httpx.Request("GET", "https://example.test")
        response = httpx.Response(status, request=request)
        return httpx.HTTPStatusError("boom", request=request, response=response)

    assert isinstance(classify_httpx_error(_status_error(500)), ProviderUnavailable)
    assert isinstance(classify_httpx_error(_status_error(429)), ProviderUnavailable)
    assert isinstance(classify_httpx_error(_status_error(404)), ProviderBadRequest)
    assert isinstance(classify_httpx_error(_status_error(400)), ProviderBadRequest)


def test_classify_httpx_network_errors_are_transient() -> None:
    import httpx

    assert isinstance(classify_httpx_error(httpx.ConnectTimeout("timeout")), ProviderUnavailable)
    assert isinstance(classify_httpx_error(httpx.ConnectError("refused")), ProviderUnavailable)
