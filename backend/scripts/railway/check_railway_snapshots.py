#!/usr/bin/env python
"""
Check snapshot data directly in Railway database.

Usage:
    railway run python scripts/railway/check_railway_snapshots.py
"""
import os
import sys
from datetime import date, timedelta

# Portfolio IDs
PORTFOLIOS = {
    "hedge_fund": {
        "id": "fcd71196-e93e-f000-5a74-31a9eead3118",
        "name": "Demo Hedge Fund Style Investor Portfolio",
    },
    "hnw": {
        "id": "e23ab931-a033-edfe-ed4f-9d02474780b4",
        "name": "Demo High Net Worth Investor Portfolio",
    },
    "individual": {
        "id": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe",
        "name": "Demo Individual Investor Portfolio",
    },
}


def main():
    # Try to get database URL
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_DATABASE_URL')

    if not db_url:
        print("ERROR: No DATABASE_URL or RAILWAY_DATABASE_URL found")
        print("Run with: railway run python scripts/railway/check_railway_snapshots.py")
        sys.exit(1)

    # Convert async URL to sync if needed
    if 'postgresql+asyncpg://' in db_url:
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    print(f"Connecting to database...")
    print(f"URL prefix: {db_url[:50]}...")

    try:
        import psycopg2
    except ImportError:
        print("Installing psycopg2-binary...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
        import psycopg2

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check recent dates
    today = date.today()
    check_dates = [today - timedelta(days=i) for i in range(7)]

    print(f"\nChecking snapshots for dates: {[str(d) for d in check_dates]}")
    print("=" * 80)

    for portfolio_key, config in PORTFOLIOS.items():
        portfolio_id = config['id']
        portfolio_name = config['name']

        print(f"\n{'=' * 80}")
        print(f"PORTFOLIO: {portfolio_name}")
        print(f"ID: {portfolio_id}")
        print("=" * 80)

        # Check if any snapshots exist for this portfolio
        cur.execute("""
            SELECT COUNT(*), MIN(snapshot_date), MAX(snapshot_date)
            FROM portfolio_snapshots
            WHERE portfolio_id = %s
        """, (portfolio_id,))
        count, min_date, max_date = cur.fetchone()
        print(f"\nTotal snapshots: {count}")
        print(f"Date range: {min_date} to {max_date}")

        # Check recent snapshots with volatility data
        print(f"\nRecent snapshots (last 10):")
        print("-" * 80)

        cur.execute("""
            SELECT
                snapshot_date,
                realized_volatility_21d,
                realized_volatility_63d,
                expected_volatility_21d,
                volatility_trend,
                beta_calculated_90d,
                beta_calculated_90d_r_squared,
                beta_provider_1y
            FROM portfolio_snapshots
            WHERE portfolio_id = %s
            ORDER BY snapshot_date DESC
            LIMIT 10
        """, (portfolio_id,))

        rows = cur.fetchall()
        if not rows:
            print("  NO SNAPSHOTS FOUND!")
        else:
            for row in rows:
                snap_date, vol_21d, vol_63d, exp_vol, trend, beta_90d, r2, beta_1y = row
                print(f"\n  Date: {snap_date}")
                print(f"    Volatility 21d: {vol_21d}")
                print(f"    Volatility 63d: {vol_63d}")
                print(f"    Expected Vol:   {exp_vol}")
                print(f"    Vol Trend:      {trend}")
                print(f"    Beta 90d:       {beta_90d}")
                print(f"    Beta R-squared: {r2}")
                print(f"    Beta 1Y:        {beta_1y}")

        # Check specific dates we're interested in
        print(f"\n\nSnapshot existence by date:")
        for check_date in check_dates:
            cur.execute("""
                SELECT
                    snapshot_date,
                    realized_volatility_21d IS NOT NULL as has_vol,
                    beta_calculated_90d IS NOT NULL as has_beta_90d,
                    beta_provider_1y IS NOT NULL as has_beta_1y
                FROM portfolio_snapshots
                WHERE portfolio_id = %s AND snapshot_date = %s
            """, (portfolio_id, check_date))

            result = cur.fetchone()
            if result:
                _, has_vol, has_beta_90d, has_beta_1y = result
                status = []
                if has_vol:
                    status.append("vol")
                if has_beta_90d:
                    status.append("beta90d")
                if has_beta_1y:
                    status.append("beta1y")
                status_str = ", ".join(status) if status else "NO DATA"
                print(f"  {check_date}: EXISTS [{status_str}]")
            else:
                print(f"  {check_date}: MISSING")

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
