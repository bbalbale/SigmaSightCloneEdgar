"""make_positions_strategy_id_nullable

Revision ID: a252603b90f8
Revises: 129542220fba
Create Date: 2025-10-04 18:55:00.539273

Make positions.strategy_id nullable to support seeding without strategies.

This aligns with the plan to eventually remove the strategies structure entirely
and revert to position + tags only. Making strategy_id nullable allows:
1. Seeding demo data without requiring strategies
2. Gradual migration away from the strategies structure
3. Backward compatibility with existing seed scripts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a252603b90f8'
down_revision: Union[str, Sequence[str], None] = '129542220fba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make positions.strategy_id nullable."""
    # Drop the NOT NULL constraint on strategy_id
    op.alter_column('positions', 'strategy_id',
                    existing_type=sa.UUID(),
                    nullable=True)


def downgrade() -> None:
    """Revert positions.strategy_id to NOT NULL."""
    # Note: This will fail if there are any NULL strategy_id values
    # Set a default strategy or update positions before downgrading
    op.alter_column('positions', 'strategy_id',
                    existing_type=sa.UUID(),
                    nullable=False)
