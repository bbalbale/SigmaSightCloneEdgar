"""create_position_market_betas

Creates table for storing position-level market betas with full historical tracking.

Revision ID: a1b2c3d4e5f6
Revises: 19c513d3bf90
Create Date: 2025-10-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '19c513d3bf90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create position_market_betas table."""
    # Create position_market_betas table
    op.create_table(
        'position_market_betas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calc_date', sa.Date, nullable=False),

        # OLS regression results
        sa.Column('beta', sa.Numeric(12, 6), nullable=False, comment='Market beta coefficient'),
        sa.Column('alpha', sa.Numeric(12, 6), nullable=True, comment='Regression intercept (alpha)'),
        sa.Column('r_squared', sa.Numeric(12, 6), nullable=True, comment='R-squared goodness of fit'),
        sa.Column('std_error', sa.Numeric(12, 6), nullable=True, comment='Standard error of beta estimate'),
        sa.Column('p_value', sa.Numeric(12, 6), nullable=True, comment='P-value for beta significance'),
        sa.Column('observations', sa.Integer, nullable=False, comment='Number of data points in regression'),

        # Calculation metadata
        sa.Column('window_days', sa.Integer, nullable=False, server_default='90', comment='Regression window length'),
        sa.Column('method', sa.String(32), nullable=False, server_default='OLS_SIMPLE', comment='Calculation method'),
        sa.Column('market_index', sa.String(16), nullable=False, server_default='SPY', comment='Market benchmark used'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Foreign keys
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='CASCADE'),

        # Unique constraint: one beta per (portfolio, position, date, method, window)
        sa.UniqueConstraint('portfolio_id', 'position_id', 'calc_date', 'method', 'window_days',
                          name='uq_position_beta_calc')
    )

    # Create indexes for performance
    op.create_index('idx_pos_beta_lookup', 'position_market_betas',
                   ['portfolio_id', 'calc_date'], postgresql_using='btree')
    op.create_index('idx_pos_beta_position', 'position_market_betas',
                   ['position_id', 'calc_date'], postgresql_using='btree')
    op.create_index('idx_pos_beta_created', 'position_market_betas',
                   ['created_at'], postgresql_using='btree')


def downgrade() -> None:
    """Downgrade schema - Drop position_market_betas table."""
    op.drop_index('idx_pos_beta_created', table_name='position_market_betas')
    op.drop_index('idx_pos_beta_position', table_name='position_market_betas')
    op.drop_index('idx_pos_beta_lookup', table_name='position_market_betas')
    op.drop_table('position_market_betas')
