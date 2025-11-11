"""
Run Alembic Migrations on Railway Production Database

This script runs migrations programmatically without requiring alembic.ini,
making it suitable for Railway environments.
"""
from alembic import command
from alembic.config import Config
import sys
import os

# Railway Production Database URL
PROD_DB_URL = "postgresql://postgres:xvymYweUKKCmCpHoFptrmBFOiqFjzLhz@maglev.proxy.rlwy.net:27062/railway"

def run_migrations():
    """Run all pending migrations to head"""
    print("=" * 70)
    print("Railway Production Database Migrations")
    print("=" * 70)

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    alembic_dir = os.path.join(backend_dir, "alembic")

    # Create Alembic config programmatically
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", alembic_dir)
    alembic_cfg.set_main_option("sqlalchemy.url", PROD_DB_URL)

    print(f"\nAlembic directory: {alembic_dir}")
    print(f"Database: maglev.proxy.rlwy.net:27062/railway")

    # Check current revision first
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(PROD_DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar()
            print(f"\nCurrent revision: {current}")
    except Exception as e:
        print(f"\nWarning: Could not check current revision: {e}")
        current = "unknown"

    # Ask for confirmation
    print("\n" + "=" * 70)
    print("WARNING: This will run ALL pending migrations on production!")
    print("=" * 70)
    response = input("\nProceed with migrations? (yes/no): ")

    if response.lower() != "yes":
        print("Migration cancelled.")
        return False

    try:
        print("\nRunning migrations to head...")
        command.upgrade(alembic_cfg, "head")
        print("\n✅ Migrations completed successfully!")

        # Verify new revision
        engine = create_engine(PROD_DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            new_revision = result.scalar()
            print(f"\nNew revision: {new_revision}")

            if new_revision == "792ffb1ab1ad":
                print("✅ Successfully migrated to merged head (792ffb1ab1ad)")
                return True
            else:
                print(f"⚠️ Warning: Expected 792ffb1ab1ad but got {new_revision}")
                return False

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check that the database is accessible")
        print("2. Verify alembic/versions/ directory exists")
        print("3. Check migration file syntax")
        return False

def show_pending_migrations():
    """Show what migrations are pending"""
    print("=" * 70)
    print("Checking Pending Migrations")
    print("=" * 70)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    alembic_dir = os.path.join(backend_dir, "alembic")

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", alembic_dir)
    alembic_cfg.set_main_option("sqlalchemy.url", PROD_DB_URL)

    try:
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine, text

        # Get current revision
        engine = create_engine(PROD_DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar()

        # Get all revisions
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get pending revisions
        head = script.get_current_head()

        print(f"\nCurrent revision: {current}")
        print(f"Target revision: {head}")

        # Get upgrade path
        revisions = list(script.iterate_revisions(current, head))
        revisions.reverse()

        if revisions:
            print(f"\nPending migrations ({len(revisions)}):")
            for i, rev in enumerate(revisions, 1):
                print(f"  {i}. {rev.revision}: {rev.doc}")
        else:
            print("\nNo pending migrations - database is up to date!")

    except Exception as e:
        print(f"\nError checking migrations: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_pending_migrations()
    else:
        success = run_migrations()
        sys.exit(0 if success else 1)
