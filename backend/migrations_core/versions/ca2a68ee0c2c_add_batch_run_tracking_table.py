"""add batch_run_tracking table

Revision ID: ca2a68ee0c2c
Revises: 035e1888bea0
Create Date: 2025-10-28 13:08:10.385487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca2a68ee0c2c'
down_revision: Union[str, Sequence[str], None] = '035e1888bea0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'batch_run_tracking',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('phase_1_status', sa.String(length=20), nullable=True),
        sa.Column('phase_2_status', sa.String(length=20), nullable=True),
        sa.Column('phase_3_status', sa.String(length=20), nullable=True),
        sa.Column('phase_1_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('phase_2_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('phase_3_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('portfolios_processed', sa.Integer(), nullable=True),
        sa.Column('symbols_fetched', sa.Integer(), nullable=True),
        sa.Column('data_coverage_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_date')
    )
    op.create_index(op.f('idx_batch_run_date'), 'batch_run_tracking', ['run_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('idx_batch_run_date'), table_name='batch_run_tracking')
    op.drop_table('batch_run_tracking')
