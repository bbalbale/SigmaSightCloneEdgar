"""
Stamp Railway database with latest migration revisions.

Directly updates the alembic_version table to mark migrations as applied.
Use this when migrations are already applied but the version table needs updating.
"""
from sqlalchemy import create_engine, text

# Railway database connection
RAILWAY_DB_URL = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

def get_current_revision():
    """Get current alembic revision"""
    engine = create_engine(RAILWAY_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        return result.scalar()

def stamp_revision(new_revision):
    """Stamp database with new revision"""
    engine = create_engine(RAILWAY_DB_URL)

    with engine.begin() as conn:
        # Update alembic_version table
        conn.execute(
            text("UPDATE alembic_version SET version_num = :version"),
            {"version": new_revision}
        )
        print(f"Database stamped with revision: {new_revision}")

def main():
    print("=" * 60)
    print("Railway Database Migration Stamping")
    print("=" * 60)

    current = get_current_revision()
    print(f"\nCurrent revision: {current}")

    # Target revisions in order
    targets = [
        ("i6j7k8l9m0n1", "add_composite_indexes_for_performance"),
        ("j7k8l9m0n1o2", "add_priority_performance_indexes"),
        ("g3h4i5j6k7l8", "add_portfolio_account_name_unique_constraint"),
        ("792ffb1ab1ad", "merge_migration_heads")
    ]

    print(f"\nMigration path:")
    for rev, desc in targets:
        status = "CURRENT" if rev == current else ""
        print(f"  {rev} - {desc} {status}")

    # Stamp with final merge revision
    final_revision = "792ffb1ab1ad"

    if current == final_revision:
        print(f"\nAlready at target revision: {final_revision}")
        print("No action needed.")
    else:
        print(f"\nStamping database from {current} to {final_revision}...")
        stamp_revision(final_revision)

        # Verify
        new_current = get_current_revision()
        print(f"Verification: New revision is {new_current}")

        if new_current == final_revision:
            print("\nSuccess! Railway database is now at the merged revision.")
        else:
            print(f"\nWarning: Expected {final_revision} but got {new_current}")

if __name__ == "__main__":
    main()
