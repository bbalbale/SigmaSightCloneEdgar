#!/usr/bin/env python3
"""Test API endpoints to find 500 errors"""
import requests
import sys

BASE_URL = "https://sigmasight-be-production.up.railway.app"
PORTFOLIO_ID = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"

# Login
print("🔐 Authenticating...")
resp = requests.post(f"{BASE_URL}/api/v1/auth/login",
                     json={"email": "demo_individual@sigmasight.com", "password": "demo12345"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Authenticated\n")

# Test endpoints
endpoints_to_test = [
    ("Data - Portfolio Complete", f"/api/v1/data/portfolio/{PORTFOLIO_ID}/complete"),
    ("Data - Positions Details", f"/api/v1/data/positions/details?portfolio_id={PORTFOLIO_ID}"),
    ("Analytics - Overview", f"/api/v1/analytics/{PORTFOLIO_ID}/overview"),
    ("Analytics - Diversification", f"/api/v1/analytics/{PORTFOLIO_ID}/diversification-score"),
    ("Analytics - Factor Exposures", f"/api/v1/analytics/{PORTFOLIO_ID}/factor-exposures"),
    ("Analytics - Correlation Matrix", f"/api/v1/analytics/{PORTFOLIO_ID}/correlation-matrix"),
]

print("=" * 80)
print("TESTING API ENDPOINTS")
print("=" * 80)

errors_found = []

for name, endpoint in endpoints_to_test:
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        status = resp.status_code

        if status == 200:
            print(f"✅ {name}")
            print(f"   Status: {status}")
        elif status == 404:
            print(f"⚠️  {name}")
            print(f"   Status: 404 Not Found")
        elif status == 500:
            print(f"❌ {name}")
            print(f"   Status: 500 Internal Server Error")
            try:
                error_detail = resp.json()
                print(f"   Error: {error_detail.get('detail', 'No detail')}")
            except:
                print(f"   Raw response: {resp.text[:200]}")
            errors_found.append((name, endpoint))
        else:
            print(f"⚠️  {name}")
            print(f"   Status: {status}")

    except Exception as e:
        print(f"❌ {name}")
        print(f"   Exception: {str(e)}")
        errors_found.append((name, endpoint))

    print()

print("=" * 80)
if errors_found:
    print(f"\n❌ FOUND {len(errors_found)} ENDPOINTS WITH 500 ERRORS:")
    for name, endpoint in errors_found:
        print(f"   - {name}: {endpoint}")
else:
    print("\n✅ NO 500 ERRORS FOUND")
print()
