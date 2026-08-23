"""Offline fixture provider tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.providers import FixtureProvider, ProviderTx, WalletInfo


async def test_fixture_provider_serves_txs_and_wallets() -> None:
    provider = FixtureProvider(
        wallets=[WalletInfo(address="0xAbC", balance_wei=Decimal("5"))],
        transactions=[
            ProviderTx(
                tx_hash="0x1",
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                from_address="0xabc",
                to_address="0xdef",
                value_wei=Decimal("3"),
            ),
            ProviderTx(
                tx_hash="0x2",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                from_address="0xabc",
                to_address="0xghi",
                value_wei=Decimal("1"),
            ),
        ],
    )

    # Address lookup is case-insensitive.
    wallet = await provider.get_wallet("0xABC")
    assert wallet.balance_wei == Decimal("5")

    # Transactions come back sorted by timestamp.
    txs = await provider.get_transactions("0xabc")
    assert [t.tx_hash for t in txs] == ["0x2", "0x1"]

    # Counterparties are reachable too (needed for reverse expansion).
    incoming = await provider.get_transactions("0xdef")
    assert incoming[0].tx_hash == "0x1"


def test_fixture_provider_satisfies_protocol() -> None:
    from app.providers.base import ChainProvider

    provider = FixtureProvider(wallets=[], transactions=[])
    assert isinstance(provider, ChainProvider)
