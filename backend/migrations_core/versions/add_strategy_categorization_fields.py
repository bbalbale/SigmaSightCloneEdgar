"""add_strategy_categorization_fields

Revision ID: add_cat_001
Revises: add_strategies_001
Create Date: 2025-10-01 12:00:00.000000

This migration adds direction and primary_investment_class fields to the strategies table
to enable filtering strategies by investment class and direction (long/short) for display purposes.

These fields are automatically calculated from the strategy's positions:
- For standalone strategies: inherited from the single position
- For multi-leg strategies: calculated based on strategy type or primary leg
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_cat_001'
down_revision: Union[str, Sequence[str], None] = 'add_strategies_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add direction and primary_investment_class columns to strategies table."""

    # Add direction field
    # Values: LONG, SHORT, LC (Long Call), LP (Long Put), SC (Short Call), SP (Short Put), NEUTRAL
    op.add_column('strategies',
        sa.Column('direction', sa.String(10), nullable=True)
    )

    # Add primary_investment_class field
    # Values: PUBLIC, OPTIONS, PRIVATE
    op.add_column('strategies',
        sa.Column('primary_investment_class', sa.String(20), nullable=True)
    )

    # Create indexes for filtering performance
    op.create_index('idx_strategies_direction', 'strategies', ['direction'])
    op.create_index('idx_strategies_inv_class', 'strategies', ['primary_investment_class'])
    op.create_index('idx_strategies_inv_class_direction', 'strategies', ['primary_investment_class', 'direction'])


def downgrade() -> None:
    """Remove direction and primary_investment_class columns from strategies table."""

    # Drop indexes
    op.drop_index('idx_strategies_inv_class_direction', table_name='strategies')
    op.drop_index('idx_strategies_inv_class', table_name='strategies')
    op.drop_index('idx_strategies_direction', table_name='strategies')

    # Drop columns
    op.drop_column('strategies', 'primary_investment_class')
    op.drop_column('strategies', 'direction')
