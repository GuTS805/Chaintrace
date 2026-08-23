"""Seed the synthetic demo scenarios into the database (offline, idempotent).

`make seed-demo` runs this. It first ingests the bundled real labels, then
writes the four synthetic scenario graphs. Re-running is safe: wallets,
transactions and labels are all upserted, never duplicated.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import LabelCategory, LabelSource
from app.ingest.labels import ingest_all
from app.models import Label, Transaction, Vasp, Wallet
from app.synthetic.scenarios import build_all_scenarios
from app.synthetic.types import Scenario

log = structlog.get_logger(__name__)


@dataclass
class SeedStats:
    scenarios: int = 0
    wallets: int = 0
    transactions: int = 0
    labels: int = 0
    vasps: int = 0
    unknown_wallets: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "scenarios": self.scenarios,
            "wallets": self.wallets,
            "transactions": self.transactions,
            "labels": self.labels,
            "vasps": self.vasps,
            "unknown_wallets": self.unknown_wallets,
        }


async def _get_or_create_vasp(
    session: AsyncSession, name: str, cache: dict[str, Vasp]
) -> tuple[Vasp, bool]:
    if name in cache:
        return cache[name], False
    existing = (
        await session.execute(select(Vasp).where(Vasp.name == name))
    ).scalar_one_or_none()
    created = existing is None
    if existing is None:
        existing = Vasp(name=name)
        session.add(existing)
        await session.flush()
    cache[name] = existing
    return existing, created


async def _seed_scenario(
    session: AsyncSession,
    scenario: Scenario,
    known_wallets: set[str],
    known_tx: set[str],
    vasp_cache: dict[str, Vasp],
    stats: SeedStats,
) -> None:
    # First/last-seen per address from this scenario's transactions.
    seen: dict[str, list[datetime]] = {}
    for tx in scenario.transactions:
        for addr in (tx.from_address, tx.to_address):
            if addr:
                seen.setdefault(addr, []).append(tx.timestamp)

    for w in scenario.wallets:
        if w.address in known_wallets:
            continue
        ts = sorted(seen.get(w.address, []))
        session.add(
            Wallet(
                address=w.address,
                is_contract=w.is_contract,
                tx_count=w.tx_count,
                balance_wei=w.balance_wei,
                first_seen=ts[0] if ts else None,
                last_seen=ts[-1] if ts else None,
            )
        )
        known_wallets.add(w.address)
        stats.wallets += 1

    for tx in scenario.transactions:
        if tx.tx_hash in known_tx:
            continue
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

    for lbl in scenario.labels:
        # Skip if the address already carries any label (bundled labels win).
        exists = (
            await session.execute(
                select(Label.id).where(Label.address == lbl.address)
            )
        ).first()
        if exists is not None:
            continue
        vasp_id: int | None = None
        if lbl.vasp:
            vasp, created = await _get_or_create_vasp(session, lbl.vasp, vasp_cache)
            if created:
                stats.vasps += 1
            vasp_id = vasp.id
        try:
            category = LabelCategory(lbl.category)
        except ValueError:
            category = LabelCategory.OTHER
        session.add(
            Label(
                address=lbl.address,
                name=lbl.name,
                category=category,
                source=LabelSource.MANUAL,
                vasp_id=vasp_id,
            )
        )
        stats.labels += 1

    await session.flush()


async def seed_demo(session: AsyncSession, *, with_labels: bool = True) -> SeedStats:
    """Ingest bundled labels then seed all synthetic scenarios (idempotent)."""
    stats = SeedStats()
    if with_labels:
        label_stats = await ingest_all(session)
        stats.labels += label_stats.inserted
        stats.vasps += label_stats.vasps_created

    known_wallets = {
        row[0]
        for row in (await session.execute(select(Wallet.address))).all()
    }
    known_tx = {
        row[0]
        for row in (await session.execute(select(Transaction.tx_hash))).all()
    }
    vasp_cache: dict[str, Vasp] = {}

    for scenario in build_all_scenarios():
        await _seed_scenario(
            session, scenario, known_wallets, known_tx, vasp_cache, stats
        )
        stats.scenarios += 1
        stats.unknown_wallets[scenario.key] = scenario.unknown_wallet

    return stats


async def _main() -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        stats = await seed_demo(session)
        await session.commit()

        total_wallets = (
            await session.execute(select(func.count()).select_from(Wallet))
        ).scalar_one()
        total_tx = (
            await session.execute(select(func.count()).select_from(Transaction))
        ).scalar_one()
        log.info(
            "seed_demo_complete",
            db_wallets=total_wallets,
            db_transactions=total_tx,
            **stats.as_dict(),
        )
        print(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
