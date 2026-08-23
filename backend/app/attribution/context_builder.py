"""Build attribution contexts (candidate GraphFacts) for a wallet from the DB.

Candidate discovery uses the bounded forward traversal; the deposit-sweep side is
gathered with direct inbound-transaction queries (kept in real money-flow
direction, unlike a reversed GraphEdge) so the facts builder sees correct edges.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Label, Transaction, Vasp
from app.providers.base import ProviderTx, normalize_address
from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository
from app.schemas.graph import GraphResult
from app.signals.facts import GraphFacts, LabelInfo, build_graph_facts


@dataclass
class AttributionContext:
    unknown: str
    candidates: list[GraphFacts]
    forward_graph: GraphResult
    reverse_graph: GraphResult
    labels: dict[str, LabelInfo] = field(default_factory=dict)


def _to_provider_tx(t: Transaction) -> ProviderTx:
    return ProviderTx(
        tx_hash=t.tx_hash,
        block_number=t.block_number,
        timestamp=t.timestamp,
        from_address=t.from_address,
        to_address=t.to_address,
        value_wei=t.value_wei,
        asset=t.asset,
    )


class ContextBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SqlGraphRepository(session)

    async def _inbound(self, addrs: Iterable[str]) -> list[Transaction]:
        addrs = list({normalize_address(a) for a in addrs})
        if not addrs:
            return []
        rows = (
            await self._session.execute(
                select(Transaction).where(Transaction.to_address.in_(addrs))
            )
        ).scalars().all()
        return list(rows)

    async def _load_labels(self, addrs: set[str]) -> dict[str, LabelInfo]:
        if not addrs:
            return {}
        rows = (
            await self._session.execute(
                select(
                    Label.address, Label.name, Vasp.name, Label.confidence, Label.category
                )
                .select_from(Label)
                .join(Vasp, Label.vasp_id == Vasp.id, isouter=True)
                .where(Label.address.in_(list(addrs)))
            )
        ).all()
        out: dict[str, LabelInfo] = {}
        for addr, name, vasp_name, conf, category in rows:
            if addr in out:
                continue
            cat = category.value if hasattr(category, "value") else str(category)
            out[addr] = LabelInfo(
                name=name, vasp_name=vasp_name, confidence=float(conf), category=cat
            )
        return out

    async def build(
        self, unknown: str, *, depth: int = 6, min_value_wei: int = 0
    ) -> AttributionContext:
        unknown = normalize_address(unknown)
        forward = await self._repo.traverse(
            unknown,
            TraversalBounds(
                max_hops=depth, direction=Direction.FORWARD, max_nodes=2000
            ),
        )
        # Reverse reachability powers the (separate) risk score: where funds came
        # from, e.g. an upstream sanctioned mixer.
        reverse = await self._repo.traverse(
            unknown,
            TraversalBounds(
                max_hops=depth, direction=Direction.REVERSE, max_nodes=2000
            ),
        )

        # Candidate VASPs = reached, labeled, VASP-linked nodes.
        vasp_hots: dict[str, set[str]] = {}
        for node in forward.nodes:
            if node.depth > 0 and node.is_labeled and node.vasp_name:
                vasp_hots.setdefault(node.vasp_name, set()).add(node.address)

        # Assemble a real-direction edge set: forward subgraph + inbound to the
        # unknown + deposits into each hot wallet + funders of those deposits.
        edges: dict[str, ProviderTx] = {}
        for e in forward.edges:
            edges[e.tx_hash] = ProviderTx(
                tx_hash=e.tx_hash,
                timestamp=e.timestamp,
                from_address=e.from_address,
                to_address=e.to_address,
                value_wei=e.value_wei,
            )

        for t in await self._inbound([unknown]):
            edges.setdefault(t.tx_hash, _to_provider_tx(t))

        all_hot = set().union(*vasp_hots.values()) if vasp_hots else set()
        deposits_into_hot = await self._inbound(all_hot)
        deposit_addrs = {t.from_address for t in deposits_into_hot}
        for t in deposits_into_hot:
            edges.setdefault(t.tx_hash, _to_provider_tx(t))
        for t in await self._inbound(deposit_addrs):
            edges.setdefault(t.tx_hash, _to_provider_tx(t))

        edge_list = list(edges.values())
        addr_set: set[str] = set()
        for ptx in edge_list:
            addr_set.add(ptx.from_address)
            if ptx.to_address:
                addr_set.add(ptx.to_address)
        # Include reverse-graph nodes so upstream labels (e.g. mixers) resolve.
        addr_set.update(n.address for n in reverse.nodes)
        labels = await self._load_labels(addr_set)

        candidates = [
            build_graph_facts(unknown, vasp, hots, edge_list, labels)
            for vasp, hots in vasp_hots.items()
        ]
        return AttributionContext(
            unknown=unknown,
            candidates=candidates,
            forward_graph=forward,
            reverse_graph=reverse,
            labels=labels,
        )
