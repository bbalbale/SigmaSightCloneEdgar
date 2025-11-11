"""add equity changes table and capital flow fields

Revision ID: 62b5c8b1d8a3
Revises: 9b0768a49ad8_add_multi_portfolio_support
Create Date: 2025-11-04 19:45:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '62b5c8b1d8a3'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    equity_change_type = sa.Enum("CONTRIBUTION", "WITHDRAWAL", name="equity_change_type")

    op.create_table(
        "equity_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("change_type", equity_change_type, nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("change_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_equity_changes_portfolio_id", "equity_changes", ["portfolio_id"])
    op.create_index(
        "ix_equity_changes_portfolio_date",
        "equity_changes",
        ["portfolio_id", "change_date"],
    )
    op.create_index(
        "ix_equity_changes_created_by_user_id",
        "equity_changes",
        ["created_by_user_id"],
    )
    op.create_index("ix_equity_changes_deleted_at", "equity_changes", ["deleted_at"])

    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "daily_capital_flow",
            sa.Numeric(16, 2),
            nullable=True,
            comment="Net capital contributions minus withdrawals recorded on this date",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "cumulative_capital_flow",
            sa.Numeric(16, 2),
            nullable=True,
            comment="Running total of net capital flows",
        ),
    )


def downgrade() -> None:
    op.drop_column("portfolio_snapshots", "cumulative_capital_flow")
    op.drop_column("portfolio_snapshots", "daily_capital_flow")

    op.drop_index("ix_equity_changes_deleted_at", table_name="equity_changes")
    op.drop_index("ix_equity_changes_created_by_user_id", table_name="equity_changes")
    op.drop_index("ix_equity_changes_portfolio_date", table_name="equity_changes")
    op.drop_index("ix_equity_changes_portfolio_id", table_name="equity_changes")
    op.drop_table("equity_changes")

    equity_change_type = sa.Enum("CONTRIBUTION", "WITHDRAWAL", name="equity_change_type")
    equity_change_type.drop(op.get_bind(), checkfirst=True)
