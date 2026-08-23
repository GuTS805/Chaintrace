"""The four demo scenarios (HARD REQUIREMENT: these ARE the demo).

All deterministic and offline. Each is designed to exercise one attribution
outcome the engine (Phase 4) must handle:

  1. ransomware_to_exchange  -> CLEAN       (Binance, ~90%+)
  2. peel_chain              -> MODERATE    (Kraken, ~70%)
  3. dead_end                -> INSUFFICIENT (no VASP linkage -> "I don't know")
  4. two_exchanges           -> AMBIGUOUS   (Binance vs Coinbase, split)

VASP hot wallets / the mixer reuse the same real addresses shipped in
data/labels, so seeding ties the synthetic graph to the ingested labels.
"""

from __future__ import annotations

from app.synthetic.builder import ScenarioBuilder
from app.synthetic.types import ExpectedOutcome, Scenario

# Real addresses that also appear in data/labels (kept in sync on purpose).
BINANCE_HOT = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
KRAKEN_HOT = "0x2910543af39aba0cd09dbb2d50200b3e800a63d2"
COINBASE_HOT = "0x71660c4005ba85c37ccec55d0c4493e66fe775d3"
TORNADO = "0x722122df12d4e14e13ac3b6895a86e84145b6967"


def _sweep_cluster(
    b: ScenarioBuilder,
    *,
    prefix: str,
    hot_ref: str,
    n: int,
    amount_eth: float,
    funder: str | None = None,
    funder_index: int = 0,
) -> list[str]:
    """Model an exchange deposit-sweep: n deposit addresses funded, then each
    swept near-full into the hot wallet at regular hourly intervals."""
    deposits: list[str] = []
    for i in range(n):
        dep = f"{prefix}_dep{i}"
        if funder is not None and i == funder_index:
            b.tx(funder, dep, amount_eth, gap_minutes=15)
        else:
            b.tx(f"{prefix}_src{i}", dep, amount_eth, gap_minutes=5)
        deposits.append(dep)
    # Consolidation phase: regular, near-full-balance transfers to the hot wallet.
    for dep in deposits:
        b.tx(dep, hot_ref, round(amount_eth - 0.01, 4), gap_minutes=60)
    return deposits


def scenario_ransomware() -> Scenario:
    b = ScenarioBuilder(
        key="ransomware_to_exchange",
        title="Ransomware payout → mixer → exchange deposit",
        description=(
            "Three victims pay a ransom; the operator launders through a "
            "sanctioned mixer, then cashes out via a Binance deposit address "
            "that is swept into Binance's hot wallet alongside many others."
        ),
    )
    b.known(BINANCE_HOT, "binance_hot")
    b.known(TORNADO, "tornado")
    b.label("binance_hot", "Binance: Hot Wallet", "EXCHANGE", vasp="Binance")
    b.label("tornado", "Tornado Cash Router", "SANCTIONED")

    # Ransom collection.
    for i in range(3):
        b.tx(f"victim{i}", "attacker", 15, gap_minutes=45)
    # Layering through the mixer (feeds the RISK score, not attribution).
    for _ in range(3):
        b.tx("attacker", "tornado", 13, gap_minutes=30)
    b.tx("tornado", "layer1", 12, gap_minutes=120)
    b.tx("layer1", "cashout", 11.5, gap_minutes=90)

    # Attribution-relevant subgraph: cashout deposits to Binance, swept with peers.
    _sweep_cluster(
        b, prefix="bnc", hot_ref="binance_hot", n=10, amount_eth=11.5,
        funder="cashout", funder_index=0,
    )

    b.wallet("cashout", balance_eth=0)
    return b.build(
        unknown="cashout",
        expected=ExpectedOutcome.CLEAN,
        ground_truth="Binance",
    )


def scenario_peel_chain() -> Scenario:
    b = ScenarioBuilder(
        key="peel_chain",
        title="Peel chain (5 hops) → Kraken",
        description=(
            "Funds move through a five-hop peel chain, shaving a small amount at "
            "each hop, before a single deposit into Kraken's hot wallet. Longer "
            "distance and no sweep cluster -> moderate confidence."
        ),
    )
    b.known(KRAKEN_HOT, "kraken_hot")
    b.label("kraken_hot", "Kraken", "EXCHANGE", vasp="Kraken")

    amount = 20.0
    prev = "unknown"
    for hop in range(1, 5):
        nxt = f"h{hop}"
        b.tx(prev, nxt, round(amount - 0.5, 4), gap_minutes=75)
        b.tx(prev, f"peel{hop}", 0.4, gap_minutes=10)  # peeled-off change
        amount -= 0.5
        prev = nxt
    # Final hop into a Kraken deposit address, then to the hot wallet.
    b.tx(prev, "kraken_deposit", round(amount - 0.5, 4), gap_minutes=75)
    b.tx("kraken_deposit", "kraken_hot", round(amount - 0.6, 4), gap_minutes=120)

    return b.build(
        unknown="unknown",
        expected=ExpectedOutcome.MODERATE,
        ground_truth="Kraken",
    )


def scenario_dead_end() -> Scenario:
    b = ScenarioBuilder(
        key="dead_end",
        title="No VASP linkage (insufficient evidence)",
        description=(
            "A wallet transacting only peer-to-peer with unlabeled counterparties. "
            "No path reaches any known VASP within bounds -> the engine must "
            "return insufficient_evidence."
        ),
    )
    b.tx("unknown", "friend1", 2.0, gap_minutes=200)
    b.tx("friend1", "friend2", 1.0, gap_minutes=300)
    b.tx("unknown", "friend3", 0.5, gap_minutes=500)
    b.tx("friend3", "friend4", 0.2, gap_minutes=400)
    b.tx("friend2", "unknown", 0.3, gap_minutes=600)

    return b.build(
        unknown="unknown",
        expected=ExpectedOutcome.INSUFFICIENT,
        ground_truth=None,
    )


def scenario_two_exchanges() -> Scenario:
    b = ScenarioBuilder(
        key="two_exchanges",
        title="Two VASPs competing (ambiguous)",
        description=(
            "The wallet splits funds almost evenly into a Binance deposit and a "
            "Coinbase deposit, each swept into its exchange's hot wallet. Two "
            "credible candidates, neither dominant -> ambiguous split."
        ),
    )
    b.known(BINANCE_HOT, "binance_hot")
    b.known(COINBASE_HOT, "coinbase_hot")
    b.label("binance_hot", "Binance: Hot Wallet", "EXCHANGE", vasp="Binance")
    b.label("coinbase_hot", "Coinbase 1", "EXCHANGE", vasp="Coinbase")

    # Near-even split into two exchanges.
    b.tx("unknown", "bnc_dep0", 10.0, gap_minutes=30)
    b.tx("unknown", "cbs_dep0", 9.5, gap_minutes=30)

    _sweep_cluster(b, prefix="bnc", hot_ref="binance_hot", n=4, amount_eth=10.0)
    _sweep_cluster(b, prefix="cbs", hot_ref="coinbase_hot", n=4, amount_eth=9.5)
    # Wire the unknown's deposits into each cluster's sweep.
    b.tx("bnc_dep0", "binance_hot", 9.99, gap_minutes=60)
    b.tx("cbs_dep0", "coinbase_hot", 9.49, gap_minutes=60)

    return b.build(
        unknown="unknown",
        expected=ExpectedOutcome.AMBIGUOUS,
        ground_truth=None,
        ground_truth_candidates=["Binance", "Coinbase"],
    )


def build_all_scenarios() -> list[Scenario]:
    return [
        scenario_ransomware(),
        scenario_peel_chain(),
        scenario_dead_end(),
        scenario_two_exchanges(),
    ]
