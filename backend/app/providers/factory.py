"""Build the configured provider chain.

Callers ask for a router, not a provider. Which upstreams exist, in what order,
and whether any of them are usable is a deployment concern that stops here.

A provider whose credentials are absent is skipped rather than constructed and
left to fail on first use: a chain of three configured providers where two have
no API key is really a chain of one, and it should say so at startup instead of
discovering it mid-investigation.
"""

from __future__ import annotations

import structlog

from app.chains import DEFAULT_CHAIN
from app.config import Settings, get_settings
from app.providers.alchemy import AlchemyProvider
from app.providers.base import BaseProvider
from app.providers.etherscan import BlockscoutProvider, EtherscanProvider
from app.providers.http import ResilientHttp
from app.providers.infura import InfuraProvider
from app.providers.router import ProviderRouter

log = structlog.get_logger(__name__)


def _http(name: str, settings: Settings) -> ResilientHttp:
    return ResilientHttp(
        name,
        timeout=settings.provider_timeout_seconds,
        max_attempts=settings.provider_max_attempts,
    )


def _build_one(
    name: str, settings: Settings, chain: str
) -> BaseProvider | None:
    """Construct one provider, or None when it is not usable here."""
    if name == "etherscan":
        if not settings.etherscan_api_key:
            return None
        return EtherscanProvider(
            api_key=settings.etherscan_api_key,
            base_url=settings.etherscan_base_url,
            chain=chain,
            http=_http("etherscan", settings),
            page_size=settings.provider_page_size,
        )

    if name == "blockscout":
        # Keyless, so it is only enabled deliberately. Otherwise every offline
        # run would silently acquire a live network dependency.
        if not settings.provider_allow_keyless:
            return None
        return BlockscoutProvider(
            base_url=settings.blockscout_base_url,
            chain=chain,
            http=_http("blockscout", settings),
            page_size=settings.provider_page_size,
        )

    if name == "alchemy":
        if not settings.alchemy_api_key:
            return None
        return AlchemyProvider(
            api_key=settings.alchemy_api_key,
            base_url=settings.alchemy_base_url,
            chain=chain,
            http=_http("alchemy", settings),
        )

    if name == "infura":
        if not settings.infura_api_key:
            return None
        return InfuraProvider(
            api_key=settings.infura_api_key,
            base_url=settings.infura_base_url,
            chain=chain,
            http=_http("infura", settings),
        )

    log.warning("provider_unknown", provider=name)
    return None


def build_providers(
    settings: Settings | None = None, *, chain: str = DEFAULT_CHAIN.value
) -> list[BaseProvider]:
    """Instantiate every configured, usable provider in preference order."""
    settings = settings or get_settings()
    built: list[BaseProvider] = []
    skipped: list[str] = []

    for name in settings.provider_order_list:
        provider = _build_one(name, settings, chain)
        if provider is None:
            skipped.append(name)
            continue
        built.append(provider)

    log.info(
        "providers_configured",
        chain=chain,
        enabled=[p.name for p in built],
        skipped=skipped,
    )
    return built


def build_router(
    settings: Settings | None = None,
    *,
    chain: str = DEFAULT_CHAIN.value,
    extra: list[BaseProvider] | None = None,
) -> ProviderRouter:
    """Assemble the router.

    ``extra`` is appended last, which makes it the final fallback — the natural
    slot for a ``FixtureProvider`` so an offline run still completes.
    """
    settings = settings or get_settings()
    providers = build_providers(settings, chain=chain)
    if extra:
        providers.extend(extra)
    if not providers:
        raise RuntimeError(
            "No chain providers are configured. Set an API key (ETHERSCAN_API_KEY, "
            "ALCHEMY_API_KEY, INFURA_API_KEY), or set PROVIDER_ALLOW_KEYLESS=true "
            "to use Blockscout, or pass a FixtureProvider via `extra`."
        )
    return ProviderRouter(
        providers,
        chain=chain,
        cache_ttl_seconds=settings.provider_cache_ttl_seconds,
        use_cache=settings.provider_cache_enabled,
        failure_threshold=settings.provider_failure_threshold,
        recovery_seconds=settings.provider_recovery_seconds,
    )
