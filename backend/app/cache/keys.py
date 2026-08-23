"""Cache key builders, in one place.

Keys are chain-scoped for the same reason the database is: the identical address
on two chains is two different wallets, and a key that omits the chain would
serve one wallet's history for the other.

Keys never include the provider name. A normalized ``ProviderTx`` is the same fact
whichever upstream produced it, so a page fetched from Blockscout must satisfy a
later request that would have gone to Etherscan — otherwise failover silently
doubles upstream traffic.
"""

from __future__ import annotations


def wallet_key(chain: str, address: str) -> str:
    return f"wallet:{chain}:{address.lower()}"


def tx_page_key(chain: str, address: str, cursor: str | None, limit: int) -> str:
    return f"txpage:{chain}:{address.lower()}:{cursor or '1'}:{limit}"


def tx_key(chain: str, tx_hash: str) -> str:
    return f"tx:{chain}:{tx_hash.lower()}"


def labels_key(chain: str, address: str) -> str:
    return f"labels:{chain}:{address.lower()}"


def investigation_key(investigation_id: str) -> str:
    return f"investigation:{investigation_id}"


def lock_key(name: str) -> str:
    return f"lock:{name}"
