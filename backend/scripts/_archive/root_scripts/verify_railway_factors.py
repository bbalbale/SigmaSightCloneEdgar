"""Verify Railway database factor configuration"""
from sqlalchemy import create_engine, text

RAILWAY_DB_URL = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

def main():
    engine = create_engine(RAILWAY_DB_URL)

    print("=" * 60)
    print("Railway Database Factor Configuration")
    print("=" * 60)

    with engine.connect() as conn:
        # Check alembic version
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"\nAlembic revision: {version}")

        # Check active style/macro factors
        result = conn.execute(text("""
            SELECT name, factor_type, is_active
            FROM factor_definitions
            WHERE factor_type IN ('style', 'macro')
            ORDER BY is_active DESC, display_order, name
        """))

        rows = result.fetchall()
        active_count = sum(1 for r in rows if r[2])

        print(f"\nStyle/Macro Factors (Total: {len(rows)}, Active: {active_count}):")
        for name, ftype, is_active in rows:
            status = "ACTIVE" if is_active else "inactive"
            print(f"  - {name:25s} ({ftype:6s}): {status}")

        # Check if we have factor exposures
        result = conn.execute(text("""
            SELECT COUNT(DISTINCT portfolio_id) as portfolios,
                   COUNT(*) as total_exposures,
                   MAX(calculation_date) as latest_date
            FROM factor_exposures
        """))

        row = result.fetchone()
        print(f"\nFactor Exposures Data:")
        print(f"  Portfolios: {row[0]}")
        print(f"  Total exposures: {row[1]}")
        print(f"  Latest calculation: {row[2]}")

        print(f"\nExpected: 9 active style/macro factors")
        print(f"Actual: {active_count} active factors")

        if active_count == 9:
            print("\nSuccess! Railway database is correctly configured.")
        else:
            print(f"\nWarning: Expected 9 active factors but found {active_count}")

if __name__ == "__main__":
    main()
