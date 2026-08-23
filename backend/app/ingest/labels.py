"""Label ingestion from bundled public sources (offline).

Sources: ethereum-lists, OFAC SDN (crypto addresses), Etherscan public tags.
The bundled files under ``backend/data/labels`` are normalized JSON so the whole
pipeline runs with zero network access. Ingestion is idempotent — re-running does
not create duplicates (enforced by uq_label_addr_src_name).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import LabelCategory, LabelSource
from app.models import Label, Vasp

log = structlog.get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "labels"

SOURCE_FILES: dict[str, LabelSource] = {
    "ethereum_lists.json": LabelSource.ETHEREUM_LISTS,
    "ofac_sdn.json": LabelSource.OFAC_SDN,
    "etherscan_tags.json": LabelSource.ETHERSCAN_TAG,
}


@dataclass
class IngestStats:
    inserted: int = 0
    skipped: int = 0
    vasps_created: int = 0
    per_source: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "inserted": self.inserted,
            "skipped": self.skipped,
            "vasps_created": self.vasps_created,
            "per_source": self.per_source,
        }


def load_source_file(path: Path) -> list[dict[str, str]]:
    """Read and lightly normalize a bundled label source file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = []
    for item in raw:
        address = str(item["address"]).strip().lower()
        if not address:
            continue
        records.append(
            {
                "address": address,
                "name": str(item["name"]).strip(),
                "category": str(item.get("category", "OTHER")).upper(),
                "vasp": str(item.get("vasp", "")).strip(),
            }
        )
    return records


async def _get_or_create_vasp(
    session: AsyncSession, name: str, cache: dict[str, Vasp]
) -> tuple[Vasp, bool]:
    """Return (vasp, created) — created is True only when a new row was inserted."""
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


async def ingest_records(
    session: AsyncSession, records: list[dict[str, str]], source: LabelSource
) -> IngestStats:
    """Insert label records for a single source, skipping ones already present."""
    stats = IngestStats()
    vasp_cache: dict[str, Vasp] = {}

    for rec in records:
        exists = (
            await session.execute(
                select(Label.id).where(
                    Label.address == rec["address"],
                    Label.source == source,
                    Label.name == rec["name"],
                )
            )
        ).first()
        if exists is not None:
            stats.skipped += 1
            continue

        try:
            category = LabelCategory(rec["category"])
        except ValueError:
            category = LabelCategory.OTHER

        vasp_id: int | None = None
        if rec["vasp"]:
            vasp, created = await _get_or_create_vasp(session, rec["vasp"], vasp_cache)
            if created:
                stats.vasps_created += 1
            vasp_id = vasp.id

        session.add(
            Label(
                address=rec["address"],
                name=rec["name"],
                category=category,
                source=source,
                vasp_id=vasp_id,
            )
        )
        stats.inserted += 1

    await session.flush()
    stats.per_source[source.value] = stats.inserted
    return stats


async def ingest_all(session: AsyncSession, data_dir: Path = DATA_DIR) -> IngestStats:
    """Ingest every bundled source file into the session (caller commits)."""
    total = IngestStats()
    for filename, source in SOURCE_FILES.items():
        path = data_dir / filename
        if not path.exists():
            log.warning("label_source_missing", path=str(path))
            continue
        records = load_source_file(path)
        stats = await ingest_records(session, records, source)
        total.inserted += stats.inserted
        total.skipped += stats.skipped
        total.vasps_created += stats.vasps_created
        total.per_source[source.value] = stats.inserted
    return total


async def _main() -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        stats = await ingest_all(session)
        await session.commit()
        log.info("label_ingest_complete", **stats.as_dict())
        print(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
