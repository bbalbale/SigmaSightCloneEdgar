#!/usr/bin/env python
"""Test the correlation matrix API endpoint with authentication"""

import requests
import json

# Login to get auth token
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "email": "demo_individual@sigmasight.com",
    "password": "demo12345"
}

response = requests.post(login_url, json=login_data)
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get portfolio ID for this user
user_info_url = "http://localhost:8000/api/v1/auth/me"
user_response = requests.get(user_info_url, headers=headers)
portfolio_id = user_response.json()["portfolio_id"]
print(f"Using portfolio ID: {portfolio_id}")

# Get correlation matrix
correlation_url = f"http://localhost:8000/api/v1/analytics/portfolio/{portfolio_id}/correlation-matrix"
params = {
    "lookback_days": 90,
    "min_overlap": 30
}

print("Testing correlation matrix endpoint...")
response = requests.get(correlation_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    if data.get("available") is False:
        print(f"No data available: {data.get('metadata', {}).get('message')}")
    else:
        matrix_data = data.get("data", {})
        matrix = matrix_data.get("matrix", {})
        if matrix:
            symbols = list(matrix.keys())
            print(f"✅ Found correlations for {len(symbols)} symbols")
            print(f"Symbols: {', '.join(symbols[:5])}...")
            print(f"Average correlation: {matrix_data.get('average_correlation')}")
            
            # Show a sample correlation
            if len(symbols) >= 2:
                sym1, sym2 = symbols[0], symbols[1]
                print(f"\nSample: {sym1} vs {sym2} = {matrix[sym1][sym2]:.3f}")
else:
    print(f"Error: {response.text}")