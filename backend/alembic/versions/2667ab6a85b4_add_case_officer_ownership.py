"""add case officer ownership

Revision ID: 2667ab6a85b4
Revises: 3954add2657d
Create Date: 2026-08-24 15:23:56.815366
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '2667ab6a85b4'
down_revision: str | None = '3954add2657d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Batch mode: SQLite has no ALTER-TABLE-ADD-CONSTRAINT, only a
    # copy-and-move recreate, which batch_alter_table handles transparently.
    # A no-op wrapper on Postgres — same DDL either way.
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('officer_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_cases_officer_id'), ['officer_id'], unique=False)
        batch_op.create_foreign_key(
            batch_op.f('fk_cases_officer_id_officers'),
            'officers', ['officer_id'], ['id'], ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cases_officer_id_officers'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_cases_officer_id'))
        batch_op.drop_column('officer_id')
