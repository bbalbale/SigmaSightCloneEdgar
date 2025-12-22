"""
Verify the symbol analytics tables were created correctly on Railway Core DB.
"""
import os
import sys
from pathlib import Path

# Set up the environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from sqlalchemy import create_engine, text

def verify_tables():
    """Verify symbol analytics tables on Railway Core DB."""
    sync_url = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
    engine = create_engine(sync_url)

    print("=" * 60)
    print("VERIFYING SYMBOL ANALYTICS TABLES ON RAILWAY CORE DB")
    print("=" * 60)

    with engine.connect() as conn:
        # Check each table
        tables = ['symbol_universe', 'symbol_factor_exposures', 'symbol_daily_metrics']

        for table in tables:
            print(f"\n--- {table.upper()} ---")

            # Check if table exists
            result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()

            if columns:
                print(f"Table exists with {len(columns)} columns:")
                for col in columns:
                    print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                print("TABLE NOT FOUND!")

        # Check indexes
        print("\n--- INDEXES ---")
        result = conn.execute(text("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('symbol_universe', 'symbol_factor_exposures', 'symbol_daily_metrics')
            ORDER BY tablename, indexname
        """))
        indexes = result.fetchall()
        for idx in indexes:
            print(f"  {idx[0]}: {idx[1]}")

        # Check foreign keys
        print("\n--- FOREIGN KEYS ---")
        result = conn.execute(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name IN ('symbol_universe', 'symbol_factor_exposures', 'symbol_daily_metrics')
        """))
        fks = result.fetchall()
        for fk in fks:
            print(f"  {fk[0]}.{fk[2]} -> {fk[3]} ({fk[1]})")

        # Check current migration version
        print("\n--- MIGRATION VERSION ---")
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = result.fetchall()
        print(f"  Current: {[v[0] for v in versions]}")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    verify_tables()
