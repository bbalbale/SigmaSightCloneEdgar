#!/usr/bin/env python3
"""Test batch processing on Railway after UUID fix"""
import requests
import time
import json

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

def login() -> str:
    """Login with demo_hnw user"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def trigger_batch(token: str):
    """Trigger batch processing"""
    print("\n🚀 Triggering batch processing on Railway...")
    response = requests.post(
        f"{RAILWAY_URL}/admin/batch/run",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Batch triggered: {json.dumps(result, indent=2)}")
        return True
    else:
        print(f"❌ Batch trigger failed: {response.status_code}")
        print(response.text)
        return False

def check_batch_status(token: str):
    """Check current batch status"""
    print("\n📊 Checking batch status...")
    response = requests.get(
        f"{RAILWAY_URL}/admin/batch/run/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"❌ Status check failed: {response.status_code}")
        print(response.text)
        return None

def get_positions(token: str, portfolio_id: str):
    """Get positions for a portfolio"""
    response = requests.get(
        f"{RAILWAY_URL}/data/positions/details?portfolio_id={portfolio_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json().get("positions", [])
    return []

if __name__ == "__main__":
    print("=" * 60)
    print("Railway Batch Processing Test - UUID Fix Verification")
    print("=" * 60)

    # Login
    token = login()
    if not token:
        exit(1)

    # Trigger batch
    if not trigger_batch(token):
        exit(1)

    # Wait for batch to process
    print("\n⏳ Waiting 5 seconds for batch to process...")
    time.sleep(5)

    # Check status
    status = check_batch_status(token)

    # Verify positions were found for all portfolios
    print("\n" + "=" * 60)
    print("Verifying Position Counts After Batch")
    print("=" * 60)

    # Login as each demo user to get their portfolios
    users = [
        ("demo_individual@sigmasight.com", "Demo Individual Investor"),
        ("demo_hnw@sigmasight.com", "Demo High Net Worth Investor"),
        ("demo_hedgefundstyle@sigmasight.com", "Demo Hedge Fund Style Investor")
    ]

    for email, name in users:
        # Login
        response = requests.post(
            f"{RAILWAY_URL}/auth/login",
            json={"email": email, "password": "demo12345"}
        )
        if response.status_code == 200:
            user_token = response.json()["access_token"]

            # Get portfolios
            portfolios_response = requests.get(
                f"{RAILWAY_URL}/data/portfolios",
                headers={"Authorization": f"Bearer {user_token}"}
            )

            if portfolios_response.status_code == 200:
                portfolios = portfolios_response.json()
                for portfolio in portfolios:
                    portfolio_id = portfolio["id"]
                    portfolio_name = portfolio["name"]
                    positions = get_positions(user_token, portfolio_id)
                    print(f"{portfolio_name}: {len(positions)} positions")

    print("\n" + "=" * 60)
    print("✅ Batch test complete!")
    print("=" * 60)
