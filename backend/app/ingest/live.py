"""On-demand live ingestion for the 'trace any wallet' feature.

Fetches a real address's transactions from Blockscout (keyless) and imports them
so the existing traversal + attribution pipeline can run on it. Results are cached
in the DB, so a wallet is fetched at most once and then works offline.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingest.chain_import import import_provider_txs
from app.models import Transaction
from app.providers.base import ProviderTx, normalize_address
from app.providers.blockscout import fetch_blockscout_tokentx, fetch_blockscout_txlist
from app.providers.etherscan import parse_etherscan_tokentx, parse_etherscan_txlist
from app.providers.tron import fetch_trongrid_trc20, is_tron_address, parse_trongrid_trc20

log = structlog.get_logger(__name__)


@dataclass
class LiveResult:
    address: str
    imported_transactions: int
    total_transactions: int
    source: str  # "cache" | "blockscout" | "trongrid"


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


async def ensure_ingested(
    session: AsyncSession, address: str, *, limit: int = 100
) -> LiveResult:
    """Ensure the wallet's transactions are in the store, fetching live if not."""
    addr = normalize_address(address)
    existing = await _tx_count(session, addr)
    if existing > 0:
        return LiveResult(addr, 0, existing, "cache")

    if is_tron_address(addr):
        base_url = get_settings().trongrid_base_url
        payload = await fetch_trongrid_trc20(addr, base_url=base_url, limit=limit)
        txs = parse_trongrid_trc20(payload)
        stats = await import_provider_txs(session, txs, chain="tron")
        await session.commit()
        await _rebuild_clusters(session)
        total = await _tx_count(session, addr)
        log.info(
            "live_ingest", address=addr, chain="tron", imported=stats.transactions, total=total
        )
        return LiveResult(addr, stats.transactions, total, "trongrid")

    base_url = get_settings().blockscout_base_url
    eth_payload = await fetch_blockscout_txlist(addr, base_url=base_url, limit=limit)
    eth_txs = parse_etherscan_txlist(eth_payload)

    # ERC-20 (USDT/USDC/…) transfers — best-effort so ETH still imports if this fails.
    token_txs: list[ProviderTx] = []
    try:
        token_payload = await fetch_blockscout_tokentx(addr, base_url=base_url, limit=limit)
        token_txs = parse_etherscan_tokentx(token_payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("tokentx_fetch_failed", address=addr, error=str(exc))

    # Tokens first: a token transfer's tx hash also appears in txlist as a value-0
    # call to the token contract; importing the token edge first keeps the real
    # sender->recipient transfer instead of the contract-call duplicate.
    stats = await import_provider_txs(session, token_txs + eth_txs, chain="ethereum")
    await session.commit()
    await _rebuild_clusters(session)
    total = await _tx_count(session, addr)
    log.info("live_ingest", address=addr, imported=stats.transactions, total=total)
    return LiveResult(addr, stats.transactions, total, "blockscout")
