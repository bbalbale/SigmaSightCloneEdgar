"""create_benchmarks_sector_weights

Stores benchmark sector weights (S&P 500) from FMP API with historical tracking.

Revision ID: 7818709e948d
Revises: b2c3d4e5f6g7
Create Date: 2025-10-17 10:09:39.093836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7818709e948d'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create benchmarks_sector_weights table for storing S&P 500 sector weights."""
    op.create_table(
        'benchmarks_sector_weights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('benchmark_code', sa.String(32), nullable=False, comment='Benchmark identifier (e.g., SP500)'),
        sa.Column('asof_date', sa.Date, nullable=False, comment='Date these weights are valid for'),
        sa.Column('sector', sa.String(64), nullable=False, comment='GICS sector name'),
        sa.Column('weight', sa.Numeric(12, 6), nullable=False, comment='Sector weight as decimal (0.28 = 28%)'),
        sa.Column('market_cap', sa.Numeric(20, 2), nullable=True, comment='Total market cap for sector in USD'),
        sa.Column('num_constituents', sa.Integer, nullable=True, comment='Number of stocks in this sector'),
        sa.Column('data_source', sa.String(32), nullable=False, server_default='FMP', comment='Data provider (FMP, manual, etc)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Unique constraint: one weight per (benchmark, date, sector)
        sa.UniqueConstraint('benchmark_code', 'asof_date', 'sector', name='uq_benchmark_sector_date')
    )

    # Indexes for performance
    op.create_index('idx_benchmark_lookup', 'benchmarks_sector_weights',
                   ['benchmark_code', 'asof_date'], postgresql_using='btree')
    op.create_index('idx_benchmark_sector', 'benchmarks_sector_weights',
                   ['benchmark_code', 'sector', 'asof_date'], postgresql_using='btree')


def downgrade() -> None:
    """Drop benchmarks_sector_weights table and its indexes."""
    op.drop_index('idx_benchmark_sector', table_name='benchmarks_sector_weights')
    op.drop_index('idx_benchmark_lookup', table_name='benchmarks_sector_weights')
    op.drop_table('benchmarks_sector_weights')
