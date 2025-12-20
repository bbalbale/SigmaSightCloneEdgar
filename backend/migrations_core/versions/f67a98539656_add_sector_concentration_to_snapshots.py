"""add_sector_concentration_to_snapshots

Adds sector exposure and concentration metrics columns to portfolio_snapshots table.

Revision ID: f67a98539656
Revises: 7818709e948d
Create Date: 2025-10-17 10:11:01.110153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f67a98539656'
down_revision: Union[str, Sequence[str], None] = '7818709e948d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sector exposure and concentration metrics columns to portfolio_snapshots."""
    # Add JSONB column for sector exposure
    op.add_column('portfolio_snapshots',
        sa.Column('sector_exposure', postgresql.JSONB, nullable=True,
                  comment='Sector weights as JSON (e.g., {"Technology": 0.35, "Healthcare": 0.18})')
    )

    # Add concentration metrics
    op.add_column('portfolio_snapshots',
        sa.Column('hhi', sa.Numeric(10, 2), nullable=True,
                  comment='Herfindahl-Hirschman Index (concentration measure)')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('effective_num_positions', sa.Numeric(10, 2), nullable=True,
                  comment='Effective number of positions (1/HHI)')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('top_3_concentration', sa.Numeric(10, 4), nullable=True,
                  comment='Sum of top 3 position weights')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('top_10_concentration', sa.Numeric(10, 4), nullable=True,
                  comment='Sum of top 10 position weights')
    )


def downgrade() -> None:
    """Remove sector exposure and concentration metrics columns from portfolio_snapshots."""
    op.drop_column('portfolio_snapshots', 'top_10_concentration')
    op.drop_column('portfolio_snapshots', 'top_3_concentration')
    op.drop_column('portfolio_snapshots', 'effective_num_positions')
    op.drop_column('portfolio_snapshots', 'hhi')
    op.drop_column('portfolio_snapshots', 'sector_exposure')
