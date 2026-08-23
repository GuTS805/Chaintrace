"""Build an offline FixtureProvider straight from the synthetic scenarios.

Lets later phases and tests run the full attribution path with no DB and no
network — just the in-memory scenario graph.
"""

from __future__ import annotations

from app.providers.fixture import FixtureProvider
from app.synthetic.scenarios import build_all_scenarios
from app.synthetic.types import Scenario


def build_fixture_provider(scenarios: list[Scenario] | None = None) -> FixtureProvider:
    scenarios = scenarios or build_all_scenarios()
    wallets = [w for s in scenarios for w in s.wallets]
    txs = [t for s in scenarios for t in s.transactions]
    return FixtureProvider(wallets=wallets, transactions=txs)
