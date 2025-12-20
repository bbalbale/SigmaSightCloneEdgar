"""empty message

Revision ID: 2fc0b47dcbc9
Revises: 2a4b9bc52cd9, 40680fc5a516
Create Date: 2025-08-06 07:36:29.987845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fc0b47dcbc9'
down_revision: Union[str, Sequence[str], None] = ('2a4b9bc52cd9', '40680fc5a516')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
