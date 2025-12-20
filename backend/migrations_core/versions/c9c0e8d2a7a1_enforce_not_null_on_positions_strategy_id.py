"""enforce_not_null_on_positions_strategy_id

Revision ID: c9c0e8d2a7a1
Revises: add_strategies_001
Create Date: 2025-09-24 11:05:00.000000

Enforce NOT NULL on positions.strategy_id after backfill is complete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9c0e8d2a7a1'
down_revision: Union[str, Sequence[str], None] = 'add_strategies_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This will fail if any rows have NULL strategy_id, which is desired to enforce integrity
    op.alter_column('positions', 'strategy_id', existing_type=sa.UUID(), nullable=False)


def downgrade() -> None:
    op.alter_column('positions', 'strategy_id', existing_type=sa.UUID(), nullable=True)

