"""
Upgrade Railway database to latest alembic revision.

Uses sync SQLAlchemy driver for Railway compatibility.
"""
import sys
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

# Railway database connection (sync driver)
RAILWAY_DB_URL = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

def get_current_revision():
    """Get current alembic revision"""
    engine = create_engine(RAILWAY_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        return result.scalar()

def upgrade_database():
    """Upgrade Railway database using alembic programmatically"""
    # Create alembic config
    alembic_cfg = Config("alembic.ini")

    # Override database URL to use sync driver
    alembic_cfg.set_main_option("sqlalchemy.url", RAILWAY_DB_URL)

    print("=" * 60)
    print("Railway Database Migration Upgrade")
    print("=" * 60)

    current = get_current_revision()
    print(f"\nCurrent revision: {current}")
    print(f"Target revision: head (792ffb1ab1ad)")
    print("\nUpgrading...")

    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")

        new_revision = get_current_revision()
        print(f"\n✓ Success! Database upgraded to: {new_revision}")

        if new_revision == "792ffb1ab1ad":
            print("✓ Railway database is now at the latest merged revision!")

        return True

    except Exception as e:
        print(f"\n✗ Error during upgrade: {e}")
        return False

if __name__ == "__main__":
    success = upgrade_database()
    sys.exit(0 if success else 1)
