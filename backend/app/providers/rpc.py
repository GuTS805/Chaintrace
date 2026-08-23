"""Shared JSON-RPC plumbing for node-style providers.

JSON-RPC reports failure inside a 200 response, so the HTTP layer's status-code
handling never sees it. This maps the error object onto the same taxonomy the
router already understands, so an RPC rate limit behaves exactly like an HTTP 429.
"""

from __future__ import annotations

from typing import Any

from app.providers.errors import ProviderBadResponse, ProviderRateLimited
from app.providers.http import ResilientHttp

#: JSON-RPC error codes that mean "slow down". -32005 is the de-facto limit-
#: exceeded code used by Infura, Alchemy and most node vendors.
_RATE_LIMIT_CODES = frozenset({-32005, 429})
_RATE_LIMIT_MARKERS = ("rate limit", "too many requests", "capacity", "throughput")


def hex_to_int(value: Any, default: int | None = None) -> int | None:
    """Parse a ``0x``-prefixed quantity. Returns `default` on anything unusable."""
    if not isinstance(value, str) or not value.startswith("0x"):
        return default
    try:
        return int(value, 16)
    except ValueError:
        return default


class JsonRpcClient:
    """Minimal JSON-RPC 2.0 caller layered on the resilient HTTP transport."""

    def __init__(self, provider: str, url: str, http: ResilientHttp) -> None:
        self._provider = provider
        self._url = url
        self._http = http

    async def call(self, method: str, params: list[Any]) -> Any:
        payload = await self._http.post_json(
            self._url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        if not isinstance(payload, dict):
            raise ProviderBadResponse(self._provider, "RPC response was not an object")

        error = payload.get("error")
        if error is not None:
            code = error.get("code") if isinstance(error, dict) else None
            message = (
                str(error.get("message", error)) if isinstance(error, dict) else str(error)
            )
            if code in _RATE_LIMIT_CODES or any(
                m in message.lower() for m in _RATE_LIMIT_MARKERS
            ):
                raise ProviderRateLimited(self._provider, message)
            raise ProviderBadResponse(self._provider, f"RPC error {code}: {message}")

        if "result" not in payload:
            raise ProviderBadResponse(self._provider, "RPC response had no 'result'")
        return payload["result"]
