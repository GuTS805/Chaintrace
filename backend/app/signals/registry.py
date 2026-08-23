"""Ordered signal registry — the single source of truth for feature order.

The classifier's feature vector and TreeSHAP contributions are indexed by this
order, so it must stay stable across training and inference.
"""

from __future__ import annotations

from app.signals.base import Signal
from app.signals.counterparty_overlap import CounterpartyOverlapSignal
from app.signals.deposit_sweep import DepositSweepSignal
from app.signals.facts import GraphFacts
from app.signals.hop_path import HopPathSignal
from app.signals.known_label import KnownLabelSignal
from app.signals.pattern_similarity import PatternSimilaritySignal
from app.signals.temporal_correlation import TemporalCorrelationSignal

SIGNALS: list[Signal] = [
    HopPathSignal(),
    DepositSweepSignal(),
    CounterpartyOverlapSignal(),
    TemporalCorrelationSignal(),
    KnownLabelSignal(),
    PatternSimilaritySignal(),
]

FEATURE_NAMES: list[str] = [s.feature_name for s in SIGNALS]


def feature_vector(facts: GraphFacts) -> list[float]:
    """Compute the ordered feature vector for a candidate."""
    return [s.feature(facts) for s in SIGNALS]
