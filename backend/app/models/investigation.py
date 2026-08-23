"""Investigation: the primary domain object of the platform.

A wallet lookup is a question; an *investigation* is the durable record of having
asked it — who asked, against which chain and bounds, which model and provider
answered, and what exactly was concluded. Everything an investigator can later be
cross-examined on hangs off this row.

Results live in a separate, write-once ``InvestigationSnapshot``. Once an
investigation completes, re-reading it returns what was true at the time it ran:
if the chain reorgs, a label is corrected, or the model is retrained tomorrow,
yesterday's report does not silently change underneath the investigator.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.chains import DEFAULT_CHAIN
from app.db.base import Base, TimestampMixin
from app.enums import InvestigationStatus

if TYPE_CHECKING:
    from app.models.case import Case


def format_public_id(row_id: int, year: int) -> str:
    """Human-quotable investigation reference, e.g. ``INV-2026-00142``.

    Derived from the primary key after insert, so it is unique without a second
    counter that two concurrent writers could race on.
    """
    return f"INV-{year}-{row_id:05d}"


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Assigned immediately after insert (needs the row id); never reused.
    public_id: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )

    # --- subject (chain + address is the wallet identity) ---
    chain: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_CHAIN.value, server_default=DEFAULT_CHAIN.value
    )
    address: Mapped[str] = mapped_column(String(64), index=True)

    # --- requested bounds, recorded so the run is reproducible ---
    depth: Mapped[int] = mapped_column(Integer, default=6)
    min_value_wei: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)
    max_nodes: Mapped[int] = mapped_column(Integer, default=2000)

    # --- lifecycle ---
    status: Mapped[InvestigationStatus] = mapped_column(
        SAEnum(InvestigationStatus, values_callable=lambda e: [m.value for m in e]),
        default=InvestigationStatus.QUEUED,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- provenance ---
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )

    case: Mapped[Case | None] = relationship()
    snapshot: Mapped[InvestigationSnapshot | None] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_investigation_chain_address", "chain", "address"),
        Index("ix_investigation_status_created", "status", "created_at"),
    )


class InvestigationSnapshot(Base):
    """Write-once result of a completed investigation.

    Deliberately has no ``updated_at``: nothing here is ever revised. To change a
    conclusion you run a new investigation, which produces a new snapshot with a
    new hash, and both remain on the record.
    """

    __tablename__ = "investigation_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )

    # --- results, stored as the exact serialized API contracts ---
    graph: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attribution: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # --- tamper-evidence ---
    # SHA-256 over the canonical (sorted, whitespace-free) evidence records.
    evidence_hash: Mapped[str] = mapped_column(String(64), index=True)

    # --- methodology, so a report can state how it was produced ---
    model_version: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64))
    confidence_threshold: Mapped[float] = mapped_column(Float)
    traversal_bounds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Newest on-chain timestamp the conclusion was based on.
    data_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="snapshot")

    __table_args__ = (
        UniqueConstraint("investigation_id", name="uq_snapshot_investigation"),
    )
