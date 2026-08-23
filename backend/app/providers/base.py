"""Chain provider abstraction.

Everything above this layer — traversal, signals, the attribution engine — sees
only ``ProviderTx`` and ``WalletInfo``. No component that reasons about evidence
knows which upstream produced a row, which is what lets providers be swapped,
routed around, or added without touching the attribution path.

Providers declare *capabilities* rather than raising "not implemented" at call
time. A JSON-RPC node can report a balance but has no address index, so it cannot
answer transaction history at all; the router needs to know that before it picks
a provider, not after it has spent a retry budget finding out.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.chains import DEFAULT_CHAIN


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


class Capability(StrEnum):
    """What a provider can actually answer."""

    WALLET_INFO = "WALLET_INFO"
    TRANSACTION_HISTORY = "TRANSACTION_HISTORY"


class ProviderPage(BaseModel):
    """One page of transaction history.

    ``partial`` marks a page the provider truncated or could only answer in part.
    It is surfaced rather than smoothed over: a traversal built on silently
    incomplete history would under-report reachability, and "no evidence found"
    from missing data looks exactly like "no evidence exists".
    """

    transactions: list[ProviderTx] = Field(default_factory=list)
    next_cursor: str | None = None
    partial: bool = False
    #: Which provider actually served this page. Set by the router, and read only
    #: by the ingest layer so imported rows carry truthful provenance. Nothing in
    #: the attribution path consumes it — a page is the same evidence whichever
    #: upstream produced it.
    source: str | None = None


@runtime_checkable
class ChainProvider(Protocol):
    """Uniform interface over chain data sources."""

    name: str
    chain: str
    capabilities: frozenset[Capability]

    async def get_wallet(self, address: str) -> WalletInfo: ...

    async def get_transactions(
        self, address: str, *, limit: int = 1000
    ) -> list[ProviderTx]: ...

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage: ...


class BaseProvider:
    """Shared scaffolding for concrete providers.

    Supplies the paging loop so each provider only implements a single page, and
    a default capability set that a subclass narrows when it cannot do something.
    """

    name: str = "base"
    chain: str = DEFAULT_CHAIN.value
    capabilities: frozenset[Capability] = frozenset(
        {Capability.WALLET_INFO, Capability.TRANSACTION_HISTORY}
    )

    #: Hard ceiling on pages walked in one `get_transactions`, so a provider that
    #: keeps handing back cursors cannot spin forever on a hot wallet.
    max_pages: int = 20

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    async def get_wallet(self, address: str) -> WalletInfo:  # pragma: no cover
        raise NotImplementedError

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:  # pragma: no cover
        raise NotImplementedError

    async def get_transactions(
        self, address: str, *, limit: int = 1000
    ) -> list[ProviderTx]:
        """Walk pages until `limit` rows are collected or the source runs out."""
        collected: list[ProviderTx] = []
        seen: set[str] = set()
        cursor: str | None = None

        for _ in range(self.max_pages):
            remaining = limit - len(collected)
            if remaining <= 0:
                break
            page = await self.get_transaction_page(
                address, limit=remaining, cursor=cursor
            )
            for tx in page.transactions:
                # Pages can overlap at their boundaries; a duplicated hash would
                # become a duplicated graph edge and inflate every count built on
                # it, so dedupe here rather than downstream.
                if tx.tx_hash in seen:
                    continue
                seen.add(tx.tx_hash)
                collected.append(tx)
            if not page.next_cursor:
                break
            cursor = page.next_cursor

        collected.sort(key=lambda t: t.timestamp)
        return collected[:limit]
