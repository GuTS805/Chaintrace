"""Flat, hashable evidence records and their integrity hash.

The API's ``Evidence`` object is shaped for reading: one entry per signal, with a
list of supporting transactions. A forensic record needs the opposite shape — one
row per concrete observation, each naming a single transaction — so a reviewer can
cite an individual line rather than a bundle.

``compute_evidence_hash`` reduces those rows to a single SHA-256 over a canonical
serialization. Canonical means keys sorted, no insignificant whitespace, all
timestamps as UTC ISO-8601, floats at fixed precision. Two runs over identical
underlying data therefore produce an identical hash, and altering any observation
after the fact changes it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.enums import SignalType
from app.schemas.attribution import VaspCandidate

# Fields deliberately excluded from the hash, and why:
#   created_at        - wall-clock at generation. Including it would make the hash
#                       differ on every re-run of identical data, defeating the
#                       reproducibility check the hash exists to provide.
#   investigation_id  - the same facts observed under two investigation ids are
#                       the same facts; binding the id in would prevent comparing
#                       two runs for evidentiary equality.
# Neither is content: neither can be altered to change what the evidence asserts.
_UNHASHED_FIELDS = frozenset({"created_at", "investigation_id"})


class EvidenceRecord(BaseModel):
    """One concrete observation supporting a candidate attribution."""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: str = Field(
        ..., description="Deterministic digest of this record's own content."
    )
    investigation_id: str
    chain: str
    vasp_name: str
    signal_type: SignalType
    description: str
    weight: float
    source_transaction: str | None = None
    source_wallet: str
    target_wallet: str | None = None
    observed_at: datetime | None = None
    created_at: datetime
    model_version: str
    provider: str


def _canonical_value(value: Any) -> Any:
    """Reduce a value to a form with exactly one serialization."""
    if isinstance(value, datetime):
        # Naive timestamps are treated as UTC; the store only ever writes UTC.
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, float):
        # Fixed precision so 0.1 + 0.2 cannot hash differently from 0.3.
        return f"{value:.6f}"
    if isinstance(value, dict):
        return {k: _canonical_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(v) for v in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return str(value)


def _canonical_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _canonical_value(val)
        for key, val in fields.items()
        if key not in _UNHASHED_FIELDS
    }


def _dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json(records: list[EvidenceRecord]) -> str:
    """Serialize records to the exact string the integrity hash is taken over."""
    payload = [_canonical_fields(rec.model_dump()) for rec in records]
    # Sort the records themselves: the hash must not depend on the order the
    # engine happened to iterate candidates in.
    payload.sort(key=_dumps)
    return _dumps(payload)


def compute_evidence_hash(records: list[EvidenceRecord]) -> str:
    """SHA-256 of the canonical evidence serialization (lowercase hex)."""
    return hashlib.sha256(canonical_json(records).encode("utf-8")).hexdigest()


def _record_digest(fields: dict[str, Any]) -> str:
    """Short deterministic id for one record, derived from its own content."""
    blob = _dumps(_canonical_fields(fields))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_evidence_records(
    *,
    investigation_id: str,
    chain: str,
    unknown_address: str,
    candidates: list[VaspCandidate],
    model_version: str,
    provider: str,
    generated_at: datetime | None = None,
) -> list[EvidenceRecord]:
    """Flatten candidate evidence into one record per observed transaction.

    A signal that cites no transaction (KNOWN_LABEL rests on a label source rather
    than a transfer) still yields exactly one record, with a null
    ``source_transaction`` — dropping it would silently remove evidence from the
    hash.
    """
    created = generated_at or datetime.now(UTC)
    records: list[EvidenceRecord] = []

    for candidate in candidates:
        for ev in candidate.evidence:
            # Pair each tx with its timestamp where the lists line up. A signal may
            # report fewer timestamps than hashes, so index defensively rather than
            # zipping (which would silently drop the unpaired transactions).
            pairs: list[tuple[str | None, datetime | None]]
            if ev.tx_hashes:
                pairs = [
                    (tx, ev.timestamps[i] if i < len(ev.timestamps) else None)
                    for i, tx in enumerate(ev.tx_hashes)
                ]
            else:
                pairs = [(None, ev.timestamps[0] if ev.timestamps else None)]

            for tx_hash, observed_at in pairs:
                fields: dict[str, Any] = {
                    "investigation_id": investigation_id,
                    "chain": chain,
                    "vasp_name": candidate.vasp_name,
                    "signal_type": ev.signal_type,
                    "description": ev.description,
                    "weight": ev.weight,
                    "source_transaction": tx_hash,
                    "source_wallet": unknown_address,
                    "target_wallet": candidate.hot_wallet,
                    "observed_at": observed_at,
                    "created_at": created,
                    "model_version": model_version,
                    "provider": provider,
                }
                records.append(
                    EvidenceRecord(evidence_id=_record_digest(fields), **fields)
                )
    return records
