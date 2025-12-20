"""Add position_factor_exposures table for factor analysis

Revision ID: b033266c0376
Revises: 5874f3dd4e4d
Create Date: 2025-08-04 15:03:46.541128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b033266c0376'
down_revision: Union[str, Sequence[str], None] = '5874f3dd4e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create position_factor_exposures table
    op.create_table('position_factor_exposures',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('position_id', sa.UUID(), nullable=False),
        sa.Column('factor_id', sa.UUID(), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('exposure_value', sa.Numeric(12, 6), nullable=False),
        sa.Column('quality_flag', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definitions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('position_id', 'factor_id', 'calculation_date', name='uq_position_factor_date')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_pfe_factor_date', 'position_factor_exposures', ['factor_id', 'calculation_date'])
    op.create_index('idx_pfe_position_date', 'position_factor_exposures', ['position_id', 'calculation_date'])
    op.create_index('idx_pfe_calculation_date', 'position_factor_exposures', ['calculation_date'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_pfe_calculation_date', table_name='position_factor_exposures')
    op.drop_index('idx_pfe_position_date', table_name='position_factor_exposures')
    op.drop_index('idx_pfe_factor_date', table_name='position_factor_exposures')
    
    # Drop table
    op.drop_table('position_factor_exposures')
