"""Laundering-typology detection against the real seeded demo scenarios."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from datetime import UTC, datetime

from app.attribution.context_builder import AttributionContext
from app.attribution.context_builder import ContextBuilder
from app.attribution.risk import RiskScorer
from app.attribution.typology import detect_bridge_hop, detect_mixer_use, detect_smurfing
from app.enums import TypologyCategory
from app.models import Transaction
from app.schemas.graph import GraphResult, PruneInfo
from app.signals.facts import GraphFacts, LabelInfo
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

# Real, verified Polygon PoS Bridge contract on Ethereum mainnet — seeded into
# data/labels/etherscan_tags.json as category BRIDGE.
POLYGON_BRIDGE = "0xa0c68c638235ee32657e8f720a23cec1bfc77c77"

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


async def test_bridge_hop_detected_via_seeded_label(session: AsyncSession) -> None:
    """A wallet sending funds straight to the real, seeded Polygon bridge
    contract is flagged — independent of the four demo scenarios."""
    await seed_demo(session)
    session.add(
        Transaction(
            tx_hash="0x" + "b1" * 32,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            from_address="0xbridgeinvestigate",
            to_address=POLYGON_BRIDGE,
            value_wei=5 * 10**18,
            asset="ETH",
        )
    )
    await session.commit()
    ctx = await ContextBuilder(session).build("0xbridgeinvestigate", depth=3)
    tags = [t.category for t in RiskScorer().score(ctx).typology_tags]
    assert TypologyCategory.BRIDGE_HOP in tags


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


def _context_with_labeled_node(category: str) -> AttributionContext:
    root = "0xunknown"
    node = {
        "address": "0xlabeled",
        "depth": 1,
        "is_labeled": True,
        "label_name": "Test Label",
        "vasp_name": None,
        "is_contract": True,
        "cluster_id": None,
    }
    forward = GraphResult.model_validate(
        {"root": root, "nodes": [node], "edges": [], "prune": PruneInfo()}
    )
    reverse = GraphResult.model_validate(
        {"root": root, "nodes": [], "edges": [], "prune": PruneInfo()}
    )
    labels = {
        "0xlabeled": LabelInfo(
            name="Test Label", vasp_name=None, confidence=1.0, category=category
        )
    }
    return AttributionContext(
        unknown=root, candidates=[], forward_graph=forward, reverse_graph=reverse, labels=labels
    )


def test_bridge_hop_fires_on_labeled_bridge_node() -> None:
    tag = detect_bridge_hop(_context_with_labeled_node("BRIDGE"))
    assert tag is not None
    assert tag.category == TypologyCategory.BRIDGE_HOP


def test_bridge_hop_does_not_fire_without_bridge_label() -> None:
    assert detect_bridge_hop(_context_with_labeled_node("EXCHANGE")) is None


def test_mixer_use_fires_when_no_vasp_reached() -> None:
    tag = detect_mixer_use(_context_with_labeled_node("MIXER"))
    assert tag is not None
    assert tag.category == TypologyCategory.MIXER_USE


def test_mixer_use_does_not_fire_when_vasp_already_reached() -> None:
    ctx = _context_with_labeled_node("MIXER")
    ctx.candidates.append(
        GraphFacts(unknown=ctx.unknown, vasp_name="Binance", hot_addresses=set(), reachable=True)
    )
    assert detect_mixer_use(ctx) is None


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
