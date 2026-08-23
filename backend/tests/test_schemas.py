"""Contract tests for the attribution + graph schemas (hard requirements)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.enums import SignalType
from app.schemas import (
    AttributionResult,
    Evidence,
    GraphEdge,
    GraphResult,
    PruneInfo,
    VaspCandidate,
)
from app.schemas.graph import PruneReason


def test_evidence_carries_traceable_fields() -> None:
    ev = Evidence(
        signal_type=SignalType.DEPOSIT_SWEEP,
        description="12 deposit addresses swept into a single hot wallet.",
        weight=0.42,
        tx_hashes=["0xaaa", "0xbbb"],
        timestamps=[datetime(2024, 5, 1, tzinfo=UTC)],
    )
    assert ev.signal_type is SignalType.DEPOSIT_SWEEP
    assert len(ev.tx_hashes) == 2


def test_probability_is_bounded() -> None:
    with pytest.raises(ValidationError):
        VaspCandidate(vasp_name="X", probability=1.4)


def test_insufficient_evidence_result() -> None:
    result = AttributionResult(
        candidates=[],
        insufficient_evidence=True,
        explanation="No candidate cleared the 0.55 confidence floor.",
        confidence_threshold=0.55,
        model_version="phase1-dev",
    )
    assert result.insufficient_evidence is True
    assert result.candidates == []


def test_ambiguous_is_distinct_from_insufficient() -> None:
    result = AttributionResult(
        candidates=[
            VaspCandidate(vasp_name="Binance", probability=0.48),
            VaspCandidate(vasp_name="Kraken", probability=0.44),
        ],
        ambiguous=True,
        confidence_threshold=0.55,
        model_version="phase1-dev",
    )
    assert result.ambiguous is True
    assert result.insufficient_evidence is False
    assert len(result.candidates) == 2


def test_graph_result_reports_pruning() -> None:
    result = GraphResult(
        root="0xabc",
        nodes=[],
        edges=[
            GraphEdge(
                tx_hash="0x1",
                from_address="0xabc",
                to_address="0xdef",
                value_wei=Decimal("1000"),
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            )
        ],
        prune=PruneInfo(
            pruned=True, reasons=[PruneReason.MAX_HOPS], nodes_visited=500
        ),
    )
    assert result.prune.pruned is True
    assert PruneReason.MAX_HOPS in result.prune.reasons
