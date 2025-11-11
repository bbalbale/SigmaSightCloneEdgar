"""add position realized events table and realized pnl fields

Revision ID: a3b4c5d6e7f8
Revises: f2a8b1c4d5e6
Create Date: 2025-11-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "2623cfc89fb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "portfolio_snapshots",
        sa.Column("daily_realized_pnl", sa.Numeric(16, 2), nullable=True, comment="Realized P&L from closed positions on this date"),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("cumulative_realized_pnl", sa.Numeric(16, 2), nullable=True, comment="Running total of realized P&L"),
    )

    op.create_table(
        "position_realized_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quantity_closed", sa.Numeric(16, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(16, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_position_realized_events_position_id",
        "position_realized_events",
        ["position_id"],
    )
    op.create_index(
        "ix_position_realized_events_portfolio_date",
        "position_realized_events",
        ["portfolio_id", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_position_realized_events_portfolio_date", table_name="position_realized_events")
    op.drop_index("ix_position_realized_events_position_id", table_name="position_realized_events")
    op.drop_table("position_realized_events")

    op.drop_column("portfolio_snapshots", "cumulative_realized_pnl")
    op.drop_column("portfolio_snapshots", "daily_realized_pnl")
