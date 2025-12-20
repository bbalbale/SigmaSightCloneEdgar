"""create_missing_stress_test_tables

Revision ID: b56aa92cde75
Revises: 714625d883d9
Create Date: 2025-08-07 08:26:03.968948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b56aa92cde75'
down_revision: Union[str, Sequence[str], None] = '714625d883d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create missing stress test tables."""
    # Create stress_test_scenarios table
    op.create_table('stress_test_scenarios',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scenario_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('shock_config', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scenario_id')
    )
    
    # Create stress_test_results table
    op.create_table('stress_test_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('scenario_id', sa.UUID(), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('direct_pnl', sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column('correlated_pnl', sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column('correlation_effect', sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column('factor_impacts', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calculation_metadata', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.ForeignKeyConstraint(['scenario_id'], ['stress_test_scenarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_stress_results_portfolio_date', 'stress_test_results', ['portfolio_id', 'calculation_date'])
    op.create_index('idx_stress_scenarios_category', 'stress_test_scenarios', ['category'])


def downgrade() -> None:
    """Drop stress test tables."""
    op.drop_index('idx_stress_results_portfolio_date', table_name='stress_test_results')
    op.drop_index('idx_stress_scenarios_category', table_name='stress_test_scenarios')
    op.drop_table('stress_test_results')
    op.drop_table('stress_test_scenarios')
