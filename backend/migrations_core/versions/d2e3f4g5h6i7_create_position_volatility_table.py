"""create_position_volatility_table

Creates position_volatility table for tracking position-level volatility metrics and HAR forecasts.
Part of Risk Metrics Phase 2 implementation.

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2025-10-17 12:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create position_volatility table."""
    op.create_table(
        'position_volatility',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calculation_date', sa.Date, nullable=False),

        # Realized volatility (trading day windows)
        sa.Column('realized_vol_21d', sa.Numeric(10, 4), nullable=True,
                  comment='21 trading days (~1 month)'),
        sa.Column('realized_vol_63d', sa.Numeric(10, 4), nullable=True,
                  comment='63 trading days (~3 months)'),

        # HAR model components (for forecasting)
        sa.Column('vol_daily', sa.Numeric(10, 4), nullable=True,
                  comment='Daily volatility component'),
        sa.Column('vol_weekly', sa.Numeric(10, 4), nullable=True,
                  comment='Weekly (5d) volatility component'),
        sa.Column('vol_monthly', sa.Numeric(10, 4), nullable=True,
                  comment='Monthly (21d) volatility component'),

        # Forecast
        sa.Column('expected_vol_21d', sa.Numeric(10, 4), nullable=True,
                  comment='HAR model forecast for next 21 trading days'),

        # Trend analysis
        sa.Column('vol_trend', sa.String(20), nullable=True,
                  comment='Volatility direction: increasing, decreasing, stable'),
        sa.Column('vol_trend_strength', sa.Numeric(10, 4), nullable=True,
                  comment='Trend strength on 0-1 scale'),

        # Percentile (vs 1-year history)
        sa.Column('vol_percentile', sa.Numeric(10, 4), nullable=True,
                  comment='Current volatility percentile vs 1-year history (0-1)'),

        # Metadata
        sa.Column('observations', sa.Integer, nullable=True,
                  comment='Number of data points used in calculation'),
        sa.Column('model_r_squared', sa.Numeric(10, 4), nullable=True,
                  comment='HAR model R-squared goodness of fit'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Foreign key
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='CASCADE'),

        # Unique constraint
        sa.UniqueConstraint('position_id', 'calculation_date', name='uq_position_volatility_date')
    )

    # Indexes for query performance
    op.create_index('ix_position_volatility_position_id', 'position_volatility', ['position_id'])
    op.create_index('ix_position_volatility_calculation_date', 'position_volatility', ['calculation_date'])
    op.create_index('ix_position_volatility_lookup', 'position_volatility',
                   ['position_id', 'calculation_date'], postgresql_using='btree')


def downgrade() -> None:
    """Drop position_volatility table."""
    op.drop_index('ix_position_volatility_lookup', table_name='position_volatility')
    op.drop_index('ix_position_volatility_calculation_date', table_name='position_volatility')
    op.drop_index('ix_position_volatility_position_id', table_name='position_volatility')
    op.drop_table('position_volatility')
