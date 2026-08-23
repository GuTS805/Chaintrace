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
from app.providers.base import ProviderTx
from app.providers.blockscout import fetch_blockscout_tokentx, fetch_blockscout_txlist
from app.providers.etherscan import parse_etherscan_tokentx, parse_etherscan_txlist

log = structlog.get_logger(__name__)


@dataclass
class LiveResult:
    address: str
    imported_transactions: int
    total_transactions: int
    source: str  # "cache" | "blockscout"


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
    addr = address.strip().lower()
    existing = await _tx_count(session, addr)
    if existing > 0:
        return LiveResult(addr, 0, existing, "cache")

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
    stats = await import_provider_txs(session, token_txs + eth_txs)
    await session.commit()
    total = await _tx_count(session, addr)
    log.info("live_ingest", address=addr, imported=stats.transactions, total=total)
    return LiveResult(addr, stats.transactions, total, "blockscout")
