"""PATTERN_SIMILARITY: cosine similarity of the candidate's deposit-cluster
fingerprint (near-full ratio, interval regularity, normalized cluster size) to a
canonical exchange sweep fingerprint.

Defined against an explicit reference vector so the score is always traceable —
not a catch-all bucket.
"""

from __future__ import annotations

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import GraphFacts


class PatternSimilaritySignal(Signal):
    signal_type = SignalType.PATTERN_SIMILARITY
    feature_name = "pattern_similarity"

    def feature(self, facts: GraphFacts) -> float:
        return facts.pattern_similarity

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if facts.pattern_similarity <= 0.0 or facts.sweep_cluster_size == 0:
            return None
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"The consolidation pattern matches a typical exchange sweep "
                f"fingerprint (similarity {facts.pattern_similarity:.2f}): "
                f"cluster size {facts.sweep_cluster_size}, "
                f"near-full {facts.near_full_ratio:.0%}, "
                f"regularity {facts.interval_regularity:.2f}."
            ),
            weight=0.0,
        )
