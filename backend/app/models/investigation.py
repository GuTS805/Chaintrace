"""Investigation: an immutable, frozen snapshot of an attribution + risk
result for a wallet, captured at a point in time.

Distinct from the live `/wallets/{address}/attribution` and `/risk`
endpoints, which recompute against whatever the DB and model happen to be
right now. An officer who filed an investigation two weeks ago must see the
exact same verdict today even if the underlying chain data or model version
has since changed — reproducibility, not a live view, is the point of this
table.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.officer import Officer


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(64), index=True)
    chain: Mapped[str] = mapped_column(String(32), default="ethereum")
    officer_id: Mapped[int] = mapped_column(
        ForeignKey("officers.id", ondelete="CASCADE"), index=True
    )

    # Everything needed to know *why* this result was what it was, so it can
    # never be silently re-attributed to "the model changed" or "the data
    # changed" without that being visible on the record itself.
    model_version: Mapped[str] = mapped_column(String(128))
    provider_source: Mapped[str] = mapped_column(String(32))  # cache | blockscout | trongrid
    traversal_max_hops: Mapped[int]
    traversal_max_nodes: Mapped[int]
    traversal_min_value_wei: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)

    # Frozen results — full serialized Pydantic objects, never recomputed on
    # read. Same JSON-column pattern as Finding.evidence.
    attribution: Mapped[dict[str, Any]] = mapped_column(JSON)
    risk: Mapped[dict[str, Any]] = mapped_column(JSON)
    graph: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Captured so a disclosure-request PDF can be regenerated from this frozen
    # snapshot later without recomputing — these don't round-trip through the
    # attribution/risk JSON alone (see app/api/report.py's live equivalent).
    evidence_hops: Mapped[int | None] = mapped_column(nullable=True)
    evidence_tx_hashes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    officer: Mapped["Officer"] = relationship()
