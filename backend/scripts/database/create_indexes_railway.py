"""Create missing performance indexes on Railway database using SQLAlchemy."""
import asyncio
import sys

# Add app to path
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.database import get_async_session

# Index definitions with their CREATE statements
INDEXES = [
    {
        'name': 'idx_market_data_cache_symbol_date',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_market_data_cache_symbol_date ON market_data_cache (symbol, date)',
        'purpose': 'Price lookups (378+ queries per run)'
    },
    {
        'name': 'idx_positions_portfolio_deleted',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_positions_portfolio_deleted ON positions (portfolio_id, deleted_at)',
        'purpose': 'Active position queries'
    },
    {
        'name': 'idx_snapshots_portfolio_date',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio_date ON portfolio_snapshots (portfolio_id, snapshot_date)',
        'purpose': 'Equity rollforward calculations'
    },
    {
        'name': 'idx_positions_active_complete',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_positions_active_complete ON positions (portfolio_id, deleted_at, exit_date, investment_class) WHERE deleted_at IS NULL',
        'purpose': 'Active PUBLIC positions'
    },
    {
        'name': 'idx_market_data_valid_prices',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_market_data_valid_prices ON market_data_cache (symbol, date) WHERE close > 0',
        'purpose': 'Valid price lookups'
    },
    {
        'name': 'idx_positions_symbol_active',
        'sql': "CREATE INDEX IF NOT EXISTS idx_positions_symbol_active ON positions (deleted_at, symbol, exit_date, expiration_date) WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''",
        'purpose': 'Portfolio aggregations by symbol'
    },
]

async def create_indexes():
    print("=" * 60)
    print("CREATING MISSING PERFORMANCE INDEXES")
    print("=" * 60)

    async with get_async_session() as db:
        # First check which indexes exist
        result = await db.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename IN ('positions', 'market_data_cache', 'portfolio_snapshots')
        """))
        existing = {row[0] for row in result.fetchall()}

        created = 0
        skipped = 0

        for idx in INDEXES:
            if idx['name'] in existing:
                print(f"[SKIP] {idx['name']} - already exists")
                skipped += 1
            else:
                print(f"[CREATE] {idx['name']} - {idx['purpose']}")
                try:
                    await db.execute(text(idx['sql']))
                    await db.commit()
                    print(f"         SUCCESS")
                    created += 1
                except Exception as e:
                    print(f"         FAILED: {e}")

        print("\n" + "=" * 60)
        print(f"SUMMARY: Created {created}, Skipped {skipped} (already existed)")
        print("=" * 60)

        if created > 0:
            print("\n*** Indexes created! Batch performance should now improve. ***")
            print("Expected improvement: 60s -> 3s per portfolio day")

if __name__ == "__main__":
    asyncio.run(create_indexes())
