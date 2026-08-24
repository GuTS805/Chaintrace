"""Live 'trace any wallet' endpoint — fetch a real address on demand."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import audit, get_current_officer
from app.db.session import get_session
from app.ingest.live import ensure_ingested
from app.models import Officer
from app.providers.resilience import ProviderUnavailable

router = APIRouter(
    prefix="/wallets", tags=["live"], dependencies=[Depends(get_current_officer)]
)


@router.post("/{address}/live-trace")
async def live_trace(
    address: str,
    limit: int = Query(100, ge=1, le=200),
    chain: str = Query(
        "ethereum",
        pattern="^(ethereum|polygon)$",
        description="EVM chain to query. Ignored for Tron addresses (auto-detected).",
    ),
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Fetch + import a real wallet's transactions (cached after first fetch)."""
    try:
        result = await ensure_ingested(session, address, limit=limit, chain=chain)
    except ProviderUnavailable as exc:
        # Distinct from any other failure: this is "the provider/network is
        # down right now", not "this address has no on-chain activity" or
        # any other data finding — 503 (retry-appropriate), never folded into
        # a result shape that could be mistaken for a verdict.
        raise HTTPException(
            status_code=503,
            detail=f"On-chain data provider is temporarily unavailable for {address}: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - surface any other fetch/parse failure cleanly
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch on-chain data for {address}: {exc}",
        ) from exc
    await audit.record(session, officer, "LIVE_TRACE", target=address, detail=f"chain={result.chain}")
    return {
        "address": result.address,
        "imported_transactions": result.imported_transactions,
        "total_transactions": result.total_transactions,
        "source": result.source,
        "chain": result.chain,
        "warnings": result.warnings,
    }
