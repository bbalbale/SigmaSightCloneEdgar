"""add_composite_indexes_for_performance

Adds composite indexes to improve query performance for batch processing:
- market_data_cache(symbol, date) - Used in price lookups
- positions(portfolio_id, deleted_at) - Used in active position queries
- portfolio_snapshots(portfolio_id, snapshot_date) - Used in equity rollforward

Revision ID: i6j7k8l9m0n1
Revises: h1i2j3k4l5m6
Create Date: 2025-11-06 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'i6j7k8l9m0n1'
down_revision: Union[str, Sequence[str], None] = '62b5c8b1d8a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add composite indexes for performance."""

    # Index 1: market_data_cache(symbol, date)
    # Used in: pnl_calculator._get_cached_price() - 378+ queries per run
    # Impact: Eliminates full table scans on 191,731 row table
    op.create_index(
        'idx_market_data_cache_symbol_date',
        'market_data_cache',
        ['symbol', 'date'],
        unique=False
    )

    # Index 2: positions(portfolio_id, deleted_at)
    # Used in: Getting active positions for portfolio
    # Impact: Speeds up "WHERE portfolio_id = X AND deleted_at IS NULL" queries
    op.create_index(
        'idx_positions_portfolio_deleted',
        'positions',
        ['portfolio_id', 'deleted_at'],
        unique=False
    )

    # Index 3: portfolio_snapshots(portfolio_id, snapshot_date)
    # Used in: Equity rollforward (getting previous snapshot)
    # Impact: Speeds up equity rollforward lookups
    op.create_index(
        'idx_snapshots_portfolio_date',
        'portfolio_snapshots',
        ['portfolio_id', 'snapshot_date'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema - Remove composite indexes."""

    op.drop_index('idx_snapshots_portfolio_date', table_name='portfolio_snapshots')
    op.drop_index('idx_positions_portfolio_deleted', table_name='positions')
    op.drop_index('idx_market_data_cache_symbol_date', table_name='market_data_cache')
