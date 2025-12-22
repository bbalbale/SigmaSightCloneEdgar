"""
Run the symbol analytics migration on Railway Core DB.
"""
import os
import sys
from pathlib import Path

# Set up the environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from alembic.config import Config
from alembic import command

def run_migration():
    """Run alembic upgrade to head."""
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))

    print("Running migration on Railway Core DB...")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")

    try:
        # Run our specific migration to avoid multiple heads issue
        command.upgrade(alembic_cfg, "n0o1p2q3r4s5")
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
