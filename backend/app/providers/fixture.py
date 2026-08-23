"""Offline fixture provider — serves normalized data from an in-memory dataset.

Runs with zero network access. Phase 2 populates it from the synthetic scenario
generator (which also produces the classifier's labeled training data).
"""

from __future__ import annotations

from collections import defaultdict

from app.providers.base import ChainProvider, ProviderTx, WalletInfo


def _norm(address: str) -> str:
    return address.strip().lower()


class FixtureProvider(ChainProvider):
    """A ChainProvider backed by lists of wallets/transactions held in memory."""

    name = "fixture"

    def __init__(
        self, wallets: list[WalletInfo], transactions: list[ProviderTx]
    ) -> None:
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

    async def get_transactions(
        self, address: str, *, limit: int = 1000
    ) -> list[ProviderTx]:
        txs = self._by_from.get(_norm(address), [])
        return sorted(txs, key=lambda t: t.timestamp)[:limit]
