"""Etherscan-compatible real-chain adapter.

Proves the pipeline is real-chain-ready: it parses the exact Etherscan
``account / txlist`` response schema into the same ``ProviderTx`` used everywhere
else, so traversal, signals, and the attribution engine work on real data
unchanged. Live fetching is optional (needs an API key); the demo replays a saved
snapshot offline and never depends on live hot-wallet traversal.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.providers.base import ProviderTx


def parse_etherscan_txlist(payload: dict[str, Any]) -> list[ProviderTx]:
    """Normalize an Etherscan ``txlist`` JSON payload into ProviderTx rows."""
    results = payload.get("result", [])
    if not isinstance(results, list):
        raise ValueError("Unexpected Etherscan payload: 'result' is not a list")

    txs: list[ProviderTx] = []
    for item in results:
        to_addr = (item.get("to") or "").strip().lower() or None
        try:
            ts = datetime.fromtimestamp(int(item["timeStamp"]), tz=UTC)
        except (KeyError, ValueError, OverflowError):
            continue
        txs.append(
            ProviderTx(
                tx_hash=str(item["hash"]),
                block_number=int(item["blockNumber"]) if item.get("blockNumber") else None,
                timestamp=ts,
                from_address=str(item["from"]).strip().lower(),
                to_address=to_addr,
                value_wei=Decimal(str(item.get("value", "0"))),
                gas_used=int(item["gasUsed"]) if item.get("gasUsed") else None,
                gas_price_wei=Decimal(str(item["gasPrice"])) if item.get("gasPrice") else None,
                asset="ETH",
            )
        )
    return txs


def parse_etherscan_tokentx(payload: dict[str, Any]) -> list[ProviderTx]:
    """Normalize an Etherscan/Blockscout ``tokentx`` payload (ERC-20 transfers).

    Value is kept in the token's raw integer units; ``asset`` carries the symbol
    (e.g. USDT). Stablecoin flows are where most laundering happens, so tracing
    them through the same pipeline matters.
    """
    results = payload.get("result", [])
    if not isinstance(results, list):
        raise ValueError("Unexpected token payload: 'result' is not a list")

    txs: list[ProviderTx] = []
    for item in results:
        to_addr = (item.get("to") or "").strip().lower() or None
        try:
            ts = datetime.fromtimestamp(int(item["timeStamp"]), tz=UTC)
        except (KeyError, ValueError, OverflowError):
            continue
        symbol = str(item.get("tokenSymbol") or "TOKEN").strip() or "TOKEN"
        txs.append(
            ProviderTx(
                tx_hash=str(item["hash"]),
                block_number=int(item["blockNumber"]) if item.get("blockNumber") else None,
                timestamp=ts,
                from_address=str(item["from"]).strip().lower(),
                to_address=to_addr,
                value_wei=Decimal(str(item.get("value", "0"))),
                gas_used=int(item["gasUsed"]) if item.get("gasUsed") else None,
                gas_price_wei=Decimal(str(item["gasPrice"])) if item.get("gasPrice") else None,
                asset=symbol,
            )
        )
    return txs


async def fetch_etherscan_txlist(
    address: str,
    api_key: str,
    *,
    base_url: str = "https://api.etherscan.io/api",
    limit: int = 200,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch normal transactions for an address from Etherscan (optional, live).

    Requires an API key. Not used by the offline demo.
    """
    import httpx

    params: dict[str, str | int] = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": limit,
        "sort": "asc",
        "apikey": api_key,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(base_url, params=params)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data
