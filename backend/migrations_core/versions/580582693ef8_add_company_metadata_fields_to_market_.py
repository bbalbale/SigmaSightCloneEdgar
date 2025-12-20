"""Add company metadata fields to market_data_cache

Revision ID: 580582693ef8
Revises: b56aa92cde75
Create Date: 2025-08-07 15:36:20.155367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '580582693ef8'
down_revision: Union[str, Sequence[str], None] = 'b56aa92cde75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add company metadata fields to market_data_cache table
    op.add_column('market_data_cache', sa.Column('exchange', sa.String(20), nullable=True))
    op.add_column('market_data_cache', sa.Column('country', sa.String(10), nullable=True))
    op.add_column('market_data_cache', sa.Column('market_cap', sa.Numeric(18, 2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove company metadata fields from market_data_cache table
    op.drop_column('market_data_cache', 'market_cap')
    op.drop_column('market_data_cache', 'country')
    op.drop_column('market_data_cache', 'exchange')
