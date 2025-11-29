"""
Railway Database Migration Upgrade Script

Checks current alembic revision and upgrades to head.
"""
import os
from sqlalchemy import create_engine, text

# Railway database connection
RAILWAY_DB_URL = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

def check_current_revision():
    """Check current alembic revision in Railway database"""
    engine = create_engine(RAILWAY_DB_URL)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"Current Railway database revision: {version}")
        return version

def main():
    print("=" * 60)
    print("Railway Database Migration Status")
    print("=" * 60)

    current = check_current_revision()

    print(f"\nCurrent revision: {current}")
    print(f"Target revision: 792ffb1ab1ad (merge migration heads)")

    if current == "792ffb1ab1ad":
        print("\n✅ Railway database is already at the latest revision!")
    else:
        print(f"\n⚠️  Railway database needs upgrade from {current} to 792ffb1ab1ad")
        print("\nTo upgrade, run:")
        print("  railway run alembic upgrade head")

if __name__ == "__main__":
    main()
