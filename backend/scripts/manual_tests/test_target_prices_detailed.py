#!/usr/bin/env python
"""Detailed test for Target Prices API with error debugging"""

import requests
import json
import sys
import traceback

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

def authenticate():
    """Get authentication token and portfolio ID"""
    print("🔐 Authenticating...")
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": EMAIL, "password": PASSWORD}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        sys.exit(1)

    token = login_response.json().get("access_token")
    
    # Get user info including portfolio ID
    headers = {"Authorization": f"Bearer {token}"}
    me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    
    if me_response.status_code != 200:
        print(f"❌ Auth verification failed: {me_response.status_code}")
        sys.exit(1)
    
    user_data = me_response.json()
    portfolio_id = user_data.get("portfolio_id")
    user_id = user_data.get("user_id")
    
    print(f"   ✅ User ID: {user_id}")
    print(f"   ✅ Portfolio ID: {portfolio_id}")
    
    return token, portfolio_id, user_id

def test_portfolio_ownership(token, portfolio_id):
    """Test if we can access portfolio data at all"""
    print("\n🏢 Testing portfolio access...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test basic portfolio endpoint
    response = requests.get(f"{BASE_URL}/api/v1/data/portfolios", headers=headers)
    print(f"   Portfolios list: {response.status_code}")
    
    if response.status_code == 200:
        portfolios = response.json()
        print(f"   Found {len(portfolios)} portfolios")
        for p in portfolios:
            print(f"     - {p.get('id')}: {p.get('name')} (user: {p.get('user_id')})")

def test_target_prices_with_debug(token, portfolio_id):
    """Test Target Prices endpoint with detailed debugging"""
    print(f"\n🎯 Testing Target Prices endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"{BASE_URL}/api/v1/target-prices/{portfolio_id}"
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} records")
            if data:
                sample = data[0]
                print(f"   📊 Sample: {sample.get('symbol')} - ${sample.get('target_price_eoy')}")
        else:
            print(f"   ❌ Error response:")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            try:
                error_data = response.json()
                print(f"   JSON Error: {json.dumps(error_data, indent=4)}")
            except:
                print(f"   Raw Error: {response.text}")
                
    except Exception as e:
        print(f"   🔥 Exception occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Detailed Target Prices API Testing")
    print("=" * 60)
    
    try:
        # Authenticate
        token, portfolio_id, user_id = authenticate()
        
        # Test portfolio access
        test_portfolio_ownership(token, portfolio_id)
        
        # Test target prices
        test_target_prices_with_debug(token, portfolio_id)
        
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        traceback.print_exc()