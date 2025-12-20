"""Add equity_balance to portfolio_snapshots

Revision ID: add_equity_balance_snapshots
Revises: add_equity_balance, e1f0c2d9b7a3
Create Date: 2025-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_equity_balance_snapshots'
down_revision: Union[str, Sequence[str], None] = ('add_equity_balance', 'e1f0c2d9b7a3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add equity_balance column to portfolio_snapshots table
    op.add_column('portfolio_snapshots',
                  sa.Column('equity_balance', sa.Numeric(precision=16, scale=2), nullable=True))


def downgrade() -> None:
    # Remove equity_balance column from portfolio_snapshots table
    op.drop_column('portfolio_snapshots', 'equity_balance')
