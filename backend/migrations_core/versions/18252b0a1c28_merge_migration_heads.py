"""merge migration heads

Revision ID: 18252b0a1c28
Revises: add_equity_balance_snapshots, add_cat_001
Create Date: 2025-10-02 23:36:17.699588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18252b0a1c28'
down_revision: Union[str, Sequence[str], None] = ('add_equity_balance_snapshots', 'add_cat_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
