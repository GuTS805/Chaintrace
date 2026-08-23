"""Keyless Blockscout adapter (Etherscan-compatible schema).

Powers the live "trace any wallet" feature: Blockscout's account/txlist endpoint
returns the same schema as Etherscan but needs no API key, so we can pull a real
address on demand and feed it to the unchanged pipeline.
"""

from __future__ import annotations

from typing import Any


async def fetch_blockscout_txlist(
    address: str,
    *,
    base_url: str,
    limit: int = 100,
    timeout: float = 20.0,
) -> dict[str, Any]:
    import httpx

    params: dict[str, str | int] = {
        "module": "account",
        "action": "txlist",
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
