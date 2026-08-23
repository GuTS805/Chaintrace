"""Label: an attribution of an address to a name/category from some source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.enums import LabelCategory, LabelSource

if TYPE_CHECKING:
    from app.models.vasp import Vasp


class Label(Base, TimestampMixin):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(256))
    category: Mapped[LabelCategory] = mapped_column(
        SAEnum(LabelCategory, values_callable=lambda e: [m.value for m in e]),
        default=LabelCategory.OTHER,
    )
    source: Mapped[LabelSource] = mapped_column(
        SAEnum(LabelSource, values_callable=lambda e: [m.value for m in e])
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    vasp_id: Mapped[int | None] = mapped_column(
        ForeignKey("vasps.id", ondelete="SET NULL"), nullable=True
    )

    vasp: Mapped[Vasp | None] = relationship(back_populates="labels")

    # One (address, source, name) row; re-ingesting the same source is idempotent.
    __table_args__ = (
        UniqueConstraint("address", "source", "name", name="uq_label_addr_src_name"),
    )
