"""One-click PDF report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder, get_engine
from app.api.cases import get_case
from app.attribution.context_builder import ContextBuilder
from app.attribution.engine import AttributionEngine
from app.attribution.risk import RiskScorer
from app.db.session import get_session
from app.report import build_case_report, build_wallet_report

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


@router.get("/cases/{case_id}/report")
async def case_report(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    detail = await get_case(case_id, session)
    pdf = build_case_report(detail)
    return _pdf(pdf, f"case-{case_id}.pdf")
