"""
Check the current migration version on Railway Core DB.
"""
import os
import sys
from pathlib import Path

# Set up the environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from sqlalchemy import create_engine, text

def check_version():
    """Check current alembic version in Railway Core DB."""
    # Use sync URL
    sync_url = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
    engine = create_engine(sync_url)

    print("Checking Railway Core DB migration version...")
    print("-" * 60)

    with engine.connect() as conn:
        # Check alembic_version table
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            versions = result.fetchall()
            print(f"Current migration version(s): {[v[0] for v in versions]}")
        except Exception as e:
            print(f"Error checking alembic_version: {e}")

        # Also check if symbol tables exist
        print("\nChecking if symbol tables already exist...")
        for table in ['symbol_universe', 'symbol_factor_exposures', 'symbol_daily_metrics']:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'"))
                exists = result.fetchone()[0] > 0
                print(f"  {table}: {'EXISTS' if exists else 'NOT EXISTS'}")
            except Exception as e:
                print(f"  {table}: Error - {e}")

if __name__ == "__main__":
    check_version()
