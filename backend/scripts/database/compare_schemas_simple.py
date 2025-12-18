"""
Compare local and Railway database schemas - simplified version.
Saves output to file for review.
"""

import asyncio
import asyncpg
import sys
from datetime import datetime


# Database URLs
LOCAL_DB_URL = "postgresql://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db"
RAILWAY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@junction.proxy.rlwy.net:47057/railway"


output_lines = []


def log(msg):
    """Log to both console and output list."""
    print(msg)
    output_lines.append(msg)


async def run_comparison():
    """Main comparison function."""
    log("=" * 80)
    log("DATABASE SCHEMA COMPARISON REPORT")
    log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 80)
    log("")

    # Connect to both databases
    log("Connecting to databases...")
    local_conn = None
    railway_conn = None

    try:
        local_conn = await asyncpg.connect(LOCAL_DB_URL)
        log("✅ Connected to LOCAL database")
    except Exception as e:
        log(f"❌ Failed to connect to LOCAL database: {e}")

    try:
        railway_conn = await asyncpg.connect(RAILWAY_DB_URL)
        log("✅ Connected to RAILWAY database")
    except Exception as e:
        log(f"❌ Failed to connect to RAILWAY database: {e}")

    if not local_conn or not railway_conn:
        log("\n❌ Cannot proceed without both connections")
        return False

    log("")

    try:
        # 1. Extensions
        log("=" * 80)
        log("1. EXTENSIONS COMPARISON")
        log("=" * 80)

        local_ext = await local_conn.fetch("SELECT extname FROM pg_extension ORDER BY extname")
        railway_ext = await railway_conn.fetch("SELECT extname FROM pg_extension ORDER BY extname")

        local_ext_names = [r['extname'] for r in local_ext]
        railway_ext_names = [r['extname'] for r in railway_ext]

        log(f"\nLocal Extensions ({len(local_ext_names)}): {', '.join(local_ext_names)}")
        log(f"Railway Extensions ({len(railway_ext_names)}): {', '.join(railway_ext_names)}")

        local_only = set(local_ext_names) - set(railway_ext_names)
        railway_only = set(railway_ext_names) - set(local_ext_names)

        if local_only:
            log(f"\n⚠️ In LOCAL only: {', '.join(local_only)}")
        if railway_only:
            log(f"\n⚠️ In RAILWAY only: {', '.join(railway_only)}")
        if not local_only and not railway_only:
            log("\n✅ Extensions match")
        log("")

        # 2. Tables
        log("=" * 80)
        log("2. TABLE COMPARISON")
        log("=" * 80)

        local_tables = await local_conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        railway_tables = await railway_conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )

        local_table_names = [r['table_name'] for r in local_tables]
        railway_table_names = [r['table_name'] for r in railway_tables]

        log(f"\nLocal Tables: {len(local_table_names)}")
        log(f"Railway Tables: {len(railway_table_names)}")

        local_only = set(local_table_names) - set(railway_table_names)
        railway_only = set(railway_table_names) - set(local_table_names)
        common = set(local_table_names) & set(railway_table_names)

        if local_only:
            log(f"\n⚠️ Tables in LOCAL only ({len(local_only)}):")
            for t in sorted(local_only):
                log(f"  - {t}")

        if railway_only:
            log(f"\n⚠️ Tables in RAILWAY only ({len(railway_only)}):")
            for t in sorted(railway_only):
                log(f"  - {t}")

        if not local_only and not railway_only:
            log("\n✅ All tables match")
        log("")

        # 3. Indexes - CRITICAL
        log("=" * 80)
        log("3. INDEX COMPARISON (CRITICAL FOR PERFORMANCE)")
        log("=" * 80)

        local_idx = await local_conn.fetch(
            "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname"
        )
        railway_idx = await railway_conn.fetch(
            "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname"
        )

        log(f"\nLocal Indexes: {len(local_idx)}")
        log(f"Railway Indexes: {len(railway_idx)}")

        local_idx_keys = {(r['tablename'], r['indexname']) for r in local_idx}
        railway_idx_keys = {(r['tablename'], r['indexname']) for r in railway_idx}

        missing_in_railway = local_idx_keys - railway_idx_keys
        missing_in_local = railway_idx_keys - local_idx_keys

        if missing_in_railway:
            log(f"\n🚨 INDEXES MISSING IN RAILWAY ({len(missing_in_railway)}):")
            log("   THIS COULD EXPLAIN THE PERFORMANCE ISSUES!\n")
            local_idx_dict = {(r['tablename'], r['indexname']): r['indexdef'] for r in local_idx}
            for table, idx_name in sorted(missing_in_railway):
                log(f"  Table: {table}")
                log(f"  Index: {idx_name}")
                log(f"  Definition: {local_idx_dict[(table, idx_name)]}")
                log("")

        if missing_in_local:
            log(f"\n⚠️ Indexes in RAILWAY only ({len(missing_in_local)}):")
            railway_idx_dict = {(r['tablename'], r['indexname']): r['indexdef'] for r in railway_idx}
            for table, idx_name in sorted(missing_in_local):
                log(f"  Table: {table}")
                log(f"  Index: {idx_name}")
                log(f"  Definition: {railway_idx_dict[(table, idx_name)]}")
                log("")

        if not missing_in_railway and not missing_in_local:
            log("\n✅ All indexes match")
        log("")

        # 4. pgvector indexes
        log("=" * 80)
        log("4. PGVECTOR INDEXES")
        log("=" * 80)

        pgv_query = """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND (indexdef ILIKE '%vector%' OR indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
            ORDER BY tablename, indexname
        """

        local_pgv = await local_conn.fetch(pgv_query)
        railway_pgv = await railway_conn.fetch(pgv_query)

        log(f"\nLocal pgvector indexes: {len(local_pgv)}")
        for r in local_pgv:
            log(f"  - {r['tablename']}.{r['indexname']}")

        log(f"\nRailway pgvector indexes: {len(railway_pgv)}")
        for r in railway_pgv:
            log(f"  - {r['tablename']}.{r['indexname']}")

        if len(local_pgv) != len(railway_pgv):
            log("\n🚨 PGVECTOR INDEX MISMATCH!")
        else:
            log("\n✅ pgvector indexes match")
        log("")

        # 5. Row counts
        log("=" * 80)
        log("5. ROW COUNT COMPARISON (KEY TABLES)")
        log("=" * 80)

        key_tables = [
            'users', 'portfolios', 'positions',
            'market_data_cache', 'portfolio_snapshots',
            'position_greeks', 'position_factor_exposures',
            'correlation_calculations',
            'ai_kb_documents', 'ai_kb_document_chunks',
            'conversations', 'messages'
        ]

        log(f"\n{'Table':<30} {'Local':<15} {'Railway':<15} {'Difference'}")
        log("-" * 75)

        for table in key_tables:
            if table in common:
                try:
                    local_count = await local_conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
                    railway_count = await railway_conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
                    diff = railway_count - local_count
                    diff_str = f"+{diff}" if diff > 0 else str(diff)
                    status = "⚠️ " if abs(diff) > 100 else "  "
                    log(f"{status}{table:<28} {local_count:<15,} {railway_count:<15,} {diff_str}")
                except Exception as e:
                    log(f"  {table:<28} Error: {e}")
        log("")

        # 6. Performance-critical indexes
        log("=" * 80)
        log("6. PERFORMANCE-CRITICAL INDEXES CHECK")
        log("=" * 80)
        log("\nChecking critical indexes for batch calculations...")

        critical_checks = [
            ('market_data_cache', 'symbol'),
            ('market_data_cache', 'date'),
            ('portfolio_snapshots', 'portfolio_id'),
            ('portfolio_snapshots', 'calculation_date'),
            ('position_greeks', 'position_id'),
            ('position_factor_exposures', 'position_id'),
            ('correlation_calculations', 'portfolio_id'),
        ]

        railway_idx_defs = {r['tablename']: r['indexdef'] for r in railway_idx}

        for table, column in critical_checks:
            if table in railway_idx_defs:
                has_index = column in railway_idx_defs[table].lower()
            else:
                # Check if any index on this table references the column
                table_indexes = [r['indexdef'] for r in railway_idx if r['tablename'] == table]
                has_index = any(column in idx.lower() for idx in table_indexes)

            status = "✅" if has_index else "🚨"
            log(f"{status} {table}.{column}")
            if not has_index:
                log(f"   MISSING INDEX - Could slow batch calculations!")

        log("")

    finally:
        if local_conn:
            await local_conn.close()
        if railway_conn:
            await railway_conn.close()

    log("=" * 80)
    log("COMPARISON COMPLETE")
    log("=" * 80)
    log("\nKey Areas to Review:")
    log("1. Missing indexes in Railway (Section 3)")
    log("2. pgvector indexes (Section 4)")
    log("3. Row count differences (Section 5)")
    log("4. Performance-critical indexes (Section 6)")
    log("")

    return True


async def main():
    """Entry point."""
    success = await run_comparison()

    # Save to file
    output_file = "schema_comparison_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"\n✅ Report saved to: {output_file}")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
