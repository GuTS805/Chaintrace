"""PDF report generation tests (offline)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.attribution import get_context_builder
from app.attribution.context_builder import ContextBuilder
from app.attribution.model import DEFAULT_MODEL_PATH
from app.db.session import get_session
from app.main import app
from app.report import build_case_report, build_wallet_report
from app.schemas.attribution import AttributionResult, Evidence, VaspCandidate
from app.schemas.case import CaseDetail
from app.schemas.graph import GraphEdge, GraphNode, GraphResult, PruneInfo
from app.schemas.risk import RiskIndicator, RiskResult
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo


def _sample_attribution() -> AttributionResult:
    return AttributionResult(
        candidates=[
            VaspCandidate(
                vasp_name="Binance",
                probability=0.99,
                evidence=[
                    Evidence(
                        signal_type="DEPOSIT_SWEEP",
                        description="12 deposit addresses consolidate into the hot wallet.",
                        weight=1.27,
                        tx_hashes=["0xaaa", "0xbbb"],
                        timestamps=[datetime(2024, 5, 1, tzinfo=UTC)],
                    )
                ],
            )
        ],
        confidence_threshold=0.55,
        model_version="phase4-xgb-isotonic-6f",
        explanation="Attributed to Binance at 99%.",
    )


def _sample_risk() -> RiskResult:
    return RiskResult(
        wallet="0xabc",
        score=0.33,
        level="MEDIUM",
        indicators=[
            RiskIndicator(
                category="SANCTIONED",
                description="Funds are 2 hop(s) from Tornado Cash.",
                address="0x7221",
                hops=2,
                contribution=0.33,
            )
        ],
    )


def _sample_graph() -> GraphResult:
    return GraphResult(
        root="0xabc",
        nodes=[
            GraphNode(address="0xabc", depth=0),
            GraphNode(address="0xdef", depth=1),
            GraphNode(
                address="0xhot", depth=2, is_labeled=True, vasp_name="Binance"
            ),
        ],
        edges=[
            GraphEdge(
                tx_hash="0x1",
                from_address="0xabc",
                to_address="0xdef",
                value_wei="1000",
                timestamp=datetime(2024, 5, 1, tzinfo=UTC),
            ),
            GraphEdge(
                tx_hash="0x2",
                from_address="0xdef",
                to_address="0xhot",
                value_wei="990",
                timestamp=datetime(2024, 5, 1, 1, tzinfo=UTC),
            ),
        ],
        prune=PruneInfo(pruned=False, nodes_visited=3, max_depth_reached=2),
    )


def test_build_wallet_report_is_pdf() -> None:
    pdf = build_wallet_report(
        "0xabc", _sample_attribution(), _sample_risk(), _sample_graph()
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_build_case_report_is_pdf() -> None:
    detail = CaseDetail(
        id=1,
        name="Ransomware trace",
        description="Test case",
        status="OPEN",
        investigator="analyst-1",
        created_at=datetime(2024, 5, 1, tzinfo=UTC),
        findings=[],
    )
    pdf = build_case_report(detail)
    assert pdf.startswith(b"%PDF")


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    await seed_demo(session)
    await session.commit()
    app.dependency_overrides[get_context_builder] = lambda: ContextBuilder(session)
    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)
async def test_wallet_report_endpoint(client: AsyncClient) -> None:
    addr = next(
        s.unknown_wallet
        for s in build_all_scenarios()
        if s.key == "ransomware_to_exchange"
    )
    resp = await client.get(f"/wallets/{addr}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


async def test_case_report_endpoint(client: AsyncClient) -> None:
    created = await client.post("/cases", json={"name": "Trace"})
    case_id = created.json()["id"]
    await client.post(
        f"/cases/{case_id}/findings",
        json={"title": "Attached wallet", "wallet_address": "0xabc", "severity": "HIGH"},
    )
    resp = await client.get(f"/cases/{case_id}/report")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
