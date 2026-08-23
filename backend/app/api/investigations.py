"""Investigation endpoints — the platform's primary resource.

``POST /investigations`` accepts work and returns ``202`` with an id; it never
blocks on a traversal. Every result sub-resource reads the frozen snapshot, so two
reads a month apart return the same bytes even if the chain, the labels, or the
model have all moved on since.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_task_sessionmaker
from app.db.session import get_session
from app.enums import InvestigationStatus
from app.investigations.runner import run_investigation
from app.models import Case, Investigation, InvestigationSnapshot, format_public_id
from app.report import build_wallet_report
from app.schemas.attribution import AttributionResult
from app.schemas.graph import GraphResult
from app.schemas.investigation import (
    EvidenceBundle,
    InvestigationCreate,
    InvestigationDetail,
    InvestigationGraph,
    InvestigationOut,
    Methodology,
)
from app.schemas.risk import RiskResult

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _to_out(inv: Investigation) -> InvestigationOut:
    return InvestigationOut(
        id=inv.public_id or str(inv.id),
        chain=inv.chain,
        address=inv.address,
        status=inv.status,
        depth=inv.depth,
        max_nodes=inv.max_nodes,
        requested_by=inv.requested_by,
        case_id=inv.case_id,
        error=inv.error,
        created_at=inv.created_at,
        started_at=inv.started_at,
        completed_at=inv.completed_at,
        has_result=inv.snapshot is not None,
    )


async def _load(session: AsyncSession, investigation_id: str) -> Investigation:
    inv = (
        await session.execute(
            select(Investigation).where(Investigation.public_id == investigation_id)
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


async def _load_snapshot(
    session: AsyncSession, investigation_id: str
) -> tuple[Investigation, InvestigationSnapshot]:
    """Fetch a completed investigation's snapshot, or explain why there isn't one.

    A pending investigation returns 409 rather than 404: the resource exists, it
    simply has no result yet, and a client polling it needs to tell those apart.
    """
    inv = await _load(session, investigation_id)
    if inv.snapshot is None:
        if inv.status is InvestigationStatus.FAILED:
            raise HTTPException(
                status_code=409,
                detail=f"Investigation {investigation_id} failed: {inv.error}",
            )
        raise HTTPException(
            status_code=409,
            detail=(
                f"Investigation {investigation_id} is {inv.status.value}; "
                "no result is available yet."
            ),
        )
    return inv, inv.snapshot


@router.post("", response_model=InvestigationOut, status_code=202)
async def create_investigation(
    payload: InvestigationCreate,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    task_sessions: async_sessionmaker[AsyncSession] = Depends(get_task_sessionmaker),
) -> InvestigationOut:
    """Open an investigation and schedule it. Returns 202 immediately."""
    if payload.case_id is not None and await session.get(Case, payload.case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")

    inv = Investigation(
        chain=payload.chain.value,
        address=payload.address,
        depth=payload.depth,
        min_value_wei=payload.min_value_wei,
        max_nodes=payload.max_nodes,
        case_id=payload.case_id,
        requested_by=payload.requested_by,
        status=InvestigationStatus.QUEUED,
    )
    session.add(inv)
    # Flush to obtain the row id the public reference is derived from.
    await session.flush()
    inv.public_id = format_public_id(inv.id, datetime.now(UTC).year)
    await session.commit()
    await session.refresh(inv)

    # In-process for now. Handing this to a Redis-backed worker later changes
    # this one line — run_investigation already owns its own session.
    background.add_task(run_investigation, inv.id, sessionmaker=task_sessions)
    return _to_out(inv)


@router.get("", response_model=list[InvestigationOut])
async def list_investigations(
    limit: int = Query(50, ge=1, le=200),
    case_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[InvestigationOut]:
    stmt = select(Investigation).order_by(Investigation.created_at.desc()).limit(limit)
    if case_id is not None:
        stmt = stmt.where(Investigation.case_id == case_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_out(inv) for inv in rows]


@router.get("/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> InvestigationDetail:
    """Status, plus the frozen conclusion once the run has completed."""
    inv = await _load(session, investigation_id)
    detail = InvestigationDetail(**_to_out(inv).model_dump())
    snap = inv.snapshot
    if snap is not None:
        detail.attribution = AttributionResult.model_validate(snap.attribution)
        detail.risk = RiskResult.model_validate(snap.risk)
        detail.methodology = Methodology(
            model_version=snap.model_version,
            provider=snap.provider,
            confidence_threshold=snap.confidence_threshold,
            traversal_bounds=snap.traversal_bounds,
            data_timestamp=snap.data_timestamp,
            evidence_hash=snap.evidence_hash,
            snapshot_created_at=snap.created_at,
        )
    return detail


@router.get("/{investigation_id}/graph", response_model=InvestigationGraph)
async def investigation_graph(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> InvestigationGraph:
    _, snap = await _load_snapshot(session, investigation_id)
    return InvestigationGraph(
        investigation_id=investigation_id,
        graph=GraphResult.model_validate(snap.graph),
    )


@router.get("/{investigation_id}/attribution", response_model=AttributionResult)
async def investigation_attribution(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> AttributionResult:
    _, snap = await _load_snapshot(session, investigation_id)
    return AttributionResult.model_validate(snap.attribution)


@router.get("/{investigation_id}/risk", response_model=RiskResult)
async def investigation_risk(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> RiskResult:
    _, snap = await _load_snapshot(session, investigation_id)
    return RiskResult.model_validate(snap.risk)


@router.get("/{investigation_id}/evidence", response_model=EvidenceBundle)
async def investigation_evidence(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> EvidenceBundle:
    """The flat evidence records and the hash that seals them."""
    _, snap = await _load_snapshot(session, investigation_id)
    return EvidenceBundle(
        investigation_id=investigation_id,
        evidence_hash=snap.evidence_hash,
        record_count=len(snap.evidence),
        records=snap.evidence,
    )


@router.get("/{investigation_id}/report")
async def investigation_report(
    investigation_id: str, session: AsyncSession = Depends(get_session)
) -> Response:
    """PDF rendered entirely from the snapshot — never recomputed."""
    inv, snap = await _load_snapshot(session, investigation_id)
    provenance = [
        ("Investigation", investigation_id),
        ("Chain", inv.chain),
        ("Subject", inv.address),
        ("Requested by", inv.requested_by or "—"),
        ("Provider", snap.provider),
        ("Model version", snap.model_version),
        (
            "Data as of",
            f"{snap.data_timestamp:%Y-%m-%d %H:%M UTC}"
            if snap.data_timestamp
            else "—",
        ),
        ("Snapshot taken", f"{snap.created_at:%Y-%m-%d %H:%M UTC}"),
        ("Evidence integrity hash", snap.evidence_hash),
    ]
    pdf = build_wallet_report(
        inv.address,
        AttributionResult.model_validate(snap.attribution),
        RiskResult.model_validate(snap.risk),
        GraphResult.model_validate(snap.graph),
        provenance=provenance,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{investigation_id}.pdf"'
        },
    )
