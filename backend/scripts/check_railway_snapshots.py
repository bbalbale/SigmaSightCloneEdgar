#!/usr/bin/env python3
"""Check if portfolio snapshots were created correctly on Railway"""
import requests
import json

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

def login(email: str) -> str:
    """Login with user credentials"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": email, "password": "demo12345"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def get_portfolio_snapshots(token: str, portfolio_id: str):
    """Get recent snapshots for a portfolio"""
    # This endpoint may not exist - we'll check
    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/snapshots",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    return None

if __name__ == "__main__":
    print("=" * 70)
    print("Railway Snapshot Verification - Post UUID Fix")
    print("=" * 70)
    print()

    users = [
        ("demo_individual@sigmasight.com", "Individual"),
        ("demo_hnw@sigmasight.com", "High Net Worth"),
        ("demo_hedgefundstyle@sigmasight.com", "Hedge Fund")
    ]

    for email, name in users:
        token = login(email)
        if not token:
            print(f"❌ Failed to login as {name}")
            continue

        # Get portfolios
        portfolios_response = requests.get(
            f"{RAILWAY_URL}/data/portfolios",
            headers={"Authorization": f"Bearer {token}"}
        )

        if portfolios_response.status_code == 200:
            portfolios = portfolios_response.json()
            for portfolio in portfolios:
                portfolio_id = portfolio["id"]
                portfolio_name = portfolio["name"]

                # Try to get snapshots
                snapshots = get_portfolio_snapshots(token, portfolio_id)

                if snapshots is None:
                    print(f"⚠️  {portfolio_name}: Snapshot endpoint not available or error")
                elif isinstance(snapshots, list):
                    if len(snapshots) > 0:
                        latest = snapshots[0]
                        position_count = latest.get("position_count", "N/A")
                        total_value = latest.get("total_market_value", "N/A")
                        date = latest.get("calculation_date", "N/A")
                        print(f"✅ {portfolio_name}:")
                        print(f"   Latest snapshot ({date}): {position_count} positions, ${total_value}")
                    else:
                        print(f"⚠️  {portfolio_name}: No snapshots created yet")
                else:
                    print(f"📊 {portfolio_name}: {json.dumps(snapshots, indent=2)}")

    print()
    print("=" * 70)
