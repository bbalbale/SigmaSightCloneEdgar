"""remove_strategy_system

Revision ID: a766488d98ea
Revises: a252603b90f8
Create Date: 2025-10-05 17:40:02.960026

Complete removal of the legacy strategy system (unused in production).

PREREQUISITES:
1. Seed script updated to stop creating strategies (Phase 3.0.0)
2. Application code no longer imports strategy models/services

This migration is **irreversible** and will drop:
- positions.strategy_id column
- strategies, strategy_legs, strategy_metrics, strategy_tags tables
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a766488d98ea"
down_revision: Union[str, Sequence[str], None] = "a252603b90f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop strategy tables and all references."""
    # Clean up any lingering strategy references on positions
    op.execute("UPDATE positions SET strategy_id = NULL WHERE strategy_id IS NOT NULL")

    # Drop FK constraint, index, and column on positions
    op.execute("DROP INDEX IF EXISTS idx_positions_strategy")
    op.execute("ALTER TABLE positions DROP CONSTRAINT IF EXISTS fk_positions_strategy")
    op.execute("ALTER TABLE positions DROP CONSTRAINT IF EXISTS positions_strategy_id_fkey")
    op.drop_column("positions", "strategy_id")

    # Drop child tables before the parent strategies table
    op.drop_table("strategy_metrics")
    op.drop_table("strategy_legs")
    op.drop_table("strategy_tags")
    op.drop_table("strategies")


def downgrade() -> None:  # pragma: no cover - irreversible migration
    """Downgrade is not supported for strategy system removal."""
    raise NotImplementedError(
        "Downgrade not supported - strategy system permanently removed. "
        "Restore from backup taken before a766488d98ea if you must recover these tables."
    )
