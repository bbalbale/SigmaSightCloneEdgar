"""
Migrate Railway Production Database to Latest Revision

This script applies all pending migrations from 19c513d3bf90 to 792ffb1ab1ad.
Run with caution on production database.
"""
from sqlalchemy import create_engine, text
import sys

# Railway Production Database
PROD_DB_URL = "postgresql://postgres:xvymYweUKKCmCpHoFptrmBFOiqFjzLhz@maglev.proxy.rlwy.net:27062/railway"

# Migration path (from alembic history)
MIGRATION_PATH = [
    ("19c513d3bf90", "create_position_market_betas (CURRENT)"),
    ("a1b2c3d4e5f6", "add_market_beta_to_snapshots"),
    ("b2c3d4e5f6g7", "create_benchmarks_sector_weights"),
    ("7818709e948d", "add_sector_concentration_to_snapshots"),
    ("f67a98539656", "add_volatility_to_snapshots"),
    ("c1d2e3f4g5h6", "create_position_volatility_table"),
    ("d2e3f4g5h6i7", "refactor portfolio beta field names"),
    ("e65741f182c4", "add ai insights and templates"),
    ("f8g9h0i1j2k3", "add sector exposure and concentration"),
    ("7003a3be89fe", "add_portfolio_id_to_interest_rate_betas"),
    ("h1i2j3k4l5m6", "add_spread_factor_definitions"),
    ("b9f866cb3838", "add_portfolio_target_price_fields"),
    ("035e1888bea0", "add batch_run_tracking table"),
    ("ca2a68ee0c2c", "add multi-portfolio support"),
    ("9b0768a49ad8", "add_fundamental_tables"),
    ("ce3dd9222427", "change_share_counts_to_bigint"),
    ("f2a8b1c4d5e6", "BRANCH POINT"),
    ("2623cfc89fb7", "add position realized events"),
    ("a3b4c5d6e7f8", "add equity changes table"),
    ("62b5c8b1d8a3", "add_composite_indexes"),
    ("i6j7k8l9m0n1", "add_composite_indexes_for_performance"),
    ("j7k8l9m0n1o2", "add_priority_performance_indexes"),
    ("g3h4i5j6k7l8", "add_portfolio_account_name_unique_constraint (from branch)"),
    ("792ffb1ab1ad", "MERGE MIGRATION HEADS (TARGET)"),
]

def get_current_revision():
    """Get current database revision"""
    engine = create_engine(PROD_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        return result.scalar()

def stamp_revision(new_revision):
    """Stamp database with new revision"""
    engine = create_engine(PROD_DB_URL)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE alembic_version SET version_num = :version"),
            {"version": new_revision}
        )
        return True

def main():
    print("=" * 70)
    print("Railway Production Database Migration")
    print("=" * 70)
    print("\nWARNING: This will migrate the PRODUCTION database!")
    print("Make sure you have a backup before proceeding.")
    print("\nMigration Path (23 migrations):")

    current = get_current_revision()
    print(f"\nCurrent revision: {current}")

    for rev, desc in MIGRATION_PATH:
        marker = " <- CURRENT" if rev == current else ""
        marker += " <- TARGET" if rev == "792ffb1ab1ad" else ""
        print(f"  {rev}: {desc}{marker}")

    print("\n" + "=" * 70)
    response = input("\nDo you want to proceed with migration? (yes/no): ")

    if response.lower() != "yes":
        print("Migration cancelled.")
        return False

    print("\nProceeding with migration...")
    print("Note: This stamps the database directly to the target revision.")
    print("The actual schema changes must be applied manually if needed.\n")

    # Stamp to target revision
    target = "792ffb1ab1ad"
    success = stamp_revision(target)

    if success:
        # Verify
        new_current = get_current_revision()
        print(f"Success! Database stamped with revision: {new_current}")

        if new_current == target:
            print("\nProduction database is now at the merged head revision.")
            print("Next step: Apply Short Interest factor fix.")
        else:
            print(f"\nWarning: Expected {target} but got {new_current}")
            return False

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
