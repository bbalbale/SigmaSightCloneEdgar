"""Add market risk scenarios tables

Revision ID: 5c561b79e1f3
Revises: b033266c0376
Create Date: 2025-08-04 15:51:52.937863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c561b79e1f3'
down_revision: Union[str, Sequence[str], None] = 'b033266c0376'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create market_risk_scenarios table
    op.create_table('market_risk_scenarios',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('scenario_type', sa.String(50), nullable=False),
        sa.Column('scenario_value', sa.Numeric(8, 6), nullable=False),
        sa.Column('predicted_pnl', sa.Numeric(16, 2), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create position_interest_rate_betas table
    op.create_table('position_interest_rate_betas',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('position_id', sa.UUID(), nullable=False),
        sa.Column('ir_beta', sa.Numeric(8, 6), nullable=False),
        sa.Column('r_squared', sa.Numeric(6, 4), nullable=True),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_market_risk_portfolio_date', 'market_risk_scenarios', ['portfolio_id', 'calculation_date'])
    op.create_index('idx_market_risk_scenario_type', 'market_risk_scenarios', ['scenario_type'])
    op.create_index('idx_ir_betas_position_date', 'position_interest_rate_betas', ['position_id', 'calculation_date'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_ir_betas_position_date', table_name='position_interest_rate_betas')
    op.drop_index('idx_market_risk_scenario_type', table_name='market_risk_scenarios')
    op.drop_index('idx_market_risk_portfolio_date', table_name='market_risk_scenarios')
    
    # Drop tables
    op.drop_table('position_interest_rate_betas')
    op.drop_table('market_risk_scenarios')
