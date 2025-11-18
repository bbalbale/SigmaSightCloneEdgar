"""add_snapshot_idempotency_fields

Revision ID: k8l9m0n1o2p3
Revises: 792ffb1ab1ad
Create Date: 2025-11-17 20:15:00.000000

Phase 2.10: Batch Processing Idempotency Fix
Adds is_complete flag and unique constraint to portfolio_snapshots table.

CRITICAL: Run scripts/repair/dedupe_snapshots_pre_migration.py BEFORE applying this migration!
If duplicate snapshots exist, this migration will fail on the unique constraint.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k8l9m0n1o2p3'
down_revision = '792ffb1ab1ad'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add idempotency fields to portfolio_snapshots table.

    1. Add is_complete flag (defaults TRUE for existing rows)
    2. Add unique constraint on (portfolio_id, snapshot_date)

    Note: Column is snapshot_date (NOT calculation_date) - see app/models/snapshots.py
    """
    # Step 1: Add is_complete column
    # Default TRUE for all existing rows (assume they are complete)
    op.add_column(
        'portfolio_snapshots',
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='true')
    )

    # Step 2: Add unique constraint on (portfolio_id, snapshot_date)
    # This will FAIL if duplicates exist - must run dedupe script first!
    op.create_unique_constraint(
        'uq_portfolio_snapshot_date',
        'portfolio_snapshots',
        ['portfolio_id', 'snapshot_date']
    )


def downgrade():
    """
    Remove idempotency fields.

    WARNING: Rolling back this migration will remove duplicate protection!
    """
    # Remove unique constraint first
    op.drop_constraint('uq_portfolio_snapshot_date', 'portfolio_snapshots', type_='unique')

    # Remove is_complete column
    op.drop_column('portfolio_snapshots', 'is_complete')
