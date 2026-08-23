"""Chain-scoped identity + investigations as the primary domain object.

Two changes that belong in one migration because the second depends on the first:

1. Identity becomes ``(chain, address)``. The same 20-byte address exists on every
   EVM chain and belongs to different parties there, so the old global uniqueness
   on ``wallets.address`` was actively wrong — it would have merged unrelated
   wallets the moment a second chain was ingested. Existing rows are Ethereum.

2. ``investigations`` + ``investigation_snapshots``. The snapshot is write-once:
   once an investigation completes, its result is frozen so a report reprinted
   next year says what it said the day it was filed.

The traversal indexes are re-cut with chain leading: ``ix_tx_from_ts`` and
``ix_tx_to_ts`` are replaced by ``ix_tx_chain_from_ts`` / ``ix_tx_chain_to_ts``.
Every traversal now filters on chain first, so the old un-chained pair could not
serve those queries and would only cost write throughput.

Revision ID: b1c4e77a9d20
Revises: 017b6a76afec
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1c4e77a9d20"
down_revision: str | None = "017b6a76afec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every row that exists before this migration was Ethereum data.
_ETH = "ethereum"
# Pre-existing rows came from the offline fixture/importer path.
_DEFAULT_PROVIDER = "fixture"

_STATUS = sa.Enum(
    "QUEUED",
    "FETCHING",
    "TRAVERSING",
    "ANALYZING",
    "COMPLETED",
    "FAILED",
    name="investigationstatus",
)


def _chain_column() -> sa.Column:
    return sa.Column(
        "chain", sa.String(length=32), nullable=False, server_default=_ETH
    )


def upgrade() -> None:
    # --- 1. chain-scoped identity -------------------------------------------
    # Column additions and index/constraint rebuilds are kept in *separate* batch
    # blocks. SQLite has no real ALTER, so alembic rebuilds the table per block;
    # doing both at once makes it try to reorder columns it has just added and it
    # fails with a circular dependency.
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(_chain_column())
        batch_op.add_column(
            sa.Column(
                "provider",
                sa.String(length=64),
                nullable=False,
                server_default=_DEFAULT_PROVIDER,
            )
        )

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        # Superseded by the chain-leading pair below.
        batch_op.drop_index("ix_tx_from_ts")
        batch_op.drop_index("ix_tx_to_ts")
        batch_op.create_index(
            batch_op.f("ix_transactions_chain"), ["chain"], unique=False
        )
        batch_op.create_index(
            "ix_tx_chain_from_ts", ["chain", "from_address", "timestamp"], unique=False
        )
        batch_op.create_index(
            "ix_tx_chain_to_ts", ["chain", "to_address", "timestamp"], unique=False
        )
        batch_op.create_unique_constraint("uq_tx_chain_hash", ["chain", "tx_hash"])

    # `wallets` already carried a chain column; it simply was not part of the
    # identity. Give it the same server default as the new ones, then move
    # uniqueness onto (chain, address).
    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.alter_column(
            "chain",
            existing_type=sa.String(length=32),
            existing_nullable=False,
            server_default=_ETH,
        )

    with op.batch_alter_table("wallets", schema=None) as batch_op:
        # Was unique; uniqueness now lives on (chain, address).
        batch_op.drop_index(batch_op.f("ix_wallets_address"))
        batch_op.create_index(
            batch_op.f("ix_wallets_address"), ["address"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_wallet_chain_address", ["chain", "address"]
        )

    with op.batch_alter_table("labels", schema=None) as batch_op:
        batch_op.add_column(_chain_column())

    with op.batch_alter_table("labels", schema=None) as batch_op:
        batch_op.drop_constraint("uq_label_addr_src_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_label_chain_addr_src_name", ["chain", "address", "source", "name"]
        )

    with op.batch_alter_table("clusters", schema=None) as batch_op:
        batch_op.add_column(_chain_column())

    # --- 2. investigations ---------------------------------------------------
    op.create_table(
        "investigations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=True),
        sa.Column(
            "chain", sa.String(length=32), nullable=False, server_default=_ETH
        ),
        sa.Column("address", sa.String(length=64), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("min_value_wei", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("max_nodes", sa.Integer(), nullable=False),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(length=128), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_investigations_case_id_cases"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigations")),
    )
    with op.batch_alter_table("investigations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_investigations_public_id"), ["public_id"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_investigations_address"), ["address"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_investigations_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_investigations_case_id"), ["case_id"], unique=False
        )
        batch_op.create_index(
            "ix_investigation_chain_address", ["chain", "address"], unique=False
        )
        batch_op.create_index(
            "ix_investigation_status_created", ["status", "created_at"], unique=False
        )

    op.create_table(
        "investigation_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("graph", sa.JSON(), nullable=False),
        sa.Column("attribution", sa.JSON(), nullable=False),
        sa.Column("risk", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("confidence_threshold", sa.Float(), nullable=False),
        sa.Column("traversal_bounds", sa.JSON(), nullable=False),
        sa.Column("data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_investigation_snapshots_investigation_id_investigations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_snapshots")),
        sa.UniqueConstraint("investigation_id", name="uq_snapshot_investigation"),
    )
    with op.batch_alter_table("investigation_snapshots", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_investigation_snapshots_investigation_id"),
            ["investigation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_investigation_snapshots_evidence_hash"),
            ["evidence_hash"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("investigation_snapshots", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_investigation_snapshots_evidence_hash"))
        batch_op.drop_index(batch_op.f("ix_investigation_snapshots_investigation_id"))
    op.drop_table("investigation_snapshots")

    with op.batch_alter_table("investigations", schema=None) as batch_op:
        batch_op.drop_index("ix_investigation_status_created")
        batch_op.drop_index("ix_investigation_chain_address")
        batch_op.drop_index(batch_op.f("ix_investigations_case_id"))
        batch_op.drop_index(batch_op.f("ix_investigations_status"))
        batch_op.drop_index(batch_op.f("ix_investigations_address"))
        batch_op.drop_index(batch_op.f("ix_investigations_public_id"))
    op.drop_table("investigations")
    _STATUS.drop(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("clusters", schema=None) as batch_op:
        batch_op.drop_column("chain")

    with op.batch_alter_table("labels", schema=None) as batch_op:
        batch_op.drop_constraint("uq_label_chain_addr_src_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_label_addr_src_name", ["address", "source", "name"]
        )
        batch_op.drop_column("chain")

    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.drop_constraint("uq_wallet_chain_address", type_="unique")
        batch_op.drop_index(batch_op.f("ix_wallets_address"))
        batch_op.create_index(batch_op.f("ix_wallets_address"), ["address"], unique=True)
        # `chain` predates this migration on wallets, so it stays; only its
        # server default was introduced here.
        batch_op.alter_column(
            "chain",
            existing_type=sa.String(length=32),
            existing_nullable=False,
            server_default=None,
        )

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_constraint("uq_tx_chain_hash", type_="unique")
        batch_op.drop_index("ix_tx_chain_to_ts")
        batch_op.drop_index("ix_tx_chain_from_ts")
        batch_op.drop_index(batch_op.f("ix_transactions_chain"))
        batch_op.create_index("ix_tx_from_ts", ["from_address", "timestamp"], unique=False)
        batch_op.create_index("ix_tx_to_ts", ["to_address", "timestamp"], unique=False)

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_column("provider")
        batch_op.drop_column("chain")
