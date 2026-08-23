"""One-click PDF report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder, get_engine
from app.api.cases import get_case
from app.attribution.context_builder import ContextBuilder
from app.attribution.engine import AttributionEngine
from app.attribution.risk import RiskScorer
from app.db.session import get_session
from app.report import (
    build_case_report,
    build_disclosure_request,
    build_wallet_report,
    disclosure_filename,
)

router = APIRouter(tags=["report"])


def _pdf(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/wallets/{address}/report")
async def wallet_report(
    address: str,
    depth: int = Query(6, ge=1, le=8),
    builder: ContextBuilder = Depends(get_context_builder),
    engine: AttributionEngine = Depends(get_engine),
) -> Response:
    context = await builder.build(address, depth=depth)
    attribution = engine.attribute(context.candidates)
    risk = RiskScorer().score(context)
    pdf = build_wallet_report(address, attribution, risk, context.forward_graph)
    return _pdf(pdf, f"wallet-{address[:10]}.pdf")


@router.get("/wallets/{address}/disclosure-request")
async def disclosure_request(
    address: str,
    depth: int = Query(6, ge=1, le=8),
    builder: ContextBuilder = Depends(get_context_builder),
    engine: AttributionEngine = Depends(get_engine),
) -> Response:
    """SAHYOG-Portal lawful disclosure-request draft for the attributed VASP."""
    context = await builder.build(address, depth=depth)
    attribution = engine.attribute(context.candidates)
    if attribution.insufficient_evidence or not attribution.candidates:
        raise HTTPException(
            status_code=409,
            detail="No attributed VASP for this wallet; cannot generate a request.",
        )
    risk = RiskScorer().score(context)
    top = attribution.candidates[0]
    facts = next(
        (f for f in context.candidates if f.vasp_name == top.vasp_name), None
    )
    hops = facts.min_hops if facts and facts.min_hops is not None else 0
    tx_hashes: list[str] = []
    for ev in top.evidence:
        for h in ev.tx_hashes:
            if h not in tx_hashes:
                tx_hashes.append(h)
    pdf = build_disclosure_request(
        address.lower(), attribution, risk, hops=hops, tx_hashes=tx_hashes[:12]
    )
    return _pdf(pdf, disclosure_filename(address.lower(), top.vasp_name))


@router.get("/cases/{case_id}/report")
async def case_report(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    detail = await get_case(case_id, session)
    pdf = build_case_report(detail)
    return _pdf(pdf, f"case-{case_id}.pdf")
