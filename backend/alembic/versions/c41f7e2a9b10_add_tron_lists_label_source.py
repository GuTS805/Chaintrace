"""add TRON_LISTS label source

Revision ID: c41f7e2a9b10
Revises: 2667ab6a85b4
Create Date: 2026-10-19

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = 'c41f7e2a9b10'
down_revision: str | None = '2667ab6a85b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite stores enums as plain strings; only Postgres has a native type to extend.
    if op.get_bind().dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE labelsource ADD VALUE IF NOT EXISTS 'TRON_LISTS'")


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type.
    pass
