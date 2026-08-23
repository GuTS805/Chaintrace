"""HOP_PATH: proximity of the unknown wallet to the candidate via shortest path.

Hop distance is a *feature* fed to the model (requirement #4) — this class never
maps a hop count to a fixed confidence.
"""

from __future__ import annotations

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import GraphFacts


class HopPathSignal(Signal):
    signal_type = SignalType.HOP_PATH
    feature_name = "hop_closeness"

    def feature(self, facts: GraphFacts) -> float:
        if not facts.reachable or facts.min_hops is None:
            return 0.0
        return 1.0 / (1.0 + facts.min_hops)

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if not facts.reachable or facts.min_hops is None:
            return None
        path = " -> ".join(facts.best_path)
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"Unknown wallet reaches {facts.vasp_name} in {facts.min_hops} hop(s): "
                f"{path}"
            ),
            weight=0.0,
            tx_hashes=list(facts.path_tx_hashes),
            timestamps=list(facts.path_timestamps),
        )
