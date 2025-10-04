#!/usr/bin/env python
"""
Comprehensive test script for Position Factor Exposures API (TODO 3.0.3.15)
GET /api/v1/analytics/portfolio/{portfolio_id}/positions/factor-exposures

Tests include:
- Authentication and basic endpoint functionality
- Pagination validation
- Symbol filtering
- Response structure validation
- Error handling
- Performance testing
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


class PositionFactorExposuresTestSuite:
    def __init__(self):
        self.token = None
        self.portfolio_id = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with color coding"""
        colors = {
            "PASS": GREEN,
            "FAIL": RED,
            "WARN": YELLOW,
            "INFO": BLUE
        }
        color = colors.get(level, RESET)
        print(f"{color}{message}{RESET}")
    
    def authenticate(self) -> bool:
        """Authenticate and get token/portfolio_id"""
        self.log("\n" + "="*60, "INFO")
        self.log("🔐 Authenticating with SigmaSight API", "INFO")
        self.log("="*60, "INFO")
        
        try:
            # Login
            login_response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
                timeout=10
            )
            
            if login_response.status_code != 200:
                self.log(f"❌ Login failed: {login_response.status_code}", "FAIL")
                self.log(f"Response: {login_response.text[:200]}", "FAIL")
                return False
            
            self.token = login_response.json().get("access_token")
            if not self.token:
                self.log("❌ No token received", "FAIL")
                return False
            
            self.log(f"✅ Got token: {self.token[:50]}...", "PASS")
            
            # Get user info
            headers = {"Authorization": f"Bearer {self.token}"}
            me_response = requests.get(
                f"{BASE_URL}/api/v1/auth/me", 
                headers=headers,
                timeout=10
            )
            
            if me_response.status_code != 200:
                self.log(f"❌ Auth verification failed: {me_response.status_code}", "FAIL")
                return False
            
            user_data = me_response.json()
            self.portfolio_id = user_data.get("portfolio_id")
            
            self.log(f"✅ Auth successful", "PASS")
            self.log(f"   User: {user_data.get('email')}", "INFO")
            self.log(f"   Portfolio ID: {self.portfolio_id}", "INFO")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Request failed: {e}", "FAIL")
            return False
    
    def run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """Run a single test and track results"""
        self.total_tests += 1
        self.log(f"\n🧪 {test_name}", "INFO")
        self.log("-" * 40, "INFO")
        
        try:
            result = test_func(*args, **kwargs)
            if result:
                self.passed_tests += 1
                self.log(f"✅ {test_name} PASSED", "PASS")
                self.test_results.append((test_name, "PASS"))
            else:
                self.log(f"❌ {test_name} FAILED", "FAIL")
                self.test_results.append((test_name, "FAIL"))
            return result
        except Exception as e:
            self.log(f"❌ {test_name} FAILED with exception: {e}", "FAIL")
            self.test_results.append((test_name, "ERROR"))
            return False
    
    def test_basic_functionality(self) -> bool:
        """Test basic endpoint functionality"""
        headers = {"Authorization": f"Bearer {self.token}"}
        url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            self.log(f"Status Code: {response.status_code}", "INFO")
            
            if response.status_code != 200:
                self.log(f"Unexpected status code: {response.status_code}", "FAIL")
                self.log(f"Response: {response.text[:500]}", "FAIL")
                return False
            
            data = response.json()
            
            # Validate required fields
            required_fields = ["available", "portfolio_id"]
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field: {field}", "FAIL")
                    return False
            
            if data["available"]:
                self.log(f"✓ Data available", "PASS")
                
                # Validate data structure when available
                if "positions" not in data:
                    self.log("Missing 'positions' field when available=true", "FAIL")
                    return False
                
                self.log(f"✓ Found {len(data['positions'])} positions", "PASS")
                
                # Check calculation date
                if "calculation_date" in data:
                    self.log(f"✓ Calculation date: {data['calculation_date']}", "PASS")
                
                # Validate position structure
                if data["positions"]:
                    position = data["positions"][0]
                    required_pos_fields = ["position_id", "symbol", "exposures"]
                    for field in required_pos_fields:
                        if field not in position:
                            self.log(f"Position missing field: {field}", "FAIL")
                            return False
                    
                    # Check exposures format
                    exposures = position["exposures"]
                    if not isinstance(exposures, dict):
                        self.log(f"Exposures should be a dict, got {type(exposures)}", "FAIL")
                        return False
                    
                    self.log(f"✓ Position structure valid", "PASS")
                    self.log(f"  Sample: {position['symbol']} has {len(exposures)} factor exposures", "INFO")
                    
                    # Show first few exposures
                    for factor, value in list(exposures.items())[:3]:
                        self.log(f"    - {factor}: {value:.4f}", "INFO")
            else:
                self.log(f"⚠️ No data available: {data.get('reason', 'Unknown')}", "WARN")
                # This is still valid response
                return True
            
            return True
            
        except Exception as e:
            self.log(f"Test failed with exception: {e}", "FAIL")
            return False
    
    def test_pagination(self) -> bool:
        """Test pagination parameters"""
        headers = {"Authorization": f"Bearer {self.token}"}
        base_url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            # Test different limit values
            test_cases = [
                {"limit": 5, "offset": 0, "description": "Small page"},
                {"limit": 10, "offset": 5, "description": "With offset"},
                {"limit": 50, "offset": 0, "description": "Default limit"},
                {"limit": 200, "offset": 0, "description": "Max limit"}
            ]
            
            for case in test_cases:
                params = {"limit": case["limit"], "offset": case["offset"]}
                response = requests.get(base_url, headers=headers, params=params, timeout=10)
                
                if response.status_code != 200:
                    self.log(f"Failed {case['description']}: status {response.status_code}", "FAIL")
                    return False
                
                data = response.json()
                if data.get("available"):
                    positions = data.get("positions", [])
                    actual_count = len(positions)
                    expected_max = case["limit"]
                    
                    if actual_count > expected_max:
                        self.log(f"Too many results for {case['description']}: {actual_count} > {expected_max}", "FAIL")
                        return False
                    
                    # Check pagination metadata
                    if "limit" in data and data["limit"] != case["limit"]:
                        self.log(f"Limit mismatch: expected {case['limit']}, got {data['limit']}", "FAIL")
                        return False
                    
                    if "offset" in data and data["offset"] != case["offset"]:
                        self.log(f"Offset mismatch: expected {case['offset']}, got {data['offset']}", "FAIL")
                        return False
                    
                    self.log(f"✓ {case['description']}: {actual_count} positions (limit={case['limit']}, offset={case['offset']})", "PASS")
            
            return True
            
        except Exception as e:
            self.log(f"Pagination test failed: {e}", "FAIL")
            return False
    
    def test_symbol_filter(self) -> bool:
        """Test symbol filtering parameter"""
        headers = {"Authorization": f"Bearer {self.token}"}
        base_url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            # First get all positions to find valid symbols
            response = requests.get(base_url, headers=headers, params={"limit": 10}, timeout=10)
            if response.status_code != 200:
                self.log("Failed to get initial positions", "FAIL")
                return False
            
            data = response.json()
            if not data.get("available") or not data.get("positions"):
                self.log("No positions available to test filtering", "WARN")
                return True  # Skip test but don't fail
            
            # Get some symbols to filter
            all_symbols = [p["symbol"] for p in data["positions"][:5]]
            if len(all_symbols) < 2:
                self.log("Not enough symbols to test filtering", "WARN")
                return True
            
            # Test with subset of symbols
            test_symbols = ",".join(all_symbols[:2])
            params = {"symbols": test_symbols}
            
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                self.log(f"Symbol filter request failed: {response.status_code}", "FAIL")
                return False
            
            filtered_data = response.json()
            if filtered_data.get("available"):
                filtered_positions = filtered_data.get("positions", [])
                filtered_symbols = [p["symbol"] for p in filtered_positions]
                
                # Check that only requested symbols are returned
                expected_symbols = set(all_symbols[:2])
                actual_symbols = set(filtered_symbols)
                
                if not actual_symbols.issubset(expected_symbols):
                    self.log(f"Unexpected symbols in filtered results: {actual_symbols - expected_symbols}", "FAIL")
                    return False
                
                self.log(f"✓ Symbol filter working: requested {test_symbols}", "PASS")
                self.log(f"  Returned {len(filtered_positions)} positions with symbols: {', '.join(filtered_symbols)}", "INFO")
            
            return True
            
        except Exception as e:
            self.log(f"Symbol filter test failed: {e}", "FAIL")
            return False
    
    def test_error_handling(self) -> bool:
        """Test various error conditions"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        error_cases = [
            {
                "name": "Invalid UUID format",
                "url": f"{BASE_URL}/api/v1/analytics/portfolio/not-a-uuid/positions/factor-exposures",
                "expected_status": 422,
                "headers": headers
            },
            {
                "name": "Missing authentication",
                "url": f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures",
                "expected_status": 401,
                "headers": {}
            },
            {
                "name": "Invalid pagination params",
                "url": f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures?limit=-1",
                "expected_status": 422,
                "headers": headers
            },
            {
                "name": "Limit too high",
                "url": f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures?limit=1000",
                "expected_status": 422,
                "headers": headers
            },
            {
                "name": "Non-existent portfolio",
                "url": f"{BASE_URL}/api/v1/analytics/portfolio/00000000-0000-0000-0000-000000000000/positions/factor-exposures",
                "expected_status": [403, 404, 500],  # Could be any of these
                "headers": headers
            }
        ]
        
        all_passed = True
        for case in error_cases:
            try:
                response = requests.get(case["url"], headers=case["headers"], timeout=10)
                
                expected = case["expected_status"]
                if isinstance(expected, list):
                    if response.status_code in expected:
                        self.log(f"✓ {case['name']}: Got {response.status_code} (expected one of {expected})", "PASS")
                    else:
                        self.log(f"✗ {case['name']}: Got {response.status_code}, expected one of {expected}", "FAIL")
                        all_passed = False
                else:
                    if response.status_code == expected:
                        self.log(f"✓ {case['name']}: Got expected {expected}", "PASS")
                    else:
                        self.log(f"✗ {case['name']}: Got {response.status_code}, expected {expected}", "FAIL")
                        all_passed = False
                        
            except Exception as e:
                self.log(f"✗ {case['name']}: Request failed with {e}", "FAIL")
                all_passed = False
        
        return all_passed
    
    def test_performance(self) -> bool:
        """Test endpoint performance"""
        headers = {"Authorization": f"Bearer {self.token}"}
        base_url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            test_cases = [
                {"limit": 10, "description": "Small request (10 positions)"},
                {"limit": 50, "description": "Medium request (50 positions)"},
                {"limit": 100, "description": "Large request (100 positions)"}
            ]
            
            for case in test_cases:
                start_time = time.time()
                response = requests.get(
                    base_url, 
                    headers=headers, 
                    params={"limit": case["limit"]},
                    timeout=10
                )
                elapsed = time.time() - start_time
                
                if response.status_code != 200:
                    self.log(f"Performance test failed: {response.status_code}", "FAIL")
                    return False
                
                # Check response time thresholds
                if elapsed < 0.5:
                    self.log(f"✓ {case['description']}: {elapsed:.3f}s (excellent)", "PASS")
                elif elapsed < 1.0:
                    self.log(f"✓ {case['description']}: {elapsed:.3f}s (good)", "PASS")
                elif elapsed < 2.0:
                    self.log(f"⚠ {case['description']}: {elapsed:.3f}s (acceptable)", "WARN")
                else:
                    self.log(f"✗ {case['description']}: {elapsed:.3f}s (too slow)", "FAIL")
                    return False
            
            return True
            
        except Exception as e:
            self.log(f"Performance test failed: {e}", "FAIL")
            return False
    
    def test_data_consistency(self) -> bool:
        """Test data consistency across requests"""
        headers = {"Authorization": f"Bearer {self.token}"}
        base_url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            # Get first page
            response1 = requests.get(
                base_url,
                headers=headers,
                params={"limit": 5, "offset": 0},
                timeout=10
            )
            
            # Get overlapping page
            response2 = requests.get(
                base_url,
                headers=headers,
                params={"limit": 5, "offset": 2},
                timeout=10
            )
            
            if response1.status_code != 200 or response2.status_code != 200:
                self.log("Failed to get pages for consistency check", "FAIL")
                return False
            
            data1 = response1.json()
            data2 = response2.json()
            
            if not (data1.get("available") and data2.get("available")):
                self.log("No data available for consistency check", "WARN")
                return True
            
            # Check calculation dates match
            if "calculation_date" in data1 and "calculation_date" in data2:
                if data1["calculation_date"] != data2["calculation_date"]:
                    self.log(f"Calculation dates don't match: {data1['calculation_date']} vs {data2['calculation_date']}", "FAIL")
                    return False
                self.log(f"✓ Calculation dates consistent: {data1['calculation_date']}", "PASS")
            
            # Check overlapping positions (positions 3-5 from first request should match 1-3 from second)
            if len(data1["positions"]) >= 3 and len(data2["positions"]) >= 3:
                overlap1 = data1["positions"][2:5]  # Positions 3-5
                overlap2 = data2["positions"][0:3]  # Positions 1-3
                
                for i, (pos1, pos2) in enumerate(zip(overlap1, overlap2)):
                    if pos1["position_id"] != pos2["position_id"]:
                        self.log(f"Position ID mismatch at overlap position {i+1}", "FAIL")
                        return False
                    
                    # Check exposures match
                    if pos1["exposures"] != pos2["exposures"]:
                        self.log(f"Exposures mismatch for position {pos1['symbol']}", "FAIL")
                        return False
                
                self.log(f"✓ Overlapping positions consistent", "PASS")
            
            return True
            
        except Exception as e:
            self.log(f"Consistency test failed: {e}", "FAIL")
            return False
    
    def test_factor_data_validity(self) -> bool:
        """Test that factor exposure values are reasonable"""
        headers = {"Authorization": f"Bearer {self.token}"}
        url = f"{BASE_URL}/api/v1/analytics/portfolio/{self.portfolio_id}/positions/factor-exposures"
        
        try:
            response = requests.get(url, headers=headers, params={"limit": 20}, timeout=10)
            
            if response.status_code != 200:
                self.log(f"Failed to get data for validity check: {response.status_code}", "FAIL")
                return False
            
            data = response.json()
            if not data.get("available") or not data.get("positions"):
                self.log("No data available for validity check", "WARN")
                return True
            
            # Expected factor names (from the spec)
            expected_factors = {"Market Beta", "Value", "Momentum", "Size", "Quality", "Low Volatility", "Growth"}
            
            all_factors = set()
            invalid_values = []
            
            for position in data["positions"]:
                exposures = position.get("exposures", {})
                
                for factor_name, value in exposures.items():
                    all_factors.add(factor_name)
                    
                    # Check value is numeric and reasonable (typically between -3 and 3 for factor exposures)
                    if not isinstance(value, (int, float)):
                        invalid_values.append(f"{position['symbol']}/{factor_name}: {value} (not numeric)")
                    elif abs(value) > 10:
                        invalid_values.append(f"{position['symbol']}/{factor_name}: {value} (too large)")
            
            # Check we have expected factors
            if all_factors:
                if all_factors == expected_factors:
                    self.log(f"✓ All expected factors present: {', '.join(sorted(all_factors))}", "PASS")
                else:
                    missing = expected_factors - all_factors
                    extra = all_factors - expected_factors
                    if missing:
                        self.log(f"⚠ Missing factors: {missing}", "WARN")
                    if extra:
                        self.log(f"⚠ Extra factors: {extra}", "WARN")
            
            # Report invalid values
            if invalid_values:
                self.log(f"✗ Found {len(invalid_values)} invalid values:", "FAIL")
                for invalid in invalid_values[:5]:  # Show first 5
                    self.log(f"  - {invalid}", "FAIL")
                return False
            else:
                self.log(f"✓ All factor values are valid", "PASS")
            
            # Show sample of factor values
            sample_position = data["positions"][0]
            self.log(f"\nSample exposures for {sample_position['symbol']}:", "INFO")
            for factor, value in sample_position["exposures"].items():
                self.log(f"  {factor}: {value:.4f}", "INFO")
            
            return True
            
        except Exception as e:
            self.log(f"Validity test failed: {e}", "FAIL")
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.log("\n" + "="*60, "INFO")
        self.log("🚀 Position Factor Exposures API Test Suite (3.0.3.15)", "INFO")
        self.log("="*60, "INFO")
        self.log(f"Timestamp: {datetime.now().isoformat()}", "INFO")
        self.log(f"Base URL: {BASE_URL}", "INFO")
        self.log(f"Test User: {EMAIL}", "INFO")
        
        # Authenticate first
        if not self.authenticate():
            self.log("\n❌ Authentication failed. Cannot proceed with tests.", "FAIL")
            return False
        
        # Run all tests
        tests = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Pagination", self.test_pagination),
            ("Symbol Filtering", self.test_symbol_filter),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("Data Consistency", self.test_data_consistency),
            ("Factor Data Validity", self.test_factor_data_validity)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        self.log("\n" + "="*60, "INFO")
        self.log("📊 TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")
        
        for test_name, result in self.test_results:
            if result == "PASS":
                self.log(f"  ✅ {test_name}: {result}", "PASS")
            elif result == "FAIL":
                self.log(f"  ❌ {test_name}: {result}", "FAIL")
            else:
                self.log(f"  ⚠️ {test_name}: {result}", "WARN")
        
        self.log(f"\nTotal: {self.passed_tests}/{self.total_tests} tests passed", "INFO")
        
        if self.passed_tests == self.total_tests:
            self.log("\n🎉 ALL TESTS PASSED! 🎉", "PASS")
            return True
        else:
            self.log(f"\n⚠️ {self.total_tests - self.passed_tests} tests failed. Review output above.", "WARN")
            return False


def main():
    """Main entry point"""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print(f"{RED}❌ Server not responding at {BASE_URL}{RESET}")
            print(f"{YELLOW}Please ensure the server is running:{RESET}")
            print(f"  cd backend && uv run uvicorn app.main:app --reload")
            return 1
    except requests.exceptions.RequestException:
        print(f"{RED}❌ Cannot connect to server at {BASE_URL}{RESET}")
        print(f"{YELLOW}Please ensure the server is running:{RESET}")
        print(f"  cd backend && uv run uvicorn app.main:app --reload")
        return 1
    
    # Run test suite
    test_suite = PositionFactorExposuresTestSuite()
    success = test_suite.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())