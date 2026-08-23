"""Unit tests for each attribution signal + the shared facts builder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.providers.base import ProviderTx
from app.signals import FEATURE_NAMES, SIGNALS, build_graph_facts, feature_vector
from app.signals.counterparty_overlap import CounterpartyOverlapSignal
from app.signals.deposit_sweep import DepositSweepSignal
from app.signals.facts import LabelInfo, detect_sweep_cluster
from app.signals.hop_path import HopPathSignal
from app.signals.known_label import KnownLabelSignal
from app.signals.pattern_similarity import PatternSimilaritySignal

HOT = "0xhot"
UNKNOWN = "0xunknown"
BASE = datetime(2024, 5, 1, tzinfo=UTC)


def _tx(i: int, frm: str, to: str, eth: float) -> ProviderTx:
    return ProviderTx(
        tx_hash=f"0x{i:064x}",
        timestamp=BASE + timedelta(hours=i),
        from_address=frm,
        to_address=to,
        value_wei=Decimal(int(eth * 10**18)),
    )


def _sweep_edges() -> list[ProviderTx]:
    edges: list[ProviderTx] = []
    n = 0
    # unknown solely funds dep0; other deposits funded by their own sources.
    edges.append(_tx(n := n + 1, UNKNOWN, "0xdep0", 10))
    for i in range(1, 10):
        edges.append(_tx(n := n + 1, f"0xsrc{i}", f"0xdep{i}", 10))
    # every deposit sweeps near-full into the hot wallet, hourly.
    for i in range(10):
        edges.append(_tx(n := n + 1, f"0xdep{i}", HOT, 9.99))
    return edges


def _facts():
    labels = {HOT: LabelInfo("Binance: Hot Wallet", "Binance", 0.9, "EXCHANGE")}
    return build_graph_facts(UNKNOWN, "Binance", {HOT}, _sweep_edges(), labels)


def test_facts_reachability_and_cluster() -> None:
    f = _facts()
    assert f.reachable is True
    assert f.min_hops == 2  # unknown -> dep0 -> hot
    assert f.reached_hot == HOT
    assert f.sweep_cluster_size == 10
    assert f.near_full_ratio == 1.0
    assert f.label_confidence == 0.9


def test_detect_sweep_cluster_standalone() -> None:
    """Same detector, called directly with pre-derived inputs (as
    cluster_builder does over a hot wallet's full inbound history, not a
    bounded attribution-context slice)."""
    edges = _sweep_edges()
    into_hot = [e for e in edges if e.to_address == HOT]
    inflow: dict[str, Decimal] = {}
    for e in edges:
        inflow[e.to_address] = inflow.get(e.to_address, Decimal(0)) + e.value_wei

    sweep = detect_sweep_cluster({HOT}, into_hot, inflow)
    assert sweep.sweep_cluster_size == 10
    assert sweep.near_full_ratio == 1.0
    assert set(sweep.deposit_cluster) == {f"0xdep{i}" for i in range(10)}


def test_feature_vector_matches_registry_order() -> None:
    f = _facts()
    vec = feature_vector(f)
    assert len(vec) == len(FEATURE_NAMES) == 6
    assert all(0.0 <= x <= 1.0 for x in vec)


def test_hop_path_signal() -> None:
    f = _facts()
    sig = HopPathSignal()
    assert sig.feature(f) == 1.0 / 3.0  # 1/(1+2)
    ev = sig.evidence(f)
    assert ev is not None and ev.tx_hashes


def test_deposit_sweep_signal_fires_strongly() -> None:
    f = _facts()
    sig = DepositSweepSignal()
    assert sig.feature(f) > 0.9  # full cluster, near-full sweeps
    ev = sig.evidence(f)
    assert ev is not None and len(ev.tx_hashes) == 10


def test_known_label_signal() -> None:
    f = _facts()
    assert KnownLabelSignal().feature(f) == 0.9


def test_pattern_similarity_positive() -> None:
    f = _facts()
    assert PatternSimilaritySignal().feature(f) > 0.5


def test_unreachable_wallet_has_zero_features_and_no_evidence() -> None:
    labels: dict[str, LabelInfo] = {}
    # A graph with no path from UNKNOWN to HOT.
    edges = [_tx(1, "0xa", "0xb", 1), _tx(2, "0xb", "0xc", 1)]
    f = build_graph_facts(UNKNOWN, "Binance", {HOT}, edges, labels)
    assert f.reachable is False
    assert feature_vector(f) == [0.0] * 6
    for sig in SIGNALS:
        assert sig.evidence(f) is None


def test_counterparty_overlap_when_shared() -> None:
    # unknown and dep0 both interact with 0xshared.
    edges = _sweep_edges()
    edges.append(_tx(100, UNKNOWN, "0xshared", 1))
    edges.append(_tx(101, "0xdep1", "0xshared", 1))
    labels = {HOT: LabelInfo("Binance", "Binance", 0.9, "EXCHANGE")}
    f = build_graph_facts(UNKNOWN, "Binance", {HOT}, edges, labels)
    assert "0xshared" in f.shared_counterparties
    assert CounterpartyOverlapSignal().feature(f) > 0.0
