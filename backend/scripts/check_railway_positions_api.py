#!/usr/bin/env python3
"""Check position counts via Railway API"""
import requests

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
        return None

def get_portfolios(token: str):
    """Get all portfolios"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

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
    token = login()
    if not token:
        exit(1)

    portfolios = get_portfolios(token)
    print(f"\n📊 Railway Database Position Counts:\n")

    for portfolio in portfolios:
        portfolio_id = portfolio["id"]
        portfolio_name = portfolio["name"]
        positions = get_positions(token, portfolio_id)
        print(f"{portfolio_name}: {len(positions)} positions")
