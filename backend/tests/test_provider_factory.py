"""Provider assembly from settings, and ingest through the router."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingest.chain_import import import_from_router
from app.models import Transaction
from app.providers.base import BaseProvider, ProviderPage, ProviderTx
from app.providers.factory import build_providers, build_router
from app.providers.fixture import FixtureProvider
from app.providers.router import ProviderRouter

T0 = datetime(2024, 3, 1, tzinfo=UTC)


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {
        "ETHERSCAN_API_KEY": "",
        "ALCHEMY_API_KEY": "",
        "INFURA_API_KEY": "",
        "PROVIDER_ALLOW_KEYLESS": False,
    }
    base.update(kw)
    return Settings(**base)  # type: ignore[arg-type]


# --- assembly -------------------------------------------------------------


def test_providers_without_credentials_are_skipped() -> None:
    """A chain of four configured providers with no keys is really a chain of none."""
    assert build_providers(settings()) == []


def test_only_the_keyed_providers_are_built() -> None:
    built = build_providers(settings(ETHERSCAN_API_KEY="k", ALCHEMY_API_KEY="a"))
    assert [p.name for p in built] == ["etherscan", "alchemy"]


def test_blockscout_needs_an_explicit_opt_in() -> None:
    """Keyless must not mean an offline run silently acquires a network dependency."""
    assert build_providers(settings()) == []
    built = build_providers(settings(PROVIDER_ALLOW_KEYLESS=True))
    assert [p.name for p in built] == ["blockscout"]


def test_order_follows_the_configured_preference() -> None:
    built = build_providers(
        settings(
            ETHERSCAN_API_KEY="k",
            ALCHEMY_API_KEY="a",
            PROVIDER_ORDER="alchemy,etherscan",
        )
    )
    assert [p.name for p in built] == ["alchemy", "etherscan"]


def test_unknown_provider_names_are_ignored() -> None:
    built = build_providers(
        settings(ETHERSCAN_API_KEY="k", PROVIDER_ORDER="etherscan,nonesuch")
    )
    assert [p.name for p in built] == ["etherscan"]


def test_building_with_nothing_configured_is_a_clear_error() -> None:
    with pytest.raises(RuntimeError, match="No chain providers are configured"):
        build_router(settings())


def test_a_fixture_provider_can_be_the_last_resort() -> None:
    router = build_router(
        settings(), extra=[FixtureProvider(wallets=[], transactions=[])]
    )
    assert [h.provider for h in router.health()] == ["fixture"]


def test_extra_providers_go_last() -> None:
    router = build_router(
        settings(ETHERSCAN_API_KEY="k"),
        extra=[FixtureProvider(wallets=[], transactions=[])],
    )
    assert [h.provider for h in router.health()] == ["etherscan", "fixture"]


# --- ingest through the router -------------------------------------------


class PagedProvider(BaseProvider):
    """Two pages, so the import loop is actually exercised."""

    name = "paged"
    chain = "ethereum"

    def __init__(self) -> None:
        self.calls = 0

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        self.calls += 1
        if cursor is None:
            return ProviderPage(transactions=[_tx(1), _tx(2)], next_cursor="2")
        return ProviderPage(transactions=[_tx(3)])


def _tx(i: int) -> ProviderTx:
    return ProviderTx(
        tx_hash=f"0x{i:064x}",
        block_number=100 + i,
        timestamp=T0,
        from_address="0xaaa",
        to_address="0xbbb",
        value_wei=Decimal(i),
    )


async def test_import_walks_pages_and_records_provenance(session: AsyncSession) -> None:
    router = ProviderRouter([PagedProvider()], use_cache=False)
    stats = await import_from_router(session, router, "0xaaa")
    await session.commit()

    assert stats.transactions == 3
    rows = (await session.execute(select(Transaction))).scalars().all()
    assert len(rows) == 3
    # The provider that actually served the page, not a deployment-wide guess.
    assert {r.provider for r in rows} == {"paged"}
    assert {r.chain for r in rows} == {"ethereum"}


async def test_import_is_idempotent(session: AsyncSession) -> None:
    router = ProviderRouter([PagedProvider()], use_cache=False)
    await import_from_router(session, router, "0xaaa")
    await session.commit()

    second = await import_from_router(session, router, "0xaaa")
    await session.commit()

    assert second.transactions == 0
    assert second.skipped == 3


async def test_import_records_the_failing_over_provider(session: AsyncSession) -> None:
    """After failover the rows must name the upstream that actually answered."""
    from app.providers.errors import ProviderUnavailable

    class Dead(BaseProvider):
        name = "dead"
        chain = "ethereum"

        async def get_transaction_page(
            self, address: str, *, limit: int = 1000, cursor: str | None = None
        ) -> ProviderPage:
            raise ProviderUnavailable("dead", "down")

    router = ProviderRouter([Dead(), PagedProvider()], use_cache=False)
    await import_from_router(session, router, "0xaaa")
    await session.commit()

    rows = (await session.execute(select(Transaction))).scalars().all()
    assert {r.provider for r in rows} == {"paged"}
