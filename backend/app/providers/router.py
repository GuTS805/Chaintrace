"""ProviderRouter — one ChainProvider that fronts many.

The router is itself a ``ChainProvider``, which is the point: the ingest layer,
the traversal, and the attribution engine call it exactly as they would call a
single upstream and never learn that failover, caching or circuit breaking
happened. Provider identity stops here.

Order of work for a request:

    cache  ->  in-process coalescing  ->  cross-process single-flight  ->
    first capable provider whose circuit is closed  ->  next on failure

Failures are classified, not merged. A provider that cannot serve an operation is
skipped silently; one that is failing is retried, then dropped and its circuit
opened; one that answered with garbage is dropped without burning retries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog

from app.cache import keys as cache_keys
from app.cache.redis import DistributedLock, cache_get, cache_set
from app.chains import DEFAULT_CHAIN
from app.providers.base import (
    BaseProvider,
    Capability,
    ProviderPage,
    ProviderTx,
    WalletInfo,
)
from app.providers.circuit import CircuitBreaker, CircuitState, ProviderHealth
from app.providers.errors import (
    AllProvidersFailed,
    ProviderError,
    ProviderNotCapable,
)

log = structlog.get_logger(__name__)

T = TypeVar("T")


class RequestCoalescer:
    """Collapses concurrent identical requests inside one process.

    Two investigations opening the same wallet in the same instant should cost
    one upstream call, not two. Waiters share the winner's result — including its
    exception, so a failure is not silently converted into a second attempt that
    the caller did not ask for.
    """

    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Task[Any]] = {}

    async def run(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        existing = self._inflight.get(key)
        if existing is not None:
            result: T = await asyncio.shield(existing)
            return result

        task: asyncio.Task[T] = asyncio.ensure_future(factory())
        self._inflight[key] = task
        try:
            return await task
        finally:
            # Only clear our own entry: a later request may already have started
            # a new task under the same key.
            if self._inflight.get(key) is task:
                del self._inflight[key]

    @property
    def inflight_count(self) -> int:
        return len(self._inflight)


class ProviderRouter(BaseProvider):
    name = "router"

    def __init__(
        self,
        providers: list[BaseProvider],
        *,
        chain: str = DEFAULT_CHAIN.value,
        cache_ttl_seconds: int = 900,
        use_cache: bool = True,
        failure_threshold: int = 3,
        recovery_seconds: float = 30.0,
        lock_wait_seconds: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("ProviderRouter needs at least one provider")
        self.chain = chain
        self._providers = providers
        self._cache_ttl = cache_ttl_seconds
        self._use_cache = use_cache
        self._lock_wait = lock_wait_seconds
        self._sleep = sleep or asyncio.sleep
        self._coalescer = RequestCoalescer()
        self._breakers = {
            p.name: CircuitBreaker(
                provider=p.name,
                failure_threshold=failure_threshold,
                recovery_seconds=recovery_seconds,
            )
            for p in providers
        }

    # -- introspection ---------------------------------------------------
    @property
    def capabilities(self) -> frozenset[Capability]:  # type: ignore[override]
        """The union of what the chain can do, not the intersection.

        The router can serve history as long as *some* provider indexes it.
        """
        caps: set[Capability] = set()
        for p in self._providers:
            caps |= set(p.capabilities)
        return frozenset(caps)

    def health(self) -> list[ProviderHealth]:
        return [self._breakers[p.name].health() for p in self._providers]

    def _capable(self, capability: Capability) -> list[BaseProvider]:
        return [p for p in self._providers if capability in p.capabilities]

    # -- core failover ---------------------------------------------------
    async def _attempt_chain(
        self,
        capability: Capability,
        operation: str,
        call: Callable[[BaseProvider], Awaitable[T]],
    ) -> T:
        candidates = self._capable(capability)
        if not candidates:
            raise ProviderNotCapable(
                self.name, f"no configured provider can serve {capability.value}"
            )

        failures: dict[str, Exception] = {}
        skipped_open: list[str] = []

        for provider in candidates:
            breaker = self._breakers[provider.name]
            if not breaker.allows_request():
                skipped_open.append(provider.name)
                continue
            try:
                result = await call(provider)
            except ProviderNotCapable as exc:
                # A routing fact, not an outage: do not penalise the provider.
                failures[provider.name] = exc
                continue
            except ProviderError as exc:
                breaker.record_failure(exc)
                failures[provider.name] = exc
                log.warning(
                    "provider_failed",
                    provider=provider.name,
                    operation=operation,
                    error=str(exc),
                    circuit=breaker.state.value,
                )
                continue
            breaker.record_success()
            return result

        for name in skipped_open:
            failures.setdefault(
                name, ProviderError(name, "circuit open; not attempted")
            )
        raise AllProvidersFailed(operation, failures)

    # -- cached, single-flight fetch -------------------------------------
    async def _cached(
        self, key: str, loader: Callable[[], Awaitable[T]], decode: Callable[[Any], T]
    ) -> T:
        if not self._use_cache:
            return await self._coalescer.run(key, loader)

        hit = await cache_get(key)
        if hit is not None:
            log.debug("provider_cache_hit", key=key)
            return decode(hit)

        async def fetch() -> T:
            # Cross-process single-flight. Losing the lock does not mean waiting
            # forever: after a bounded pause we re-check the cache and, failing
            # that, fetch anyway. Duplicated work beats a stalled investigation.
            async with DistributedLock(cache_keys.lock_key(key)) as lock:
                if not lock.acquired:
                    await self._sleep(self._lock_wait)
                    second = await cache_get(key)
                    if second is not None:
                        return decode(second)
                value = await loader()
                await cache_set(key, _encode(value), ttl_seconds=self._cache_ttl)
                return value

        return await self._coalescer.run(key, fetch)

    # -- ChainProvider surface -------------------------------------------
    async def get_wallet(self, address: str) -> WalletInfo:
        key = cache_keys.wallet_key(self.chain, address)

        async def load() -> WalletInfo:
            return await self._attempt_chain(
                Capability.WALLET_INFO,
                "get_wallet",
                lambda p: p.get_wallet(address),
            )

        return await self._cached(key, load, lambda raw: WalletInfo.model_validate(raw))

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        key = cache_keys.tx_page_key(self.chain, address, cursor, limit)

        async def load() -> ProviderPage:
            async def fetch(p: BaseProvider) -> ProviderPage:
                page = await p.get_transaction_page(address, limit=limit, cursor=cursor)
                # Stamp provenance here, where the answering provider is known.
                page.source = p.name
                return page

            return await self._attempt_chain(
                Capability.TRANSACTION_HISTORY, "get_transaction_page", fetch
            )

        return await self._cached(key, load, lambda raw: ProviderPage.model_validate(raw))

    async def get_transactions(
        self, address: str, *, limit: int = 1000
    ) -> list[ProviderTx]:
        """Page through history.

        Failover happens per page, so one provider dying mid-walk does not lose
        the pages already collected — the next page simply comes from elsewhere.
        """
        return await super().get_transactions(address, limit=limit)


def _encode(value: Any) -> Any:
    """Serialize a pydantic result for the JSON cache."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


__all__ = [
    "CircuitState",
    "ProviderRouter",
    "RequestCoalescer",
]
