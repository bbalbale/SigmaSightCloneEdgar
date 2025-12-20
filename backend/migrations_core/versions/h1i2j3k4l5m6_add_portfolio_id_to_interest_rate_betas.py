"""add_portfolio_id_to_interest_rate_betas

Adds portfolio_id column to position_interest_rate_betas table to enable
efficient deletion by portfolio and maintain consistency with other calculation tables.

Revision ID: h1i2j3k4l5m6
Revises: 7003a3be89fe
Create Date: 2025-10-19 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, Sequence[str], None] = '7003a3be89fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add portfolio_id to position_interest_rate_betas."""

    # Step 1: Add portfolio_id column (nullable initially)
    op.add_column('position_interest_rate_betas',
                  sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Step 2: Backfill portfolio_id from positions table
    op.execute("""
        UPDATE position_interest_rate_betas pirb
        SET portfolio_id = p.portfolio_id
        FROM positions p
        WHERE pirb.position_id = p.id
    """)

    # Step 3: Make portfolio_id NOT NULL now that it's backfilled
    op.alter_column('position_interest_rate_betas', 'portfolio_id',
                   existing_type=postgresql.UUID(as_uuid=True),
                   nullable=False)

    # Step 4: Add foreign key constraint
    op.create_foreign_key('fk_position_ir_betas_portfolio',
                         'position_interest_rate_betas', 'portfolios',
                         ['portfolio_id'], ['id'],
                         ondelete='CASCADE')

    # Step 5: Add index for efficient portfolio lookups
    op.create_index('idx_ir_betas_portfolio_date', 'position_interest_rate_betas',
                   ['portfolio_id', 'calculation_date'], unique=False)

    # Note: idx_ir_betas_position_date already exists from original table creation


def downgrade() -> None:
    """Downgrade schema - Remove portfolio_id from position_interest_rate_betas."""

    # Drop index
    op.drop_index('idx_ir_betas_portfolio_date', table_name='position_interest_rate_betas')

    # Drop foreign key
    op.drop_constraint('fk_position_ir_betas_portfolio', 'position_interest_rate_betas', type_='foreignkey')

    # Drop column
    op.drop_column('position_interest_rate_betas', 'portfolio_id')
