"""Chain provider abstraction.

Phase 1 ships only the offline FixtureProvider. The live Etherscan/RPC provider
and failover wrapper are deferred (they are not on the offline demo path).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ProviderTx(BaseModel):
    """Normalized transaction as returned by any provider."""

    tx_hash: str
    block_number: int | None = None
    timestamp: datetime
    from_address: str
    to_address: str | None = None
    value_wei: Decimal = Decimal(0)
    gas_used: int | None = None
    gas_price_wei: Decimal | None = None
    asset: str = "ETH"


class WalletInfo(BaseModel):
    address: str
    balance_wei: Decimal | None = None
    is_contract: bool = False
    tx_count: int = 0


def normalize_address(addr: str) -> str:
    """Canonicalize an address for storage/comparison.

    EVM addresses are case-insensitive hex, so lowercasing is safe and is the
    existing convention throughout the store. Tron (and other base58) addresses
    are case-sensitive/checksummed — lowercasing would corrupt them — so they
    pass through unchanged.
    """
    a = addr.strip()
    if a.lower().startswith("0x"):
        return a.lower()
    return a


@runtime_checkable
class ChainProvider(Protocol):
    """Uniform interface over chain data sources."""

    name: str

    async def get_wallet(self, address: str) -> WalletInfo: ...

    async def get_transactions(
        self, address: str, *, limit: int = 1000
    ) -> list[ProviderTx]: ...
