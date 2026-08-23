"""Recursive-CTE implementation of GraphRepository.

Uses a single `WITH RECURSIVE` walk over the transaction store, portable across
Postgres (deployment) and SQLite (offline tests). Cycle-free via a path string
carried through the recursion. Traversal is always bounded (HARD REQUIREMENT #5)
and reports exactly why it stopped.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, and_, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import CTE

from app.models import Label, Transaction, Vasp, Wallet
from app.repositories.graph_repository import (
    Direction,
    GraphRepository,
    TraversalBounds,
)
from app.schemas.graph import (
    GraphEdge,
    GraphNode,
    GraphResult,
    PruneInfo,
    PruneReason,
)

_TX = Transaction.__table__


def _norm(address: str) -> str:
    return address.strip().lower()


class SqlGraphRepository(GraphRepository):
    """Bounded traversal backed by SQL recursive CTEs."""

    # Safety ceiling on rows pulled from the recursive CTE regardless of bounds.
    _ROW_HARD_CAP = 20_000

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- edge relation ---------------------------------------------------
    def _edge_cte(self, bounds: TraversalBounds) -> CTE:
        """Directed edges (a -> b) that satisfy the value/time bounds.

        FORWARD follows money out (a=from, b=to); REVERSE follows money in
        (a=to, b=from); BOTH is the union (needed for deposit-sweep analysis).
        """
        conds: list[ColumnElement[bool]] = [
            _TX.c.to_address.is_not(None),
            _TX.c.value_wei >= bounds.min_value_wei,
        ]
        if bounds.since is not None:
            conds.append(_TX.c.timestamp >= bounds.since)
        if bounds.until is not None:
            conds.append(_TX.c.timestamp <= bounds.until)
        base = and_(*conds)

        fwd = select(
            _TX.c.from_address.label("a"),
            _TX.c.to_address.label("b"),
            _TX.c.tx_hash,
            _TX.c.value_wei,
            _TX.c.timestamp,
            _TX.c.asset,
        ).where(base)
        rev = select(
            _TX.c.to_address.label("a"),
            _TX.c.from_address.label("b"),
            _TX.c.tx_hash,
            _TX.c.value_wei,
            _TX.c.timestamp,
            _TX.c.asset,
        ).where(base)

        if bounds.direction is Direction.FORWARD:
            return fwd.cte("edges")
        if bounds.direction is Direction.REVERSE:
            return rev.cte("edges")
        return fwd.union_all(rev).cte("edges")

    def _walk_cte(self, root: str, bounds: TraversalBounds) -> CTE:
        """Recursive, cycle-free walk from `root`, carrying depth + path."""
        e = self._edge_cte(bounds)
        sep = literal("|")

        anchor = (
            select(
                e.c.a.label("src"),
                e.c.b.label("dst"),
                e.c.tx_hash,
                e.c.value_wei,
                e.c.timestamp,
                e.c.asset,
                literal(1).label("depth"),
                sep.concat(root).concat(sep).concat(e.c.b).concat(sep).label("path"),
            )
            .where(and_(e.c.a == root, e.c.b != root))
        )
        trav = anchor.cte("trav", recursive=True)

        rec = (
            select(
                e.c.a,
                e.c.b,
                e.c.tx_hash,
                e.c.value_wei,
                e.c.timestamp,
                e.c.asset,
                (trav.c.depth + 1).label("depth"),
                trav.c.path.concat(e.c.b).concat(sep).label("path"),
            )
            .select_from(trav.join(e, e.c.a == trav.c.dst))
            .where(
                and_(
                    trav.c.depth < bounds.max_hops,
                    trav.c.path.not_like(
                        literal("%|").concat(e.c.b).concat(literal("|%"))
                    ),
                )
            )
        )
        return trav.union_all(rec)

    # -- traversal -------------------------------------------------------
    async def traverse(self, root: str, bounds: TraversalBounds) -> GraphResult:
        root = _norm(root)
        trav = self._walk_cte(root, bounds)
        stmt = select(
            trav.c.src, trav.c.dst, trav.c.tx_hash, trav.c.value_wei,
            trav.c.timestamp, trav.c.asset, trav.c.depth,
        ).limit(self._ROW_HARD_CAP)
        rows = (await self._session.execute(stmt)).all()

        # BFS order: shallowest first, higher-value first within a depth.
        rows = sorted(rows, key=lambda r: (r.depth, -r.value_wei))

        node_depth: dict[str, int] = {root: 0}
        edges: list[GraphEdge] = []
        node_cap_hit = False

        for r in rows:
            if r.dst not in node_depth:
                if len(node_depth) >= bounds.max_nodes:
                    node_cap_hit = True
                    continue
                node_depth[r.dst] = r.depth
            edges.append(
                GraphEdge(
                    tx_hash=r.tx_hash,
                    from_address=r.src,
                    to_address=r.dst,
                    value_wei=r.value_wei,
                    timestamp=r.timestamp,
                    asset=r.asset,
                )
            )

        nodes = await self._build_nodes(node_depth)
        prune = await self._detect_prune(node_depth, bounds, node_cap_hit)
        return GraphResult(root=root, nodes=nodes, edges=edges, prune=prune)

    async def _build_nodes(self, node_depth: dict[str, int]) -> list[GraphNode]:
        addrs = list(node_depth)
        # Labels (+ VASP name) for discovered addresses.
        label_rows = (
            await self._session.execute(
                select(Label.address, Label.name, Vasp.name)
                .select_from(Label)
                .join(Vasp, Label.vasp_id == Vasp.id, isouter=True)
                .where(Label.address.in_(addrs))
            )
        ).all()
        labels: dict[str, tuple[str, str | None]] = {}
        for addr, name, vasp_name in label_rows:
            labels.setdefault(addr, (name, vasp_name))

        contract_rows = (
            await self._session.execute(
                select(Wallet.address, Wallet.is_contract).where(
                    Wallet.address.in_(addrs)
                )
            )
        ).all()
        contracts = {addr: bool(is_c) for addr, is_c in contract_rows}

        nodes: list[GraphNode] = []
        for addr, depth in sorted(node_depth.items(), key=lambda kv: kv[1]):
            label_name, vasp_name = labels.get(addr, (None, None))
            nodes.append(
                GraphNode(
                    address=addr,
                    depth=depth,
                    is_labeled=addr in labels,
                    label_name=label_name,
                    vasp_name=vasp_name,
                    is_contract=contracts.get(addr, False),
                )
            )
        return nodes

    async def _exists_edge(
        self,
        nodes: Sequence[str],
        direction: Direction,
        extra: list[ColumnElement[bool]],
    ) -> bool:
        if not nodes:
            return False
        if direction is Direction.FORWARD:
            membership: ColumnElement[bool] = _TX.c.from_address.in_(nodes)
        elif direction is Direction.REVERSE:
            membership = _TX.c.to_address.in_(nodes)
        else:
            membership = or_(
                _TX.c.from_address.in_(nodes), _TX.c.to_address.in_(nodes)
            )
        stmt = (
            select(literal(1))
            .select_from(_TX)
            .where(and_(_TX.c.to_address.is_not(None), membership, *extra))
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def _detect_prune(
        self,
        node_depth: dict[str, int],
        bounds: TraversalBounds,
        node_cap_hit: bool,
    ) -> PruneInfo:
        reasons: list[PruneReason] = []
        if node_cap_hit:
            reasons.append(PruneReason.MAX_NODES)

        max_depth_nodes = [a for a, d in node_depth.items() if d == bounds.max_hops]
        expandable = [a for a, d in node_depth.items() if d < bounds.max_hops]

        time_conds: list[ColumnElement[bool]] = []
        if bounds.since is not None:
            time_conds.append(_TX.c.timestamp >= bounds.since)
        if bounds.until is not None:
            time_conds.append(_TX.c.timestamp <= bounds.until)

        # MAX_HOPS: nodes sitting at the depth cap still have onward in-bounds edges.
        if await self._exists_edge(
            max_depth_nodes,
            bounds.direction,
            [_TX.c.value_wei >= bounds.min_value_wei, *time_conds],
        ):
            reasons.append(PruneReason.MAX_HOPS)

        # MIN_VALUE: an expandable node has an adjacent edge excluded only by value.
        if bounds.min_value_wei > 0 and await self._exists_edge(
            expandable,
            bounds.direction,
            [_TX.c.value_wei < bounds.min_value_wei, *time_conds],
        ):
            reasons.append(PruneReason.MIN_VALUE)

        # TIME_WINDOW: an expandable node has an adjacent edge excluded only by time.
        if (bounds.since is not None or bounds.until is not None):
            out_of_window: list[ColumnElement[bool]] = []
            if bounds.since is not None:
                out_of_window.append(_TX.c.timestamp < bounds.since)
            if bounds.until is not None:
                out_of_window.append(_TX.c.timestamp > bounds.until)
            if await self._exists_edge(
                expandable,
                bounds.direction,
                [_TX.c.value_wei >= bounds.min_value_wei, or_(*out_of_window)],
            ):
                reasons.append(PruneReason.TIME_WINDOW)

        return PruneInfo(
            pruned=bool(reasons),
            reasons=reasons,
            nodes_visited=len(node_depth),
            max_depth_reached=max(node_depth.values()) if node_depth else 0,
        )

    # -- path extraction -------------------------------------------------
    async def shortest_paths(
        self, source: str, target: str, bounds: TraversalBounds, limit: int = 5
    ) -> list[list[str]]:
        source = _norm(source)
        target = _norm(target)
        if source == target:
            return [[source]]

        trav = self._walk_cte(source, bounds)
        stmt = (
            select(trav.c.path, trav.c.depth)
            .where(trav.c.dst == target)
            .order_by(trav.c.depth)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()

        paths: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for r in rows:
            parts = tuple(p for p in r.path.split("|") if p)
            if parts and parts not in seen:
                seen.add(parts)
                paths.append(list(parts))
        return paths
