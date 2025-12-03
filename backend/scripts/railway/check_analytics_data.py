#!/usr/bin/env python
"""
Comprehensive analytics data check for Railway.

Checks both API endpoints and database tables to diagnose data issues.

Usage:
    # API checks only (from anywhere)
    python scripts/railway/check_analytics_data.py api

    # Database checks only (requires railway run)
    railway run python scripts/railway/check_analytics_data.py db

    # Both API and database checks (requires railway run)
    railway run python scripts/railway/check_analytics_data.py all

    # Check specific portfolio
    python scripts/railway/check_analytics_data.py api hedge_fund
"""
import os
import sys
from datetime import date, timedelta

import requests

# Railway production API
BASE_URL = "https://sigmasight-be-production.up.railway.app/api/v1"
PASSWORD = "demo12345"

# Portfolio configs
PORTFOLIOS = {
    "hedge_fund": {
        "id": "fcd71196-e93e-f000-5a74-31a9eead3118",
        "name": "Demo Hedge Fund Style Investor Portfolio",
        "email": "demo_hedgefundstyle@sigmasight.com",
    },
    "hnw": {
        "id": "e23ab931-a033-edfe-ed4f-9d02474780b4",
        "name": "Demo High Net Worth Investor Portfolio",
        "email": "demo_hnw@sigmasight.com",
    },
    "individual": {
        "id": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe",
        "name": "Demo Individual Investor Portfolio",
        "email": "demo_individual@sigmasight.com",
    },
}


# =============================================================================
# API CHECKS
# =============================================================================

def login(email: str) -> str:
    """Login and get access token."""
    print(f"  Logging in as {email}...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  Login failed: {resp.status_code}")
        print(resp.text)
        return None
    return resp.json().get("access_token")


def check_api_volatility(token: str, portfolio_id: str) -> dict:
    """Check volatility endpoint."""
    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/volatility",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"ok": False, "error": resp.status_code}

    data = resp.json()
    vol_data = data.get('data', {})
    return {
        "ok": data.get('available', False),
        "date": data.get('calculation_date'),
        "vol_21d": vol_data.get('realized_volatility_21d'),
        "vol_63d": vol_data.get('realized_volatility_63d'),
        "expected": vol_data.get('expected_volatility_21d'),
        "trend": vol_data.get('volatility_trend'),
    }


def check_api_beta_90d(token: str, portfolio_id: str) -> dict:
    """Check 90-day calculated beta endpoint."""
    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/beta-calculated-90d",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"ok": False, "error": resp.status_code}

    data = resp.json()
    beta_data = data.get('data', {})
    return {
        "ok": data.get('available', False),
        "date": data.get('calculation_date'),
        "beta": beta_data.get('beta_calculated_90d'),
        "r_squared": beta_data.get('beta_calculated_90d_r_squared'),
        "observations": beta_data.get('beta_calculated_90d_observations'),
    }


def check_api_beta_1y(token: str, portfolio_id: str) -> dict:
    """Check 1-year provider beta endpoint."""
    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/beta-provider-1y",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"ok": False, "error": resp.status_code}

    data = resp.json()
    beta_data = data.get('data', {})
    return {
        "ok": data.get('available', False),
        "date": data.get('calculation_date'),
        "beta": beta_data.get('beta_provider_1y'),
    }


def check_api_factor_exposures(token: str, portfolio_id: str) -> dict:
    """Check factor exposures endpoint (used by Risk Metrics page)."""
    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/factor-exposures?use_latest_successful=true",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"ok": False, "error": resp.status_code}

    data = resp.json()
    return {
        "ok": data.get('available', False),
        "date": data.get('calculation_date'),
        "factors_count": len(data.get('factors', [])),
        "metadata": data.get('metadata', {}),
    }


def check_api_stress_test(token: str, portfolio_id: str) -> dict:
    """Check stress test endpoint."""
    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/stress-test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"ok": False, "error": resp.status_code}

    data = resp.json()
    # Stress test response has scenarios inside 'data' object
    stress_data = data.get('data', {})
    scenarios = stress_data.get('scenarios', [])
    return {
        "ok": data.get('available', False) and len(scenarios) > 0,
        "scenarios_count": len(scenarios),
        "date": stress_data.get('calculation_date'),
    }


def run_api_checks(portfolio_keys=None):
    """Run all API checks for specified portfolios."""
    print("\n" + "=" * 80)
    print("API ENDPOINT CHECKS")
    print("=" * 80)

    if portfolio_keys is None:
        portfolio_keys = list(PORTFOLIOS.keys())

    for portfolio_key in portfolio_keys:
        if portfolio_key not in PORTFOLIOS:
            print(f"\nUnknown portfolio: {portfolio_key}")
            continue

        config = PORTFOLIOS[portfolio_key]
        print(f"\n{'-' * 80}")
        print(f"PORTFOLIO: {config['name']}")
        print(f"ID: {config['id']}")
        print(f"{'-' * 80}")

        token = login(config['email'])
        if not token:
            print("  [FAIL] Could not login")
            continue

        portfolio_id = config['id']

        # Volatility
        vol = check_api_volatility(token, portfolio_id)
        status = "[OK]" if vol['ok'] else "[FAIL]"
        print(f"\n  {status} Volatility")
        print(f"      Date: {vol.get('date')}")
        if vol['ok']:
            print(f"      21d: {vol.get('vol_21d')}, 63d: {vol.get('vol_63d')}, Expected: {vol.get('expected')}")

        # Beta 90d
        beta90 = check_api_beta_90d(token, portfolio_id)
        status = "[OK]" if beta90['ok'] else "[FAIL]"
        print(f"\n  {status} Beta Calculated 90D")
        print(f"      Date: {beta90.get('date')}")
        if beta90['ok']:
            print(f"      Beta: {beta90.get('beta')}, R2: {beta90.get('r_squared')}")

        # Beta 1Y
        beta1y = check_api_beta_1y(token, portfolio_id)
        status = "[OK]" if beta1y['ok'] else "[FAIL]"
        print(f"\n  {status} Beta Provider 1Y")
        print(f"      Date: {beta1y.get('date')}")
        if beta1y['ok']:
            print(f"      Beta: {beta1y.get('beta')}")

        # Factor Exposures (Risk Metrics page uses this date)
        factors = check_api_factor_exposures(token, portfolio_id)
        status = "[OK]" if factors['ok'] else "[FAIL]"
        print(f"\n  {status} Factor Exposures (Risk Metrics page date)")
        print(f"      Date: {factors.get('date')}")
        if factors['ok']:
            print(f"      Factors: {factors.get('factors_count')}")

        # Stress Test
        stress = check_api_stress_test(token, portfolio_id)
        status = "[OK]" if stress['ok'] else "[FAIL]"
        print(f"\n  {status} Stress Test")
        print(f"      Date: {stress.get('date')}")
        if stress['ok']:
            print(f"      Scenarios: {stress.get('scenarios_count')}")


# =============================================================================
# DATABASE CHECKS
# =============================================================================

def run_db_checks(portfolio_keys=None):
    """Run database checks for specified portfolios."""
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_DATABASE_URL')

    if not db_url:
        print("\n[ERROR] No DATABASE_URL found. Run with: railway run python scripts/railway/check_analytics_data.py db")
        return

    if 'postgresql+asyncpg://' in db_url:
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    print("\n" + "=" * 80)
    print("DATABASE CHECKS")
    print("=" * 80)
    print(f"Connected to: {db_url[:50]}...")

    try:
        import psycopg2
    except ImportError:
        print("Installing psycopg2-binary...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
        import psycopg2

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    today = date.today()
    check_dates = [today - timedelta(days=i) for i in range(7)]

    if portfolio_keys is None:
        portfolio_keys = list(PORTFOLIOS.keys())

    for portfolio_key in portfolio_keys:
        if portfolio_key not in PORTFOLIOS:
            continue

        config = PORTFOLIOS[portfolio_key]
        portfolio_id = config['id']

        print(f"\n{'-' * 80}")
        print(f"PORTFOLIO: {config['name']}")
        print(f"ID: {portfolio_id}")
        print(f"{'-' * 80}")

        # Snapshot summary
        cur.execute("""
            SELECT COUNT(*), MIN(snapshot_date), MAX(snapshot_date)
            FROM portfolio_snapshots
            WHERE portfolio_id = %s
        """, (portfolio_id,))
        count, min_date, max_date = cur.fetchone()
        print(f"\n  Snapshots: {count} total, {min_date} to {max_date}")

        # Recent snapshots with data
        print(f"\n  Recent snapshots (last 5):")
        cur.execute("""
            SELECT
                snapshot_date,
                realized_volatility_21d,
                beta_calculated_90d,
                beta_provider_1y
            FROM portfolio_snapshots
            WHERE portfolio_id = %s
            ORDER BY snapshot_date DESC
            LIMIT 5
        """, (portfolio_id,))

        for row in cur.fetchall():
            snap_date, vol, beta90, beta1y = row
            day_name = snap_date.strftime('%a') if snap_date else '?'
            vol_str = f"{float(vol):.4f}" if vol else "NULL"
            beta90_str = f"{float(beta90):.4f}" if beta90 else "NULL"
            beta1y_str = f"{float(beta1y):.4f}" if beta1y else "NULL"
            print(f"    {snap_date} ({day_name}): vol={vol_str}, beta90={beta90_str}, beta1y={beta1y_str}")

        # Snapshot existence by date
        print(f"\n  Snapshot existence (last 7 days):")
        for check_date in check_dates:
            day_name = check_date.strftime('%a')
            cur.execute("""
                SELECT
                    realized_volatility_21d IS NOT NULL,
                    beta_calculated_90d IS NOT NULL,
                    beta_provider_1y IS NOT NULL
                FROM portfolio_snapshots
                WHERE portfolio_id = %s AND snapshot_date = %s
            """, (portfolio_id, check_date))

            result = cur.fetchone()
            if result:
                has_vol, has_beta90, has_beta1y = result
                fields = []
                if has_vol: fields.append("vol")
                if has_beta90: fields.append("beta90")
                if has_beta1y: fields.append("beta1y")
                status = ", ".join(fields) if fields else "EMPTY"
                print(f"    {check_date} ({day_name}): EXISTS [{status}]")
            else:
                print(f"    {check_date} ({day_name}): MISSING")

        # Factor exposures dates
        print(f"\n  Factor Exposures dates (last 10):")
        cur.execute("""
            SELECT DISTINCT calculation_date
            FROM factor_exposures
            WHERE portfolio_id = %s
            ORDER BY calculation_date DESC
            LIMIT 10
        """, (portfolio_id,))

        for row in cur.fetchall():
            calc_date = row[0]
            day_name = calc_date.strftime('%A') if calc_date else 'Unknown'
            weekend = " [WEEKEND!]" if day_name in ('Saturday', 'Sunday') else ""
            print(f"    {calc_date} ({day_name}){weekend}")

    cur.close()
    conn.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = sys.argv[1:]

    if not args or args[0] in ('-h', '--help', 'help'):
        print(__doc__)
        return

    mode = args[0].lower()
    portfolio_keys = args[1:] if len(args) > 1 else None

    if mode == 'api':
        run_api_checks(portfolio_keys)
    elif mode == 'db':
        run_db_checks(portfolio_keys)
    elif mode == 'all':
        run_api_checks(portfolio_keys)
        run_db_checks(portfolio_keys)
    else:
        # Assume it's a portfolio key
        run_api_checks([mode] + (portfolio_keys or []))

    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
