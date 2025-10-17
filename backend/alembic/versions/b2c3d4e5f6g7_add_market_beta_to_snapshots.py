"""add_market_beta_to_snapshots

Adds aggregated portfolio-level market beta columns to snapshots table.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-17 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add market beta columns to portfolio_snapshots."""
    # Add market beta columns
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_weighted', sa.Numeric(10, 4), nullable=True,
                  comment='Equity-weighted average of position betas')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_r_squared', sa.Numeric(10, 4), nullable=True,
                  comment='Weighted average R-squared from position betas')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_observations', sa.Integer, nullable=True,
                  comment='Minimum observations across all positions')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_direct', sa.Numeric(10, 4), nullable=True,
                  comment='Direct OLS regression of portfolio returns vs SPY (Phase 3 future work)')
    )

    # Add index for performance
    op.create_index('idx_snapshots_beta', 'portfolio_snapshots',
                    ['portfolio_id', 'snapshot_date', 'market_beta_weighted'],
                    postgresql_using='btree')


def downgrade() -> None:
    """Downgrade schema - Remove market beta columns from portfolio_snapshots."""
    op.drop_index('idx_snapshots_beta', table_name='portfolio_snapshots')
    op.drop_column('portfolio_snapshots', 'market_beta_direct')
    op.drop_column('portfolio_snapshots', 'market_beta_observations')
    op.drop_column('portfolio_snapshots', 'market_beta_r_squared')
    op.drop_column('portfolio_snapshots', 'market_beta_weighted')
