"""Production-scale stress test for the traversal + attribution pipeline.

Not a pytest suite — a standalone benchmark run against a throwaway SQLite
database (same engine the offline demo/tests use; Postgres was not available
to benchmark against in this environment — see the caveat printed in the
report). Generates synthetic graphs of controlled size/shape so results are
reproducible, then separately drives the *real* live-fetch path (network
calls) against real high-degree wallets for the fetch-time numbers no
synthetic data can honestly produce.

Usage:
    python scripts/scale_test.py
    python scripts/scale_test.py --skip-live   # synthetic tests only, offline
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import event, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - populate metadata before create_all
from app.db.base import Base
from app.models import Transaction
from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository


# ------------------------------------------------------------------ timing --


@dataclass
class Timing:
    label: str
    seconds: float = 0.0
    queries: int = 0
    peak_kb: float = 0.0


class _Stopwatch:
    """Measures wall time, SQL statement count, and peak Python-heap delta for
    one block of work against one session's underlying sync engine."""

    def __init__(self, session: AsyncSession, label: str) -> None:
        self._session = session
        self.label = label
        self._count = 0

    def _on_execute(self, *_args: object, **_kwargs: object) -> None:
        self._count += 1

    async def __aenter__(self) -> "_Stopwatch":
        self._count = 0
        engine = self._session.get_bind()
        sync_engine = engine.sync_engine if hasattr(engine, "sync_engine") else engine
        event.listen(sync_engine, "before_cursor_execute", self._on_execute)
        self._sync_engine = sync_engine
        gc.collect()
        tracemalloc.start()
        self._t0 = time.perf_counter()
        return self

    async def __aexit__(self, *exc: object) -> None:
        self._elapsed = time.perf_counter() - self._t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self._peak_kb = peak / 1024
        event.remove(self._sync_engine, "before_cursor_execute", self._on_execute)

    def result(self) -> Timing:
        return Timing(self.label, self._elapsed, self._count, self._peak_kb)


# ------------------------------------------------------------ synthetic data --

ROOT = "0xroot0000000000000000000000000000000000"
HUB = "0xhub00000000000000000000000000000000000"


def _addr(prefix: str, i: int) -> str:
    return f"0x{prefix}{i:034x}"[:42]


async def _bulk_insert(session: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    # executemany-style bulk insert, not one ORM object per row — this is what
    # a real ingestion path should do too, so it's also a fair baseline.
    await session.execute(insert(Transaction), rows)
    await session.flush()


async def gen_branching_graph(
    session: AsyncSession, *, n_edges: int, branching: int, root: str = ROOT
) -> None:
    """A tree-shaped fan-out from `root`: each discovered node gets up to
    `branching` outgoing edges to fresh addresses, breadth-first, until
    `n_edges` total edges exist. Depth ~ log_branching(n_edges)."""
    rows: list[dict] = []
    frontier = [root]
    counter = 0
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    while len(rows) < n_edges and frontier:
        next_frontier: list[str] = []
        for node in frontier:
            for _ in range(branching):
                if len(rows) >= n_edges:
                    break
                counter += 1
                child = _addr("n", counter)
                rows.append(
                    {
                        "tx_hash": f"0x{'a' * 24}{counter:040x}"[:66],
                        "block_number": counter,
                        "timestamp": base_ts + timedelta(minutes=counter),
                        "from_address": node,
                        "to_address": child,
                        "value_wei": Decimal(1_000_000_000_000_000_000 - counter),
                        "asset": "ETH",
                    }
                )
                next_frontier.append(child)
        frontier = next_frontier
    await _bulk_insert(session, rows)


async def gen_token_heavy_graph(session: AsyncSession, *, n_edges: int, root: str = ROOT) -> None:
    """Same branching shape, but round-robins across several ERC-20 assets —
    stresses the same traversal, exercising the asset-aware edge path."""
    assets = ["USDT", "USDC", "DAI", "WETH", "ETH"]
    rows: list[dict] = []
    frontier = [root]
    counter = 0
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    while len(rows) < n_edges and frontier:
        next_frontier: list[str] = []
        for node in frontier:
            for _ in range(3):
                if len(rows) >= n_edges:
                    break
                counter += 1
                child = _addr("t", counter)
                rows.append(
                    {
                        "tx_hash": f"0x{'b' * 24}{counter:040x}"[:66],
                        "block_number": counter,
                        "timestamp": base_ts + timedelta(minutes=counter),
                        "from_address": node,
                        "to_address": child,
                        "value_wei": Decimal((counter % 9999) * 10**6),
                        "asset": assets[counter % len(assets)],
                    }
                )
                next_frontier.append(child)
        frontier = next_frontier
    await _bulk_insert(session, rows)


async def gen_high_degree_graph(
    session: AsyncSession, *, hub_edges: int, upstream_hops: int = 3
) -> str:
    """A real exchange hot wallet looks like this: thousands of distinct
    deposit addresses all feeding into one hub, and the hub fanning out to
    thousands of withdrawals. `root` sits a few hops upstream of the hub, the
    way an investigated wallet would."""
    rows: list[dict] = []
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    counter = 0

    # A short upstream chain from ROOT to a "feeder" that deposits into the hub.
    prev = ROOT
    for hop in range(upstream_hops):
        counter += 1
        nxt = _addr("u", counter)
        rows.append(
            {
                "tx_hash": f"0x{'c' * 24}{counter:040x}"[:66],
                "block_number": counter,
                "timestamp": base_ts + timedelta(minutes=counter),
                "from_address": prev,
                "to_address": nxt,
                "value_wei": Decimal(5 * 10**18),
                "asset": "ETH",
            }
        )
        prev = nxt
    counter += 1
    rows.append(
        {
            "tx_hash": f"0x{'c' * 24}{counter:040x}"[:66],
            "block_number": counter,
            "timestamp": base_ts + timedelta(minutes=counter),
            "from_address": prev,
            "to_address": HUB,
            "value_wei": Decimal(5 * 10**18),
            "asset": "ETH",
        }
    )

    # Thousands of unrelated deposit addresses also feeding the hub (in-degree).
    for i in range(hub_edges // 2):
        counter += 1
        dep = _addr("d", counter)
        rows.append(
            {
                "tx_hash": f"0x{'d' * 24}{counter:040x}"[:66],
                "block_number": counter,
                "timestamp": base_ts + timedelta(minutes=counter),
                "from_address": dep,
                "to_address": HUB,
                "value_wei": Decimal(3 * 10**18),
                "asset": "ETH",
            }
        )
    # And the hub fanning out to thousands of withdrawals (out-degree) — the
    # part that a naive traversal FROM the hub would have to expand.
    for i in range(hub_edges // 2):
        counter += 1
        wd = _addr("w", counter)
        rows.append(
            {
                "tx_hash": f"0x{'e' * 24}{counter:040x}"[:66],
                "block_number": counter,
                "timestamp": base_ts + timedelta(minutes=counter),
                "from_address": HUB,
                "to_address": wd,
                "value_wei": Decimal(1 * 10**18),
                "asset": "ETH",
            }
        )
    await _bulk_insert(session, rows)
    return HUB


# ------------------------------------------------------------------ report --


def _fmt_time(s: float) -> str:
    return f"{s * 1000:.0f}ms" if s < 1 else f"{s:.2f}s"


def _row(cols: list[str], widths: list[int]) -> str:
    return "  ".join(c.ljust(w) for c, w in zip(cols, widths, strict=False))


@dataclass
class CaseResult:
    name: str
    nodes: int
    edges: int
    pruned: bool
    prune_reasons: list[str]
    traversal: Timing
    attribution_timing: Timing | None = None
    fetch_seconds: float | None = None
    extra: dict[str, str] = field(default_factory=dict)


async def run_traversal_case(
    session: AsyncSession, *, name: str, root: str, max_hops: int, max_nodes: int
) -> CaseResult:
    repo = SqlGraphRepository(session)
    bounds = TraversalBounds(max_hops=max_hops, max_nodes=max_nodes, direction=Direction.FORWARD)
    async with _Stopwatch(session, name) as sw:
        graph = await repo.traverse(root, bounds)
    t = sw.result()
    return CaseResult(
        name=name,
        nodes=len(graph.nodes),
        edges=len(graph.edges),
        pruned=graph.prune.pruned,
        prune_reasons=[r.value for r in graph.prune.reasons],
        traversal=t,
    )


async def run_attribution_case(session: AsyncSession, *, name: str, root: str, depth: int) -> CaseResult:
    from app.attribution.context_builder import ContextBuilder

    builder = ContextBuilder(session)
    async with _Stopwatch(session, name) as sw:
        ctx = await builder.build(root, depth=depth)
    t = sw.result()
    return CaseResult(
        name=name,
        nodes=len(ctx.forward_graph.nodes),
        edges=len(ctx.forward_graph.edges),
        pruned=ctx.forward_graph.prune.pruned,
        prune_reasons=[r.value for r in ctx.forward_graph.prune.reasons],
        traversal=t,
        extra={"candidates": str(len(ctx.candidates))},
    )


class _FreshDb:
    """One isolated database per case. Reusing a single engine across cases
    (an earlier version of this script did) silently accumulates every prior
    case's rows into the next one's traversal — a benchmark-harness bug that
    inflates later cases, not a finding about the real system.

    Defaults to an in-memory SQLite database (the offline demo engine). Pass
    a Postgres URL to run the identical case against a real Postgres instance
    instead — "fresh" there means drop+recreate all tables on the same DB,
    since Postgres has no equivalent of a throwaway in-memory database.
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url or "sqlite+aiosqlite://"

    async def __aenter__(self) -> AsyncSession:
        is_sqlite = self._db_url.startswith("sqlite")
        kwargs = (
            {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
            if is_sqlite
            else {}
        )
        self._engine = create_async_engine(self._db_url, **kwargs)
        async with self._engine.begin() as conn:
            if not is_sqlite:
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        self._session = maker()
        return self._session

    async def __aexit__(self, *exc: object) -> None:
        await self._session.close()
        await self._engine.dispose()


async def synthetic_suite(db_url: str | None = None) -> list[CaseResult]:
    results: list[CaseResult] = []

    async with _FreshDb(db_url) as session:
        await gen_branching_graph(session, n_edges=100, branching=4)
        await session.commit()
        results.append(await run_traversal_case(session, name="A: Small (100 tx, 3 hops)", root=ROOT, max_hops=3, max_nodes=500))

    async with _FreshDb(db_url) as session:
        await gen_branching_graph(session, n_edges=1_000, branching=3)
        await session.commit()
        results.append(await run_traversal_case(session, name="B: Medium (1,000 tx, 5 hops)", root=ROOT, max_hops=5, max_nodes=2_000))

    async with _FreshDb(db_url) as session:
        await gen_branching_graph(session, n_edges=10_000, branching=3)
        await session.commit()
        results.append(await run_traversal_case(session, name="C: Large (10,000 tx, 8 hops)", root=ROOT, max_hops=8, max_nodes=20_000))

    async with _FreshDb(db_url) as session:
        await gen_token_heavy_graph(session, n_edges=1_000)
        await session.commit()
        results.append(await run_traversal_case(session, name="E: Token-heavy (1,000 tx, 5 assets)", root=ROOT, max_hops=5, max_nodes=2_000))

    # High-degree hub — this is the case the user specifically flagged: what
    # happens if the traversal has to pass THROUGH (not start at) a
    # Binance/Kraken-shaped hot wallet, at three different max_nodes ceilings.
    # Each ceiling gets its own fresh DB so the three runs don't interfere.
    for max_nodes in (100, 1_000, 10_000):
        async with _FreshDb(db_url) as session:
            await gen_high_degree_graph(session, hub_edges=40_000, upstream_hops=3)
            await session.commit()
            case = await run_traversal_case(
                session,
                name=f"D: High-degree hub, max_nodes={max_nodes}",
                root=ROOT,
                max_hops=6,
                max_nodes=max_nodes,
            )
            case.extra["bound_enforced"] = "PASS" if case.nodes <= max_nodes else "FAIL"
            results.append(case)

    # Same high-degree data, but through the full attribution context builder
    # (this is what an officer's /attribution request actually triggers) —
    # rooted at the upstream feeder, one hop before the hub.
    async with _FreshDb(db_url) as session:
        await gen_high_degree_graph(session, hub_edges=40_000, upstream_hops=3)
        await session.commit()
        results.append(
            await run_attribution_case(session, name="D2: High-degree via ContextBuilder (attribution path)", root=ROOT, depth=6)
        )

    return results


async def explain_high_degree(db_url: str, max_nodes_values: list[int]) -> dict[int, str]:
    """EXPLAIN (ANALYZE, BUFFERS) the exact recursive-CTE traversal query the
    high-degree hub case runs, on Postgres — the question being whether the
    outer LIMIT (the _ROW_HARD_CAP safety net) actually bounds how much the
    recursive term materializes, or whether Postgres computes far more Work
    than the requested max_nodes before cutting it off."""
    out: dict[int, str] = {}
    for max_nodes in max_nodes_values:
        async with _FreshDb(db_url) as session:
            await gen_high_degree_graph(session, hub_edges=40_000, upstream_hops=3)
            await session.commit()

            repo = SqlGraphRepository(session)
            bounds = TraversalBounds(max_hops=6, max_nodes=max_nodes, direction=Direction.FORWARD)
            trav = repo._walk_cte(ROOT, bounds)  # noqa: SLF001 - diagnostic use only
            stmt = select(
                trav.c.src, trav.c.dst, trav.c.tx_hash, trav.c.value_wei,
                trav.c.timestamp, trav.c.asset, trav.c.depth,
            ).limit(repo._ROW_HARD_CAP)  # noqa: SLF001
            compiled = stmt.compile(
                dialect=session.get_bind().dialect, compile_kwargs={"literal_binds": True}
            )
            result = await session.execute(text(f"EXPLAIN (ANALYZE, BUFFERS) {compiled}"))
            out[max_nodes] = "\n".join(row[0] for row in result.fetchall())
    return out


async def live_suite() -> list[CaseResult]:
    """Real network fetch against real high-degree / token-heavy wallets —
    the fetch-time numbers no synthetic data can honestly produce."""
    from app.ingest.live import ensure_ingested

    # Real addresses: a normal low-degree wallet (control) and a real,
    # extremely high-degree exchange hot wallet, on both Ethereum and Polygon.
    cases = [
        ("Live D: Binance 14 hot wallet (Ethereum, real)", "0x28c6c06298d514db089934071355e5743bf21d60", "ethereum"),
        ("Live E: USDT contract itself (Ethereum, token-heavy)", "0xdac17f958d2ee523a2206206994597c13d831ec7", "ethereum"),
        ("Live F: Polygon bridge contract (cross-chain)", "0xa0c68c638235ee32657e8f720a23cec1bfc77c77", "polygon"),
    ]
    results: list[CaseResult] = []
    for name, addr, chain in cases:
        async with _FreshDb() as session:  # live fetch is network-bound; SQLite is fine here
            t0 = time.perf_counter()
            try:
                live_result = await asyncio.wait_for(
                    ensure_ingested(session, addr, limit=100, chain=chain), timeout=30
                )
                fetch_s = time.perf_counter() - t0
                case = await run_traversal_case(
                    session, name=name, root=live_result.address, max_hops=4, max_nodes=2_000
                )
                case.fetch_seconds = fetch_s
                case.extra["imported_tx"] = str(live_result.imported_transactions)
                case.extra["source"] = live_result.source
                results.append(case)
            except (TimeoutError, Exception) as exc:  # noqa: BLE001
                results.append(
                    CaseResult(
                        name=name, nodes=0, edges=0, pruned=False, prune_reasons=[],
                        traversal=Timing(name, 0, 0, 0),
                        extra={"error": f"{type(exc).__name__}: {exc}"},
                    )
                )
    return results


def print_report(
    synthetic: list[CaseResult],
    live: list[CaseResult],
    pg_synthetic: list[CaseResult] | None = None,
    pg_explain: dict[int, str] | None = None,
) -> None:
    print("=" * 78)
    print("CHAINTRACE SCALE TEST")
    print("=" * 78)
    if pg_synthetic is None:
        print(
            "DB: in-memory SQLite (offline demo engine). Postgres was not available\n"
            "in this environment to benchmark separately — see the caveat at the\n"
            "bottom of this report before treating these as production numbers.\n"
        )
    else:
        print("DB: in-memory SQLite (offline demo engine) AND real local Postgres.\n")

    widths = [46, 8, 8, 10, 8, 8]
    print("SQLite:")
    print(_row(["Case", "Nodes", "Edges", "Time", "Mem(KB)", "Queries"], widths))
    print("-" * 78)
    for c in synthetic:
        print(
            _row(
                [c.name, str(c.nodes), str(c.edges), _fmt_time(c.traversal.seconds),
                 f"{c.traversal.peak_kb:.0f}", str(c.traversal.queries)],
                widths,
            )
        )
        extras = ", ".join(f"{k}={v}" for k, v in c.extra.items())
        pruned = f"pruned=[{', '.join(c.prune_reasons)}]" if c.pruned else "pruned=no"
        print(f"    {pruned}" + (f"  {extras}" if extras else ""))
    print()

    if pg_synthetic is not None:
        print("Postgres (real local instance, identical cases):")
        print(_row(["Case", "Nodes", "Edges", "Time", "Mem(KB)", "Queries"], widths))
        print("-" * 78)
        for c in pg_synthetic:
            print(
                _row(
                    [c.name, str(c.nodes), str(c.edges), _fmt_time(c.traversal.seconds),
                     f"{c.traversal.peak_kb:.0f}", str(c.traversal.queries)],
                    widths,
                )
            )
            extras = ", ".join(f"{k}={v}" for k, v in c.extra.items())
            pruned = f"pruned=[{', '.join(c.prune_reasons)}]" if c.pruned else "pruned=no"
            print(f"    {pruned}" + (f"  {extras}" if extras else ""))
        print()

    if pg_explain:
        print("Postgres EXPLAIN (ANALYZE, BUFFERS) — high-degree hub traversal:")
        print("-" * 78)
        for max_nodes, plan in pg_explain.items():
            print(f"  -- max_nodes={max_nodes} --")
            for line in plan.splitlines():
                print(f"  {line}")
            print()

    print("Live network fetch (real chains, real wallets):")
    print("-" * 78)
    for c in live:
        if "error" in c.extra:
            print(f"  {c.name}: FAILED — {c.extra['error']}")
            continue
        fetch = _fmt_time(c.fetch_seconds) if c.fetch_seconds is not None else "n/a"
        print(
            f"  {c.name}\n"
            f"    fetch={fetch}  traversal={_fmt_time(c.traversal.seconds)}  "
            f"nodes={c.nodes}  edges={c.edges}  "
            f"imported_tx={c.extra.get('imported_tx', '?')}  source={c.extra.get('source', '?')}"
        )
    print()

    print("Max-node bound enforcement (high-degree hub, forward traversal):")
    print("-" * 78)
    for c in synthetic:
        if "bound_enforced" in c.extra:
            print(f"  {c.name}: {c.extra['bound_enforced']}  (nodes returned={c.nodes})")
    print()
    print("=" * 78)
    pg_line = (
        "  - Also run against a real local Postgres instance (see the Postgres\n"
        "    section above) — not a hypothetical extrapolation from SQLite.\n"
        if pg_synthetic is not None
        else
        "  - Measured on SQLite, not Postgres. The recursive-CTE query plan,\n"
        "    index usage, and concurrency behavior can differ materially on\n"
        "    Postgres — this run could not include a Postgres comparison\n"
        "    (docker was not available in this environment). Re-run against\n"
        "    the real deployment target before using these numbers to size\n"
        "    infrastructure.\n"
    )
    print(
        "CAVEATS (read before treating any of this as a production verdict):\n"
        + pg_line +
        "  - Memory is Python-heap peak (tracemalloc) for the traversal call\n"
        "    only, not full process RSS — it excludes the driver's own\n"
        "    native-code buffers.\n"
        "  - Synthetic graphs are branching trees, not real transaction\n"
        "    topology (real graphs have back-edges, repeated counterparties,\n"
        "    temporal clustering) — they stress node/edge *count* and hub\n"
        "    fan-out faithfully, but not every real-world shape.\n"
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-live", action="store_true", help="Synthetic tests only, no network calls.")
    parser.add_argument(
        "--postgres-url",
        default=None,
        help=(
            "Also run the synthetic suite against this Postgres URL "
            "(postgresql+asyncpg://...) and EXPLAIN the high-degree hub query."
        ),
    )
    args = parser.parse_args()

    synthetic = await synthetic_suite()
    live = [] if args.skip_live else await live_suite()

    pg_synthetic = None
    pg_explain = None
    if args.postgres_url:
        pg_synthetic = await synthetic_suite(db_url=args.postgres_url)
        pg_explain = await explain_high_degree(args.postgres_url, [100, 1_000, 10_000])

    print_report(synthetic, live, pg_synthetic, pg_explain)


if __name__ == "__main__":
    asyncio.run(main())
