"""Transaction: a value transfer edge between two addresses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(80), index=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    from_address: Mapped[str] = mapped_column(String(64), index=True)
    to_address: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    value_wei: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)
    gas_used: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gas_price_wei: Mapped[Decimal | None] = mapped_column(Numeric(78, 0), nullable=True)
    asset: Mapped[str] = mapped_column(String(32), default="ETH")

    # Compound indexes to keep bounded traversal (Phase 3 recursive CTE) fast.
    __table_args__ = (
        Index("ix_tx_from_ts", "from_address", "timestamp"),
        Index("ix_tx_to_ts", "to_address", "timestamp"),
    )
