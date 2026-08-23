"""Synthetic dataset generator.

Produces four deterministic, offline demo scenarios (see scenarios.py). The same
generator output doubles as labeled training data for the Phase 4 classifier:
each scenario declares an `unknown_wallet` and its `ground_truth` VASP (or None),
plus the `expected` attribution outcome.
"""

from app.synthetic.scenarios import build_all_scenarios
from app.synthetic.types import ExpectedOutcome, Scenario

__all__ = ["ExpectedOutcome", "Scenario", "build_all_scenarios"]
