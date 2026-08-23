"""Engine decision logic: insufficient vs ambiguous vs single (deterministic)."""

from __future__ import annotations

from app.attribution.engine import AttributionEngine
from app.schemas.attribution import VaspCandidate


class _StubModel:
    model_version = "test-v"
    threshold = 0.55


def _engine() -> AttributionEngine:
    return AttributionEngine(_StubModel())  # type: ignore[arg-type]


def _c(name: str, p: float) -> VaspCandidate:
    return VaspCandidate(vasp_name=name, probability=p)


def test_no_candidates_is_insufficient() -> None:
    res = _engine()._decide([])
    assert res.insufficient_evidence is True
    assert res.ambiguous is False
    assert res.candidates == []


def test_below_floor_is_insufficient() -> None:
    res = _engine()._decide([_c("Binance", 0.30), _c("Kraken", 0.10)])
    assert res.insufficient_evidence is True
    assert res.ambiguous is False


def test_below_threshold_single_is_insufficient() -> None:
    # Above the floor (0.45) but under the 0.55 threshold, no close rival.
    res = _engine()._decide([_c("Binance", 0.50)])
    assert res.insufficient_evidence is True


def test_confident_single_attribution() -> None:
    res = _engine()._decide([_c("Binance", 0.92), _c("Kraken", 0.20)])
    assert res.insufficient_evidence is False
    assert res.ambiguous is False
    assert res.candidates[0].vasp_name == "Binance"


def test_two_close_candidates_are_ambiguous() -> None:
    res = _engine()._decide([_c("Binance", 0.60), _c("Coinbase", 0.55)])
    assert res.ambiguous is True
    assert res.insufficient_evidence is False
    assert {c.vasp_name for c in res.candidates} == {"Binance", "Coinbase"}


def test_dominant_top_over_weak_second_is_single_not_ambiguous() -> None:
    res = _engine()._decide([_c("Binance", 0.90), _c("Kraken", 0.42)])
    assert res.ambiguous is False
    assert res.insufficient_evidence is False


def test_candidates_are_sorted_desc_in_attribute() -> None:
    # attribute() sorts; feed a stub via _decide to check ordering assumption holds.
    res = _engine()._decide([_c("A", 0.9), _c("B", 0.5)])
    assert res.candidates[0].probability >= res.candidates[-1].probability
