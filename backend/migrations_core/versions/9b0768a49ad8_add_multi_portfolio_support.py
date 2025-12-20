"""add multi-portfolio support

Revision ID: 9b0768a49ad8
Revises: ca2a68ee0c2c
Create Date: 2025-11-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b0768a49ad8'
down_revision: Union[str, Sequence[str], None] = 'ca2a68ee0c2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add multi-portfolio support by:
    1. Adding account_name, account_type, is_active columns
    2. Removing unique constraint on user_id
    3. Setting defaults for existing portfolios
    """
    # Add new columns (nullable initially)
    op.add_column('portfolios', sa.Column('account_name', sa.String(length=100), nullable=True))
    op.add_column('portfolios', sa.Column('account_type', sa.String(length=20), nullable=True))
    op.add_column('portfolios', sa.Column('is_active', sa.Boolean(), nullable=True))

    # Set default values for existing portfolios
    # Use existing 'name' as account_name
    op.execute("UPDATE portfolios SET account_name = name WHERE account_name IS NULL")
    op.execute("UPDATE portfolios SET account_type = 'taxable' WHERE account_type IS NULL")
    op.execute("UPDATE portfolios SET is_active = true WHERE is_active IS NULL")

    # Make columns non-nullable after setting defaults
    op.alter_column('portfolios', 'account_name', nullable=False)
    op.alter_column('portfolios', 'account_type', nullable=False)
    op.alter_column('portfolios', 'is_active', nullable=False, server_default='true')

    # Drop unique constraint on user_id (allows multiple portfolios per user)
    op.drop_constraint('uq_portfolios_user_id', 'portfolios', type_='unique')

    # Add performance index on user_id (non-unique)
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'], unique=False)


def downgrade() -> None:
    """
    Rollback multi-portfolio support.

    WARNING: This will fail if users have multiple portfolios.
    Only safe to run if all users still have exactly one portfolio.
    """
    # Remove index
    op.drop_index('ix_portfolios_user_id', table_name='portfolios')

    # Re-add unique constraint
    # NOTE: This will FAIL if any users have multiple portfolios
    op.create_unique_constraint('uq_portfolios_user_id', 'portfolios', ['user_id'])

    # Remove new columns
    op.drop_column('portfolios', 'is_active')
    op.drop_column('portfolios', 'account_type')
    op.drop_column('portfolios', 'account_name')
