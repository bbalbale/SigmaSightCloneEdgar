#!/usr/bin/env python3
"""
Test script for /data/company-profiles endpoint
Tests all three query modes: symbols, position_ids, portfolio_id
"""
import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "demo_individual@sigmasight.com"
TEST_PASSWORD = "demo12345"


def get_auth_token() -> str:
    """Get JWT token for authentication"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def test_symbols_query(token: str):
    """Test direct symbol lookup (no ownership check)"""
    print("\n" + "="*80)
    print("TEST 1: Direct Symbol Lookup (symbols parameter)")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={"symbols": "AAPL,MSFT,GOOGL"}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Query type: {data['meta']['query_type']}")
        print(f"   Requested symbols: {data['meta']['requested_symbols']}")
        print(f"   Returned profiles: {data['meta']['returned_profiles']}")
        print(f"   Missing profiles: {data['meta']['missing_profiles']}")

        if data['profiles']:
            print(f"\n   Sample profile (AAPL):")
            aapl = next((p for p in data['profiles'] if p['symbol'] == 'AAPL'), None)
            if aapl:
                print(f"      Company: {aapl.get('company_name')}")
                print(f"      Sector: {aapl.get('sector')}")
                print(f"      Industry: {aapl.get('industry')}")
                print(f"      Market Cap: {aapl.get('market_cap')}")
                print(f"      PE Ratio: {aapl.get('pe_ratio')}")
                print(f"      Total fields: {len(aapl)}")
    else:
        print(f"❌ Failed: {response.text}")

    return response.status_code == 200


def test_field_filtering(token: str):
    """Test field filtering for performance"""
    print("\n" + "="*80)
    print("TEST 2: Field Filtering (fields parameter)")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "symbols": "AAPL,MSFT",
            "fields": "sector,industry,market_cap,pe_ratio"
        }
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Fields requested: {data['meta']['fields_requested']}")
        print(f"   Returned profiles: {data['meta']['returned_profiles']}")

        if data['profiles']:
            print(f"\n   Filtered profile (AAPL):")
            aapl = next((p for p in data['profiles'] if p['symbol'] == 'AAPL'), None)
            if aapl:
                print(f"      {json.dumps(aapl, indent=6, default=str)}")
                print(f"      Total fields: {len(aapl)} (vs 54 without filtering)")
    else:
        print(f"❌ Failed: {response.text}")

    return response.status_code == 200


def test_portfolio_query(token: str):
    """Test portfolio-based query (ownership required)"""
    print("\n" + "="*80)
    print("TEST 3: Portfolio Query (portfolio_id parameter)")
    print("="*80)

    # First, get user's portfolios
    portfolios_response = requests.get(
        f"{BASE_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )

    if portfolios_response.status_code != 200:
        print(f"❌ Failed to get portfolios: {portfolios_response.text}")
        return False

    portfolios = portfolios_response.json()
    if not portfolios:
        print("❌ No portfolios found")
        return False

    portfolio_id = portfolios[0]["id"]
    print(f"Using portfolio: {portfolios[0]['name']} ({portfolio_id})")

    response = requests.get(
        f"{BASE_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Query type: {data['meta']['query_type']}")
        print(f"   Portfolio ID: {data['meta']['portfolio_id']}")
        print(f"   Requested symbols: {len(data['meta']['requested_symbols'])}")
        print(f"   Returned profiles: {data['meta']['returned_profiles']}")
        print(f"   Missing profiles: {len(data['meta']['missing_profiles'])}")

        if data['meta']['missing_profiles']:
            print(f"   Missing symbols (PRIVATE positions): {data['meta']['missing_profiles'][:5]}")

        if data['profiles']:
            print(f"\n   Sample profiles:")
            for profile in data['profiles'][:3]:
                print(f"      {profile['symbol']}: {profile.get('company_name')} ({profile.get('sector')})")
    else:
        print(f"❌ Failed: {response.text}")

    return response.status_code == 200


def test_position_ids_query(token: str):
    """Test position IDs query (ownership required)"""
    print("\n" + "="*80)
    print("TEST 4: Position IDs Query (position_ids parameter)")
    print("="*80)

    # Get user's positions
    portfolios_response = requests.get(
        f"{BASE_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )

    if portfolios_response.status_code != 200:
        print(f"❌ Failed to get portfolios")
        return False

    portfolios = portfolios_response.json()
    if not portfolios:
        print("❌ No portfolios found")
        return False

    portfolio_id = portfolios[0]["id"]

    # Get positions
    positions_response = requests.get(
        f"{BASE_URL}/data/positions/details",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    if positions_response.status_code != 200:
        print(f"❌ Failed to get positions")
        return False

    positions = positions_response.json()["positions"]
    if not positions:
        print("❌ No positions found")
        return False

    # Test with first 3 positions
    position_ids = [p["id"] for p in positions[:3]]
    position_ids_str = ",".join(position_ids)

    print(f"Testing with {len(position_ids)} positions")

    response = requests.get(
        f"{BASE_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={"position_ids": position_ids_str}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Query type: {data['meta']['query_type']}")
        print(f"   Position IDs: {len(data['meta']['position_ids'])}")
        print(f"   Returned profiles: {data['meta']['returned_profiles']}")

        if data['meta'].get('position_symbol_map'):
            print(f"\n   Position → Symbol mapping:")
            for pos_id, symbol in list(data['meta']['position_symbol_map'].items())[:3]:
                print(f"      {pos_id[:8]}... → {symbol}")

        if data['profiles']:
            print(f"\n   Profiles returned:")
            for profile in data['profiles']:
                print(f"      {profile['symbol']}: {profile.get('company_name')}")
    else:
        print(f"❌ Failed: {response.text}")

    return response.status_code == 200


def test_error_cases(token: str):
    """Test error handling"""
    print("\n" + "="*80)
    print("TEST 5: Error Cases")
    print("="*80)

    test_cases = [
        {
            "name": "No parameters",
            "params": {},
            "expected": 400
        },
        {
            "name": "Multiple parameters",
            "params": {"symbols": "AAPL", "portfolio_id": "00000000-0000-0000-0000-000000000000"},
            "expected": 400
        },
        {
            "name": "Invalid field name",
            "params": {"symbols": "AAPL", "fields": "invalid_field"},
            "expected": 400
        },
        {
            "name": "Invalid portfolio ID",
            "params": {"portfolio_id": "00000000-0000-0000-0000-000000000000"},
            "expected": 404
        }
    ]

    all_passed = True
    for test in test_cases:
        response = requests.get(
            f"{BASE_URL}/data/company-profiles",
            headers={"Authorization": f"Bearer {token}"},
            params=test["params"]
        )

        if response.status_code == test["expected"]:
            print(f"   ✅ {test['name']}: {response.status_code} (expected {test['expected']})")
        else:
            print(f"   ❌ {test['name']}: {response.status_code} (expected {test['expected']})")
            all_passed = False

    return all_passed


def test_missing_profiles(token: str):
    """Test handling of missing profiles (PRIVATE positions)"""
    print("\n" + "="*80)
    print("TEST 6: Missing Profiles (PRIVATE positions)")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={"symbols": "AAPL,HOME_EQUITY,CRYPTO_BTC_ETH"}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Requested symbols: {data['meta']['requested_symbols']}")
        print(f"   Returned profiles: {data['meta']['returned_profiles']}")
        print(f"   Missing profiles: {data['meta']['missing_profiles']}")
        print(f"   Note: Missing profiles are expected for PRIVATE assets")
    else:
        print(f"❌ Failed: {response.text}")

    return response.status_code == 200


def main():
    """Run all tests"""
    print("="*80)
    print("Company Profiles Endpoint Test Suite")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_EMAIL}")

    try:
        # Get auth token
        print("\nAuthenticating...")
        token = get_auth_token()
        print("✅ Authentication successful")

        # Run tests
        results = {
            "Direct symbol lookup": test_symbols_query(token),
            "Field filtering": test_field_filtering(token),
            "Portfolio query": test_portfolio_query(token),
            "Position IDs query": test_position_ids_query(token),
            "Error handling": test_error_cases(token),
            "Missing profiles": test_missing_profiles(token)
        }

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        passed = sum(results.values())
        total = len(results)

        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test_name}")

        print(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1

    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
