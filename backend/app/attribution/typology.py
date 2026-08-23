"""Laundering-typology detection — real-time, computed from the already-fetched
attribution context (no extra DB queries).

Independent of `risk.py`'s sanctioned/mixer/scam proximity score: a typology
tag describes the *shape* of fund movement (peel chain, layering, structuring),
not what it's near.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from app.attribution.context_builder import AttributionContext
from app.enums import TypologyCategory
from app.schemas.graph import GraphEdge, GraphResult
from app.schemas.risk import TypologyTag

# Peel chain: at each hop the dominant continuation must carry a clear majority
# of value (a real onward transfer) while still shedding a distinct side amount
# (the "peel") — not a pure 1:1 forward, not a near-even split.
_PEEL_MIN_HOPS = 3
_PEEL_DOMINANT_RATIO = (0.70, 0.995)

# Structuring/fan-out: enough distinct recipients, at similar-enough values,
# that it reads as splitting one sum rather than ordinary bill-paying.
_SMURF_MIN_RECIPIENTS = 5
_SMURF_VALUE_TOLERANCE = 0.20


def _out_edges(graph: GraphResult) -> dict[str, list[GraphEdge]]:
    out: dict[str, list[GraphEdge]] = defaultdict(list)
    for e in graph.edges:
        out[e.from_address].append(e)
    return out


def detect_peel_chain(forward_graph: GraphResult) -> TypologyTag | None:
    """Walk the dominant forward path; flag sustained peel-and-forward hops."""
    out = _out_edges(forward_graph)
    node = forward_graph.root
    visited = {node}
    hops = 0

    while True:
        edges = out.get(node, [])
        if len(edges) < 2:
            break
        total = sum(e.value_wei for e in edges)
        if total <= 0:
            break
        dominant = max(edges, key=lambda e: e.value_wei)
        ratio = float(dominant.value_wei) / float(total)
        lo, hi = _PEEL_DOMINANT_RATIO
        if not (lo <= ratio <= hi):
            break
        nxt = dominant.to_address
        if not nxt or nxt in visited:
            break
        visited.add(nxt)
        node = nxt
        hops += 1

    if hops < _PEEL_MIN_HOPS:
        return None
    return TypologyTag(
        category=TypologyCategory.PEEL_CHAIN,
        description=(
            f"{hops} consecutive hops each forward the bulk of value while "
            "shedding a smaller amount to a side address — a peel chain."
        ),
        confidence=min(1.0, hops / (_PEEL_MIN_HOPS + 2)),
    )


_LAYERING_CATEGORIES = {"MIXER", "SANCTIONED"}


def detect_layering(context: AttributionContext) -> TypologyTag | None:
    """A mixer/sanctioned intermediary lies upstream or downstream of a VASP
    the wallet reaches.

    Checks both directions: the intermediary commonly sits *upstream*
    (reverse_graph — funds arrived at the unknown wallet having passed
    through it) before the wallet forwards on to a VASP (forward_graph).
    """
    if not any(c.reachable for c in context.candidates):
        return None
    mixer_nodes = [
        n
        for n in (*context.forward_graph.nodes, *context.reverse_graph.nodes)
        if n.depth > 0
        and n.address in context.labels
        and context.labels[n.address].category in _LAYERING_CATEGORIES
    ]
    if not mixer_nodes:
        return None
    names = ", ".join(sorted({n.label_name or n.address for n in mixer_nodes})[:3])
    return TypologyTag(
        category=TypologyCategory.LAYERING,
        description=(
            f"Funds pass through a mixer/sanctioned intermediary ({names}) "
            "before reaching a VASP — layering between origin and cash-out."
        ),
        confidence=0.8,
    )


def detect_smurfing(forward_graph: GraphResult) -> TypologyTag | None:
    """The wallet fans out to many recipients at similar values (structuring)."""
    direct = [e for e in forward_graph.edges if e.from_address == forward_graph.root]
    recipients = {e.to_address for e in direct if e.to_address}
    if len(recipients) < _SMURF_MIN_RECIPIENTS:
        return None
    values = [float(e.value_wei) for e in direct if e.to_address]
    median = statistics.median(values)
    if median <= 0:
        return None
    similar = [v for v in values if abs(v - median) / median <= _SMURF_VALUE_TOLERANCE]
    if len(similar) < _SMURF_MIN_RECIPIENTS:
        return None
    return TypologyTag(
        category=TypologyCategory.SMURFING,
        description=(
            f"{len(similar)} outgoing transfers of similar size to distinct "
            "recipients — consistent with structuring a single sum."
        ),
        confidence=min(1.0, len(similar) / (_SMURF_MIN_RECIPIENTS + 3)),
    )


def detect_typology(context: AttributionContext) -> list[TypologyTag]:
    tags = [
        detect_peel_chain(context.forward_graph),
        detect_layering(context),
        detect_smurfing(context.forward_graph),
    ]
    return [t for t in tags if t is not None]
