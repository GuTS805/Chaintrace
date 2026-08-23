"""Import real-chain transactions into the store (Etherscan schema).

Offline (replay a saved snapshot):
    python -m app.ingest.chain_import --file data/realchain/sample_etherscan_txlist.json

Live (optional, needs ETHERSCAN_API_KEY) — snapshot a real low-degree wallet and
save it so the demo can replay it offline:
    python -m app.ingest.chain_import --address 0x... --save data/realchain/<name>.json

The imported rows feed the exact same traversal + attribution pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.base import ProviderTx
from app.providers.etherscan import fetch_etherscan_txlist, parse_etherscan_txlist

log = structlog.get_logger(__name__)


@dataclass
class ImportStats:
    transactions: int = 0
    wallets: int = 0
    skipped: int = 0


async def import_provider_txs(
    session: AsyncSession, txs: list[ProviderTx]
) -> ImportStats:
    """Idempotently upsert wallets + transactions from normalized ProviderTx rows."""
    from app.models import Transaction, Wallet

    stats = ImportStats()
    known_tx = {
        row[0] for row in (await session.execute(select(Transaction.tx_hash))).all()
    }
    known_wallets = {
        row[0] for row in (await session.execute(select(Wallet.address))).all()
    }

    seen: dict[str, list[datetime]] = {}
    for tx in txs:
        for addr in (tx.from_address, tx.to_address):
            if addr:
                seen.setdefault(addr, []).append(tx.timestamp)

    for tx in txs:
        if tx.tx_hash in known_tx:
            stats.skipped += 1
            continue
        for addr in (tx.from_address, tx.to_address):
            if addr and addr not in known_wallets:
                ts = sorted(seen.get(addr, []))
                session.add(
                    Wallet(
                        address=addr,
                        first_seen=ts[0] if ts else None,
                        last_seen=ts[-1] if ts else None,
                    )
                )
                known_wallets.add(addr)
                stats.wallets += 1
        session.add(
            Transaction(
                tx_hash=tx.tx_hash,
                block_number=tx.block_number,
                timestamp=tx.timestamp,
                from_address=tx.from_address,
                to_address=tx.to_address,
                value_wei=tx.value_wei,
                gas_used=tx.gas_used,
                gas_price_wei=tx.gas_price_wei,
                asset=tx.asset,
            )
        )
        known_tx.add(tx.tx_hash)
        stats.transactions += 1

    await session.flush()
    return stats


async def _from_file(path: Path) -> list[ProviderTx]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_etherscan_txlist(payload)


async def _from_live(address: str, save: Path | None) -> list[ProviderTx]:
    from app.config import get_settings

    api_key = get_settings().etherscan_api_key
    if not api_key:
        raise SystemExit("ETHERSCAN_API_KEY is not set; cannot fetch live data.")
    payload = await fetch_etherscan_txlist(address, api_key)
    if save is not None:
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info("snapshot_saved", path=str(save), count=len(payload.get("result", [])))
    return parse_etherscan_txlist(payload)


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Import real-chain transactions.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Saved Etherscan txlist JSON.")
    group.add_argument("--address", type=str, help="Address to fetch live (needs API key).")
    parser.add_argument("--save", type=Path, help="Save a live fetch to this JSON path.")
    args = parser.parse_args()

    txs = (
        await _from_file(args.file)
        if args.file
        else await _from_live(args.address, args.save)
    )

    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        stats = await import_provider_txs(session, txs)
        await session.commit()
        result = {
            "parsed": len(txs),
            "imported_transactions": stats.transactions,
            "new_wallets": stats.wallets,
            "skipped_existing": stats.skipped,
        }
        log.info("chain_import_complete", **result)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
