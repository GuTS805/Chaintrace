"""GraphFacts: all per-candidate graph derivations, computed once.

`build_graph_facts` takes a plain edge list (works identically whether the edges
came from the DB at inference time or from the synthetic training generator) and
derives every quantity the signals need. This single code path is what keeps the
trained model's features consistent with what it sees in production.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.providers.base import ProviderTx

# An exchange hot wallet typically consolidates many deposit addresses; this is
# the reference cluster size at which the sweep signal is considered "saturated".
CANONICAL_CLUSTER_SIZE = 8
NEAR_FULL_THRESHOLD = 0.9  # swept value / deposit inflow >= this == near-full
MAX_BFS_HOPS = 8
# A sweep is a many-to-one consolidation; a lone deposit is not a sweep.
MIN_SWEEP_CLUSTER = 2


def _norm(a: str) -> str:
    return a.strip().lower()


@dataclass(frozen=True)
class LabelInfo:
    name: str
    vasp_name: str | None
    confidence: float
    category: str


@dataclass
class GraphFacts:
    """Fully-derived facts for one (unknown wallet, candidate VASP) pair."""

    unknown: str
    vasp_name: str
    hot_addresses: set[str]

    # Reachability / path.
    reachable: bool = False
    min_hops: int | None = None
    best_path: list[str] = field(default_factory=list)
    path_tx_hashes: list[str] = field(default_factory=list)
    path_timestamps: list[datetime] = field(default_factory=list)
    reached_hot: str | None = None

    # Deposit-sweep.
    deposit_cluster: list[str] = field(default_factory=list)
    sweep_tx_hashes: list[str] = field(default_factory=list)
    sweep_timestamps: list[datetime] = field(default_factory=list)
    sweep_cluster_size: int = 0
    near_full_ratio: float = 0.0
    interval_regularity: float = 0.0

    # Counterparty overlap.
    shared_counterparties: list[str] = field(default_factory=list)
    counterparty_overlap_ratio: float = 0.0

    # Temporal.
    temporal_correlation: float = 0.0

    # Label certainty.
    label_confidence: float = 0.0

    # Pattern similarity (cosine to a canonical exchange fingerprint).
    pattern_similarity: float = 0.0


def _bfs_shortest_path(
    unknown: str,
    hot: set[str],
    adj: dict[str, list[tuple[str, ProviderTx]]],
) -> tuple[int | None, list[str], list[ProviderTx]]:
    """Shortest forward path from unknown to any hot address (BFS, bounded)."""
    if unknown in hot:
        return 0, [unknown], []
    visited = {unknown}
    # queue holds (node, path_nodes, path_edges)
    queue: deque[tuple[str, list[str], list[ProviderTx]]] = deque([(unknown, [unknown], [])])
    while queue:
        node, path, pedges = queue.popleft()
        if len(path) - 1 >= MAX_BFS_HOPS:
            continue
        for nxt, edge in adj.get(node, []):
            if nxt in visited:
                continue
            new_path = [*path, nxt]
            new_edges = [*pedges, edge]
            if nxt in hot:
                return len(new_path) - 1, new_path, new_edges
            visited.add(nxt)
            queue.append((nxt, new_path, new_edges))
    return None, [], []


def canonical_pattern_similarity(
    near_full_ratio: float, interval_regularity: float, cluster_size: int
) -> float:
    """Cosine similarity of a deposit fingerprint to the canonical exchange
    fingerprint [1, 1, 1]. Shared by inference and the training generator so both
    compute the pattern feature identically."""
    v = [
        near_full_ratio,
        interval_regularity,
        min(cluster_size / CANONICAL_CLUSTER_SIZE, 1.0),
    ]
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return 0.0
    return min(sum(v) / (math.sqrt(3.0) * norm), 1.0)


def _interval_regularity(timestamps: list[datetime]) -> float:
    """1 / (1 + coefficient of variation of inter-event gaps), in [0, 1]."""
    if len(timestamps) < 3:
        return 0.0
    ts = sorted(timestamps)
    gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:], strict=False)]
    gaps = [g for g in gaps if g > 0]
    if len(gaps) < 2:
        return 0.0
    mean = statistics.fmean(gaps)
    if mean == 0:
        return 0.0
    cv = statistics.pstdev(gaps) / mean
    return 1.0 / (1.0 + cv)


def build_graph_facts(
    unknown: str,
    vasp_name: str,
    hot_addresses: set[str],
    edges: list[ProviderTx],
    labels: dict[str, LabelInfo],
) -> GraphFacts:
    unknown = _norm(unknown)
    hot = {_norm(h) for h in hot_addresses}
    facts = GraphFacts(unknown=unknown, vasp_name=vasp_name, hot_addresses=hot)

    adj: dict[str, list[tuple[str, ProviderTx]]] = defaultdict(list)
    counterparties: dict[str, set[str]] = defaultdict(set)
    inflow: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    into_hot: list[ProviderTx] = []

    for e in edges:
        frm = _norm(e.from_address)
        to = _norm(e.to_address) if e.to_address else None
        if to is None:
            continue
        adj[frm].append((to, e))
        counterparties[frm].add(to)
        counterparties[to].add(frm)
        inflow[to] += e.value_wei
        if to in hot:
            into_hot.append(e)

    # --- reachability / path ---
    min_hops, path, pedges = _bfs_shortest_path(unknown, hot, adj)
    if min_hops is not None:
        facts.reachable = True
        facts.min_hops = min_hops
        facts.best_path = path
        facts.reached_hot = path[-1]
        facts.path_tx_hashes = [e.tx_hash for e in pedges]
        facts.path_timestamps = [e.timestamp for e in pedges]
        reached = facts.reached_hot
        if reached in labels:
            facts.label_confidence = labels[reached].confidence

    # --- deposit-sweep (many-to-one only; a lone deposit is not a sweep) ---
    deposit_cluster = sorted({_norm(e.from_address) for e in into_hot} - hot)
    if len(deposit_cluster) < MIN_SWEEP_CLUSTER:
        deposit_cluster = []
    facts.deposit_cluster = deposit_cluster
    facts.sweep_cluster_size = len(deposit_cluster)
    cluster_set = set(deposit_cluster)
    sweep_edges = [e for e in into_hot if _norm(e.from_address) in cluster_set]
    facts.sweep_tx_hashes = [e.tx_hash for e in sweep_edges]
    facts.sweep_timestamps = [e.timestamp for e in sweep_edges]

    if sweep_edges:
        near_full = 0
        for e in sweep_edges:
            dep = _norm(e.from_address)
            received = inflow.get(dep, Decimal(0))
            if received > 0 and float(e.value_wei) / float(received) >= NEAR_FULL_THRESHOLD:
                near_full += 1
        facts.near_full_ratio = near_full / len(sweep_edges)
    facts.interval_regularity = _interval_regularity(facts.sweep_timestamps)

    # --- counterparty overlap ---
    unknown_cps = counterparties.get(unknown, set()) - {unknown}
    cluster_cps: set[str] = set()
    for dep in deposit_cluster:
        cluster_cps |= counterparties.get(dep, set())
    cluster_cps -= hot
    cluster_cps.discard(unknown)
    shared = sorted(unknown_cps & cluster_cps)
    facts.shared_counterparties = shared
    facts.counterparty_overlap_ratio = (
        len(shared) / len(unknown_cps) if unknown_cps else 0.0
    )

    # --- temporal correlation (deposit time vs sweep times) ---
    if facts.path_timestamps and facts.sweep_timestamps:
        t_deposit = max(facts.path_timestamps)  # when the unknown's funds arrived
        gaps_h = [
            abs((s - t_deposit).total_seconds()) / 3600.0 for s in facts.sweep_timestamps
        ]
        min_gap = min(gaps_h)
        facts.temporal_correlation = 1.0 / (1.0 + min_gap / 24.0)

    # --- pattern similarity (cosine to canonical exchange fingerprint [1,1,1]) ---
    facts.pattern_similarity = canonical_pattern_similarity(
        facts.near_full_ratio, facts.interval_regularity, facts.sweep_cluster_size
    )

    return facts
