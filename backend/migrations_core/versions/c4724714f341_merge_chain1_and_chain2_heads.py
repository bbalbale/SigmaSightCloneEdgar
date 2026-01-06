"""merge_chain1_and_chain2_heads

Merges two parallel Alembic migration chains that diverged from f8g9h0i1j2k3:
- Chain 1: k8l9m0n1o2p3 (snapshot idempotency, Oct-Nov 2025)
- Chain 2: r4s5t6u7v8w9 (symbol analytics, admin tables, Dec 2025)

This is a no-op migration - all schema objects already exist in production.
See backend/_docs/ALEMBIC_MULTIPLE_HEADS_INVESTIGATION.md for full details.

Revision ID: c4724714f341
Revises: k8l9m0n1o2p3, r4s5t6u7v8w9
Create Date: 2026-01-05 22:25:12.937318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4724714f341'
down_revision: Union[str, Sequence[str], None] = ('k8l9m0n1o2p3', 'r4s5t6u7v8w9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op merge - all schema already exists in production."""
    pass


def downgrade() -> None:
    """No-op merge."""
    pass
