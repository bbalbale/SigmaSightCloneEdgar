#!/usr/bin/env python3
"""
Test historical prices endpoint with different lookback_days values
to confirm date filtering is working correctly.
"""
import requests
from datetime import date, timedelta

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

def login() -> str:
    """Login with demo_hnw user"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_lookback(token: str, lookback_days: int):
    """Test historical prices with specific lookback_days"""
    # Get portfolio
    portfolios = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    if not portfolios:
        print("No portfolios found")
        return

    portfolio_id = portfolios[0]["id"]

    # Get historical prices
    response = requests.get(
        f"{RAILWAY_URL}/data/prices/historical/{portfolio_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": lookback_days}
    )

    if response.status_code == 200:
        data = response.json()
        symbols = data.get("symbols", {})

        # Get date range from a symbol with data
        if symbols:
            # Use AAPL as test symbol (should have most data)
            symbol_data = symbols.get("AAPL", {})
            if symbol_data and symbol_data.get("dates"):
                dates = symbol_data["dates"]
                data_points = len(dates)
                first_date = min(dates)
                last_date = max(dates)

                # Calculate expected start date
                today = date.today()
                expected_start = today - timedelta(days=lookback_days)

                print(f"\n📊 Lookback Days: {lookback_days}")
                print(f"   Expected Start: {expected_start} (calendar days)")
                print(f"   Actual Start:   {first_date}")
                print(f"   Actual End:     {last_date}")
                print(f"   Trading Days:   {data_points}")
                print(f"   Match: {'✅' if str(expected_start) == first_date else '⚠️ Mismatch'}")

                return {
                    "lookback_days": lookback_days,
                    "expected_start": str(expected_start),
                    "actual_start": first_date,
                    "actual_end": last_date,
                    "trading_days": data_points
                }
        else:
            print(f"❌ No symbol data for lookback_days={lookback_days}")
    else:
        print(f"❌ API error: {response.status_code}")

    return None

def main():
    print("🔍 Testing Historical Prices Lookback Date Filtering")
    print("=" * 80)

    # Login
    token = login()
    if not token:
        print("❌ Login failed")
        return

    print("✅ Authenticated\n")

    # Test different lookback values
    test_cases = [30, 60, 90, 120, 150, 180]

    results = []
    for lookback in test_cases:
        result = test_lookback(token, lookback)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print(f"{'Lookback':<12} {'Expected':<12} {'Actual':<12} {'Days':<8} {'Match':<8}")
    print("-" * 60)

    for r in results:
        match = "✅" if r["expected_start"] == r["actual_start"] else "⚠️"
        print(f"{r['lookback_days']:<12} {r['expected_start']:<12} {r['actual_start']:<12} {r['trading_days']:<8} {match:<8}")

    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()
