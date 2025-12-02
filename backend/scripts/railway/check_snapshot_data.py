#!/usr/bin/env python
"""
Check snapshot data for portfolios on Railway.

Usage:
    python scripts/railway/check_snapshot_data.py              # Check all portfolios
    python scripts/railway/check_snapshot_data.py hedge_fund   # Check specific portfolio
    python scripts/railway/check_snapshot_data.py hnw
    python scripts/railway/check_snapshot_data.py individual
"""
import requests
import sys

# Railway production API
BASE_URL = "https://sigmasight-be-production.up.railway.app/api/v1"
PASSWORD = "demo12345"

# Portfolio configs - each portfolio has a different owner
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


def login(email: str) -> str:
    """Login and get access token."""
    print(f"Logging in as {email}...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    token = resp.json().get("access_token")
    print("[OK] Login successful\n")
    return token


def check_volatility(token: str, portfolio_id: str):
    """Check volatility endpoint."""
    print("=" * 60)
    print("VOLATILITY ANALYTICS")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/volatility",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return False

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        vol_data = data['data']
        print(f"Realized Vol 21d: {vol_data.get('realized_volatility_21d')}")
        print(f"Realized Vol 63d: {vol_data.get('realized_volatility_63d')}")
        print(f"Expected Vol 21d: {vol_data.get('expected_volatility_21d')}")
        print(f"Volatility Trend: {vol_data.get('volatility_trend')}")
        return True
    else:
        print("NO VOLATILITY DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")
        return False


def check_beta_90d(token: str, portfolio_id: str):
    """Check 90-day calculated beta endpoint."""
    print("\n" + "=" * 60)
    print("BETA CALCULATED 90D")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/beta-calculated-90d",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return False

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        beta_data = data['data']
        print(f"Beta: {beta_data.get('beta')}")
        print(f"R-Squared: {beta_data.get('r_squared')}")
        return True
    else:
        print("NO BETA DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")
        return False


def check_beta_1y(token: str, portfolio_id: str):
    """Check 1-year provider beta endpoint."""
    print("\n" + "=" * 60)
    print("BETA PROVIDER 1Y")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/beta-provider-1y",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return False

    data = resp.json()
    print(f"Available: {data.get('available')}")
    print(f"Calculation Date: {data.get('calculation_date')}")

    if data.get('data'):
        beta_data = data['data']
        print(f"Beta: {beta_data.get('beta')}")
        return True
    else:
        print("NO BETA DATA")
        if data.get('metadata'):
            print(f"Metadata: {data['metadata']}")
        return False


def check_stress_test(token: str, portfolio_id: str):
    """Check stress test endpoint."""
    print("\n" + "=" * 60)
    print("STRESS TEST")
    print("=" * 60)

    resp = requests.get(
        f"{BASE_URL}/analytics/portfolio/{portfolio_id}/stress-test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(resp.text)
        return False

    data = resp.json()
    print(f"Available: {data.get('available', 'N/A')}")

    if data.get('scenarios'):
        print(f"Scenarios count: {len(data['scenarios'])}")
        # Show first scenario as example
        if data['scenarios']:
            first = data['scenarios'][0]
            print(f"Example scenario: {first.get('scenario_name')} -> Direct P&L: ${first.get('direct_pnl', 0):,.0f}")
        return True
    else:
        print("NO STRESS TEST DATA")
        return False


def check_portfolio(portfolio_key: str):
    """Check all endpoints for a specific portfolio."""
    if portfolio_key not in PORTFOLIOS:
        print(f"Unknown portfolio: {portfolio_key}")
        print(f"Available: {', '.join(PORTFOLIOS.keys())}")
        sys.exit(1)

    config = PORTFOLIOS[portfolio_key]

    print("=" * 60)
    print(f"CHECKING: {config['name']}")
    print(f"ID: {config['id']}")
    print(f"Owner: {config['email']}")
    print("=" * 60 + "\n")

    token = login(config['email'])
    portfolio_id = config['id']

    results = {
        'volatility': check_volatility(token, portfolio_id),
        'beta_90d': check_beta_90d(token, portfolio_id),
        'beta_1y': check_beta_1y(token, portfolio_id),
        'stress_test': check_stress_test(token, portfolio_id),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for endpoint, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {endpoint}")

    return results


def main():
    # Check command line arguments
    if len(sys.argv) > 1:
        portfolio_key = sys.argv[1].lower()
        check_portfolio(portfolio_key)
    else:
        # Check all portfolios
        print("Checking all portfolios...\n")
        all_results = {}
        for portfolio_key in PORTFOLIOS.keys():
            print("\n" + "#" * 70)
            all_results[portfolio_key] = check_portfolio(portfolio_key)
            print("#" * 70 + "\n")

        # Final summary
        print("\n" + "=" * 70)
        print("FINAL SUMMARY - ALL PORTFOLIOS")
        print("=" * 70)
        for portfolio_key, results in all_results.items():
            success_count = sum(1 for v in results.values() if v)
            total = len(results)
            status = "[OK]" if success_count == total else "[WARN]"
            print(f"  {status} {portfolio_key}: {success_count}/{total} endpoints OK")


if __name__ == "__main__":
    main()
