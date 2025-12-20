"""add_volatility_to_snapshots

Adds realized volatility, expected volatility, and trend columns to portfolio_snapshots table.
Part of Risk Metrics Phase 2 implementation.

Revision ID: c1d2e3f4g5h6
Revises: f67a98539656
Create Date: 2025-10-17 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, Sequence[str], None] = 'f67a98539656'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add volatility analytics columns to portfolio_snapshots."""
    # Add realized volatility columns (trading day windows)
    op.add_column('portfolio_snapshots',
        sa.Column('realized_volatility_21d', sa.Numeric(10, 4), nullable=True,
                  comment='Realized volatility over 21 trading days (~1 month)')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('realized_volatility_63d', sa.Numeric(10, 4), nullable=True,
                  comment='Realized volatility over 63 trading days (~3 months)')
    )

    # Add HAR model forecast
    op.add_column('portfolio_snapshots',
        sa.Column('expected_volatility_21d', sa.Numeric(10, 4), nullable=True,
                  comment='HAR model forecast for next 21 trading days')
    )

    # Add trend analysis
    op.add_column('portfolio_snapshots',
        sa.Column('volatility_trend', sa.String(20), nullable=True,
                  comment='Volatility direction: increasing, decreasing, stable')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('volatility_percentile', sa.Numeric(10, 4), nullable=True,
                  comment='Current volatility percentile vs 1-year history (0-1)')
    )

    # Add index for volatility lookups
    op.create_index('idx_snapshots_volatility', 'portfolio_snapshots',
                    ['portfolio_id', 'snapshot_date', 'realized_volatility_21d'],
                    postgresql_using='btree')


def downgrade() -> None:
    """Remove volatility analytics columns from portfolio_snapshots."""
    op.drop_index('idx_snapshots_volatility', table_name='portfolio_snapshots')
    op.drop_column('portfolio_snapshots', 'volatility_percentile')
    op.drop_column('portfolio_snapshots', 'volatility_trend')
    op.drop_column('portfolio_snapshots', 'expected_volatility_21d')
    op.drop_column('portfolio_snapshots', 'realized_volatility_63d')
    op.drop_column('portfolio_snapshots', 'realized_volatility_21d')
