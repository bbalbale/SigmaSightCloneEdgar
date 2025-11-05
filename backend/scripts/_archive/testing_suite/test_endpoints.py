#!/usr/bin/env python
"""Test Factor Exposures endpoints"""
import requests
import json

BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": EMAIL, "password": PASSWORD}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get portfolio ID
me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
portfolio_id = me_response.json()["portfolio_id"]

print(f"Portfolio ID: {portfolio_id}")
print("\n=== Portfolio Factor Exposures ===")
response = requests.get(
    f"{BASE_URL}/api/v1/analytics/portfolio/{portfolio_id}/factor-exposures",
    headers=headers
)
print(f"Status: {response.status_code}")
data = response.json()
print(json.dumps(data, indent=2)[:500])

print("\n=== Position Factor Exposures ===")
response = requests.get(
    f"{BASE_URL}/api/v1/analytics/portfolio/{portfolio_id}/positions/factor-exposures",
    headers=headers,
    params={"limit": 2}
)
print(f"Status: {response.status_code}")
data = response.json()
if "positions" in data:
    # Truncate for readability
    data["positions"] = data["positions"][:2]
print(json.dumps(data, indent=2))
