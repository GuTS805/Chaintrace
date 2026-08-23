"""Bounded recursive-CTE traversal + path extraction (offline SQLite)."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository
from app.schemas.graph import PruneReason
from app.synthetic import build_all_scenarios
from app.synthetic.builder import eth_to_wei
from app.synthetic.scenarios import BINANCE_HOT, KRAKEN_HOT
from app.synthetic.seed import seed_demo

SCN = {s.key: s for s in build_all_scenarios()}
RANSOM = SCN["ransomware_to_exchange"].unknown_wallet
PEEL = SCN["peel_chain"].unknown_wallet
DEAD = SCN["dead_end"].unknown_wallet


@pytest_asyncio.fixture
async def repo(session: AsyncSession) -> SqlGraphRepository:
    await seed_demo(session)
    await session.commit()
    return SqlGraphRepository(session)


async def test_forward_traversal_reaches_labeled_hot_wallet(
    repo: SqlGraphRepository,
) -> None:
    result = await repo.traverse(RANSOM, TraversalBounds(max_hops=4))
    by_addr = {n.address: n for n in result.nodes}
    assert BINANCE_HOT in by_addr
    hot = by_addr[BINANCE_HOT]
    assert hot.is_labeled is True
    assert hot.vasp_name == "Binance"
    assert result.root == RANSOM
    assert by_addr[RANSOM].depth == 0


async def test_max_hops_prune_is_reported(repo: SqlGraphRepository) -> None:
    result = await repo.traverse(RANSOM, TraversalBounds(max_hops=1))
    assert result.prune.pruned is True
    assert PruneReason.MAX_HOPS in result.prune.reasons
    # Depth-1 only: the hot wallet (depth 2) must not appear.
    assert BINANCE_HOT not in {n.address for n in result.nodes}


async def test_max_nodes_prune_is_reported(repo: SqlGraphRepository) -> None:
    result = await repo.traverse(RANSOM, TraversalBounds(max_hops=4, max_nodes=2))
    assert PruneReason.MAX_NODES in result.prune.reasons
    assert result.prune.nodes_visited <= 2


async def test_min_value_prune_excludes_peels(repo: SqlGraphRepository) -> None:
    # Peels are 0.4 ETH; main flow is ~19 ETH. A 1 ETH floor drops the peels.
    result = await repo.traverse(
        PEEL, TraversalBounds(max_hops=6, min_value_wei=eth_to_wei(1))
    )
    assert PruneReason.MIN_VALUE in result.prune.reasons
    # Main chain still reaches Kraken within 6 hops.
    assert KRAKEN_HOT in {n.address for n in result.nodes}


async def test_unbounded_case_is_not_flagged_pruned(repo: SqlGraphRepository) -> None:
    # Generous bounds: the whole ransomware subgraph fits, nothing is cut.
    result = await repo.traverse(RANSOM, TraversalBounds(max_hops=8, max_nodes=5000))
    assert result.prune.pruned is False
    assert result.prune.reasons == []


async def test_reverse_traversal_finds_deposit_addresses(
    repo: SqlGraphRepository,
) -> None:
    result = await repo.traverse(
        BINANCE_HOT, TraversalBounds(max_hops=1, direction=Direction.REVERSE)
    )
    # Many deposit addresses consolidate INTO the hot wallet.
    assert len(result.nodes) > 5
    assert result.prune.nodes_visited > 5


async def test_shortest_path_extraction(repo: SqlGraphRepository) -> None:
    paths = await repo.shortest_paths(RANSOM, BINANCE_HOT, TraversalBounds(max_hops=4))
    assert paths
    best = min(paths, key=len)
    assert best[0] == RANSOM
    assert best[-1] == BINANCE_HOT
    # cashout -> deposit -> hot wallet == 3 nodes / 2 hops.
    assert len(best) == 3


async def test_dead_end_reaches_no_labeled_wallet(repo: SqlGraphRepository) -> None:
    result = await repo.traverse(DEAD, TraversalBounds(max_hops=6))
    assert all(not n.is_labeled for n in result.nodes)


async def test_shortest_paths_source_equals_target(repo: SqlGraphRepository) -> None:
    paths = await repo.shortest_paths(RANSOM, RANSOM, TraversalBounds(max_hops=4))
    assert paths == [[RANSOM]]
