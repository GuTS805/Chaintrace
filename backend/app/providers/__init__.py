"""Chain data providers.

Everything above this package sees only ``ChainProvider``, ``ProviderTx`` and
``WalletInfo``. Use ``build_router`` to assemble the configured chain rather than
instantiating a concrete provider directly, so callers never depend on which
upstream happens to be available.
"""

from app.providers.alchemy import AlchemyProvider
from app.providers.base import (
    BaseProvider,
    Capability,
    ChainProvider,
    ProviderPage,
    ProviderTx,
    WalletInfo,
)
from app.providers.errors import (
    AllProvidersFailed,
    ProviderBadResponse,
    ProviderError,
    ProviderNotCapable,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.providers.etherscan import (
    BlockscoutProvider,
    EtherscanCompatibleProvider,
    EtherscanProvider,
)
from app.providers.factory import build_router
from app.providers.fixture import FixtureProvider
from app.providers.infura import InfuraProvider
from app.providers.router import ProviderRouter, RequestCoalescer

__all__ = [
    "AlchemyProvider",
    "AllProvidersFailed",
    "BaseProvider",
    "BlockscoutProvider",
    "Capability",
    "ChainProvider",
    "EtherscanCompatibleProvider",
    "EtherscanProvider",
    "FixtureProvider",
    "InfuraProvider",
    "ProviderBadResponse",
    "ProviderError",
    "ProviderNotCapable",
    "ProviderPage",
    "ProviderRateLimited",
    "ProviderRouter",
    "ProviderTx",
    "ProviderUnavailable",
    "RequestCoalescer",
    "WalletInfo",
    "build_router",
]
