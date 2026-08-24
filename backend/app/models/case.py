"""Case: an investigation workspace that groups wallets, notes, and findings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
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
    # Nullable so any pre-existing rows from before this column existed still
    # load; a case with no owner is a data artifact to clean up, not something
    # the app should crash on. Every new case is created with an owner (see
    # app/api/cases.py's create_case) and access is scoped to it.
    officer_id: Mapped[int | None] = mapped_column(
        ForeignKey("officers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    findings: Mapped[list[Finding]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
