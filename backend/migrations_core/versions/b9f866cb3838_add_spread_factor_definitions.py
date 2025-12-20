"""add_spread_factor_definitions

Adds 4 long-short spread factor definitions to factor_definitions table:
- Growth-Value Spread (VUG - VTV)
- Momentum Spread (MTUM - SPY)
- Size Spread (IWM - SPY)
- Quality Spread (QUAL - SPY)

These spread factors address multicollinearity in the traditional 7-factor model
by using factor spreads instead of raw factor ETFs.

Revision ID: b9f866cb3838
Revises: h1i2j3k4l5m6
Create Date: 2025-10-20 08:54:27.517514

"""
from typing import Sequence, Union
from datetime import datetime
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b9f866cb3838'
down_revision: Union[str, Sequence[str], None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 4 spread factor definitions to factor_definitions table."""

    # Define factor_definitions table structure for bulk insert
    factor_definitions = table('factor_definitions',
        column('id', UUID),
        column('name', sa.String),
        column('description', sa.String),
        column('factor_type', sa.String),
        column('calculation_method', sa.String),
        column('etf_proxy', sa.String),
        column('display_order', sa.Integer),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    # Define spread factors
    now = datetime.utcnow()
    spread_factors = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Growth-Value Spread',
            'description': 'Long-short factor measuring growth vs value exposure. VUG - VTV. Positive = growth tilt, Negative = value tilt. Low correlation with market (~0.3) eliminates multicollinearity.',
            'factor_type': 'spread',
            'calculation_method': 'OLS_SPREAD',
            'etf_proxy': 'VUG-VTV',
            'display_order': 10,
            'is_active': True,
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Momentum Spread',
            'description': 'Long-short factor measuring momentum exposure. MTUM - SPY. Positive = momentum chasing, Negative = contrarian. Captures momentum factor independent of market movements.',
            'factor_type': 'spread',
            'calculation_method': 'OLS_SPREAD',
            'etf_proxy': 'MTUM-SPY',
            'display_order': 11,
            'is_active': True,
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Size Spread',
            'description': 'Long-short factor measuring size exposure. IWM - SPY. Positive = small cap tilt, Negative = large cap tilt. Measures small cap premium relative to large caps.',
            'factor_type': 'spread',
            'calculation_method': 'OLS_SPREAD',
            'etf_proxy': 'IWM-SPY',
            'display_order': 12,
            'is_active': True,
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Quality Spread',
            'description': 'Long-short factor measuring quality exposure. QUAL - SPY. Positive = quality tilt, Negative = speculative tilt. Captures preference for high-quality companies over market average.',
            'factor_type': 'spread',
            'calculation_method': 'OLS_SPREAD',
            'etf_proxy': 'QUAL-SPY',
            'display_order': 13,
            'is_active': True,
            'created_at': now,
            'updated_at': now
        }
    ]

    # Insert spread factor definitions
    op.bulk_insert(factor_definitions, spread_factors)


def downgrade() -> None:
    """Remove spread factor definitions."""
    op.execute("""
        DELETE FROM factor_definitions
        WHERE factor_type = 'spread'
    """)
