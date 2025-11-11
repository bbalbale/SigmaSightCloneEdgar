"""change_share_counts_to_bigint

Revision ID: f2a8b1c4d5e6
Revises: ce3dd9222427
Create Date: 2025-11-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a8b1c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'ce3dd9222427'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - change share count columns to BigInteger."""
    # Change basic_average_shares from INTEGER to BIGINT
    op.alter_column('income_statements', 'basic_average_shares',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)

    # Change diluted_average_shares from INTEGER to BIGINT
    op.alter_column('income_statements', 'diluted_average_shares',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema - change share count columns back to Integer."""
    # Change basic_average_shares from BIGINT back to INTEGER
    op.alter_column('income_statements', 'basic_average_shares',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)

    # Change diluted_average_shares from BIGINT back to INTEGER
    op.alter_column('income_statements', 'diluted_average_shares',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
