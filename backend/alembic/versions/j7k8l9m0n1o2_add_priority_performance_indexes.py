"""add_priority_performance_indexes

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2025-11-06 21:00:00.000000

Priority 1-3 Performance Indexes from Batch Caching Optimization Plan:
- Priority 1: Extended position active lookup (90%+ query speedup)
- Priority 2: Market data valid prices (eliminates null price lookups)
- Priority 3: Position symbol active filter (portfolio aggregation speedup)

These indexes are PREREQUISITES for smart caching implementation.
Expected impact: 10x-100x speedup on filtered queries.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j7k8l9m0n1o2'
down_revision = 'i6j7k8l9m0n1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Priority 1: Extended Position Active Lookup
    # Composite index on (portfolio_id, deleted_at, exit_date, investment_class)
    # with partial index WHERE deleted_at IS NULL
    # Use case: Get all active PUBLIC positions for a portfolio
    op.create_index(
        'idx_positions_active_complete',
        'positions',
        ['portfolio_id', 'deleted_at', 'exit_date', 'investment_class'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Priority 2: Market Data Valid Prices
    # Composite index on (symbol, date) with partial index WHERE close > 0
    # Use case: Get valid prices for symbols (filter out null/zero prices)
    op.create_index(
        'idx_market_data_valid_prices',
        'market_data_cache',
        ['symbol', 'date'],
        unique=False,
        postgresql_where=sa.text('close > 0')
    )

    # Priority 3: Position Symbol Active Filter
    # Composite index on (deleted_at, symbol, exit_date, expiration_date)
    # with partial index WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''
    # Use case: Portfolio aggregations by symbol, filtering active positions
    op.create_index(
        'idx_positions_symbol_active',
        'positions',
        ['deleted_at', 'symbol', 'exit_date', 'expiration_date'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''")
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_positions_symbol_active', table_name='positions')
    op.drop_index('idx_market_data_valid_prices', table_name='market_data_cache')
    op.drop_index('idx_positions_active_complete', table_name='positions')
