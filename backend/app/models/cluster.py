"""Cluster: a set of addresses grouped by a co-spend / behavioral heuristic."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Cluster(Base, TimestampMixin):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    heuristic: Mapped[str] = mapped_column(String(64))

    members: Mapped[list[ClusterMember]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), index=True
    )
    address: Mapped[str] = mapped_column(String(64), index=True)

    cluster: Mapped[Cluster] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("cluster_id", "address", name="uq_cluster_member"),
    )
