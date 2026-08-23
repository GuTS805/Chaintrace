"""The evidence integrity hash must be reproducible and tamper-sensitive."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.enums import SignalType
from app.investigations.evidence import (
    build_evidence_records,
    canonical_json,
    compute_evidence_hash,
)
from app.schemas.attribution import Evidence, VaspCandidate

T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _candidate(name: str = "Binance", weight: float = 0.42) -> VaspCandidate:
    return VaspCandidate(
        vasp_name=name,
        probability=0.87,
        hot_wallet="0x" + "aa" * 20,
        evidence=[
            Evidence(
                signal_type=SignalType.HOP_PATH,
                description="2 hops to a labeled Binance hot wallet",
                weight=weight,
                tx_hashes=["0xdead", "0xbeef"],
                timestamps=[T0, T0 + timedelta(hours=1)],
            ),
            Evidence(
                signal_type=SignalType.KNOWN_LABEL,
                description="Destination carries a high-confidence exchange label",
                weight=0.31,
            ),
        ],
    )


def _records(**kw: object) -> list:
    params: dict = {
        "investigation_id": "INV-2026-00001",
        "chain": "ethereum",
        "unknown_address": "0x" + "11" * 20,
        "candidates": [_candidate()],
        "model_version": "phase4-test",
        "provider": "fixture",
        "generated_at": T0,
    }
    params.update(kw)
    return build_evidence_records(**params)  # type: ignore[arg-type]


def test_one_record_per_transaction() -> None:
    records = _records()
    # 2 tx hashes on the hop-path signal + 1 for the label signal, which cites no
    # transaction but must still be represented.
    assert len(records) == 3
    label_rec = next(r for r in records if r.signal_type is SignalType.KNOWN_LABEL)
    assert label_rec.source_transaction is None
    assert label_rec.target_wallet == "0x" + "aa" * 20


def test_hash_is_reproducible() -> None:
    assert compute_evidence_hash(_records()) == compute_evidence_hash(_records())


def test_hash_ignores_generation_time() -> None:
    """Re-running over identical facts a day later must hash identically."""
    later = _records(generated_at=T0 + timedelta(days=1))
    assert compute_evidence_hash(_records()) == compute_evidence_hash(later)


def test_hash_ignores_investigation_id() -> None:
    """The same facts are the same facts, whichever investigation observed them."""
    other = _records(investigation_id="INV-2026-99999")
    assert compute_evidence_hash(_records()) == compute_evidence_hash(other)


def test_hash_ignores_candidate_order() -> None:
    a = _records(candidates=[_candidate("Binance"), _candidate("Kraken")])
    b = _records(candidates=[_candidate("Kraken"), _candidate("Binance")])
    assert compute_evidence_hash(a) == compute_evidence_hash(b)


def test_hash_changes_when_evidence_changes() -> None:
    baseline = compute_evidence_hash(_records())
    assert compute_evidence_hash(_records(chain="polygon")) != baseline
    assert (
        compute_evidence_hash(_records(candidates=[_candidate(weight=0.99)]))
        != baseline
    )
    assert compute_evidence_hash(_records(provider="etherscan")) != baseline
    assert (
        compute_evidence_hash(_records(model_version="phase5-test")) != baseline
    )


def test_tampering_with_a_description_changes_the_hash() -> None:
    records = _records()
    baseline = compute_evidence_hash(records)
    records[0].description = "3 hops to a labeled Binance hot wallet"
    assert compute_evidence_hash(records) != baseline


def test_canonical_json_is_stable_and_compact() -> None:
    blob = canonical_json(_records())
    # No insignificant whitespace, and timestamps normalized to UTC 'Z' form.
    assert ", " not in blob
    assert "2026-03-01T12:00:00Z" in blob


def test_evidence_id_is_content_derived() -> None:
    """Two records differing only in content get different ids."""
    ids = {r.evidence_id for r in _records()}
    assert len(ids) == 3
    # Stable across runs.
    assert ids == {r.evidence_id for r in _records()}
