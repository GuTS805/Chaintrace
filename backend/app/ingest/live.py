"""On-demand live ingestion for the 'trace any wallet' feature.

Fetches a real address's transactions from Blockscout (keyless) and imports them
so the existing traversal + attribution pipeline can run on it. Results are cached
in the DB, so a wallet is fetched at most once and then works offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingest.chain_import import import_provider_txs
from app.models import Transaction
from app.providers.base import ProviderTx, normalize_address
from app.providers.blockscout import fetch_blockscout_tokentx, fetch_blockscout_txlist
from app.providers.etherscan import parse_etherscan_tokentx, parse_etherscan_txlist
from app.providers.resilience import ProviderUnavailable, resilient_call
from app.providers.tron import fetch_trongrid_trc20, is_tron_address, parse_trongrid_trc20

log = structlog.get_logger(__name__)

# EVM chains reachable through a Blockscout-compatible instance — same
# account/txlist + tokentx schema as Ethereum, so they share fetch/parse code
# and differ only in base URL + native gas-token symbol. (BNB Smart Chain has
# no public Blockscout instance and BscScan's keyless API was retired, so it
# isn't offered here — adding it would need a paid/free-tier BscScan key.)
EVM_CHAINS: dict[str, str] = {
    "ethereum": "ETH",
    "polygon": "POL",
}


@dataclass
class LiveResult:
    address: str
    imported_transactions: int
    total_transactions: int
    source: str  # "cache" | "blockscout" | "trongrid"
    chain: str = "ethereum"
    # Non-fatal degradation the caller should see, e.g. "token transfers
    # unavailable, provider degraded" — a silently incomplete result would be
    # worse than a slow-but-honest one for a forensic tool.
    warnings: list[str] = field(default_factory=list)


async def _rebuild_clusters(session: AsyncSession) -> None:
    from app.attribution.cluster_builder import rebuild_all_clusters

    await rebuild_all_clusters(session)
    await session.commit()


async def _tx_count(session: AsyncSession, address: str) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(Transaction)
                .where(
                    or_(
                        Transaction.from_address == address,
                        Transaction.to_address == address,
                    )
                )
            )
        ).scalar_one()
    )


def _evm_base_url(chain: str) -> str:
    settings = get_settings()
    return {
        "ethereum": settings.blockscout_base_url,
        "polygon": settings.polygon_blockscout_base_url,
    }[chain]


async def ensure_ingested(
    session: AsyncSession, address: str, *, limit: int = 100, chain: str = "ethereum"
) -> LiveResult:
    """Ensure the wallet's transactions are in the store, fetching live if not.

    ``chain`` picks the EVM chain to query (ethereum/polygon) — it's ignored
    for Tron addresses, which are auto-detected by address shape since Tron's
    base58 format can't be confused with an EVM address.
    """
    addr = normalize_address(address)
    existing = await _tx_count(session, addr)
    if existing > 0:
        return LiveResult(addr, 0, existing, "cache")

    settings = get_settings()
    retry_kwargs = {
        "max_retries": settings.provider_max_retries,
        "base_delay": settings.provider_retry_base_delay,
    }

    if is_tron_address(addr):
        base_url = settings.trongrid_base_url
        payload = await resilient_call(
            lambda: fetch_trongrid_trc20(addr, base_url=base_url, limit=limit),
            key="tron:trongrid",
            **retry_kwargs,
        )
        txs = parse_trongrid_trc20(payload)
        stats = await import_provider_txs(session, txs, chain="tron")
        await session.commit()
        await _rebuild_clusters(session)
        total = await _tx_count(session, addr)
        log.info(
            "live_ingest", address=addr, chain="tron", imported=stats.transactions, total=total
        )
        return LiveResult(addr, stats.transactions, total, "trongrid", chain="tron")

    if chain not in EVM_CHAINS:
        raise ValueError(f"Unsupported chain: {chain!r}")
    native_asset = EVM_CHAINS[chain]
    base_url = _evm_base_url(chain)
    # Native transfers are the primary data — if this fails after retries, the
    # whole call fails loudly rather than returning a hollow "success".
    eth_payload = await resilient_call(
        lambda: fetch_blockscout_txlist(addr, base_url=base_url, limit=limit),
        key=f"{chain}:blockscout",
        **retry_kwargs,
    )
    eth_txs = parse_etherscan_txlist(eth_payload, native_asset=native_asset)

    # ERC-20-style token transfers — secondary. A degraded provider here must
    # not be swallowed into a silently-incomplete "success": the caller is
    # told explicitly that token data may be missing, instead of just getting
    # fewer transactions with no explanation.
    token_txs: list[ProviderTx] = []
    warnings: list[str] = []
    try:
        token_payload = await resilient_call(
            lambda: fetch_blockscout_tokentx(addr, base_url=base_url, limit=limit),
            key=f"{chain}:blockscout",
            **retry_kwargs,
        )
        token_txs = parse_etherscan_tokentx(token_payload)
    except ProviderUnavailable as exc:
        log.warning("tokentx_fetch_degraded", address=addr, error=str(exc))
        warnings.append(
            "Token (ERC-20) transfer data could not be fetched — provider degraded. "
            f"Only native {native_asset} transfers are included; retry to fill in tokens."
        )

    # Tokens first: a token transfer's tx hash also appears in txlist as a value-0
    # call to the token contract; importing the token edge first keeps the real
    # sender->recipient transfer instead of the contract-call duplicate.
    stats = await import_provider_txs(session, token_txs + eth_txs, chain=chain)
    await session.commit()
    await _rebuild_clusters(session)
    total = await _tx_count(session, addr)
    log.info(
        "live_ingest", address=addr, chain=chain, imported=stats.transactions, total=total,
        degraded=bool(warnings),
    )
    return LiveResult(addr, stats.transactions, total, "blockscout", chain=chain, warnings=warnings)
