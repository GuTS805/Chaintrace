"""Offline fixture provider — serves normalized data from an in-memory dataset.

Runs with zero network access. Populated from the synthetic scenario generator
(which also produces the classifier's labeled training data), and used as the
last link in the provider chain so the demo completes with no credentials and no
connectivity.
"""

from __future__ import annotations

from collections import defaultdict

from app.chains import DEFAULT_CHAIN
from app.providers.base import (
    BaseProvider,
    Capability,
    ProviderPage,
    ProviderTx,
    WalletInfo,
)


def _norm(address: str) -> str:
    return address.strip().lower()


class FixtureProvider(BaseProvider):
    """A ChainProvider backed by lists of wallets/transactions held in memory."""

    name = "fixture"
    requires_api_key = False
    capabilities = frozenset({Capability.WALLET_INFO, Capability.TRANSACTION_HISTORY})

    def __init__(
        self,
        wallets: list[WalletInfo],
        transactions: list[ProviderTx],
        *,
        chain: str = DEFAULT_CHAIN.value,
    ) -> None:
        self.chain = chain
        self._wallets: dict[str, WalletInfo] = {_norm(w.address): w for w in wallets}
        self._by_from: dict[str, list[ProviderTx]] = defaultdict(list)
        for tx in transactions:
            self._by_from[_norm(tx.from_address)].append(tx)
            if tx.to_address:
                # Ensure counterparties are reachable via get_transactions too.
                self._by_from[_norm(tx.to_address)].append(tx)

    async def get_wallet(self, address: str) -> WalletInfo:
        addr = _norm(address)
        return self._wallets.get(addr, WalletInfo(address=addr))

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        offset = int(cursor) if cursor else 0
        txs = sorted(self._by_from.get(_norm(address), []), key=lambda t: t.timestamp)
        window = txs[offset : offset + limit]
        end = offset + len(window)
        return ProviderPage(
            transactions=window,
            next_cursor=str(end) if end < len(txs) else None,
        )
