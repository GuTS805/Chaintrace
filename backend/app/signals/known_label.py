"""KNOWN_LABEL: the unknown wallet's funds reach a wallet carrying a known label,
weighted by that label's source confidence (OFAC/ethereum-lists/etc.)."""

from __future__ import annotations

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import GraphFacts


class KnownLabelSignal(Signal):
    signal_type = SignalType.KNOWN_LABEL
    feature_name = "label_confidence"

    def feature(self, facts: GraphFacts) -> float:
        if not facts.reachable:
            return 0.0
        return facts.label_confidence

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if not facts.reachable or facts.label_confidence <= 0.0:
            return None
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"Funds reach {facts.reached_hot}, a wallet labeled as "
                f"{facts.vasp_name} (label confidence {facts.label_confidence:.2f})."
            ),
            weight=0.0,
            tx_hashes=list(facts.path_tx_hashes),
        )
