"""Investigation snapshots: freeze an attribution + risk result immutably.

Distinct from the live `/wallets/{address}/attribution` and `/risk`
endpoints — those always recompute against current DB/model state. Creating
an investigation captures a point-in-time verdict (plus everything needed to
explain *why* it was that verdict — model version, provider, bounds) that
will read back identically no matter what changes afterward.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder, get_engine
from app.attribution.context_builder import ContextBuilder, TraversalTimeout
from app.attribution.engine import AttributionEngine
from app.attribution.risk import RiskScorer
from app.auth import audit, get_current_officer
from app.db.session import get_session
from app.ingest.live import ensure_ingested
from app.models import Investigation, Officer
from app.providers.base import normalize_address
from app.providers.resilience import ProviderUnavailable
from app.report import build_disclosure_request, build_wallet_report, disclosure_filename
from app.schemas.attribution import AttributionResult
from app.schemas.graph import GraphResult
from app.schemas.investigation import InvestigationOut, InvestigationSummary
from app.schemas.risk import RiskResult

router = APIRouter(tags=["investigations"], dependencies=[Depends(get_current_officer)])


def _pdf(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _get_investigation(session: AsyncSession, investigation_id: int) -> Investigation:
    row = await session.get(Investigation, investigation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return row


def _summarize(row: Investigation) -> InvestigationSummary:
    candidates = row.attribution.get("candidates") or []
    top = candidates[0] if candidates else None
    return InvestigationSummary(
        id=row.id,
        wallet_address=row.wallet_address,
        chain=row.chain,
        officer_id=row.officer_id,
        model_version=row.model_version,
        created_at=row.created_at,
        top_vasp=top.get("vasp_name") if top else None,
        top_probability=top.get("probability") if top else None,
        insufficient_evidence=bool(row.attribution.get("insufficient_evidence")),
        risk_level=row.risk.get("level"),
        flagged=bool(row.risk.get("flagged")),
    )


@router.post(
    "/wallets/{address}/investigations", response_model=InvestigationOut, status_code=201
)
async def create_investigation(
    address: str,
    depth: int = Query(6, ge=1, le=8),
    chain: str = Query(
        "ethereum",
        pattern="^(ethereum|polygon)$",
        description="Only used if the wallet isn't already ingested; ignored for Tron addresses.",
    ),
    builder: ContextBuilder = Depends(get_context_builder),
    engine: AttributionEngine = Depends(get_engine),
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> Investigation:
    """Fetch (if needed), attribute, score, and permanently freeze the result."""
    try:
        live_result = await ensure_ingested(session, address, chain=chain)
    except ProviderUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=f"On-chain data provider is temporarily unavailable for {address}: {exc}",
        ) from exc

    try:
        context = await builder.build(address, depth=depth)
    except TraversalTimeout as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "The trace took too long to complete and was aborted before any "
                "verdict was computed — this is not an 'insufficient evidence' result."
            ),
        ) from exc

    attribution = engine.attribute(context.candidates)
    risk = RiskScorer().score(context)

    hops: int | None = None
    tx_hashes: list[str] = []
    if attribution.candidates:
        top = attribution.candidates[0]
        facts = next(
            (f for f in context.candidates if f.vasp_name == top.vasp_name), None
        )
        hops = facts.min_hops if facts and facts.min_hops is not None else None
        for ev in top.evidence:
            for h in ev.tx_hashes:
                if h not in tx_hashes:
                    tx_hashes.append(h)

    row = Investigation(
        wallet_address=context.unknown,
        chain=live_result.chain,
        officer_id=officer.id,
        model_version=attribution.model_version,
        provider_source=live_result.source,
        traversal_max_hops=context.hops_used,
        traversal_max_nodes=context.max_nodes_used,
        traversal_min_value_wei=0,
        attribution=attribution.model_dump(mode="json"),
        risk=risk.model_dump(mode="json"),
        graph=context.forward_graph.model_dump(mode="json"),
        evidence_hops=hops,
        evidence_tx_hashes=tx_hashes[:12] or None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    await audit.record(session, officer, "INVESTIGATION_CREATED", target=address)
    return row


@router.get("/wallets/{address}/investigations", response_model=list[InvestigationSummary])
async def list_investigations_for_wallet(
    address: str, session: AsyncSession = Depends(get_session)
) -> list[InvestigationSummary]:
    rows = (
        await session.execute(
            select(Investigation)
            .where(Investigation.wallet_address == normalize_address(address))
            .order_by(Investigation.created_at.desc())
        )
    ).scalars().all()
    return [_summarize(r) for r in rows]


@router.get("/investigations/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: int, session: AsyncSession = Depends(get_session)
) -> Investigation:
    """The frozen record, exactly as captured — never recomputed."""
    return await _get_investigation(session, investigation_id)


@router.get("/investigations/{investigation_id}/report")
async def investigation_report(
    investigation_id: int,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row = await _get_investigation(session, investigation_id)
    attribution = AttributionResult.model_validate(row.attribution)
    risk = RiskResult.model_validate(row.risk)
    graph = GraphResult.model_validate(row.graph) if row.graph else GraphResult(root=row.wallet_address)
    pdf = build_wallet_report(row.wallet_address, attribution, risk, graph, generated_at=row.created_at)
    await audit.record(
        session, officer, "INVESTIGATION_REPORT", target=str(investigation_id)
    )
    return _pdf(pdf, f"investigation-{investigation_id}.pdf")


@router.get("/investigations/{investigation_id}/disclosure-request")
async def investigation_disclosure_request(
    investigation_id: int,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row = await _get_investigation(session, investigation_id)
    attribution = AttributionResult.model_validate(row.attribution)
    if attribution.insufficient_evidence or not attribution.candidates:
        raise HTTPException(
            status_code=409,
            detail="This investigation has no attributed VASP; cannot generate a request.",
        )
    risk = RiskResult.model_validate(row.risk)
    top = attribution.candidates[0]
    pdf = build_disclosure_request(
        row.wallet_address,
        attribution,
        risk,
        hops=row.evidence_hops or 0,
        tx_hashes=row.evidence_tx_hashes or [],
        officer_name=f"{officer.full_name} ({officer.badge_no})"
        if officer.badge_no
        else officer.full_name,
        officer_department=officer.department,
        generated_at=row.created_at,
    )
    await audit.record(
        session, officer, "INVESTIGATION_DISCLOSURE_REQUEST",
        target=str(investigation_id), detail=top.vasp_name,
    )
    return _pdf(pdf, disclosure_filename(row.wallet_address, top.vasp_name))
