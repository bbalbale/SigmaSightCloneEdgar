"""
Fast Market Data Copy: Old DB -> New Core DB

Uses pandas for efficient bulk operations.
Copies market_data_cache and company_profiles in chunks.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text

OLD_DB = os.environ.get("OLD_DATABASE_URL", "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway")
NEW_CORE_DB = os.environ.get("NEW_CORE_DATABASE_URL", "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway")

CHUNK_SIZE = 10000  # Rows per chunk

TABLES = [
    "market_data_cache",
    "company_profiles",
    "income_statements",
    "balance_sheets",
    "cash_flows",
    "benchmarks_sector_weights",
]


def copy_table_fast(old_engine, new_engine, table: str):
    """Copy table using pandas for bulk operations."""

    # Count rows
    with old_engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        total_rows = result.scalar()

    if total_rows == 0:
        print(f"  {table}: empty, skipping")
        return 0

    print(f"  {table}: {total_rows} rows", end="", flush=True)

    # Clear existing data in target first
    with new_engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        conn.commit()
    print(" (cleared)", end="", flush=True)

    # Get columns excluding 'id' (let DB generate new UUIDs)
    with old_engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{table}' AND table_schema = 'public' AND column_name != 'id'
            ORDER BY ordinal_position
        """))
        columns = [r[0] for r in result.fetchall()]

    col_list = ", ".join(columns)

    # Copy in chunks
    copied = 0
    for chunk_start in range(0, total_rows, CHUNK_SIZE):
        # Read chunk from old DB (excluding id)
        df = pd.read_sql(
            f"SELECT {col_list} FROM {table} LIMIT {CHUNK_SIZE} OFFSET {chunk_start}",
            old_engine
        )

        # Write chunk to new DB
        df.to_sql(
            table,
            new_engine,
            if_exists="append",
            index=False,
            method="multi"
        )

        copied += len(df)
        print(f"\r  {table}: {copied}/{total_rows} rows", end="", flush=True)

    print(f"\r  {table}: {copied} rows [OK]" + " " * 20)
    return copied


def main():
    print("=" * 60)
    print("Fast Market Data Copy: Old DB -> New Core DB")
    print("=" * 60)

    old_engine = create_engine(OLD_DB)
    new_engine = create_engine(NEW_CORE_DB)

    # Test connections
    print("\nTesting connections...")
    with old_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  Old DB: connected")

    with new_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  New Core DB: connected")

    print("\nCopying tables...")
    total = 0
    for table in TABLES:
        try:
            count = copy_table_fast(old_engine, new_engine, table)
            total += count
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    # Verify
    print("\nVerification:")
    with new_engine.connect() as conn:
        for table in TABLES:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count} rows")

    print(f"\nTotal: {total} rows copied")
    print("=" * 60)

    old_engine.dispose()
    new_engine.dispose()


if __name__ == "__main__":
    main()
