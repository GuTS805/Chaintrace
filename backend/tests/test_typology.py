"""Laundering-typology detection against the real seeded demo scenarios."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.context_builder import ContextBuilder
from app.attribution.risk import RiskScorer
from app.attribution.typology import detect_smurfing
from app.enums import TypologyCategory
from app.schemas.graph import GraphResult, PruneInfo
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

SCN = {s.key: s for s in build_all_scenarios()}


async def _typology_tags(session: AsyncSession, key: str) -> list[str]:
    await seed_demo(session)
    await session.commit()
    builder = ContextBuilder(session)
    ctx = await builder.build(SCN[key].unknown_wallet, depth=6)
    result = RiskScorer().score(ctx)
    return [t.category for t in result.typology_tags]


async def test_peel_chain_scenario_detected_as_peel_chain(session: AsyncSession) -> None:
    tags = await _typology_tags(session, "peel_chain")
    assert TypologyCategory.PEEL_CHAIN in tags


async def test_ransomware_scenario_detected_as_layering(session: AsyncSession) -> None:
    """Funds pass through the labeled Tornado Cash mixer (upstream, reverse
    graph) before the wallet forwards on to Binance (forward graph)."""
    tags = await _typology_tags(session, "ransomware_to_exchange")
    assert TypologyCategory.LAYERING in tags


async def test_dead_end_scenario_has_no_typology(session: AsyncSession) -> None:
    tags = await _typology_tags(session, "dead_end")
    assert tags == []


def test_smurfing_fires_on_fan_out_to_similar_values() -> None:
    root = "0xunknown"
    edges = [
        {
            "tx_hash": f"0x{i:064x}",
            "from_address": root,
            "to_address": f"0xrecv{i}",
            "value_wei": 10 * 10**18,
            "timestamp": "2024-05-01T00:00:00Z",
            "asset": "ETH",
        }
        for i in range(6)
    ]
    graph = GraphResult.model_validate(
        {"root": root, "nodes": [], "edges": edges, "prune": PruneInfo()}
    )
    tag = detect_smurfing(graph)
    assert tag is not None
    assert tag.category == TypologyCategory.SMURFING


def test_smurfing_does_not_fire_on_few_recipients() -> None:
    root = "0xunknown"
    edges = [
        {
            "tx_hash": f"0x{i:064x}",
            "from_address": root,
            "to_address": f"0xrecv{i}",
            "value_wei": 10 * 10**18,
            "timestamp": "2024-05-01T00:00:00Z",
            "asset": "ETH",
        }
        for i in range(2)
    ]
    graph = GraphResult.model_validate(
        {"root": root, "nodes": [], "edges": edges, "prune": PruneInfo()}
    )
    assert detect_smurfing(graph) is None
