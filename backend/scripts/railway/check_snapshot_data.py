#!/usr/bin/env python
"""
Check snapshot data for Hedge Fund portfolio on Railway.

Usage:
    python scripts/railway/check_snapshot_data.py
"""
import requests
import sys

# Railway production API
BASE_URL = "https://sigmasight-be-production.up.railway.app/api/v1"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# Hedge Fund portfolio ID
HEDGE_FUND_PORTFOLIO_ID = "fcd71196-e93e-f000-5a74-31a9eead3118"


def login():
    """Login and get access token."""
    print("Logging in...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    token = resp.json().get("access_token")
    print("✓ Login successful\n")
    return token


def check_volatility(token: str):
    """Check volatility endpoint."""
    print("=" * 60)
    print("VOLATILITY ANALYTICS")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{HEDGE_FUND_PORTFOLIO_ID}/volatility",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        vol_data = data['data']
        print(f"Realized Vol 21d: {vol_data.get('realized_volatility_21d')}")
        print(f"Realized Vol 63d: {vol_data.get('realized_volatility_63d')}")
        print(f"Expected Vol 21d: {vol_data.get('expected_volatility_21d')}")
        print(f"Volatility Trend: {vol_data.get('volatility_trend')}")
    else:
        print("NO VOLATILITY DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")


def check_beta_90d(token: str):
    """Check 90-day calculated beta endpoint."""
    print("\n" + "=" * 60)
    print("BETA CALCULATED 90D")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{HEDGE_FUND_PORTFOLIO_ID}/beta-calculated-90d",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        beta_data = data['data']
        print(f"Beta: {beta_data.get('beta')}")
        print(f"R-Squared: {beta_data.get('r_squared')}")
    else:
        print("NO BETA DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")


def check_beta_1y(token: str):
    """Check 1-year provider beta endpoint."""
    print("\n" + "=" * 60)
    print("BETA PROVIDER 1Y")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{HEDGE_FUND_PORTFOLIO_ID}/beta-provider-1y",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        beta_data = data['data']
        print(f"Beta: {beta_data.get('beta')}")
    else:
        print("NO BETA DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")


def check_stress_test(token: str):
    """Check stress test endpoint."""
    print("\n" + "=" * 60)
    print("STRESS TEST")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{HEDGE_FUND_PORTFOLIO_ID}/stress-test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    print(f"Available: {data.get('available', 'N/A')}")

    if data.get('scenarios'):
        print(f"Scenarios count: {len(data['scenarios'])}")
        # Show first scenario as example
        if data['scenarios']:
            first = data['scenarios'][0]
            print(f"Example scenario: {first.get('scenario_name')} -> Direct P&L: ${first.get('direct_pnl', 0):,.0f}")
    else:
        print("NO STRESS TEST DATA")


def main():
    print("=" * 60)
    print(f"CHECKING HEDGE FUND PORTFOLIO")
    print(f"ID: {HEDGE_FUND_PORTFOLIO_ID}")
    print("=" * 60 + "\n")

    token = login()

    check_volatility(token)
    check_beta_90d(token)
    check_beta_1y(token)
    check_stress_test(token)

    print("\n" + "=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
