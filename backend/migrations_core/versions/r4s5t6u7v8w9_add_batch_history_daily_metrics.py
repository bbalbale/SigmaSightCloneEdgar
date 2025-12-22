"""Add batch_run_history and daily_metrics tables

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2025-12-22 (Phase 5 Admin Dashboard)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "r4s5t6u7v8w9"
down_revision: Union[str, None] = "q3r4s5t6u7v8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create batch_run_history table
    op.create_table(
        "batch_run_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_run_id", sa.String(255), nullable=False),
        sa.Column("triggered_by", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("total_jobs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_jobs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_jobs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("phase_durations", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for batch_run_history
    op.create_index("ix_batch_run_history_batch_run_id", "batch_run_history", ["batch_run_id"])
    op.create_index("ix_batch_run_history_status", "batch_run_history", ["status"])
    op.create_index("ix_batch_run_history_started_at", "batch_run_history", ["started_at"])
    op.create_index("ix_batch_run_history_created_at", "batch_run_history", ["created_at"])

    # Create daily_metrics table
    op.create_table(
        "daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("metric_type", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Numeric(16, 4), nullable=False),
        sa.Column("dimensions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Unique constraint for daily_metrics (date + metric_type + dimensions)
    op.create_unique_constraint(
        "uq_daily_metrics_date_type_dims",
        "daily_metrics",
        ["date", "metric_type", "dimensions"],
    )

    # Indexes for daily_metrics
    op.create_index("ix_daily_metrics_date", "daily_metrics", ["date"])
    op.create_index("ix_daily_metrics_metric_type", "daily_metrics", ["metric_type"])
    op.create_index("ix_daily_metrics_date_type", "daily_metrics", ["date", "metric_type"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_daily_metrics_date_type", table_name="daily_metrics")
    op.drop_index("ix_daily_metrics_metric_type", table_name="daily_metrics")
    op.drop_index("ix_daily_metrics_date", table_name="daily_metrics")
    op.drop_constraint("uq_daily_metrics_date_type_dims", "daily_metrics", type_="unique")

    op.drop_index("ix_batch_run_history_created_at", table_name="batch_run_history")
    op.drop_index("ix_batch_run_history_started_at", table_name="batch_run_history")
    op.drop_index("ix_batch_run_history_status", table_name="batch_run_history")
    op.drop_index("ix_batch_run_history_batch_run_id", table_name="batch_run_history")

    # Drop tables
    op.drop_table("daily_metrics")
    op.drop_table("batch_run_history")
