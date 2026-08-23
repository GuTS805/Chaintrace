"""End-to-end attribution + risk over the four seeded demo scenarios.

Uses the committed model artifact; skipped if it hasn't been trained yet.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.context_builder import ContextBuilder
from app.attribution.engine import AttributionEngine
from app.attribution.model import DEFAULT_MODEL_PATH, AttributionModel
from app.attribution.risk import RiskScorer
from app.schemas.risk import RiskLevel
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(),
    reason="model artifact missing; run `make train`",
)

SCN = {s.key: s for s in build_all_scenarios()}


@pytest_asyncio.fixture
async def wired(session: AsyncSession):
    await seed_demo(session)
    await session.commit()
    model = AttributionModel.load()
    engine = AttributionEngine(model, threshold=0.55)
    builder = ContextBuilder(session)
    return builder, engine, RiskScorer()


async def _attribute(wired, key: str):
    builder, engine, risk = wired
    ctx = await builder.build(SCN[key].unknown_wallet, depth=6)
    return engine.attribute(ctx.candidates), risk.score(ctx)


async def test_ransomware_is_clean_attribution_to_binance(wired) -> None:
    res, rk = await _attribute(wired, "ransomware_to_exchange")
    assert res.insufficient_evidence is False
    assert res.ambiguous is False
    assert res.candidates[0].vasp_name == "Binance"
    assert res.candidates[0].probability >= 0.8
    # Evidence is present and traceable.
    ev = res.candidates[0].evidence
    assert ev and any(e.tx_hashes for e in ev)
    # Risk is computed independently and flags the upstream mixer.
    assert rk.level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
    assert any(i.category == "SANCTIONED" for i in rk.indicators)


async def test_peel_chain_is_moderate_single(wired) -> None:
    res, _ = await _attribute(wired, "peel_chain")
    assert res.insufficient_evidence is False
    assert res.ambiguous is False
    assert res.candidates[0].vasp_name == "Kraken"
    assert res.candidates[0].probability >= 0.55


async def test_dead_end_is_insufficient(wired) -> None:
    res, rk = await _attribute(wired, "dead_end")
    assert res.insufficient_evidence is True
    assert res.candidates == [] or all(c.probability < 0.55 for c in res.candidates)
    assert res.explanation
    assert rk.level == RiskLevel.LOW


async def test_two_exchanges_is_ambiguous(wired) -> None:
    res, _ = await _attribute(wired, "two_exchanges")
    assert res.ambiguous is True
    assert res.insufficient_evidence is False
    names = {c.vasp_name for c in res.candidates}
    assert {"Binance", "Coinbase"} <= names


async def test_model_version_surfaced(wired) -> None:
    res, _ = await _attribute(wired, "ransomware_to_exchange")
    assert res.model_version.startswith("phase4-")
    assert res.confidence_threshold == 0.55
