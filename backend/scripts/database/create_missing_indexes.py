"""
Create Missing Performance Indexes on Railway Database

This script creates the critical performance indexes that should have been
created by migrations i6j7k8l9m0n1 and j7k8l9m0n1o2.

Run this if migrations failed or were skipped during the pgvector migration.
"""

import asyncio
import asyncpg
from datetime import datetime


RAILWAY_PUBLIC_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@junction.proxy.rlwy.net:47057/railway"


# Index creation SQL from the migrations
INDEXES_TO_CREATE = [
    # From i6j7k8l9m0n1
    {
        'name': 'idx_market_data_cache_symbol_date',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_cache_symbol_date
            ON market_data_cache (symbol, date);
        """,
        'description': 'Price lookups (378+ queries per run)',
    },
    {
        'name': 'idx_positions_portfolio_deleted',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_portfolio_deleted
            ON positions (portfolio_id, deleted_at);
        """,
        'description': 'Active position queries',
    },
    {
        'name': 'idx_snapshots_portfolio_date',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_snapshots_portfolio_date
            ON portfolio_snapshots (portfolio_id, snapshot_date);
        """,
        'description': 'Equity rollforward',
    },
    # From j7k8l9m0n1o2
    {
        'name': 'idx_positions_active_complete',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_active_complete
            ON positions (portfolio_id, deleted_at, exit_date, investment_class)
            WHERE deleted_at IS NULL;
        """,
        'description': 'Active PUBLIC positions (90%+ speedup)',
    },
    {
        'name': 'idx_market_data_valid_prices',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_valid_prices
            ON market_data_cache (symbol, date)
            WHERE close > 0;
        """,
        'description': 'Valid price lookups',
    },
    {
        'name': 'idx_positions_symbol_active',
        'sql': """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_symbol_active
            ON positions (deleted_at, symbol, exit_date, expiration_date)
            WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != '';
        """,
        'description': 'Portfolio aggregations by symbol',
    },
]


async def create_indexes(dry_run=False):
    """Create missing indexes."""
    print("=" * 100)
    print("CREATE MISSING PERFORMANCE INDEXES")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will create indexes)'}")
    print("=" * 100)
    print()

    # Connect
    print("Connecting to Railway database...")
    try:
        conn = await asyncpg.connect(RAILWAY_PUBLIC_URL)
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print()

    try:
        # Check which indexes already exist
        print("Checking existing indexes...")
        existing = await conn.fetch("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
        """)
        existing_names = {idx['indexname'] for idx in existing}
        print(f"Found {len(existing_names)} existing indexes")
        print()

        # Create each index
        print("=" * 100)
        print("INDEX CREATION")
        print("=" * 100)
        print()

        created = 0
        skipped = 0
        failed = 0

        for idx_info in INDEXES_TO_CREATE:
            name = idx_info['name']
            sql = idx_info['sql']
            desc = idx_info['description']

            if name in existing_names:
                print(f"⏭️  SKIP: {name}")
                print(f"   Reason: Already exists")
                print(f"   Purpose: {desc}")
                skipped += 1
            else:
                print(f"🔨 CREATE: {name}")
                print(f"   Purpose: {desc}")

                if dry_run:
                    print(f"   SQL: {sql.strip()}")
                    print(f"   Status: DRY RUN - not executed")
                    created += 1
                else:
                    try:
                        # Note: CREATE INDEX CONCURRENTLY cannot run in a transaction
                        # asyncpg.connect() by default doesn't use transactions
                        await conn.execute(sql)
                        print(f"   Status: ✅ Created successfully")
                        created += 1
                    except Exception as e:
                        print(f"   Status: ❌ Failed: {e}")
                        failed += 1

            print()

        # Summary
        print("=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print()
        print(f"Total indexes processed: {len(INDEXES_TO_CREATE)}")
        print(f"✅ Created/Would create: {created}")
        print(f"⏭️  Skipped (already exist): {skipped}")
        print(f"❌ Failed: {failed}")
        print()

        if dry_run:
            print("This was a DRY RUN - no changes were made")
            print("To actually create indexes, run:")
            print("  python scripts/database/create_missing_indexes.py --live")
        else:
            if created > 0:
                print(f"✅ Successfully created {created} indexes")
                print()
                print("Expected performance improvement:")
                print("  - Batch calculation time: 60s → 3s per day")
                print("  - Overall query performance: 20x faster")
                print()
                print("Next steps:")
                print("  1. Run ANALYZE to update table statistics:")
                print("     railway run 'psql -c \"ANALYZE;\"'")
                print()
                print("  2. Test batch calculations:")
                print("     cd backend && uv run python scripts/run_batch_calculations.py")
            elif skipped == len(INDEXES_TO_CREATE):
                print("All indexes already exist - no action needed")
            else:
                print(f"⚠️ {failed} indexes failed to create - check errors above")

    finally:
        await conn.close()


async def main():
    import sys

    # Check for --live flag
    dry_run = '--live' not in sys.argv

    if dry_run:
        print("Running in DRY RUN mode (no changes will be made)")
        print("Use --live flag to actually create indexes")
        print()

    await create_indexes(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
