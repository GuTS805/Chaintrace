"""Chain identity.

A wallet is identified by ``(chain, address)`` — never by address alone. The same
byte-identical address exists on every EVM chain and belongs to different parties
there, so an address-only identity silently merges unrelated wallets. Every
transaction, label, and investigation therefore carries a chain.
"""

from __future__ import annotations

from enum import StrEnum


class Chain(StrEnum):
    """Chains the platform can hold data for."""

    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    BASE = "base"


#: The chain assumed for rows written before chains were modelled explicitly.
DEFAULT_CHAIN = Chain.ETHEREUM

#: Chains whose addresses are hex and case-insensitive (EIP-55 is a checksum
#: encoding of the same address, so it must be folded before comparison).
EVM_CHAINS = frozenset(
    {Chain.ETHEREUM, Chain.POLYGON, Chain.ARBITRUM, Chain.BASE}
)


def is_evm(chain: Chain | str) -> bool:
    return Chain(chain) in EVM_CHAINS


def normalize_address(address: str, chain: Chain | str = DEFAULT_CHAIN) -> str:
    """Canonicalize an address for storage and comparison.

    EVM addresses are case-folded (0xAbC and 0xabc are the same account).
    Bitcoin addresses are Base58/Bech32 and case-significant, so only surrounding
    whitespace is stripped — lowercasing one would corrupt it.
    """
    address = address.strip()
    if is_evm(chain):
        return address.lower()
    return address
