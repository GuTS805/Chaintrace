"""Case: an investigation workspace that groups wallets, notes, and findings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.enums import CaseStatus

if TYPE_CHECKING:
    from app.models.finding import Finding


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, values_callable=lambda e: [m.value for m in e]),
        default=CaseStatus.OPEN,
    )
    investigator: Mapped[str | None] = mapped_column(String(128), nullable=True)

    findings: Mapped[list[Finding]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
