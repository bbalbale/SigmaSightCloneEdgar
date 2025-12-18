"""Simple index check for Railway database."""
import asyncio
import asyncpg
import os

CRITICAL_INDEXES = [
    'idx_market_data_cache_symbol_date',
    'idx_positions_portfolio_deleted',
    'idx_snapshots_portfolio_date',
    'idx_positions_active_complete',
    'idx_market_data_valid_prices',
    'idx_positions_symbol_active',
]

async def check():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set")
        return

    print("Connecting to database...")
    conn = await asyncpg.connect(url)

    # Get all indexes on key tables
    print("\n=== EXISTING INDEXES ===")
    result = await conn.fetch("""
        SELECT indexname, tablename
        FROM pg_indexes
        WHERE tablename IN ('positions', 'market_data_cache', 'portfolio_snapshots')
        ORDER BY tablename, indexname
    """)

    existing = set()
    for row in result:
        print(f"  {row['tablename']}: {row['indexname']}")
        existing.add(row['indexname'])

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
    sizes = await conn.fetch("""
        SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as size,
               n_live_tup as row_count
        FROM pg_stat_user_tables
        WHERE relname IN ('positions', 'market_data_cache', 'portfolio_snapshots')
        ORDER BY pg_total_relation_size(relid) DESC
    """)
    for row in sizes:
        print(f"  {row['relname']}: {row['size']} ({row['row_count']} rows)")

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total indexes found: {len(result)}")
    print(f"Critical indexes missing: {len(missing)}")
    if missing:
        print(f"\n*** RECOMMENDATION: Create missing indexes to fix performance ***")
        print(f"Missing: {', '.join(missing)}")
    else:
        print("\n*** All critical indexes present - performance should be optimal ***")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
