"""Router behaviour: failover, capability routing, circuits, cache, coalescing."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.cache import redis as redis_module
from app.providers.base import (
    BaseProvider,
    Capability,
    ProviderPage,
    ProviderTx,
    WalletInfo,
)
from app.providers.circuit import CircuitState
from app.providers.errors import (
    AllProvidersFailed,
    ProviderBadResponse,
    ProviderNotCapable,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.providers.router import ProviderRouter, RequestCoalescer

T0 = datetime(2024, 3, 1, tzinfo=UTC)


def make_tx(i: int) -> ProviderTx:
    return ProviderTx(
        tx_hash=f"0x{i:064x}",
        timestamp=T0,
        from_address="0xaaa",
        to_address="0xbbb",
        value_wei=Decimal(i),
    )


class StubProvider(BaseProvider):
    """A provider whose outcome each call is scripted."""

    def __init__(
        self,
        name: str,
        *,
        outcomes: list[Any] | None = None,
        capabilities: frozenset[Capability] | None = None,
    ) -> None:
        self.name = name
        self.chain = "ethereum"
        if capabilities is not None:
            self.capabilities = capabilities
        self._outcomes = outcomes or []
        self.calls = 0

    def _next(self) -> Any:
        self.calls += 1
        if not self._outcomes:
            return ProviderPage(transactions=[make_tx(1)])
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        return self._next()

    async def get_wallet(self, address: str) -> WalletInfo:
        result = self._next()
        if isinstance(result, WalletInfo):
            return result
        return WalletInfo(address=address, tx_count=1)


def router(providers: list[BaseProvider], **kw: Any) -> ProviderRouter:
    kw.setdefault("use_cache", False)
    return ProviderRouter(providers, **kw)


# --- failover -------------------------------------------------------------


async def test_first_healthy_provider_wins_and_others_are_untouched() -> None:
    primary = StubProvider("primary")
    fallback = StubProvider("fallback")
    await router([primary, fallback]).get_transaction_page("0xabc")
    assert primary.calls == 1
    assert fallback.calls == 0


async def test_fails_over_on_a_transient_error() -> None:
    primary = StubProvider("primary", outcomes=[ProviderUnavailable("primary", "503")])
    fallback = StubProvider("fallback", outcomes=[ProviderPage(transactions=[make_tx(7)])])
    page = await router([primary, fallback]).get_transaction_page("0xabc")
    assert [t.tx_hash for t in page.transactions] == [f"0x{7:064x}"]
    assert fallback.calls == 1


async def test_fails_over_on_a_rate_limit() -> None:
    primary = StubProvider("primary", outcomes=[ProviderRateLimited("primary", "slow down")])
    fallback = StubProvider("fallback")
    await router([primary, fallback]).get_transaction_page("0xabc")
    assert fallback.calls == 1


async def test_fails_over_on_a_bad_response() -> None:
    primary = StubProvider("primary", outcomes=[ProviderBadResponse("primary", "garbage")])
    fallback = StubProvider("fallback")
    await router([primary, fallback]).get_transaction_page("0xabc")
    assert fallback.calls == 1


async def test_all_failed_reports_every_provider() -> None:
    a = StubProvider("a", outcomes=[ProviderUnavailable("a", "down")])
    b = StubProvider("b", outcomes=[ProviderBadResponse("b", "garbage")])
    with pytest.raises(AllProvidersFailed) as exc:
        await router([a, b]).get_transaction_page("0xabc")
    assert set(exc.value.failures) == {"a", "b"}
    assert "down" in str(exc.value)
    assert "garbage" in str(exc.value)


# --- capability routing ---------------------------------------------------


async def test_a_provider_without_the_capability_is_never_called() -> None:
    """Infura-shaped: can report a balance, has no address index."""
    node = StubProvider("node", capabilities=frozenset({Capability.WALLET_INFO}))
    indexer = StubProvider("indexer")
    await router([node, indexer]).get_transaction_page("0xabc")
    assert node.calls == 0
    assert indexer.calls == 1


async def test_capability_gap_is_reported_not_silently_empty() -> None:
    node = StubProvider("node", capabilities=frozenset({Capability.WALLET_INFO}))
    with pytest.raises(ProviderNotCapable):
        await router([node]).get_transaction_page("0xabc")


async def test_not_capable_does_not_open_a_circuit() -> None:
    """A routing fact must not be recorded as an outage."""
    picky = StubProvider("picky", outcomes=[ProviderNotCapable("picky", "nope")])
    healthy = StubProvider("healthy")
    r = router([picky, healthy], failure_threshold=1)
    await r.get_transaction_page("0xabc")
    states = {h.provider: h.state for h in r.health()}
    assert states["picky"] is CircuitState.CLOSED


async def test_router_capabilities_are_the_union() -> None:
    node = StubProvider("node", capabilities=frozenset({Capability.WALLET_INFO}))
    indexer = StubProvider(
        "indexer", capabilities=frozenset({Capability.TRANSACTION_HISTORY})
    )
    caps = router([node, indexer]).capabilities
    assert caps == frozenset({Capability.WALLET_INFO, Capability.TRANSACTION_HISTORY})


# --- circuits -------------------------------------------------------------


async def test_repeated_failures_open_the_circuit_and_stop_the_calls() -> None:
    bad = StubProvider("bad", outcomes=[ProviderUnavailable("bad", "down")])
    good = StubProvider("good")
    r = router([bad, good], failure_threshold=2)

    await r.get_transaction_page("0xabc")
    await r.get_transaction_page("0xabc")
    assert bad.calls == 2

    before = bad.calls
    await r.get_transaction_page("0xabc")
    assert bad.calls == before, "an open circuit must not be dialled"
    assert {h.provider: h.state for h in r.health()}["bad"] is CircuitState.OPEN


async def test_an_open_primary_still_reports_in_the_failure_list() -> None:
    bad = StubProvider("bad", outcomes=[ProviderUnavailable("bad", "down")])
    r = router([bad], failure_threshold=1)
    with pytest.raises(AllProvidersFailed):
        await r.get_transaction_page("0xabc")
    with pytest.raises(AllProvidersFailed) as exc:
        await r.get_transaction_page("0xabc")
    assert "circuit open" in str(exc.value)


async def test_health_exposes_every_provider() -> None:
    r = router([StubProvider("a"), StubProvider("b")])
    assert [h.provider for h in r.health()] == ["a", "b"]


# --- coalescing -----------------------------------------------------------


async def test_concurrent_identical_requests_hit_upstream_once() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    class SlowProvider(BaseProvider):
        name = "slow"
        chain = "ethereum"

        async def get_transaction_page(
            self, address: str, *, limit: int = 1000, cursor: str | None = None
        ) -> ProviderPage:
            calls["n"] += 1
            started.set()
            await release.wait()
            return ProviderPage(transactions=[make_tx(1)])

    r = router([SlowProvider()])
    task_a = asyncio.create_task(r.get_transaction_page("0xabc"))
    await started.wait()
    task_b = asyncio.create_task(r.get_transaction_page("0xabc"))
    await asyncio.sleep(0)
    release.set()

    page_a, page_b = await asyncio.gather(task_a, task_b)
    assert calls["n"] == 1, "the second caller should have joined the first"
    assert page_a.transactions[0].tx_hash == page_b.transactions[0].tx_hash


async def test_coalescer_shares_the_failure_too() -> None:
    """A joined waiter must see the real outcome, not a silent retry."""
    coalescer = RequestCoalescer()
    calls = {"n": 0}

    async def boom() -> str:
        calls["n"] += 1
        await asyncio.sleep(0)
        raise RuntimeError("upstream exploded")

    results = await asyncio.gather(
        coalescer.run("k", boom), coalescer.run("k", boom), return_exceptions=True
    )
    assert calls["n"] == 1
    assert all(isinstance(r, RuntimeError) for r in results)


async def test_coalescer_clears_its_slot_after_completion() -> None:
    coalescer = RequestCoalescer()

    async def one() -> int:
        return 1

    assert await coalescer.run("k", one) == 1
    assert coalescer.inflight_count == 0


# --- cache ----------------------------------------------------------------


class FakeRedis:
    """Just enough Redis for the cache and lock paths."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(
        self, key: str, value: str, ex: int | None = None,
        nx: bool = False, px: int | None = None,
    ) -> bool | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(redis_module, "get_client", lambda: fake)
    return fake


async def test_second_request_is_served_from_cache(fake_redis: FakeRedis) -> None:
    provider = StubProvider("p")
    r = ProviderRouter([provider], use_cache=True)

    first = await r.get_transaction_page("0xabc")
    second = await r.get_transaction_page("0xabc")

    assert provider.calls == 1, "the cached page should not be refetched"
    assert [t.tx_hash for t in second.transactions] == [
        t.tx_hash for t in first.transactions
    ]


async def test_cache_key_ignores_which_provider_answered(fake_redis: FakeRedis) -> None:
    """Failover must not double upstream traffic on the next request."""
    primary = StubProvider("primary", outcomes=[ProviderUnavailable("primary", "down")])
    fallback = StubProvider("fallback")
    r = ProviderRouter([primary, fallback], use_cache=True)

    await r.get_transaction_page("0xabc")
    fallback_calls = fallback.calls
    await r.get_transaction_page("0xabc")
    assert fallback.calls == fallback_calls


async def test_different_addresses_do_not_share_a_cache_entry(
    fake_redis: FakeRedis,
) -> None:
    provider = StubProvider("p")
    r = ProviderRouter([provider], use_cache=True)
    await r.get_transaction_page("0xaaa")
    await r.get_transaction_page("0xbbb")
    assert provider.calls == 2


async def test_different_chains_do_not_share_a_cache_entry(
    fake_redis: FakeRedis,
) -> None:
    """The same address on two chains is two different wallets."""
    eth = ProviderRouter([StubProvider("p")], chain="ethereum", use_cache=True)
    poly = ProviderRouter([StubProvider("p")], chain="polygon", use_cache=True)
    await eth.get_transaction_page("0xabc")
    await poly.get_transaction_page("0xabc")
    keys = [k for k in fake_redis.store if k.startswith("txpage:")]
    assert len(keys) == 2


async def test_wallet_lookups_are_cached(fake_redis: FakeRedis) -> None:
    provider = StubProvider("p", outcomes=[WalletInfo(address="0xabc", tx_count=9)])
    r = ProviderRouter([provider], use_cache=True)
    assert (await r.get_wallet("0xabc")).tx_count == 9
    assert (await r.get_wallet("0xabc")).tx_count == 9
    assert provider.calls == 1


async def test_a_dead_cache_does_not_break_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An investigation must not fail because an optimisation is unavailable."""

    class DeadRedis:
        async def get(self, key: str) -> str:
            raise ConnectionError("redis is down")

        async def set(self, *a: Any, **kw: Any) -> bool:
            raise ConnectionError("redis is down")

        async def delete(self, key: str) -> int:
            raise ConnectionError("redis is down")

    monkeypatch.setattr(redis_module, "get_client", lambda: DeadRedis())
    r = ProviderRouter([StubProvider("p")], use_cache=True)
    page = await r.get_transaction_page("0xabc")
    assert len(page.transactions) == 1


# --- construction ---------------------------------------------------------


def test_router_requires_at_least_one_provider() -> None:
    with pytest.raises(ValueError):
        ProviderRouter([])
