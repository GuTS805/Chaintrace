"""Retry, backoff and rate-limit behaviour of the shared HTTP transport.

Sleeps are injected and recorded rather than performed, so the timing policy is
asserted directly instead of being inferred from a slow test.
"""

from __future__ import annotations

import httpx
import pytest

from app.providers.errors import (
    ProviderBadResponse,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.providers.http import ResilientHttp

URL = "https://example.test/api"


class Recorder:
    """Captures the delays the client would have slept for."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def client(
    handler, *, max_attempts: int = 3, recorder: Recorder | None = None, **kw
) -> tuple[ResilientHttp, Recorder]:
    rec = recorder or Recorder()
    return (
        ResilientHttp(
            "test",
            max_attempts=max_attempts,
            transport=httpx.MockTransport(handler),
            sleep=rec,
            # Deterministic full-jitter: always the top of the window.
            jitter=lambda: 1.0,
            **kw,
        ),
        rec,
    )


async def test_success_makes_one_call() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url)
        return httpx.Response(200, json={"ok": True})

    http, rec = client(handler)
    assert await http.get_json(URL) == {"ok": True}
    assert len(calls) == 1
    assert rec.waits == []


async def test_retries_5xx_then_succeeds() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    http, rec = client(handler)
    assert await http.get_json(URL) == {"ok": True}
    assert attempts["n"] == 3
    # Exponential: 0.5 * 2^0, 0.5 * 2^1.
    assert rec.waits == [0.5, 1.0]


async def test_gives_up_after_max_attempts() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503)

    http, rec = client(handler, max_attempts=3)
    with pytest.raises(ProviderUnavailable):
        await http.get_json(URL)
    assert attempts["n"] == 3
    # Slept between attempts, never after the final one.
    assert len(rec.waits) == 2


async def test_backoff_is_capped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    http, rec = client(handler, max_attempts=8, max_backoff=2.0)
    with pytest.raises(ProviderUnavailable):
        await http.get_json(URL)
    assert max(rec.waits) == 2.0


async def test_429_is_retried_and_honours_retry_after() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "4"})
        return httpx.Response(200, json={"ok": True})

    http, rec = client(handler)
    assert await http.get_json(URL) == {"ok": True}
    # The server's own guidance wins over our backoff curve.
    assert rec.waits == [4.0]


async def test_absurd_retry_after_fails_over_instead_of_waiting() -> None:
    """Holding an investigation open for minutes is worse than failing over."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "600"})

    http, rec = client(handler, max_retry_after=30.0)
    with pytest.raises(ProviderRateLimited):
        await http.get_json(URL)
    assert rec.waits == []


async def test_unparseable_retry_after_falls_back_to_backoff() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            # HTTP-date form; deliberately not honoured.
            return httpx.Response(
                429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
            )
        return httpx.Response(200, json={"ok": True})

    http, rec = client(handler)
    assert await http.get_json(URL) == {"ok": True}
    assert rec.waits == [0.5]


async def test_4xx_is_not_retried() -> None:
    """A bad key or malformed request returns the same answer every time."""
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(403, text="forbidden")

    http, rec = client(handler)
    with pytest.raises(ProviderBadResponse):
        await http.get_json(URL)
    assert attempts["n"] == 1
    assert rec.waits == []


async def test_non_json_body_is_a_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>maintenance</html>")

    http, _ = client(handler)
    with pytest.raises(ProviderBadResponse):
        await http.get_json(URL)


async def test_timeout_is_retried_as_unavailable() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ReadTimeout("too slow", request=request)

    http, _ = client(handler, max_attempts=2)
    with pytest.raises(ProviderUnavailable):
        await http.get_json(URL)
    assert attempts["n"] == 2


async def test_transport_error_is_retried() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json={"ok": True})

    http, _ = client(handler)
    assert await http.get_json(URL) == {"ok": True}
    assert attempts["n"] == 2
