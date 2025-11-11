"""
Check Railway Production Database Status

Checks current alembic revision and database state.
"""
from sqlalchemy import create_engine, text

# Railway Production Database
PROD_DB_URL = "postgresql://postgres:xvymYweUKKCmCpHoFptrmBFOiqFjzLhz@maglev.proxy.rlwy.net:27062/railway"

def main():
    print("=" * 70)
    print("Railway Production Database Status Check")
    print("=" * 70)

    engine = create_engine(PROD_DB_URL)

    with engine.connect() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'alembic_version'
            )
        """))
        has_alembic = result.scalar()

        if has_alembic:
            # Get current revision
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"\nCurrent alembic revision: {version}")
        else:
            print("\nNo alembic_version table found - database may need initialization")
            version = None

        # Check factor_definitions table
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'factor_definitions'
            )
        """))
        has_factors = result.scalar()

        if has_factors:
            # Count factors
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_active = TRUE AND factor_type IN ('style', 'macro')) as active_style_macro
                FROM factor_definitions
            """))
            row = result.fetchone()
            print(f"\nFactor Definitions:")
            print(f"  Total factors: {row[0]}")
            print(f"  Active style/macro: {row[1]}")

            # Check Short Interest status
            result = conn.execute(text("""
                SELECT name, is_active, factor_type
                FROM factor_definitions
                WHERE name = 'Short Interest'
            """))
            si_row = result.fetchone()
            if si_row:
                print(f"\n  Short Interest: is_active={si_row[1]}, factor_type={si_row[2]}")
        else:
            print("\nNo factor_definitions table found")

        # Check portfolios
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'portfolios'
            )
        """))
        has_portfolios = result.scalar()

        if has_portfolios:
            result = conn.execute(text("SELECT COUNT(*) FROM portfolios"))
            portfolio_count = result.scalar()
            print(f"\nPortfolios: {portfolio_count}")

            # Check positions
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'positions'
                )
            """))
            has_positions = result.scalar()

            if has_positions:
                result = conn.execute(text("SELECT COUNT(*) FROM positions"))
                position_count = result.scalar()
                print(f"Positions: {position_count}")

        # Summary
        print("\n" + "=" * 70)
        print("Summary:")
        print("=" * 70)
        if version:
            print(f"Current revision: {version}")
            print(f"Target revision: 792ffb1ab1ad (merged head)")
            print(f"\nDatabase appears to be initialized.")
            if version != "792ffb1ab1ad":
                print(f"Migration needed: {version} -> 792ffb1ab1ad")
        else:
            print("Database needs initialization or migration")

if __name__ == "__main__":
    main()
