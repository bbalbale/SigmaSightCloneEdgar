"""
Compare local and Railway database schemas to identify performance issues.

This script:
1. Connects to both local and Railway databases
2. Compares table structures, indexes, constraints
3. Checks row counts for key tables
4. Identifies missing indexes that could cause slowdowns
"""

import asyncio
import asyncpg
from typing import Dict, List, Any
import json
from datetime import datetime


# Database URLs
LOCAL_DB_URL = "postgresql://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db"
RAILWAY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@junction.proxy.rlwy.net:47057/railway"


async def get_connection(db_url: str):
    """Create asyncpg connection."""
    return await asyncpg.connect(db_url)


async def get_tables(conn) -> List[str]:
    """Get all table names."""
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    rows = await conn.fetch(query)
    return [row['table_name'] for row in rows]


async def get_indexes(conn, table_name: str) -> List[Dict[str, Any]]:
    """Get all indexes for a table."""
    query = """
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename = $1
        ORDER BY indexname;
    """
    rows = await conn.fetch(query, table_name)
    return [dict(row) for row in rows]


async def get_all_indexes(conn) -> List[Dict[str, Any]]:
    """Get all indexes in the database."""
    query = """
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def get_constraints(conn, table_name: str) -> List[Dict[str, Any]]:
    """Get all constraints for a table."""
    query = """
        SELECT
            conname as constraint_name,
            contype as constraint_type,
            pg_get_constraintdef(c.oid) as definition
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = 'public'
        AND t.relname = $1
        ORDER BY conname;
    """
    rows = await conn.fetch(query, table_name)
    return [dict(row) for row in rows]


async def get_row_count(conn, table_name: str) -> int:
    """Get row count for a table."""
    try:
        result = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
        return result
    except Exception as e:
        print(f"Error counting {table_name}: {e}")
        return -1


async def get_table_size(conn, table_name: str) -> str:
    """Get table size in human-readable format."""
    query = "SELECT pg_size_pretty(pg_total_relation_size($1::regclass));"
    try:
        result = await conn.fetchval(query, table_name)
        return result
    except Exception as e:
        return f"Error: {e}"


async def get_extensions(conn) -> List[str]:
    """Get installed PostgreSQL extensions."""
    query = "SELECT extname FROM pg_extension ORDER BY extname;"
    rows = await conn.fetch(query)
    return [row['extname'] for row in rows]


async def check_pgvector_indexes(conn) -> List[Dict[str, Any]]:
    """Check for pgvector-specific indexes."""
    query = """
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND (
            indexdef ILIKE '%vector_cosine_ops%'
            OR indexdef ILIKE '%vector_l2_ops%'
            OR indexdef ILIKE '%vector_ip_ops%'
            OR indexdef ILIKE '%ivfflat%'
            OR indexdef ILIKE '%hnsw%'
        )
        ORDER BY tablename, indexname;
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def compare_databases():
    """Main comparison function."""
    print("=" * 80)
    print("DATABASE SCHEMA COMPARISON REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Connect to both databases
    print("Connecting to databases...")
    try:
        local_conn = await get_connection(LOCAL_DB_URL)
        print("✅ Connected to LOCAL database")
    except Exception as e:
        print(f"❌ Failed to connect to LOCAL database: {e}")
        local_conn = None

    try:
        railway_conn = await get_connection(RAILWAY_DB_URL)
        print("✅ Connected to RAILWAY database")
    except Exception as e:
        print(f"❌ Failed to connect to RAILWAY database: {e}")
        railway_conn = None

    if not local_conn or not railway_conn:
        print("\n❌ Cannot proceed without both connections")
        return

    print()

    # 1. Compare Extensions
    print("=" * 80)
    print("1. EXTENSIONS COMPARISON")
    print("=" * 80)
    local_extensions = await get_extensions(local_conn)
    railway_extensions = await get_extensions(railway_conn)

    print(f"\nLocal Extensions ({len(local_extensions)}):")
    for ext in local_extensions:
        print(f"  - {ext}")

    print(f"\nRailway Extensions ({len(railway_extensions)}):")
    for ext in railway_extensions:
        print(f"  - {ext}")

    local_only = set(local_extensions) - set(railway_extensions)
    railway_only = set(railway_extensions) - set(local_extensions)

    if local_only:
        print(f"\n⚠️ Extensions in LOCAL only: {', '.join(local_only)}")
    if railway_only:
        print(f"\n⚠️ Extensions in RAILWAY only: {', '.join(railway_only)}")
    if not local_only and not railway_only:
        print("\n✅ Extensions match")
    print()

    # 2. Compare Tables
    print("=" * 80)
    print("2. TABLE COMPARISON")
    print("=" * 80)
    local_tables = await get_tables(local_conn)
    railway_tables = await get_tables(railway_conn)

    print(f"\nLocal Tables: {len(local_tables)}")
    print(f"Railway Tables: {len(railway_tables)}")

    local_only = set(local_tables) - set(railway_tables)
    railway_only = set(railway_tables) - set(local_tables)
    common_tables = set(local_tables) & set(railway_tables)

    if local_only:
        print(f"\n⚠️ Tables in LOCAL only ({len(local_only)}):")
        for table in sorted(local_only):
            print(f"  - {table}")

    if railway_only:
        print(f"\n⚠️ Tables in RAILWAY only ({len(railway_only)}):")
        for table in sorted(railway_only):
            print(f"  - {table}")

    if not local_only and not railway_only:
        print("\n✅ All tables match")
    print()

    # 3. Compare Indexes (CRITICAL FOR PERFORMANCE)
    print("=" * 80)
    print("3. INDEX COMPARISON (CRITICAL FOR PERFORMANCE)")
    print("=" * 80)
    local_indexes = await get_all_indexes(local_conn)
    railway_indexes = await get_all_indexes(railway_conn)

    # Create dictionaries for comparison
    local_idx_dict = {(idx['tablename'], idx['indexname']): idx['indexdef'] for idx in local_indexes}
    railway_idx_dict = {(idx['tablename'], idx['indexname']): idx['indexdef'] for idx in railway_indexes}

    print(f"\nLocal Indexes: {len(local_indexes)}")
    print(f"Railway Indexes: {len(railway_indexes)}")

    local_idx_keys = set(local_idx_dict.keys())
    railway_idx_keys = set(railway_idx_dict.keys())

    missing_in_railway = local_idx_keys - railway_idx_keys
    missing_in_local = railway_idx_keys - local_idx_keys

    if missing_in_railway:
        print(f"\n🚨 INDEXES MISSING IN RAILWAY ({len(missing_in_railway)}):")
        print("   THIS COULD EXPLAIN THE PERFORMANCE ISSUES!")
        for table, idx_name in sorted(missing_in_railway):
            print(f"\n  Table: {table}")
            print(f"  Index: {idx_name}")
            print(f"  Definition: {local_idx_dict[(table, idx_name)]}")

    if missing_in_local:
        print(f"\n⚠️ Indexes in RAILWAY only ({len(missing_in_local)}):")
        for table, idx_name in sorted(missing_in_local):
            print(f"\n  Table: {table}")
            print(f"  Index: {idx_name}")
            print(f"  Definition: {railway_idx_dict[(table, idx_name)]}")

    if not missing_in_railway and not missing_in_local:
        print("\n✅ All indexes match")
    print()

    # 4. Check pgvector indexes specifically
    print("=" * 80)
    print("4. PGVECTOR INDEXES (AI Knowledge Base)")
    print("=" * 80)
    local_pgv_indexes = await check_pgvector_indexes(local_conn)
    railway_pgv_indexes = await check_pgvector_indexes(railway_conn)

    print(f"\nLocal pgvector indexes: {len(local_pgv_indexes)}")
    for idx in local_pgv_indexes:
        print(f"  - {idx['tablename']}.{idx['indexname']}")
        print(f"    {idx['indexdef']}")

    print(f"\nRailway pgvector indexes: {len(railway_pgv_indexes)}")
    for idx in railway_pgv_indexes:
        print(f"  - {idx['tablename']}.{idx['indexname']}")
        print(f"    {idx['indexdef']}")

    if len(local_pgv_indexes) != len(railway_pgv_indexes):
        print("\n🚨 PGVECTOR INDEX MISMATCH - This could cause vector search slowness!")
    else:
        print("\n✅ pgvector indexes match")
    print()

    # 5. Compare Row Counts for Key Tables
    print("=" * 80)
    print("5. ROW COUNT COMPARISON (KEY TABLES)")
    print("=" * 80)

    key_tables = [
        'users',
        'portfolios',
        'positions',
        'market_data_cache',
        'portfolio_snapshots',
        'position_greeks',
        'position_factor_exposures',
        'correlation_calculations',
        'ai_kb_documents',
        'ai_kb_document_chunks',
        'conversations',
        'messages'
    ]

    print(f"\n{'Table':<30} {'Local':<15} {'Railway':<15} {'Difference':<15}")
    print("-" * 75)

    for table in key_tables:
        if table in common_tables:
            local_count = await get_row_count(local_conn, table)
            railway_count = await get_row_count(railway_conn, table)
            diff = railway_count - local_count
            diff_str = f"+{diff}" if diff > 0 else str(diff)

            # Flag significant differences
            status = "⚠️ " if abs(diff) > 100 else "  "
            print(f"{status}{table:<28} {local_count:<15,} {railway_count:<15,} {diff_str:<15}")
    print()

    # 6. Compare Table Sizes
    print("=" * 80)
    print("6. TABLE SIZE COMPARISON")
    print("=" * 80)
    print(f"\n{'Table':<30} {'Local Size':<20} {'Railway Size':<20}")
    print("-" * 70)

    for table in sorted(common_tables):
        if table not in ['alembic_version']:  # Skip system tables
            local_size = await get_table_size(local_conn, table)
            railway_size = await get_table_size(railway_conn, table)
            print(f"  {table:<28} {local_size:<20} {railway_size:<20}")
    print()

    # 7. Performance-Critical Indexes
    print("=" * 80)
    print("7. PERFORMANCE-CRITICAL INDEXES CHECK")
    print("=" * 80)
    print("\nChecking for indexes that should exist for batch calculations...")

    critical_indexes = [
        ('market_data_cache', 'market_data_cache', 'symbol'),
        ('market_data_cache', 'market_data_cache', 'date'),
        ('portfolio_snapshots', 'portfolio_snapshots', 'portfolio_id'),
        ('portfolio_snapshots', 'portfolio_snapshots', 'calculation_date'),
        ('position_greeks', 'position_greeks', 'position_id'),
        ('position_factor_exposures', 'position_factor_exposures', 'position_id'),
        ('correlation_calculations', 'correlation_calculations', 'portfolio_id'),
    ]

    for table, expected_table, column in critical_indexes:
        # Check if there's an index on this column
        railway_table_indexes = [idx for idx in railway_indexes if idx['tablename'] == table]
        has_index = any(column in idx['indexdef'].lower() for idx in railway_table_indexes)

        status = "✅" if has_index else "🚨"
        print(f"{status} {table}.{column}")

        if not has_index:
            print(f"   MISSING INDEX - This could slow down batch calculations!")

    print()

    # Close connections
    await local_conn.close()
    await railway_conn.close()

    print("=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)
    print("\nKey Findings:")
    print("1. Check for missing indexes in Railway (Section 3)")
    print("2. Verify pgvector indexes match (Section 4)")
    print("3. Look for significant row count differences (Section 5)")
    print("4. Review performance-critical indexes (Section 7)")
    print()


if __name__ == "__main__":
    asyncio.run(compare_databases())
