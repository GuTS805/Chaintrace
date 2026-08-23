"""TEMPORAL_CORRELATION: timing alignment between the unknown wallet's deposit and
the candidate hot wallet's sweeps."""

from __future__ import annotations

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import GraphFacts


class TemporalCorrelationSignal(Signal):
    signal_type = SignalType.TEMPORAL_CORRELATION
    feature_name = "temporal_correlation"

    def feature(self, facts: GraphFacts) -> float:
        return facts.temporal_correlation

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if facts.temporal_correlation <= 0.0 or not facts.sweep_timestamps:
            return None
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"The unknown wallet's deposit is closely timed with sweeps into "
                f"{facts.vasp_name}'s hot wallet (alignment "
                f"{facts.temporal_correlation:.2f})."
            ),
            weight=0.0,
            timestamps=[*facts.path_timestamps, *facts.sweep_timestamps],
        )
