"""
Comprehensive Data Migration Script: Old DB → New Dual DBs

This script migrates ALL data from the old single database to the new
dual-database architecture (Core + AI).

Usage:
    export OLD_DATABASE_URL="postgresql://..."
    export NEW_CORE_DATABASE_URL="postgresql://..."
    export NEW_AI_DATABASE_URL="postgresql://..."

    python scripts/database/migrate_to_new_dbs.py

What gets migrated:

PHASE 6 - AI Database:
    - ai_kb_documents (RAG knowledge base)
    - ai_memories (user preferences)
    - ai_feedback (message ratings)

PHASE 7 - Core Database (User Data):
    - users (with hashed passwords)
    - portfolios
    - positions
    - portfolio_snapshots (last 5 days)
    - snapshot_positions (last 5 days)
    - tags_v2, position_tags
    - target_prices
    - agent_conversations, agent_messages (chat history)
    - equity_changes, position_realized_events
    - Position calculations: greeks, factor_exposures, betas

PHASE 7.5 - Core Database (Market Data):
    - market_data_cache
    - company_profiles
    - income_statements, balance_sheets, cash_flows
    - benchmarks_sector_weights
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

# Configuration
OLD_DB_URL = os.environ.get("OLD_DATABASE_URL", "")
NEW_CORE_DB_URL = os.environ.get("NEW_CORE_DATABASE_URL", "")
NEW_AI_DB_URL = os.environ.get("NEW_AI_DATABASE_URL", "")

SNAPSHOT_DAYS = 5  # How many days of snapshots to copy

# Tables to migrate - ORDER MATTERS (foreign key dependencies)

# Phase 6: AI Database tables
AI_TABLES = [
    "ai_kb_documents",
    "ai_memories",
    "ai_feedback",
]

# Phase 7: Core user data tables (order respects FK constraints)
CORE_USER_TABLES = [
    # Users first (no dependencies)
    "users",

    # Portfolios depend on users
    "portfolios",

    # Positions depend on portfolios
    "positions",

    # Tags (no dependencies)
    "tags_v2",

    # Position tags depend on positions and tags
    "position_tags",

    # Target prices depend on positions
    "target_prices",

    # Chat history
    "agent_conversations",
    "agent_messages",

    # P&L tracking
    "equity_changes",
    "position_realized_events",

    # Position calculations (depend on positions)
    "position_greeks",
    "position_factor_exposures",
    "position_market_betas",
]

# Phase 7 (date-filtered): Snapshots for last N days
SNAPSHOT_TABLES = [
    "portfolio_snapshots",
    "snapshot_positions",
]

# Phase 7.5: Market data tables
MARKET_DATA_TABLES = [
    "market_data_cache",
    "company_profiles",
    "income_statements",
    "balance_sheets",
    "cash_flows",
    "benchmarks_sector_weights",
]


def get_sync_engine(url: str) -> Engine:
    """Create a sync engine from async URL."""
    sync_url = url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
    return create_engine(sync_url)


def get_table_columns(engine: Engine, table: str) -> List[str]:
    """Get column names for a table."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table AND table_schema = 'public'
            ORDER BY ordinal_position
        """), {"table": table})
        return [row[0] for row in result.fetchall()]


def copy_table(
    old_engine: Engine,
    new_engine: Engine,
    table: str,
    where_clause: str = None,
    batch_size: int = 500
) -> int:
    """Copy all rows from old DB table to new DB table."""

    # Get columns
    columns = get_table_columns(old_engine, table)
    if not columns:
        print(f"  [WARN] {table}: table not found in source DB")
        return 0

    # Check if table exists in target
    target_columns = get_table_columns(new_engine, table)
    if not target_columns:
        print(f"  [WARN] {table}: table not found in target DB")
        return 0

    # Use only columns that exist in both
    common_columns = [c for c in columns if c in target_columns]
    if not common_columns:
        print(f"  [WARN] {table}: no common columns")
        return 0

    col_names = ", ".join(common_columns)

    # Build SELECT query
    select_sql = f"SELECT {col_names} FROM {table}"
    if where_clause:
        select_sql += f" WHERE {where_clause}"

    # Fetch from old DB
    with old_engine.connect() as old_conn:
        result = old_conn.execute(text(select_sql))
        rows = result.fetchall()

    if not rows:
        print(f"  [WARN] {table}: no rows to copy")
        return 0

    # Build INSERT query with ON CONFLICT DO NOTHING
    placeholders = ", ".join([f":{col}" for col in common_columns])
    insert_sql = f"""
        INSERT INTO {table} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """

    # Insert into new DB in batches
    total = 0
    with new_engine.connect() as new_conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            for row in batch:
                row_dict = dict(zip(common_columns, row))
                new_conn.execute(text(insert_sql), row_dict)
            new_conn.commit()
            total += len(batch)
            if total % 1000 == 0 or total == len(rows):
                print(f"    {table}: {total}/{len(rows)} rows", end="\r")

    print(f"  [OK] {table}: {total} rows copied" + " " * 20)
    return total


def migrate_ai_data(old_engine: Engine, ai_engine: Engine):
    """Phase 6: Migrate AI data to AI database."""
    print("\n" + "=" * 60)
    print("PHASE 6: Migrating AI Data -> AI Database")
    print("=" * 60)

    total = 0
    for table in AI_TABLES:
        try:
            count = copy_table(old_engine, ai_engine, table)
            total += count
        except Exception as e:
            print(f"  [ERR] {table}: {e}")

    print(f"\nPhase 6 Complete: {total} total rows migrated to AI DB")
    return total


def migrate_user_data(old_engine: Engine, core_engine: Engine):
    """Phase 7: Migrate user data to Core database."""
    print("\n" + "=" * 60)
    print("PHASE 7: Migrating User Data -> Core Database")
    print("=" * 60)

    total = 0
    for table in CORE_USER_TABLES:
        try:
            count = copy_table(old_engine, core_engine, table)
            total += count
        except Exception as e:
            print(f"  [ERR] {table}: {e}")

    # Handle date-filtered snapshot tables
    print("\n  Snapshots (last 5 days):")
    cutoff_date = (datetime.utcnow() - timedelta(days=SNAPSHOT_DAYS)).strftime('%Y-%m-%d')

    for table in SNAPSHOT_TABLES:
        try:
            # portfolio_snapshots has 'snapshot_date', snapshot_positions links via FK
            if table == "portfolio_snapshots":
                where = f"snapshot_date >= '{cutoff_date}'"
            elif table == "snapshot_positions":
                # Get snapshot IDs from the last 5 days
                where = f"snapshot_id IN (SELECT id FROM portfolio_snapshots WHERE snapshot_date >= '{cutoff_date}')"
            else:
                where = None

            count = copy_table(old_engine, core_engine, table, where_clause=where)
            total += count
        except Exception as e:
            print(f"  [ERR] {table}: {e}")

    print(f"\nPhase 7 Complete: {total} total rows migrated to Core DB")
    return total


def migrate_market_data(old_engine: Engine, core_engine: Engine):
    """Phase 7.5: Migrate market data to Core database."""
    print("\n" + "=" * 60)
    print("PHASE 7.5: Migrating Market Data -> Core Database")
    print("=" * 60)

    total = 0
    for table in MARKET_DATA_TABLES:
        try:
            count = copy_table(old_engine, core_engine, table)
            total += count
        except Exception as e:
            print(f"  [ERR] {table}: {e}")

    print(f"\nPhase 7.5 Complete: {total} total rows migrated to Core DB")
    return total


def verify_migration(old_engine: Engine, core_engine: Engine, ai_engine: Engine):
    """Verify row counts match."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Comparing Row Counts")
    print("=" * 60)

    def count_rows(engine: Engine, table: str, where: str = None) -> int:
        try:
            sql = f"SELECT COUNT(*) FROM {table}"
            if where:
                sql += f" WHERE {where}"
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                return result.scalar() or 0
        except:
            return -1

    print("\nCore Database Tables:")
    all_core_tables = CORE_USER_TABLES + SNAPSHOT_TABLES + MARKET_DATA_TABLES
    for table in all_core_tables:
        old_count = count_rows(old_engine, table)
        new_count = count_rows(core_engine, table)
        status = "[OK]" if new_count >= 0 else "[ERR]"
        print(f"  {status} {table}: {new_count} rows (source had {old_count})")

    print("\nAI Database Tables:")
    for table in AI_TABLES:
        old_count = count_rows(old_engine, table)
        new_count = count_rows(ai_engine, table)
        status = "[OK]" if new_count >= 0 else "[ERR]"
        print(f"  {status} {table}: {new_count} rows (source had {old_count})")


def main():
    """Main migration orchestrator."""
    print("=" * 60)
    print("SigmaSight Data Migration: Old DB -> New Dual DBs")
    print("=" * 60)

    # Validate environment
    if not OLD_DB_URL:
        print("ERROR: OLD_DATABASE_URL not set")
        print("  export OLD_DATABASE_URL='postgresql://...'")
        return 1

    if not NEW_CORE_DB_URL:
        print("ERROR: NEW_CORE_DATABASE_URL not set")
        print("  export NEW_CORE_DATABASE_URL='postgresql://...'")
        return 1

    if not NEW_AI_DB_URL:
        print("ERROR: NEW_AI_DATABASE_URL not set")
        print("  export NEW_AI_DATABASE_URL='postgresql://...'")
        return 1

    print(f"\nSource DB: {OLD_DB_URL[:50]}...")
    print(f"Target Core DB: {NEW_CORE_DB_URL[:50]}...")
    print(f"Target AI DB: {NEW_AI_DB_URL[:50]}...")
    print(f"Snapshot days: {SNAPSHOT_DAYS}")

    # Create engines
    old_engine = get_sync_engine(OLD_DB_URL)
    core_engine = get_sync_engine(NEW_CORE_DB_URL)
    ai_engine = get_sync_engine(NEW_AI_DB_URL)

    try:
        # Test connections
        print("\nTesting connections...")
        with old_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] Old DB connected")

        with core_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] New Core DB connected")

        with ai_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] New AI DB connected")

        # Run migrations
        migrate_ai_data(old_engine, ai_engine)
        migrate_user_data(old_engine, core_engine)
        migrate_market_data(old_engine, core_engine)

        # Verify
        verify_migration(old_engine, core_engine, ai_engine)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Run batch calculations: python scripts/run_batch_calculations.py")
        print("  2. Proceed to Phase 8 (update main repo code)")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        old_engine.dispose()
        core_engine.dispose()
        ai_engine.dispose()


if __name__ == "__main__":
    exit(main())
