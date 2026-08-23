"""Common signal interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.enums import SignalType
from app.schemas.attribution import Evidence
from app.signals.facts import GraphFacts


@dataclass
class SignalResult:
    """A signal's numeric feature plus its (optional) evidence."""

    feature: float
    evidence: Evidence | None


class Signal(ABC):
    """Maps GraphFacts -> one classifier feature + one Evidence object."""

    signal_type: SignalType
    feature_name: str

    @abstractmethod
    def feature(self, facts: GraphFacts) -> float:
        """The numeric feature fed to the classifier (never a hard-coded score)."""

    @abstractmethod
    def evidence(self, facts: GraphFacts) -> Evidence | None:
        """Human-readable evidence, or None if the signal did not fire.

        The engine fills in `weight` with the model's TreeSHAP contribution.
        """

    def evaluate(self, facts: GraphFacts) -> SignalResult:
        return SignalResult(feature=self.feature(facts), evidence=self.evidence(facts))
