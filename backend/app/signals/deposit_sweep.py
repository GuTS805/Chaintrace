"""DEPOSIT_SWEEP: many deposit addresses consolidating into the candidate hot
wallet (a first-class signal, requirement #3).

Feature blends cluster size and near-full-balance ratio; the exact contribution
is still learned by the model.
"""

from __future__ import annotations

import math

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import CANONICAL_CLUSTER_SIZE, GraphFacts


class DepositSweepSignal(Signal):
    signal_type = SignalType.DEPOSIT_SWEEP
    feature_name = "sweep_intensity"

    def feature(self, facts: GraphFacts) -> float:
        if facts.sweep_cluster_size == 0:
            return 0.0
        size_component = min(facts.sweep_cluster_size / CANONICAL_CLUSTER_SIZE, 1.0)
        # Geometric mean: both a sizeable cluster AND near-full sweeps must hold.
        return math.sqrt(size_component * facts.near_full_ratio)

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if facts.sweep_cluster_size == 0:
            return None
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"{facts.sweep_cluster_size} deposit address(es) consolidate into "
                f"{facts.vasp_name}'s hot wallet; "
                f"{facts.near_full_ratio:.0%} of sweeps move near-full balances "
                f"(interval regularity {facts.interval_regularity:.2f})."
            ),
            weight=0.0,
            tx_hashes=list(facts.sweep_tx_hashes),
            timestamps=list(facts.sweep_timestamps),
        )
