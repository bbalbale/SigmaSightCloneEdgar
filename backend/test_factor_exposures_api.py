#!/usr/bin/env python
"""Test script for Factor Exposures API endpoints (3.0.3.12)"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

def authenticate() -> tuple[str, str]:
    """Authenticate and return token and portfolio_id"""
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
    
    # Get user info
    headers = {"Authorization": f"Bearer {token}"}
    me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    
    if me_response.status_code != 200:
        print(f"❌ Auth verification failed: {me_response.status_code}")
        print(me_response.text)
        sys.exit(1)
    
    user_data = me_response.json()
    portfolio_id = user_data.get("portfolio_id")
    print(f"✅ Auth works - Portfolio ID: {portfolio_id}")
    
    return token, portfolio_id

def test_portfolio_factor_exposures(token: str, portfolio_id: str):
    """Test portfolio-level factor exposures endpoint"""
    print("\n" + "="*60)
    print("📊 Testing Portfolio Factor Exposures API (3.0.3.12a)")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/api/v1/analytics/portfolio/{portfolio_id}/factor-exposures"
    
    response = requests.get(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)[:500]}...")  # First 500 chars
        
        # Validate structure
        if "available" in data:
            if data["available"]:
                print(f"\n✅ Data available")
                if "exposures" in data:
                    print(f"   - Found {len(data['exposures'])} factor exposures")
                    for exposure in data["exposures"][:3]:  # Show first 3
                        print(f"   - {exposure.get('factor_name')}: {exposure.get('exposure_value'):.4f}")
                if "metadata" in data:
                    print(f"   - Calculation date: {data['metadata'].get('calculation_date')}")
                    print(f"   - Portfolio value: ${data['metadata'].get('total_portfolio_value', 0):,.2f}")
            else:
                print(f"⚠️ No data available: {data.get('metadata', {}).get('reason', 'Unknown reason')}")
        else:
            print("❌ Response missing 'available' field")
            
        return response.status_code == 200
    else:
        print(f"❌ Request failed: {response.text[:500]}")
        return False

def test_position_factor_exposures(token: str, portfolio_id: str):
    """Test position-level factor exposures endpoint"""
    print("\n" + "="*60)
    print("📊 Testing Position Factor Exposures API (3.0.3.12b)")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/api/v1/analytics/portfolio/{portfolio_id}/positions/factor-exposures"
    params = {"limit": 10, "offset": 0}
    
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)[:500]}...")  # First 500 chars
        
        # Validate structure
        if "available" in data:
            if data["available"]:
                print(f"\n✅ Data available")
                if "positions" in data:
                    print(f"   - Found {len(data['positions'])} positions with factor data")
                    for position in data["positions"][:2]:  # Show first 2
                        print(f"\n   Position: {position.get('symbol')} ({position.get('position_id')[:8]}...)")
                        if "exposures" in position:
                            exposures = position["exposures"]
                            if isinstance(exposures, dict):
                                # Exposures are returned as dict
                                for factor_name, value in list(exposures.items())[:3]:  # First 3 factors
                                    print(f"     - {factor_name}: {value:.4f}")
                            else:
                                # Exposures are returned as list
                                for exposure in exposures[:3]:  # First 3 factors
                                    print(f"     - {exposure.get('factor_name')}: {exposure.get('exposure_value'):.4f}")
                if "metadata" in data:
                    print(f"\n   - Total positions: {data['metadata'].get('total_count', 0)}")
                    print(f"   - Page info: limit={data['metadata'].get('limit')}, offset={data['metadata'].get('offset')}")
            else:
                print(f"⚠️ No data available: {data.get('metadata', {}).get('reason', 'Unknown reason')}")
        else:
            print("❌ Response missing 'available' field")
            
        return response.status_code == 200
    else:
        print(f"❌ Request failed: {response.text[:500]}")
        return False

def test_error_responses(token: str):
    """Test error conditions"""
    print("\n" + "="*60)
    print("🔍 Testing Error Response Handling")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Invalid portfolio ID
    print("\n1. Testing with invalid portfolio ID...")
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/portfolio/invalid-uuid/factor-exposures",
        headers=headers
    )
    print(f"   Status: {response.status_code} (expected 422)")
    if response.status_code == 422:
        print("   ✅ Correctly rejected invalid UUID")
    else:
        print(f"   ❌ Unexpected response: {response.text[:200]}")
    
    # Test 2: Non-existent portfolio
    print("\n2. Testing with non-existent portfolio...")
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/portfolio/00000000-0000-0000-0000-000000000000/factor-exposures",
        headers=headers
    )
    print(f"   Status: {response.status_code} (expected 404 or 403)")
    if response.status_code in [403, 404]:
        print("   ✅ Correctly handled non-existent portfolio")
    else:
        print(f"   ❌ Unexpected response: {response.text[:200]}")
    
    # Test 3: Missing authentication
    print("\n3. Testing without authentication...")
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/portfolio/some-id/factor-exposures"
    )
    print(f"   Status: {response.status_code} (expected 401)")
    if response.status_code == 401:
        print("   ✅ Correctly rejected unauthenticated request")
    else:
        print(f"   ❌ Unexpected response: {response.text[:200]}")
    
    # Test 4: Invalid pagination params
    print("\n4. Testing with invalid pagination params...")
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/portfolio/some-id/positions/factor-exposures",
        headers=headers,
        params={"limit": -1, "offset": "invalid"}
    )
    print(f"   Status: {response.status_code} (expected 422)")
    if response.status_code == 422:
        print("   ✅ Correctly rejected invalid parameters")
    else:
        print(f"   ❌ Unexpected response: {response.text[:200]}")

def main():
    """Main test execution"""
    print("🚀 Starting Factor Exposures API Tests (3.0.3.12)")
    print("="*60)
    
    # Authenticate
    token, portfolio_id = authenticate()
    
    # Run tests
    success_count = 0
    total_tests = 2
    
    # Test portfolio factor exposures
    if test_portfolio_factor_exposures(token, portfolio_id):
        success_count += 1
    
    # Test position factor exposures  
    if test_position_factor_exposures(token, portfolio_id):
        success_count += 1
    
    # Test error responses
    test_error_responses(token)
    
    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    print(f"✅ Passed: {success_count}/{total_tests} main tests")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())