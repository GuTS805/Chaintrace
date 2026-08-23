"""Types describing a synthetic scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.providers.base import ProviderTx, WalletInfo


class ExpectedOutcome(StrEnum):
    """Ground-truth attribution outcome a scenario is designed to exercise."""

    CLEAN = "CLEAN"  # single dominant candidate, high confidence
    MODERATE = "MODERATE"  # single candidate, moderate confidence
    INSUFFICIENT = "INSUFFICIENT"  # no candidate clears the floor -> "I don't know"
    AMBIGUOUS = "AMBIGUOUS"  # multiple credible candidates, none dominant


@dataclass
class ScenarioLabel:
    """A label to seed alongside the scenario (VASP hot wallet, mixer, ...)."""

    address: str
    name: str
    category: str
    vasp: str | None = None


@dataclass
class Scenario:
    """A self-contained synthetic graph plus its ground truth."""

    key: str
    title: str
    description: str
    unknown_wallet: str
    expected: ExpectedOutcome
    # Ground-truth VASP for the unknown wallet (None for the INSUFFICIENT case).
    ground_truth: str | None
    # For AMBIGUOUS: the set of plausible VASPs competing for the wallet.
    ground_truth_candidates: list[str] = field(default_factory=list)
    wallets: list[WalletInfo] = field(default_factory=list)
    transactions: list[ProviderTx] = field(default_factory=list)
    labels: list[ScenarioLabel] = field(default_factory=list)
