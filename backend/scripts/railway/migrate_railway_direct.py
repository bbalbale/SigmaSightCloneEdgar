#!/usr/bin/env python
"""
Direct Railway migration script with hardcoded credentials.
Run Alembic migrations on Railway database using public URL.
"""
import os
import sys

# Set environment variables BEFORE any imports
os.environ["MIGRATION_MODE"] = "1"
os.environ["DATABASE_URL"] = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

# Now import after environment is set
from alembic.config import Config
from alembic import command

def main():
    print("=" * 60)
    print("RAILWAY DATABASE MIGRATION")
    print("=" * 60)
    print(f"Target: hopper.proxy.rlwy.net:56725/railway")
    print(f"Mode: MIGRATION_MODE=1 (sync driver)")
    print()

    # Ensure we're in the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    # Create Alembic config
    alembic_cfg = Config("alembic.ini")

    # Override database URL with Railway public URL
    railway_url = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"
    alembic_cfg.set_main_option("sqlalchemy.url", railway_url)

    print("Checking current migration status...")
    try:
        command.current(alembic_cfg, verbose=True)
    except Exception as e:
        print(f"Note: {e}")

    print()
    print("Running migrations to head...")
    try:
        command.upgrade(alembic_cfg, "head", sql=False)
        print()
        print("=" * 60)
        print("SUCCESS: Migrations completed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: Migration failed")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
