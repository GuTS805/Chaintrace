"""Label ingestion tests — offline, idempotent, VASP linkage."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import LabelCategory, LabelSource
from app.ingest.labels import ingest_all
from app.models import Label, Vasp


async def test_ingest_all_populates_labels_and_vasps(session: AsyncSession) -> None:
    stats = await ingest_all(session)
    await session.commit()

    # Bundled files: 4 + 3 + 8 (etherscan, incl. 5 BRIDGE) + 8 (tron) = 23 rows.
    assert stats.inserted == 23
    assert stats.skipped == 0

    total_labels = (
        await session.execute(select(func.count()).select_from(Label))
    ).scalar_one()
    assert total_labels == 23

    # Sanctioned mixer addresses came in via the OFAC source.
    sanctioned = (
        await session.execute(
            select(func.count())
            .select_from(Label)
            .where(Label.category == LabelCategory.SANCTIONED)
        )
    ).scalar_one()
    assert sanctioned == 3

    # Binance appears across sources but is a single VASP entity.
    binance = (
        await session.execute(select(Vasp).where(Vasp.name == "Binance"))
    ).scalar_one()
    assert binance.id is not None

    # Exchange labels are linked to their VASP.
    linked = (
        await session.execute(
            select(func.count())
            .select_from(Label)
            .where(Label.vasp_id == binance.id)
        )
    ).scalar_one()
    assert linked >= 2  # Binance hot wallet, Binance 2, Binance 14


async def test_ingest_is_idempotent(session: AsyncSession) -> None:
    first = await ingest_all(session)
    await session.commit()
    second = await ingest_all(session)
    await session.commit()

    assert first.inserted == 23
    assert second.inserted == 0
    assert second.skipped == 23

    total = (
        await session.execute(select(func.count()).select_from(Label))
    ).scalar_one()
    assert total == 23

    # VASPs are not duplicated on re-ingest either.
    vasps = (
        await session.execute(select(func.count()).select_from(Vasp))
    ).scalar_one()
    assert vasps == 7  # Binance, Kraken, Coinbase, HTX, OKX, Bybit, KuCoin


async def test_ofac_source_tagging(session: AsyncSession) -> None:
    await ingest_all(session)
    await session.commit()
    ofac = (
        await session.execute(
            select(func.count())
            .select_from(Label)
            .where(Label.source == LabelSource.OFAC_SDN)
        )
    ).scalar_one()
    assert ofac == 3
