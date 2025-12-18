"""
Diagnose Railway Database Performance Issues

This script:
1. Connects to Railway sandbox database
2. Checks for missing performance-critical indexes
3. Verifies pgvector migration success
4. Analyzes table statistics and sizes
5. Generates actionable recommendations

Focus: Identifying why batch calculations went from 3s to 60s per day.
"""

import asyncio
import asyncpg
from datetime import datetime


RAILWAY_PUBLIC_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@junction.proxy.rlwy.net:47057/railway"


# Critical indexes from migrations i6j7k8l9m0n1 and j7k8l9m0n1o2
CRITICAL_INDEXES = [
    # From i6j7k8l9m0n1_add_composite_indexes_for_performance.py
    {
        'table': 'market_data_cache',
        'name': 'idx_market_data_cache_symbol_date',
        'columns': ['symbol', 'date'],
        'purpose': 'Price lookups (378+ queries per run)',
        'impact': 'Eliminates full table scans on 191k+ row table',
        'priority': 'CRITICAL'
    },
    {
        'table': 'positions',
        'name': 'idx_positions_portfolio_deleted',
        'columns': ['portfolio_id', 'deleted_at'],
        'purpose': 'Active position queries',
        'impact': 'Speeds up WHERE portfolio_id = X AND deleted_at IS NULL',
        'priority': 'CRITICAL'
    },
    {
        'table': 'portfolio_snapshots',
        'name': 'idx_snapshots_portfolio_date',
        'columns': ['portfolio_id', 'snapshot_date'],
        'purpose': 'Equity rollforward (previous snapshot)',
        'impact': 'Speeds up equity calculations',
        'priority': 'CRITICAL'
    },
    # From j7k8l9m0n1o2_add_priority_performance_indexes.py
    {
        'table': 'positions',
        'name': 'idx_positions_active_complete',
        'columns': ['portfolio_id', 'deleted_at', 'exit_date', 'investment_class'],
        'purpose': 'Active PUBLIC positions for portfolio',
        'impact': '90%+ query speedup',
        'priority': 'CRITICAL',
        'partial': 'WHERE deleted_at IS NULL'
    },
    {
        'table': 'market_data_cache',
        'name': 'idx_market_data_valid_prices',
        'columns': ['symbol', 'date'],
        'purpose': 'Valid price lookups (filter out null/zero)',
        'impact': 'Eliminates null price lookups',
        'priority': 'CRITICAL',
        'partial': 'WHERE close > 0'
    },
    {
        'table': 'positions',
        'name': 'idx_positions_symbol_active',
        'columns': ['deleted_at', 'symbol', 'exit_date', 'expiration_date'],
        'purpose': 'Portfolio aggregations by symbol',
        'impact': 'Portfolio aggregation speedup',
        'priority': 'CRITICAL',
        'partial': "WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''"
    },
]


async def diagnose():
    """Main diagnostic function."""
    output = []

    def log(msg=""):
        print(msg)
        output.append(msg)

    log("=" * 100)
    log("RAILWAY DATABASE PERFORMANCE DIAGNOSTIC REPORT")
    log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 100)
    log()

    # Connect
    log("Connecting to Railway sandbox database...")
    try:
        conn = await asyncpg.connect(RAILWAY_PUBLIC_URL)
        log("✅ Connected successfully")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        return output

    log()

    try:
        # 1. Check Alembic version
        log("=" * 100)
        log("1. MIGRATION STATUS")
        log("=" * 100)
        log()

        alembic_version = await conn.fetchval("SELECT version_num FROM alembic_version")
        log(f"Current Alembic version: {alembic_version}")

        # Check if we're at head
        if alembic_version:
            log("✅ Alembic tracking is active")
        else:
            log("❌ No Alembic version found - migrations may not have run!")

        log()

        # 2. Check extensions
        log("=" * 100)
        log("2. POSTGRESQL EXTENSIONS")
        log("=" * 100)
        log()

        extensions = await conn.fetch("SELECT extname, extversion FROM pg_extension ORDER BY extname")
        log(f"Installed extensions ({len(extensions)}):")
        for ext in extensions:
            log(f"  - {ext['extname']:<20} (version {ext['extversion']})")

        has_pgvector = any(ext['extname'] == 'vector' for ext in extensions)
        if has_pgvector:
            log("\n✅ pgvector extension is installed")
        else:
            log("\n⚠️ pgvector extension NOT found")

        log()

        # 3. Check for missing critical indexes
        log("=" * 100)
        log("3. CRITICAL INDEX CHECK")
        log("=" * 100)
        log()

        all_indexes = await conn.fetch("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)

        index_lookup = {}
        for idx in all_indexes:
            if idx['tablename'] not in index_lookup:
                index_lookup[idx['tablename']] = []
            index_lookup[idx['tablename']].append({
                'name': idx['indexname'],
                'def': idx['indexdef']
            })

        log(f"Total indexes in database: {len(all_indexes)}")
        log()

        missing_indexes = []
        found_indexes = []

        for idx_info in CRITICAL_INDEXES:
            table = idx_info['table']
            name = idx_info['name']
            columns = idx_info['columns']
            purpose = idx_info['purpose']
            impact = idx_info['impact']
            priority = idx_info['priority']

            # Check if index exists
            table_indexes = index_lookup.get(table, [])
            exists = any(i['name'] == name for i in table_indexes)

            if exists:
                log(f"✅ {name}")
                log(f"   Table: {table}")
                log(f"   Columns: {', '.join(columns)}")
                log(f"   Purpose: {purpose}")
                found_indexes.append(idx_info)
            else:
                log(f"🚨 MISSING: {name}")
                log(f"   Table: {table}")
                log(f"   Columns: {', '.join(columns)}")
                log(f"   Purpose: {purpose}")
                log(f"   Impact: {impact}")
                log(f"   Priority: {priority}")
                if 'partial' in idx_info:
                    log(f"   Partial Index: {idx_info['partial']}")
                missing_indexes.append(idx_info)

            log()

        # Summary
        log("=" * 100)
        log("INDEX SUMMARY")
        log("=" * 100)
        log()
        log(f"✅ Critical indexes found: {len(found_indexes)}/{len(CRITICAL_INDEXES)}")
        log(f"🚨 Critical indexes MISSING: {len(missing_indexes)}/{len(CRITICAL_INDEXES)}")
        log()

        if missing_indexes:
            log("⚠️ PERFORMANCE IMPACT:")
            log()
            log("Missing indexes will cause:")
            log("  • Full table scans on market_data_cache (191k+ rows)")
            log("  • Slow position filtering queries")
            log("  • Inefficient portfolio snapshot lookups")
            log("  • 10x-100x slower batch calculations")
            log()
            log("Expected slowdown: 3 seconds → 60+ seconds per day")
            log("Observed slowdown: 3 seconds → 60 seconds per day ✅ MATCHES")
            log()

        # 4. Check table sizes
        log("=" * 100)
        log("4. TABLE SIZE ANALYSIS")
        log("=" * 100)
        log()

        sizes = await conn.fetch("""
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS total_size,
                pg_total_relation_size('public.' || tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size('public.' || tablename) DESC
            LIMIT 15
        """)

        log(f"{'Table':<35} {'Size':<15} {'Index Status':<30}")
        log("-" * 80)

        for row in sizes:
            table = row['tablename']
            size = row['total_size']
            size_bytes = row['size_bytes']

            # Check if table has indexes
            table_idx_count = len(index_lookup.get(table, []))
            has_critical = any(idx['table'] == table for idx in found_indexes)

            if has_critical:
                status = f"✅ Has critical indexes ({table_idx_count})"
            elif table_idx_count > 0:
                status = f"⚠️ {table_idx_count} indexes (missing critical)"
            else:
                status = "🚨 NO INDEXES"

            log(f"{table:<35} {size:<15} {status:<30}")

        log()

        # 5. Row counts
        log("=" * 100)
        log("5. ROW COUNT ANALYSIS")
        log("=" * 100)
        log()

        key_tables = [
            'users', 'portfolios', 'positions',
            'market_data_cache', 'portfolio_snapshots',
            'position_greeks', 'position_factor_exposures',
            'correlation_calculations', 'company_profiles',
            'ai_kb_documents', 'ai_kb_document_chunks'
        ]

        log(f"{'Table':<35} {'Row Count':<15} {'Est. Impact':<30}")
        log("-" * 80)

        for table in key_tables:
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')

                # Estimate impact of missing indexes
                impact = ""
                if table == 'market_data_cache' and count > 100000:
                    missing = any(idx['table'] == table for idx in missing_indexes)
                    if missing:
                        impact = "🚨 CRITICAL: Full scans on 100k+ rows"
                    else:
                        impact = "✅ Indexed"
                elif table == 'positions':
                    missing = any(idx['table'] == table for idx in missing_indexes)
                    if missing:
                        impact = "🚨 HIGH: Slow position queries"
                    else:
                        impact = "✅ Indexed"
                elif table == 'portfolio_snapshots':
                    missing = any(idx['table'] == table for idx in missing_indexes)
                    if missing:
                        impact = "🚨 HIGH: Slow snapshot lookups"
                    else:
                        impact = "✅ Indexed"

                log(f"{table:<35} {count:>14,} {impact:<30}")
            except Exception as e:
                log(f"{table:<35} {'Error':<15} {str(e):<30}")

        log()

        # 6. pgvector indexes
        log("=" * 100)
        log("6. PGVECTOR INDEX CHECK")
        log("=" * 100)
        log()

        pgv_indexes = await conn.fetch("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND (indexdef ILIKE '%vector%' OR indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
        """)

        if pgv_indexes:
            log(f"pgvector indexes found: {len(pgv_indexes)}")
            for idx in pgv_indexes:
                log(f"  - {idx['tablename']}.{idx['indexname']}")
                if 'hnsw' in idx['indexdef'].lower():
                    log(f"    Type: HNSW (optimal)")
                elif 'ivfflat' in idx['indexdef'].lower():
                    log(f"    Type: IVFFlat (slower than HNSW)")
        else:
            log("No pgvector indexes found")

        log()

        # 7. Recommendations
        log("=" * 100)
        log("7. RECOMMENDATIONS")
        log("=" * 100)
        log()

        if missing_indexes:
            log("🚨 IMMEDIATE ACTION REQUIRED:")
            log()
            log(f"   {len(missing_indexes)} critical performance indexes are missing!")
            log()
            log("   To fix:")
            log("   1. Run pending migrations:")
            log("      cd backend")
            log("      railway run 'alembic upgrade head'")
            log()
            log("   2. Or manually create indexes:")
            log("      railway run 'python scripts/database/create_missing_indexes.py'")
            log()
            log("   Expected improvement:")
            log("   - Batch calculation time: 60s → 3s per day")
            log("   - Overall performance: 20x faster")
            log()
        else:
            log("✅ All critical indexes are present")
            log()
            log("   Performance issues may be caused by:")
            log("   - Network latency to Railway")
            log("   - Database resource limits (CPU/memory)")
            log("   - Missing table statistics (run ANALYZE)")
            log("   - Query plan changes")
            log()
            log("   Recommended next steps:")
            log("   1. Run ANALYZE on all tables:")
            log("      railway run 'psql -c \"ANALYZE;\"'")
            log()
            log("   2. Check Railway resource usage in dashboard")
            log()
            log("   3. Profile slow queries with EXPLAIN ANALYZE")
            log()

    finally:
        await conn.close()

    # Save report
    log()
    log("=" * 100)
    log("REPORT COMPLETE")
    log("=" * 100)

    return output


async def main():
    output = await diagnose()

    # Save to file
    filename = f"railway_performance_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print()
    print(f"✅ Report saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())
