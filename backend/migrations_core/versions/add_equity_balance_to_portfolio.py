"""Add equity_balance field to Portfolio model

Revision ID: add_equity_balance
Revises: 
Create Date: 2025-09-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_equity_balance'
down_revision = '4e4d181af13d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add equity_balance column to portfolios table
    op.add_column('portfolios', sa.Column('equity_balance', sa.Numeric(16, 2), nullable=True))
    
    # Set default values for demo portfolios
    op.execute("""
        UPDATE portfolios 
        SET equity_balance = CASE 
            WHEN id = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe' THEN 600000.00
            WHEN id = 'e23ab931-a033-edfe-ed4f-9d02474780b4' THEN 2000000.00
            WHEN id = 'fcd71196-e93e-f000-5a74-31a9eead3118' THEN 4000000.00
            ELSE NULL
        END
        WHERE id IN (
            '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe',
            'e23ab931-a033-edfe-ed4f-9d02474780b4',
            'fcd71196-e93e-f000-5a74-31a9eead3118'
        )
    """)


def downgrade() -> None:
    # Remove equity_balance column
    op.drop_column('portfolios', 'equity_balance')