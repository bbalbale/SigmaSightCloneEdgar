"""add_portfolio_account_name_unique_constraint

Revision ID: g3h4i5j6k7l8
Revises: f2a8b1c4d5e6
Create Date: 2025-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f2a8b1c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on (user_id, account_name) to prevent duplicate account names per user."""
    op.create_unique_constraint(
        'uq_portfolio_user_account_name',
        'portfolios',
        ['user_id', 'account_name']
    )


def downgrade() -> None:
    """Remove unique constraint on (user_id, account_name)."""
    op.drop_constraint(
        'uq_portfolio_user_account_name',
        'portfolios',
        type_='unique'
    )
