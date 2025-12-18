"""
Check Railway database for missing performance-critical indexes.

This script focuses on identifying missing indexes that could cause
the 20-30x slowdown in batch calculations (3s → 1min per day).
"""

import asyncio
import asyncpg
from datetime import datetime


# Railway database URLs (both internal and external)
RAILWAY_INTERNAL_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@pgvector.railway.internal:5432/railway"
RAILWAY_PUBLIC_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@junction.proxy.rlwy.net:47057/railway"


# Performance-critical indexes that MUST exist for fast batch calculations
CRITICAL_INDEXES = {
    'market_data_cache': [
        ('idx_market_data_cache_symbol', 'symbol'),
        ('idx_market_data_cache_date', 'date'),
        ('idx_market_data_cache_symbol_date', 'symbol, date'),
    ],
    'portfolio_snapshots': [
        ('idx_portfolio_snapshots_portfolio_id', 'portfolio_id'),
        ('idx_portfolio_snapshots_calculation_date', 'calculation_date'),
        ('idx_portfolio_snapshots_portfolio_date', 'portfolio_id, calculation_date'),
    ],
    'positions': [
        ('idx_positions_portfolio_id', 'portfolio_id'),
        ('idx_positions_symbol', 'symbol'),
        ('idx_positions_active', 'is_active'),
    ],
    'position_greeks': [
        ('idx_position_greeks_position_id', 'position_id'),
        ('idx_position_greeks_calculation_date', 'calculation_date'),
    ],
    'position_factor_exposures': [
        ('idx_position_factor_exposures_position_id', 'position_id'),
        ('idx_position_factor_exposures_factor_name', 'factor_name'),
    ],
    'correlation_calculations': [
        ('idx_correlation_calculations_portfolio_id', 'portfolio_id'),
    ],
    'company_profiles': [
        ('idx_company_profiles_symbol', 'symbol'),
    ],
}


async def check_indexes():
    """Check for missing indexes."""
    print("=" * 80)
    print("RAILWAY DATABASE INDEX AUDIT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Try public URL first, fall back to internal
    conn = None
    db_url = None

    for url, name in [(RAILWAY_PUBLIC_URL, "Public"), (RAILWAY_INTERNAL_URL, "Internal")]:
        try:
            print(f"Attempting to connect via {name} URL...")
            conn = await asyncpg.connect(url)
            db_url = url
            print(f"✅ Connected to Railway via {name} URL")
            break
        except Exception as e:
            print(f"❌ Failed to connect via {name} URL: {e}")

    if not conn:
        print("\n❌ Could not connect to Railway database")
        print("\nTroubleshooting:")
        print("1. Ensure you have network access to Railway")
        print("2. Verify the database password is correct")
        print("3. Check if Railway database is running")
        return

    print()

    try:
        # Get all indexes
        print("Fetching all indexes from Railway database...")
        indexes_query = """
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """
        indexes = await conn.fetch(indexes_query)
        print(f"Found {len(indexes)} total indexes\n")

        # Build index lookup
        index_lookup = {}
        for idx in indexes:
            table = idx['tablename']
            if table not in index_lookup:
                index_lookup[table] = []
            index_lookup[table].append({
                'name': idx['indexname'],
                'definition': idx['indexdef']
            })

        # Check for missing critical indexes
        print("=" * 80)
        print("CRITICAL INDEX CHECK")
        print("=" * 80)
        print()

        total_missing = 0
        total_found = 0

        for table, expected_indexes in CRITICAL_INDEXES.items():
            print(f"Table: {table}")
            print("-" * 40)

            table_indexes = index_lookup.get(table, [])
            table_index_names = [idx['name'].lower() for idx in table_indexes]
            table_index_defs = [idx['definition'].lower() for idx in table_indexes]

            for idx_name, columns in expected_indexes:
                # Check if index exists by name or by columns in definition
                found = False

                # Check by name
                if idx_name.lower() in table_index_names:
                    found = True

                # Check by columns in any definition
                if not found:
                    columns_clean = columns.replace(' ', '').lower()
                    for defn in table_index_defs:
                        defn_clean = defn.replace(' ', '').replace('(', '').replace(')', '')
                        if columns_clean in defn_clean:
                            found = True
                            break

                if found:
                    print(f"  ✅ {idx_name} ({columns})")
                    total_found += 1
                else:
                    print(f"  🚨 MISSING: {idx_name} ({columns})")
                    print(f"      This could significantly slow queries on {table}!")
                    total_missing += 1

            # Show what indexes DO exist on this table
            if table_indexes:
                print(f"\n  Existing indexes on {table}:")
                for idx in table_indexes:
                    print(f"    - {idx['name']}")
            else:
                print(f"\n  ⚠️ No indexes found on {table}!")

            print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\n✅ Critical indexes found: {total_found}")
        print(f"🚨 Critical indexes MISSING: {total_missing}")

        if total_missing > 0:
            print(f"\n⚠️ WARNING: {total_missing} critical indexes are missing!")
            print("   This could explain the 20-30x performance degradation.")
            print("\n   Missing indexes slow down:")
            print("   - Market data lookups (symbol, date)")
            print("   - Portfolio snapshot queries")
            print("   - Factor exposure calculations")
            print("   - Correlation matrix generation")

        # Check pgvector extension
        print()
        print("=" * 80)
        print("PGVECTOR EXTENSION CHECK")
        print("=" * 80)
        print()

        pgvector_check = await conn.fetch("SELECT * FROM pg_extension WHERE extname = 'vector'")
        if pgvector_check:
            print("✅ pgvector extension is installed")
            for ext in pgvector_check:
                print(f"   Version: {ext['extversion']}")
        else:
            print("❌ pgvector extension NOT installed")

        # Check for pgvector indexes
        pgvector_indexes = await conn.fetch("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND (indexdef ILIKE '%vector%' OR indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
            ORDER BY tablename, indexname
        """)

        print(f"\npgvector indexes found: {len(pgvector_indexes)}")
        for idx in pgvector_indexes:
            print(f"  - {idx['tablename']}.{idx['indexname']}")
            if 'hnsw' in idx['indexdef'].lower():
                print(f"    Type: HNSW (optimal)")
            elif 'ivfflat' in idx['indexdef'].lower():
                print(f"    Type: IVFFlat (slower than HNSW)")

        # Check table sizes
        print()
        print("=" * 80)
        print("TABLE SIZE CHECK (LARGEST TABLES)")
        print("=" * 80)
        print()

        size_query = """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10;
        """

        sizes = await conn.fetch(size_query)
        print(f"{'Table':<35} {'Size':<15} {'Status':<20}")
        print("-" * 70)

        for row in sizes:
            table = row['tablename']
            size = row['size']
            size_bytes = row['size_bytes']

            # Check if table has indexes
            has_indexes = table in index_lookup and len(index_lookup[table]) > 0
            status = "✅ Has indexes" if has_indexes else "🚨 NO INDEXES"

            # For very large tables without indexes, this is critical
            if size_bytes > 1_000_000 and not has_indexes:
                status = "🚨🚨 CRITICAL: Large table, no indexes!"

            print(f"{table:<35} {size:<15} {status:<20}")

        # Row count check
        print()
        print("=" * 80)
        print("ROW COUNT CHECK (KEY TABLES)")
        print("=" * 80)
        print()

        key_tables = [
            'users', 'portfolios', 'positions',
            'market_data_cache', 'portfolio_snapshots',
            'position_greeks', 'position_factor_exposures',
            'correlation_calculations', 'company_profiles'
        ]

        print(f"{'Table':<35} {'Row Count':<15}")
        print("-" * 50)

        for table in key_tables:
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
                print(f"{table:<35} {count:>14,}")
            except Exception as e:
                print(f"{table:<35} Error: {e}")

    finally:
        await conn.close()

    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    print()

    if total_missing > 0:
        print("🚨 ACTION REQUIRED:")
        print("   Run the following to create missing indexes:")
        print()
        print("   cd backend")
        print("   uv run python scripts/database/create_missing_indexes.py")
        print()
    else:
        print("✅ All critical indexes are present")
        print("   Performance issues may be caused by other factors:")
        print("   - Network latency to Railway")
        print("   - Database resource constraints (CPU/memory)")
        print("   - Query plan changes after migration")
        print("   - Missing table statistics (ANALYZE needed)")


async def main():
    await check_indexes()


if __name__ == "__main__":
    asyncio.run(main())
