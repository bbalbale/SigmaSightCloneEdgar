#!/usr/bin/env python
"""Test Target Prices API endpoint"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

def authenticate():
    """Get authentication token and portfolio ID"""
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
    
    return token, portfolio_id

def test_target_prices_list(token, portfolio_id):
    """Test the List Target Prices endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🧪 Testing: GET /api/v1/target-prices/{portfolio_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/target-prices/{portfolio_id}",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {len(data)} target price records")
        
        if len(data) > 0:
            # Show first record as example
            first_record = data[0]
            print(f"📊 Sample record:")
            print(json.dumps({
                "symbol": first_record.get("symbol"),
                "target_price_eoy": first_record.get("target_price_eoy"),
                "current_price": first_record.get("current_price"),
                "expected_return_eoy": first_record.get("expected_return_eoy")
            }, indent=2))
            
            # Validate expected return calculation
            target = first_record.get("target_price_eoy")
            current = first_record.get("current_price")
            expected_return = first_record.get("expected_return_eoy")
            
            if target and current:
                calculated_return = round((target / current - 1) * 100, 2)
                print(f"🧮 Return calculation check:")
                print(f"   Expected: {expected_return}%")
                print(f"   Calculated: {calculated_return}%")
                print(f"   Match: {'✅' if abs(calculated_return - expected_return) < 0.1 else '❌'}")
        
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Target Prices API")
    print("=" * 50)
    
    # Authenticate
    print("1. Authenticating...")
    token, portfolio_id = authenticate()
    print(f"   ✅ Portfolio ID: {portfolio_id}")
    
    # Test target prices list
    print("\n2. Testing Target Prices List endpoint...")
    success = test_target_prices_list(token, portfolio_id)
    
    print(f"\n{'🎉 All tests passed!' if success else '💥 Tests failed!'}")