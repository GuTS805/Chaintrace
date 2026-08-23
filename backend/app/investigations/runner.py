"""Execute an investigation and freeze its result.

The runner is deliberately a plain ``async`` function that takes an investigation
id and owns its own database session. It does not know how it was scheduled. Today
FastAPI's background tasks call it in-process; swapping that for a Redis-backed
worker means changing the caller only — nothing in here moves.

Every run ends in a terminal state. A crash is recorded as ``FAILED`` with the
reason attached to the row, never as a silently abandoned ``QUEUED``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.attribution.context_builder import AttributionContext, ContextBuilder
from app.attribution.engine import AttributionEngine
from app.attribution.model import AttributionModel
from app.attribution.risk import RiskScorer
from app.config import get_settings
from app.db.session import get_sessionmaker
from app.enums import InvestigationStatus
from app.investigations.evidence import build_evidence_records, compute_evidence_hash
from app.models import Investigation, InvestigationSnapshot, Transaction
from app.schemas.attribution import AttributionResult
from app.schemas.risk import RiskResult

log = structlog.get_logger(__name__)

#: Reported when no transaction in the traversal has a recorded provider, which
#: happens only for a store seeded before provenance was tracked.
UNKNOWN_PROVIDER = "unknown"


async def _set_status(
    session: AsyncSession, inv: Investigation, status: InvestigationStatus
) -> None:
    """Persist a stage transition immediately so pollers see real progress."""
    inv.status = status
    if status is InvestigationStatus.FETCHING and inv.started_at is None:
        inv.started_at = datetime.now(UTC)
    await session.commit()
    log.info(
        "investigation_stage",
        investigation_id=inv.public_id,
        status=status.value,
        chain=inv.chain,
        address=inv.address,
    )


async def _providers_for(
    session: AsyncSession, chain: str, tx_hashes: set[str]
) -> str:
    """Which data sources the traversed transactions actually came from."""
    if not tx_hashes:
        return UNKNOWN_PROVIDER
    rows = (
        await session.execute(
            select(Transaction.provider)
            .where(Transaction.chain == chain, Transaction.tx_hash.in_(list(tx_hashes)))
            .distinct()
        )
    ).scalars().all()
    names = sorted({r for r in rows if r})
    return ",".join(names) if names else UNKNOWN_PROVIDER


def _data_timestamp(context: AttributionContext) -> datetime | None:
    """Newest on-chain timestamp the conclusion rests on."""
    stamps = [e.timestamp for e in context.forward_graph.edges]
    stamps += [e.timestamp for e in context.reverse_graph.edges]
    return max(stamps) if stamps else None


async def run_investigation(
    investigation_id: int,
    *,
    sessionmaker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Run the pipeline for one investigation and write its snapshot.

    Never raises: a failure is a recorded outcome of the job, not of the caller
    that scheduled it.
    """
    maker = sessionmaker or get_sessionmaker()
    async with maker() as session:
        inv = await session.get(Investigation, investigation_id)
        if inv is None:
            log.error("investigation_missing", investigation_id=investigation_id)
            return
        if inv.status.is_terminal:
            # Already finished (a retry or a duplicate schedule). Re-running would
            # overwrite a frozen snapshot, which is exactly what must not happen.
            log.info("investigation_already_terminal", investigation_id=inv.public_id)
            return

        try:
            await _execute(session, inv)
        except Exception as exc:  # noqa: BLE001 - the failure belongs on the row
            log.exception("investigation_failed", investigation_id=inv.public_id)
            inv.status = InvestigationStatus.FAILED
            inv.error = f"{type(exc).__name__}: {exc}"
            inv.completed_at = datetime.now(UTC)
            await session.commit()


async def _execute(session: AsyncSession, inv: Investigation) -> None:
    settings = get_settings()

    # --- FETCHING: load the model before touching the graph, so a missing model
    # fails the job in seconds rather than after a full traversal. ---
    await _set_status(session, inv, InvestigationStatus.FETCHING)
    model = AttributionModel.load()
    engine = AttributionEngine(model, threshold=settings.confidence_threshold)

    # --- TRAVERSING ---
    await _set_status(session, inv, InvestigationStatus.TRAVERSING)
    builder = ContextBuilder(session, chain=inv.chain)
    context = await builder.build(
        inv.address, depth=inv.depth, min_value_wei=int(inv.min_value_wei)
    )

    # --- ANALYZING ---
    await _set_status(session, inv, InvestigationStatus.ANALYZING)
    attribution: AttributionResult = engine.attribute(context.candidates)
    risk: RiskResult = RiskScorer().score(context)

    tx_hashes = {e.tx_hash for e in context.forward_graph.edges}
    tx_hashes |= {e.tx_hash for e in context.reverse_graph.edges}
    provider = await _providers_for(session, inv.chain, tx_hashes)

    records = build_evidence_records(
        investigation_id=inv.public_id or str(inv.id),
        chain=inv.chain,
        unknown_address=inv.address,
        candidates=attribution.candidates,
        model_version=attribution.model_version,
        provider=provider,
    )

    # --- freeze ---
    session.add(
        InvestigationSnapshot(
            investigation_id=inv.id,
            graph=context.forward_graph.model_dump(mode="json"),
            attribution=attribution.model_dump(mode="json"),
            risk=risk.model_dump(mode="json"),
            evidence=[r.model_dump(mode="json") for r in records],
            evidence_hash=compute_evidence_hash(records),
            model_version=attribution.model_version,
            provider=provider,
            confidence_threshold=attribution.confidence_threshold,
            traversal_bounds={
                "chain": inv.chain,
                "max_hops": inv.depth,
                "min_value_wei": str(inv.min_value_wei),
                "max_nodes": inv.max_nodes,
            },
            data_timestamp=_data_timestamp(context),
            created_at=datetime.now(UTC),
        )
    )
    inv.status = InvestigationStatus.COMPLETED
    inv.completed_at = datetime.now(UTC)
    await session.commit()
    log.info(
        "investigation_completed",
        investigation_id=inv.public_id,
        candidates=len(attribution.candidates),
        evidence_records=len(records),
        provider=provider,
    )
