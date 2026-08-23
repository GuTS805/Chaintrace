"""Keyless TronGrid adapter — TRC20 (USDT and other token) transfers.

Powers the Tron leg of multi-chain tracing: USDT-TRC20 is the dominant
laundering rail into Indian exchanges, so it's the first non-EVM chain added.
Mirrors ``blockscout.py``'s "no API key needed for the offline-safe demo path"
philosophy — an optional ``TRONGRID_API_KEY`` header only raises rate limits,
it is never required.

Scope note: only TRC20 transfers are parsed (not native TRX transfers). The
TronGrid TRC20 endpoint returns addresses already in Tron's native base58
format, so no hex<->base58 conversion is needed and addresses stay consistent
with ``normalize_address``'s "leave non-EVM addresses untouched" rule. Native
TRX transfers are nested inside signed contract data (addresses in hex) and
are a natural follow-up, not needed for the USDT-TRC20 tracing this ships.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.providers.base import ProviderTx, normalize_address

# Tron base58 addresses start with "T" and are 34 characters long.
TRON_ADDRESS_PREFIX = "T"
TRON_ADDRESS_LENGTH = 34


def is_tron_address(address: str) -> bool:
    a = address.strip()
    return (
        len(a) == TRON_ADDRESS_LENGTH
        and a.startswith(TRON_ADDRESS_PREFIX)
        and a.isalnum()
    )


async def fetch_trongrid_trc20(
    address: str,
    *,
    base_url: str,
    limit: int = 100,
    timeout: float = 20.0,
    contract_address: str | None = None,
) -> dict[str, Any]:
    """TRC20 transfers (USDT/…) for an address, keyless."""
    import httpx

    params: dict[str, str | int] = {
        "limit": limit,
        "only_confirmed": "true",
    }
    if contract_address:
        params["contract_address"] = contract_address
    url = f"{base_url.rstrip('/')}/v1/accounts/{address}/transactions/trc20"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def parse_trongrid_trc20(payload: dict[str, Any]) -> list[ProviderTx]:
    """Normalize a TronGrid ``transactions/trc20`` payload into ProviderTx rows."""
    results = payload.get("data", [])
    if not isinstance(results, list):
        raise ValueError("Unexpected TronGrid payload: 'data' is not a list")

    txs: list[ProviderTx] = []
    for item in results:
        to_addr = item.get("to")
        from_addr = item.get("from")
        if not to_addr or not from_addr:
            continue
        try:
            ts = datetime.fromtimestamp(int(item["block_timestamp"]) / 1000, tz=UTC)
        except (KeyError, ValueError, OverflowError, TypeError):
            continue
        token_info = item.get("token_info") or {}
        symbol = str(token_info.get("symbol") or "TRC20").strip() or "TRC20"
        txs.append(
            ProviderTx(
                tx_hash=str(item["transaction_id"]),
                block_number=None,
                timestamp=ts,
                from_address=normalize_address(str(from_addr)),
                to_address=normalize_address(str(to_addr)),
                value_wei=Decimal(str(item.get("value", "0"))),
                asset=symbol,
            )
        )
    return txs
