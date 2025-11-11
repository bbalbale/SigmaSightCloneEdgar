"""Merge migration heads

Revision ID: 792ffb1ab1ad
Revises: g3h4i5j6k7l8, j7k8l9m0n1o2
Create Date: 2025-11-11 15:04:07.613981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '792ffb1ab1ad'
down_revision: Union[str, Sequence[str], None] = ('g3h4i5j6k7l8', 'j7k8l9m0n1o2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
