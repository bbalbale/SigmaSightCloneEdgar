"""Add activity_log and portfolio_id columns to batch_run_history

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-01-11

Phase 7.3 Enhancement: Persistent log storage for batch processing.
- activity_log: JSONB array storing full activity log, written at each phase completion
- portfolio_id: UUID for linking batch runs to portfolios (for onboarding batches)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 's5t6u7v8w9x0'
down_revision = 'r4s5t6u7v8w9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add activity_log column (JSONB array for storing log entries)
    op.add_column(
        'batch_run_history',
        sa.Column('activity_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Add portfolio_id column for linking to portfolios
    op.add_column(
        'batch_run_history',
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add index for portfolio_id lookups
    op.create_index(
        'ix_batch_run_history_portfolio_id',
        'batch_run_history',
        ['portfolio_id'],
        unique=False
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_batch_run_history_portfolio_id', table_name='batch_run_history')

    # Remove columns
    op.drop_column('batch_run_history', 'portfolio_id')
    op.drop_column('batch_run_history', 'activity_log')
