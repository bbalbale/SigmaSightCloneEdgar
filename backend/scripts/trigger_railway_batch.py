#!/usr/bin/env python3
"""
Trigger batch processing on Railway via API
"""
import requests
import time

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"


def login():
    """Login and get token"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None


def trigger_daily_batch(token: str, portfolio_id: str = None):
    """Trigger full daily batch processing"""
    print(f"\n🚀 Triggering Daily Batch Processing on Railway...")
    print(f"=" * 80)

    params = {}
    if portfolio_id:
        params["portfolio_id"] = portfolio_id
        print(f"   Target: Portfolio {portfolio_id}")
    else:
        print(f"   Target: ALL portfolios")

    response = requests.post(
        f"{RAILWAY_URL}/admin/batch/trigger/daily",
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Batch processing triggered successfully!")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Triggered by: {result.get('triggered_by')}")
        return True
    else:
        print(f"\n❌ Failed to trigger batch: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def trigger_market_data(token: str):
    """Trigger market data sync"""
    print(f"\n📊 Triggering Market Data Sync on Railway...")
    print(f"=" * 80)

    response = requests.post(
        f"{RAILWAY_URL}/admin/batch/trigger/market-data",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Market data sync triggered successfully!")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        return True
    else:
        print(f"\n❌ Failed to trigger market data: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def get_portfolio_ids(token: str):
    """Get all portfolio IDs"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        portfolios = response.json()
        return [p["id"] for p in portfolios]
    return []


def trigger_greeks(token: str, portfolio_id: str):
    """Trigger Greeks calculation"""
    print(f"\n📐 Triggering Greeks Calculation...")
    print(f"   Portfolio: {portfolio_id}")

    response = requests.post(
        f"{RAILWAY_URL}/admin/batch/trigger/greeks",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ {result.get('message')}")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return False


def trigger_factors(token: str, portfolio_id: str):
    """Trigger factor analysis"""
    print(f"\n🏭 Triggering Factor Analysis...")
    print(f"   Portfolio: {portfolio_id}")

    response = requests.post(
        f"{RAILWAY_URL}/admin/batch/trigger/factors",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ {result.get('message')}")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return False


def check_data_quality(token: str, portfolio_id: str):
    """Check data quality after batch processing"""
    print(f"\n🔍 Checking Data Quality...")

    response = requests.get(
        f"{RAILWAY_URL}/data/portfolio/{portfolio_id}/data-quality",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        quality = response.json()
        summary = quality.get("summary", {})

        print(f"   Total Positions: {summary.get('total_positions', 0)}")
        print(f"   With Greeks: {summary.get('positions_with_greeks', 0)}")
        print(f"   With Factors: {summary.get('positions_with_factors', 0)}")
        print(f"   Completeness: {summary.get('data_completeness_percent', 0):.1f}%")

        return summary
    else:
        print(f"   ❌ Failed to get data quality: {response.status_code}")
        return None


def main():
    """Main execution"""
    print("🚀 Railway Batch Processing Trigger")
    print(f"Backend: {RAILWAY_URL}\n")

    # Login
    print("🔐 Logging in...")
    token = login()
    if not token:
        return

    print("✅ Authenticated\n")

    # Option 1: Trigger full daily batch (recommended)
    print("\n" + "=" * 80)
    print("OPTION 1: Full Daily Batch (Market Data + Calculations)")
    print("=" * 80)
    trigger_daily_batch(token)

    # Wait a bit for processing
    print("\n⏱️  Waiting 30 seconds for processing to complete...")
    time.sleep(30)

    # Check results
    print("\n" + "=" * 80)
    print("RESULTS CHECK")
    print("=" * 80)

    portfolio_ids = get_portfolio_ids(token)
    if portfolio_ids:
        for pid in portfolio_ids[:1]:  # Check first portfolio
            check_data_quality(token, pid)

    print("\n" + "=" * 80)
    print("✅ Batch processing triggered!")
    print("=" * 80)
    print("\nNote: Processing runs in background. Check Railway logs for progress.")
    print("      Run this script again in 5 minutes to verify data populated.")


if __name__ == "__main__":
    main()
