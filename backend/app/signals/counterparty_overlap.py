"""COUNTERPARTY_OVERLAP: shared counterparties between the unknown wallet and the
candidate's deposit cluster."""

from __future__ import annotations

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.base import Signal
from app.signals.facts import GraphFacts


class CounterpartyOverlapSignal(Signal):
    signal_type = SignalType.COUNTERPARTY_OVERLAP
    feature_name = "counterparty_overlap"

    def feature(self, facts: GraphFacts) -> float:
        return facts.counterparty_overlap_ratio

    def evidence(self, facts: GraphFacts) -> Evidence | None:
        if not facts.shared_counterparties:
            return None
        shown = facts.shared_counterparties[:5]
        return Evidence(
            signal_type=self.signal_type,
            description=(
                f"{len(facts.shared_counterparties)} counterparties shared between the "
                f"unknown wallet and {facts.vasp_name}'s deposit cluster "
                f"({facts.counterparty_overlap_ratio:.0%} of the wallet's counterparties). "
                f"e.g. {', '.join(shown)}"
            ),
            weight=0.0,
        )
