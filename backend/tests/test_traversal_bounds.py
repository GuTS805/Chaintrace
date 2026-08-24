"""Config-driven traversal bounds: a server-side ceiling that no caller (API
or otherwise) can exceed, and a wall-clock timeout that surfaces as a
distinct failure — never as an attribution/risk result."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.context_builder import ContextBuilder, TraversalTimeout
from app.config import Settings
from app.ingest.chain_import import import_provider_txs
from app.providers.base import ProviderTx
from datetime import UTC, datetime


async def _seed_small_graph(session: AsyncSession) -> None:
    txs = [
        ProviderTx(
            tx_hash=f"0x{i:064x}",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            from_address="0xroot0000000000000000000000000000000001",
            to_address=f"0xchild{i:034x}"[:42],
            value_wei=10**18,
            asset="ETH",
        )
        for i in range(5)
    ]
    await import_provider_txs(session, txs, chain="ethereum")
    await session.commit()


def _settings(**overrides: object) -> Settings:
    base = {
        "traversal_max_nodes": 2000,
        "traversal_max_nodes_ceiling": 10_000,
        "traversal_max_hops": 6,
        "traversal_max_hops_ceiling": 8,
        "traversal_timeout_seconds": 20.0,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


async def test_max_nodes_request_above_ceiling_is_clamped(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_small_graph(session)
    monkeypatch.setattr(
        "app.attribution.context_builder.get_settings",
        lambda: _settings(traversal_max_nodes_ceiling=3),
    )
    ctx = await ContextBuilder(session).build(
        "0xroot0000000000000000000000000000000001", depth=4, max_nodes=999_999
    )
    # 5 children exist; the ceiling of 3 must win over both the request and
    # the data actually available.
    assert len(ctx.forward_graph.nodes) <= 3 + 1  # +1 for the root itself


async def test_max_nodes_default_comes_from_settings_not_a_hardcoded_literal(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_small_graph(session)
    monkeypatch.setattr(
        "app.attribution.context_builder.get_settings",
        lambda: _settings(traversal_max_nodes=2, traversal_max_nodes_ceiling=10_000),
    )
    ctx = await ContextBuilder(session).build(
        "0xroot0000000000000000000000000000000001", depth=4
    )
    assert len(ctx.forward_graph.nodes) <= 2 + 1


async def test_depth_beyond_hop_ceiling_is_clamped(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_small_graph(session)
    monkeypatch.setattr(
        "app.attribution.context_builder.get_settings",
        lambda: _settings(traversal_max_hops_ceiling=1),
    )
    # Should not raise even though requested depth (50) is absurd — it's
    # silently clamped to the ceiling, not rejected or unbounded.
    ctx = await ContextBuilder(session).build(
        "0xroot0000000000000000000000000000000001", depth=50
    )
    assert ctx.forward_graph.prune.max_depth_reached <= 1


async def test_traversal_timeout_raises_distinct_exception_not_a_result(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow traversal must fail loudly as TraversalTimeout, never come back
    disguised as an empty/insufficient-evidence AttributionContext — conflating
    the two would let a provider/infrastructure failure masquerade as a
    genuine 'no VASP evidence' finding."""
    await _seed_small_graph(session)
    monkeypatch.setattr(
        "app.attribution.context_builder.get_settings",
        lambda: _settings(traversal_timeout_seconds=0.01),
    )

    from app.repositories.sql_graph_repository import SqlGraphRepository

    async def _slow_traverse(self, root, bounds):  # noqa: ANN001
        await asyncio.sleep(0.2)
        raise AssertionError("should have been cancelled by the timeout")

    monkeypatch.setattr(SqlGraphRepository, "traverse", _slow_traverse)

    with pytest.raises(TraversalTimeout):
        await ContextBuilder(session).build(
            "0xroot0000000000000000000000000000000001", depth=4
        )
