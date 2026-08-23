"""Wallet: an on-chain address we have observed or reasoned about."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.chains import DEFAULT_CHAIN
from app.db.base import Base, TimestampMixin


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(64), index=True)
    chain: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_CHAIN.value, server_default=DEFAULT_CHAIN.value
    )
    is_contract: Mapped[bool] = mapped_column(Boolean, default=False)
    tx_count: Mapped[int] = mapped_column(BigInteger, default=0)
    balance_wei: Mapped[Decimal | None] = mapped_column(Numeric(78, 0), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Identity is (chain, address) — the same address on Polygon and Ethereum is
    # two different wallets, so `address` alone must NOT be unique. The unique
    # constraint's own index serves (chain, address) lookups.
    __table_args__ = (
        UniqueConstraint("chain", "address", name="uq_wallet_chain_address"),
    )
