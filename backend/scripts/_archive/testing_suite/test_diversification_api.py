#!/usr/bin/env python
"""Test script for Diversification Score API endpoint"""

import requests
import json
import sys

# Login and get token
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    sys.exit(1)

token = login_response.json().get("access_token")
if not token:
    print("❌ No token received")
    sys.exit(1)

print(f"✅ Got token: {token[:50]}...")

# Get user info to confirm auth works
headers = {"Authorization": f"Bearer {token}"}
me_response = requests.get("http://localhost:8000/api/v1/auth/me", headers=headers)

if me_response.status_code != 200:
    print(f"❌ Auth verification failed: {me_response.status_code}")
    print(me_response.text)
else:
    user_data = me_response.json()
    portfolio_id = user_data.get("portfolio_id")
    print(f"✅ Auth works - Portfolio ID: {portfolio_id}")

    # Test diversification score endpoint
    print("\n📊 Testing Diversification Score API...")
    
    url = f"http://localhost:8000/api/v1/analytics/portfolio/{portfolio_id}/diversification-score"
    params = {"lookback_days": 90, "min_overlap": 30}
    
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("available"):
            print(f"✅ SUCCESS: Portfolio correlation = {data.get('portfolio_correlation')}")
        else:
            print(f"⚠️ No data available: {data.get('metadata', {}).get('reason')}")
    else:
        print(f"❌ Request failed")