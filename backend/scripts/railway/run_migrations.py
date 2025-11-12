#!/usr/bin/env python
"""
Run Alembic migrations on Railway database.
This script runs migrations using the Railway DATABASE_URL environment variable.
"""
import os
import sys

def main():
    # Convert asyncpg URL to sync psycopg2 URL BEFORE any imports
    if "DATABASE_URL" in os.environ:
        database_url = os.environ["DATABASE_URL"]
        # Replace postgresql+asyncpg with postgresql for sync driver
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        os.environ["DATABASE_URL"] = sync_url
        print(f"Converted DATABASE_URL to sync driver for migrations")

    # Now import after environment is fixed
    from alembic.config import Config
    from alembic import command

    # Ensure we're in the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    # Create Alembic config
    alembic_cfg = Config("alembic.ini")

    # Override database URL if provided via environment
    if "DATABASE_URL" in os.environ:
        alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    print("Running migrations...")
    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
