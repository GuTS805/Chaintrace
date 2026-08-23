"""Attribution + risk endpoints (separate, independently computed)."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.context_builder import ContextBuilder
from app.attribution.engine import AttributionEngine
from app.attribution.model import AttributionModel
from app.attribution.risk import RiskScorer
from app.config import get_settings
from app.db.session import get_session
from app.schemas.attribution import AttributionResult
from app.schemas.risk import RiskResult

router = APIRouter(prefix="/wallets", tags=["attribution"])


@lru_cache
def _load_model() -> AttributionModel:
    return AttributionModel.load()


def get_engine() -> AttributionEngine:
    try:
        model = _load_model()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Attribution model not trained. Run `make train`.",
        ) from exc
    return AttributionEngine(model, threshold=get_settings().confidence_threshold)


async def get_context_builder(
    session: AsyncSession = Depends(get_session),
) -> ContextBuilder:
    return ContextBuilder(session)


@router.get("/{address}/attribution", response_model=AttributionResult)
async def attribution(
    address: str,
    depth: int = Query(6, ge=1, le=8),
    builder: ContextBuilder = Depends(get_context_builder),
    engine: AttributionEngine = Depends(get_engine),
) -> AttributionResult:
    context = await builder.build(address, depth=depth)
    return engine.attribute(context.candidates)


@router.get("/{address}/risk", response_model=RiskResult)
async def risk(
    address: str,
    depth: int = Query(6, ge=1, le=8),
    builder: ContextBuilder = Depends(get_context_builder),
) -> RiskResult:
    context = await builder.build(address, depth=depth)
    return RiskScorer().score(context)
