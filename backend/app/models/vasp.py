"""VASP: a Virtual Asset Service Provider (exchange, custodian, ...)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.enums import VaspCategory

if TYPE_CHECKING:
    from app.models.label import Label


class Vasp(Base, TimestampMixin):
    __tablename__ = "vasps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[VaspCategory] = mapped_column(
        SAEnum(VaspCategory, values_callable=lambda e: [m.value for m in e]),
        default=VaspCategory.CENTRALIZED_EXCHANGE,
    )
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)

    labels: Mapped[list[Label]] = relationship(back_populates="vasp")
