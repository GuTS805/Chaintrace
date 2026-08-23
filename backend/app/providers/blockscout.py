"""Keyless Blockscout adapter (Etherscan-compatible schema).

Powers the live "trace any wallet" feature: Blockscout's account/txlist endpoint
returns the same schema as Etherscan but needs no API key, so we can pull a real
address on demand and feed it to the unchanged pipeline.
"""

from __future__ import annotations

from typing import Any


async def _fetch(
    action: str, address: str, base_url: str, limit: int, timeout: float
) -> dict[str, Any]:
    import httpx

    params: dict[str, str | int] = {
        "module": "account",
        "action": action,
        "address": address,
        "sort": "asc",
        "page": 1,
        "offset": limit,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(base_url, params=params)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


async def fetch_blockscout_txlist(
    address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0
) -> dict[str, Any]:
    """Native ETH transfers for an address."""
    return await _fetch("txlist", address, base_url, limit, timeout)


async def fetch_blockscout_tokentx(
    address: str, *, base_url: str, limit: int = 100, timeout: float = 20.0
) -> dict[str, Any]:
    """ERC-20 token transfers (USDT/USDC/…) for an address."""
    return await _fetch("tokentx", address, base_url, limit, timeout)
