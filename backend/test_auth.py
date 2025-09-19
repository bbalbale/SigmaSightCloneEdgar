#!/usr/bin/env python
"""Reliable authentication test for SigmaSight API"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": EMAIL, "password": PASSWORD}
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

# Verify authentication
headers = {"Authorization": f"Bearer {token}"}
me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

if me_response.status_code != 200:
    print(f"❌ Auth verification failed: {me_response.status_code}")
    print(me_response.text)
    sys.exit(1)

user_data = me_response.json()
portfolio_id = user_data.get("portfolio_id")
print(f"✅ Auth works - Portfolio ID: {portfolio_id}")
print(f"✅ User: {user_data.get('email')}")

# Export for use in bash if needed
print(f"\n# Export these for bash testing:")
print(f"export TOKEN='{token}'")
print(f"export PORTFOLIO_ID='{portfolio_id}'")