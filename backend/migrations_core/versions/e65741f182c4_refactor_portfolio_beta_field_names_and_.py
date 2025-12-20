"""refactor portfolio beta field names and add provider beta

Revision ID: e65741f182c4
Revises: d2e3f4g5h6i7
Create Date: 2025-10-18 14:53:27.885394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e65741f182c4'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4g5h6i7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Refactor beta field names in portfolio_snapshots table for clarity:
    - Rename market_beta_weighted → beta_calculated_90d
    - Rename market_beta_r_squared → beta_calculated_90d_r_squared
    - Rename market_beta_observations → beta_calculated_90d_observations
    - Rename market_beta_direct → beta_portfolio_regression
    - Add beta_provider_1y for company profile beta
    """
    # Rename existing columns to descriptive names
    op.alter_column('portfolio_snapshots', 'market_beta_weighted',
                    new_column_name='beta_calculated_90d')
    op.alter_column('portfolio_snapshots', 'market_beta_r_squared',
                    new_column_name='beta_calculated_90d_r_squared')
    op.alter_column('portfolio_snapshots', 'market_beta_observations',
                    new_column_name='beta_calculated_90d_observations')
    op.alter_column('portfolio_snapshots', 'market_beta_direct',
                    new_column_name='beta_portfolio_regression')

    # Add new column for provider beta
    op.add_column('portfolio_snapshots',
                  sa.Column('beta_provider_1y', sa.Numeric(precision=10, scale=4), nullable=True))


def downgrade() -> None:
    """
    Downgrade schema.

    Reverse the beta field name changes.
    """
    # Remove provider beta column
    op.drop_column('portfolio_snapshots', 'beta_provider_1y')

    # Rename columns back to original names
    op.alter_column('portfolio_snapshots', 'beta_portfolio_regression',
                    new_column_name='market_beta_direct')
    op.alter_column('portfolio_snapshots', 'beta_calculated_90d_observations',
                    new_column_name='market_beta_observations')
    op.alter_column('portfolio_snapshots', 'beta_calculated_90d_r_squared',
                    new_column_name='market_beta_r_squared')
    op.alter_column('portfolio_snapshots', 'beta_calculated_90d',
                    new_column_name='market_beta_weighted')
