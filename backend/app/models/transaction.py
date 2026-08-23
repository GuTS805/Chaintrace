"""Transaction: a value transfer edge between two addresses on one chain."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.chains import DEFAULT_CHAIN
from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chain: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_CHAIN.value, server_default=DEFAULT_CHAIN.value,
        index=True,
    )
    tx_hash: Mapped[str] = mapped_column(String(80), index=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    from_address: Mapped[str] = mapped_column(String(64), index=True)
    to_address: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    value_wei: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)
    gas_used: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gas_price_wei: Mapped[Decimal | None] = mapped_column(Numeric(78, 0), nullable=True)
    asset: Mapped[str] = mapped_column(String(32), default="ETH")
    # Which data source this row came from. Recorded per row (not per deployment)
    # so a snapshot can state truthfully which providers its conclusion rests on,
    # even in a store fed by several importers over time.
    provider: Mapped[str] = mapped_column(
        String(64), default="fixture", server_default="fixture"
    )

    # Compound indexes to keep bounded traversal (recursive CTE) fast. Chain leads
    # every index because every traversal is scoped to exactly one chain.
    __table_args__ = (
        Index("ix_tx_chain_from_ts", "chain", "from_address", "timestamp"),
        Index("ix_tx_chain_to_ts", "chain", "to_address", "timestamp"),
        # A tx hash is unique within a chain, not across chains.
        UniqueConstraint("chain", "tx_hash", name="uq_tx_chain_hash"),
    )
