"""Check Railway database indexes using SQLAlchemy (no asyncpg import needed)."""
import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.database import get_async_session

CRITICAL_INDEXES = [
    'idx_market_data_cache_symbol_date',
    'idx_positions_portfolio_deleted',
    'idx_snapshots_portfolio_date',
    'idx_positions_active_complete',
    'idx_market_data_valid_prices',
    'idx_positions_symbol_active',
]

async def check():
    print("Connecting to database...")

    async with get_async_session() as db:
        # Get all indexes on key tables
        print("\n=== EXISTING INDEXES ===")
        result = await db.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename IN ('positions', 'market_data_cache', 'portfolio_snapshots')
            ORDER BY tablename, indexname
        """))
        rows = result.fetchall()

        existing = set()
        for row in rows:
            print(f"  {row[1]}: {row[0]}")
            existing.add(row[0])

        # Check for missing critical indexes
        print("\n=== CRITICAL INDEX STATUS ===")
        missing = []
        for idx in CRITICAL_INDEXES:
            if idx in existing:
                print(f"  [OK] {idx}")
            else:
                print(f"  [MISSING] {idx}")
                missing.append(idx)

        # Get table sizes
        print("\n=== TABLE SIZES ===")
        sizes_result = await db.execute(text("""
            SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as size,
                   n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE relname IN ('positions', 'market_data_cache', 'portfolio_snapshots')
            ORDER BY pg_total_relation_size(relid) DESC
        """))
        for row in sizes_result.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]} rows)")

        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Total indexes found: {len(rows)}")
        print(f"Critical indexes missing: {len(missing)}")
        if missing:
            print(f"\n*** ACTION REQUIRED: Create missing indexes to fix performance ***")
            print(f"Missing: {', '.join(missing)}")
            print(f"\nRun: python scripts/database/create_indexes_railway.py")
        else:
            print("\n*** All critical indexes present - performance should be optimal ***")

if __name__ == "__main__":
    asyncio.run(check())
