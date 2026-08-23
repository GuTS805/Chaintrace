"""Attribution signals.

Each signal is a small class with a common interface (see base.Signal) that maps
a precomputed GraphFacts into (a) one numeric feature for the classifier and
(b) a human-readable Evidence object. The expensive graph derivations are done
once in facts.build_graph_facts so training and inference compute features
identically (no train/serve skew).
"""

from app.signals.base import Signal, SignalResult
from app.signals.facts import GraphFacts, LabelInfo, build_graph_facts
from app.signals.registry import FEATURE_NAMES, SIGNALS, feature_vector

__all__ = [
    "FEATURE_NAMES",
    "SIGNALS",
    "GraphFacts",
    "LabelInfo",
    "Signal",
    "SignalResult",
    "build_graph_facts",
    "feature_vector",
]
