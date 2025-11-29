"""
Audit Production Database Schema

Checks which tables/columns from recent migrations exist in production.
"""
from sqlalchemy import create_engine, text

PROD_DB_URL = "postgresql://postgres:xvymYweUKKCmCpHoFptrmBFOiqFjzLhz@maglev.proxy.rlwy.net:27062/railway"

def check_table_exists(conn, table_name):
    """Check if table exists"""
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()

def check_column_exists(conn, table_name, column_name):
    """Check if column exists in table"""
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        )
    """))
    return result.scalar()

def main():
    print("=" * 70)
    print("Production Database Schema Audit")
    print("=" * 70)

    engine = create_engine(PROD_DB_URL)

    with engine.connect() as conn:
        # Get current revision
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_rev = result.scalar()
        print(f"\nCurrent alembic revision: {current_rev}")

        # Check for tables from recent migrations
        checks = {
            "Tables from recent migrations": [
                ("equity_changes", "Equity changes table (a3b4c5d6e7f8)"),
                ("position_realized_events", "Position realized events (2623cfc89fb7)"),
                ("batch_run_tracking", "Batch run tracking (035e1888bea0)"),
                ("spread_factor_definitions", "Spread factors (h1i2j3k4l5m6)"),
                ("position_volatility", "Position volatility (c1d2e3f4g5h6)"),
                ("ai_insights", "AI insights (e65741f182c4)"),
                ("ai_insight_templates", "AI templates (e65741f182c4)"),
            ],
            "Columns from recent migrations": [
                ("portfolios.equity_balance", "Equity balance field"),
                ("portfolio_snapshots.beta_calculated_90d", "Calculated beta"),
                ("portfolio_snapshots.beta_provider_1y", "Provider beta"),
                ("portfolio_snapshots.realized_volatility_21d", "Volatility fields"),
                ("portfolio_snapshots.hhi", "Concentration metrics"),
                ("portfolio_snapshots.target_price_return_eoy", "Target price fields"),
            ],
        }

        print("\n" + "=" * 70)
        print("Schema Checks:")
        print("=" * 70)

        # Check tables
        print("\nTables:")
        for table, desc in checks["Tables from recent migrations"]:
            exists = check_table_exists(conn, table)
            status = "EXISTS" if exists else "MISSING"
            print(f"  [{status}] {table:35s} - {desc}")

        # Check columns
        print("\nColumns:")
        for col_spec, desc in checks["Columns from recent migrations"]:
            table, column = col_spec.split(".")
            if check_table_exists(conn, table):
                exists = check_column_exists(conn, table, column)
                status = "EXISTS" if exists else "MISSING"
                print(f"  [{status}] {col_spec:45s} - {desc}")
            else:
                print(f"  [SKIP]   {col_spec:45s} - {desc} (table missing)")

        print("\n" + "=" * 70)
        print("Recommendation:")
        print("=" * 70)
        print("\nIf most schema elements exist:")
        print("  -> Safe to STAMP database to 792ffb1ab1ad")
        print("\nIf many schema elements are missing:")
        print("  -> Need to run actual migrations (requires Railway CLI)")

if __name__ == "__main__":
    main()
