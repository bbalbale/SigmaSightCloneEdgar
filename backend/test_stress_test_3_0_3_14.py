#!/usr/bin/env python
"""
Comprehensive test suite for 3.0.3.14 Stress Test API
Tests GET /api/v1/analytics/portfolio/{portfolio_id}/stress-test

This script validates:
1. Basic functionality with available/unavailable pattern
2. Scenario filtering with CSV parameter
3. Impact calculations (dollar, percentage, new value)
4. Sorting by category and name
5. Error handling for invalid inputs
6. Performance benchmarks
7. Data consistency and validation
"""

import requests
import json
import time
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import statistics

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class StressTestAPITestSuite:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.portfolio_id = None
        self.headers = {}
        self.results = []
        
    def authenticate(self) -> bool:
        """Authenticate and get token"""
        try:
            print(f"{BLUE}Authenticating...{RESET}")
            
            # Login
            login_response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD}
            )
            
            if login_response.status_code != 200:
                print(f"{RED}❌ Login failed: {login_response.status_code}{RESET}")
                print(login_response.text)
                return False
                
            self.token = login_response.json().get("access_token")
            if not self.token:
                print(f"{RED}❌ No token received{RESET}")
                return False
                
            self.headers = {"Authorization": f"Bearer {self.token}"}
            
            # Get portfolio ID
            me_response = requests.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=self.headers
            )
            
            if me_response.status_code != 200:
                print(f"{RED}❌ Failed to get user info: {me_response.status_code}{RESET}")
                return False
                
            user_data = me_response.json()
            self.portfolio_id = user_data.get("portfolio_id")
            
            if not self.portfolio_id:
                print(f"{RED}❌ No portfolio_id in user data{RESET}")
                return False
                
            print(f"{GREEN}✅ Authenticated successfully{RESET}")
            print(f"   Portfolio ID: {self.portfolio_id}")
            print(f"   User: {user_data.get('email')}")
            return True
            
        except Exception as e:
            print(f"{RED}❌ Authentication error: {e}{RESET}")
            return False
    
    def test_basic_functionality(self) -> bool:
        """Test basic stress test retrieval"""
        print(f"\n{BOLD}Testing Basic Functionality{RESET}")
        
        try:
            # Test without scenario filter
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers
            )
            
            if response.status_code != 200:
                print(f"{RED}❌ Unexpected status code: {response.status_code}{RESET}")
                print(f"   Response: {response.text[:200]}")
                return False
            
            data = response.json()
            
            # Check response structure
            if "available" not in data:
                print(f"{RED}❌ Missing 'available' field{RESET}")
                return False
            
            if data["available"]:
                # Validate available response
                if "data" not in data or not data["data"]:
                    print(f"{RED}❌ Missing 'data' field in available response{RESET}")
                    return False
                
                payload = data["data"]
                
                # Check required fields
                required_fields = ["scenarios", "portfolio_value", "calculation_date"]
                for field in required_fields:
                    if field not in payload:
                        print(f"{RED}❌ Missing field '{field}' in payload{RESET}")
                        return False
                
                # Validate scenarios
                if not isinstance(payload["scenarios"], list):
                    print(f"{RED}❌ 'scenarios' is not a list{RESET}")
                    return False
                
                if payload["scenarios"]:
                    scenario = payload["scenarios"][0]
                    required_scenario_fields = ["id", "name", "impact"]
                    for field in required_scenario_fields:
                        if field not in scenario:
                            print(f"{RED}❌ Missing field '{field}' in scenario{RESET}")
                            return False
                    
                    # Validate impact structure
                    impact = scenario["impact"]
                    required_impact_fields = ["dollar_impact", "percentage_impact", "new_portfolio_value"]
                    for field in required_impact_fields:
                        if field not in impact:
                            print(f"{RED}❌ Missing field '{field}' in impact{RESET}")
                            return False
                
                print(f"{GREEN}✅ Available response validated{RESET}")
                print(f"   Scenarios: {len(payload['scenarios'])}")
                print(f"   Portfolio Value: ${payload['portfolio_value']:,.2f}")
                print(f"   Calculation Date: {payload['calculation_date']}")
                
                # Show first scenario
                if payload["scenarios"]:
                    s = payload["scenarios"][0]
                    print(f"   First Scenario: {s['name']} ({s['id']})")
                    print(f"     Dollar Impact: ${s['impact']['dollar_impact']:,.2f}")
                    print(f"     Percentage Impact: {s['impact']['percentage_impact']:.2f}%")
                
            else:
                # Validate unavailable response
                if "metadata" in data and "reason" in data.get("metadata", {}):
                    reason = data["metadata"]["reason"]
                    print(f"{YELLOW}⚠️ Data unavailable: {reason}{RESET}")
                    
                    # Valid reasons
                    valid_reasons = ["no_results", "no_snapshot"]
                    if reason not in valid_reasons:
                        print(f"{RED}❌ Invalid reason: {reason}{RESET}")
                        return False
                else:
                    print(f"{YELLOW}⚠️ Data unavailable (no reason provided){RESET}")
            
            return True
            
        except Exception as e:
            print(f"{RED}❌ Test failed: {e}{RESET}")
            return False
    
    def test_scenario_filtering(self) -> bool:
        """Test scenario filtering with CSV parameter"""
        print(f"\n{BOLD}Testing Scenario Filtering{RESET}")
        
        try:
            # First get all scenarios to know what's available
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers
            )
            
            if response.status_code != 200 or not response.json().get("available"):
                print(f"{YELLOW}⚠️ No stress test data available for filtering test{RESET}")
                return True  # Not a failure, just no data
            
            all_data = response.json()["data"]
            all_scenarios = all_data["scenarios"]
            
            if len(all_scenarios) < 2:
                print(f"{YELLOW}⚠️ Not enough scenarios to test filtering (found {len(all_scenarios)}){RESET}")
                return True
            
            # Test with specific scenario IDs
            scenario_ids = [all_scenarios[0]["id"], all_scenarios[1]["id"]]
            filter_param = ",".join(scenario_ids)
            
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers,
                params={"scenarios": filter_param}
            )
            
            if response.status_code != 200:
                print(f"{RED}❌ Failed with scenario filter: {response.status_code}{RESET}")
                return False
            
            filtered_data = response.json()
            
            if not filtered_data.get("available"):
                print(f"{RED}❌ Filtered request returned unavailable{RESET}")
                return False
            
            # Check metadata includes requested scenarios
            if "metadata" in filtered_data:
                if "scenarios_requested" in filtered_data["metadata"]:
                    requested = filtered_data["metadata"]["scenarios_requested"]
                    if set(requested) != set(scenario_ids):
                        print(f"{RED}❌ Metadata scenarios_requested mismatch{RESET}")
                        print(f"   Expected: {scenario_ids}")
                        print(f"   Got: {requested}")
                        return False
                else:
                    print(f"{YELLOW}⚠️ No scenarios_requested in metadata{RESET}")
            
            # Verify filtered results
            filtered_scenarios = filtered_data["data"]["scenarios"]
            filtered_ids = [s["id"] for s in filtered_scenarios]
            
            # Check that requested scenarios are in results (may have more)
            for sid in scenario_ids:
                if sid not in filtered_ids:
                    print(f"{RED}❌ Requested scenario '{sid}' not in results{RESET}")
                    return False
            
            print(f"{GREEN}✅ Scenario filtering works{RESET}")
            print(f"   Requested: {scenario_ids}")
            print(f"   Returned: {len(filtered_scenarios)} scenarios")
            
            # Test with non-existent scenario
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers,
                params={"scenarios": "non_existent_scenario_xyz"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("available") and data["data"]["scenarios"]:
                    print(f"{YELLOW}⚠️ Non-existent scenario filter returned results{RESET}")
                else:
                    print(f"{GREEN}✅ Non-existent scenario handled correctly{RESET}")
            
            return True
            
        except Exception as e:
            print(f"{RED}❌ Test failed: {e}{RESET}")
            return False
    
    def test_impact_calculations(self) -> bool:
        """Test impact calculation consistency"""
        print(f"\n{BOLD}Testing Impact Calculations{RESET}")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers
            )
            
            if response.status_code != 200 or not response.json().get("available"):
                print(f"{YELLOW}⚠️ No stress test data available for calculation test{RESET}")
                return True
            
            data = response.json()["data"]
            portfolio_value = data["portfolio_value"]
            scenarios = data["scenarios"]
            
            if not scenarios:
                print(f"{YELLOW}⚠️ No scenarios to validate calculations{RESET}")
                return True
            
            print(f"   Portfolio Value: ${portfolio_value:,.2f}")
            
            errors = []
            for scenario in scenarios:
                impact = scenario["impact"]
                dollar_impact = impact["dollar_impact"]
                percentage_impact = impact["percentage_impact"]
                new_value = impact["new_portfolio_value"]
                
                # Validate percentage calculation
                expected_percentage = (dollar_impact / portfolio_value) * 100
                percentage_diff = abs(percentage_impact - expected_percentage)
                
                if percentage_diff > 0.01:  # Allow 0.01% tolerance
                    errors.append(f"Scenario '{scenario['name']}': percentage mismatch")
                    errors.append(f"  Expected: {expected_percentage:.2f}%, Got: {percentage_impact:.2f}%")
                
                # Validate new portfolio value
                expected_new_value = portfolio_value + dollar_impact
                value_diff = abs(new_value - expected_new_value)
                
                if value_diff > 0.01:  # Allow $0.01 tolerance
                    errors.append(f"Scenario '{scenario['name']}': new value mismatch")
                    errors.append(f"  Expected: ${expected_new_value:,.2f}, Got: ${new_value:,.2f}")
            
            if errors:
                print(f"{RED}❌ Calculation errors found:{RESET}")
                for error in errors:
                    print(f"   {error}")
                return False
            
            print(f"{GREEN}✅ All impact calculations consistent{RESET}")
            print(f"   Validated {len(scenarios)} scenarios")
            
            # Show sample calculations
            if scenarios:
                s = scenarios[0]
                print(f"   Sample: {s['name']}")
                print(f"     Dollar Impact: ${s['impact']['dollar_impact']:,.2f}")
                print(f"     Percentage: {s['impact']['percentage_impact']:.2f}%")
                print(f"     New Value: ${s['impact']['new_portfolio_value']:,.2f}")
            
            return True
            
        except Exception as e:
            print(f"{RED}❌ Test failed: {e}{RESET}")
            return False
    
    def test_sorting(self) -> bool:
        """Test scenario sorting by category and name"""
        print(f"\n{BOLD}Testing Scenario Sorting{RESET}")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers
            )
            
            if response.status_code != 200 or not response.json().get("available"):
                print(f"{YELLOW}⚠️ No stress test data available for sorting test{RESET}")
                return True
            
            scenarios = response.json()["data"]["scenarios"]
            
            if len(scenarios) < 2:
                print(f"{YELLOW}⚠️ Not enough scenarios to test sorting{RESET}")
                return True
            
            # Check sorting: category ASC, then name ASC
            prev_category = ""
            prev_name = ""
            sorted_correctly = True
            
            for i, scenario in enumerate(scenarios):
                category = scenario.get("category", "")
                name = scenario.get("name", "")
                
                if i > 0:
                    # Check category ordering
                    if category < prev_category:
                        print(f"{RED}❌ Category sorting violation at index {i}{RESET}")
                        print(f"   Previous: '{prev_category}', Current: '{category}'")
                        sorted_correctly = False
                        break
                    
                    # Within same category, check name ordering
                    if category == prev_category and name < prev_name:
                        print(f"{RED}❌ Name sorting violation within category at index {i}{RESET}")
                        print(f"   Category: '{category}'")
                        print(f"   Previous name: '{prev_name}', Current: '{name}'")
                        sorted_correctly = False
                        break
                
                prev_category = category
                prev_name = name
            
            if sorted_correctly:
                print(f"{GREEN}✅ Scenarios correctly sorted by category, then name{RESET}")
                
                # Show sorting structure
                categories = {}
                for s in scenarios:
                    cat = s.get("category", "uncategorized")
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(s["name"])
                
                print(f"   Categories found: {len(categories)}")
                for cat in sorted(categories.keys()):
                    print(f"     {cat}: {len(categories[cat])} scenarios")
            
            return sorted_correctly
            
        except Exception as e:
            print(f"{RED}❌ Test failed: {e}{RESET}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling for invalid inputs"""
        print(f"\n{BOLD}Testing Error Handling{RESET}")
        
        test_cases = [
            ("Invalid UUID", f"{self.base_url}/api/v1/analytics/portfolio/invalid-uuid/stress-test", 422),
            ("Non-existent portfolio", f"{self.base_url}/api/v1/analytics/portfolio/00000000-0000-0000-0000-000000000000/stress-test", 404),
            ("Missing auth", f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test", 401, {}),
        ]
        
        all_passed = True
        for test_name, url, expected_status, *args in test_cases:
            headers = args[0] if args else self.headers
            
            try:
                response = requests.get(url, headers=headers)
                
                if response.status_code == expected_status:
                    print(f"{GREEN}✅ {test_name}: Got expected {expected_status}{RESET}")
                else:
                    print(f"{RED}❌ {test_name}: Expected {expected_status}, got {response.status_code}{RESET}")
                    all_passed = False
                    
            except Exception as e:
                print(f"{RED}❌ {test_name} failed: {e}{RESET}")
                all_passed = False
        
        return all_passed
    
    def test_performance(self) -> bool:
        """Test endpoint performance"""
        print(f"\n{BOLD}Testing Performance{RESET}")
        
        try:
            # Warm-up request
            requests.get(
                f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                headers=self.headers
            )
            
            # Performance test
            times = []
            iterations = 5
            
            for i in range(iterations):
                start = time.time()
                response = requests.get(
                    f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                    headers=self.headers
                )
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code != 200:
                    print(f"{RED}❌ Request {i+1} failed: {response.status_code}{RESET}")
                    return False
            
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            # Check if average response time is under 200ms (target from spec)
            target_time = 0.2
            if avg_time > target_time:
                print(f"{YELLOW}⚠️ Average response time {avg_time:.3f}s exceeds target {target_time}s{RESET}")
            else:
                print(f"{GREEN}✅ Performance meets target{RESET}")
            
            print(f"   Average: {avg_time*1000:.1f}ms")
            print(f"   Min: {min_time*1000:.1f}ms")
            print(f"   Max: {max_time*1000:.1f}ms")
            
            return True
            
        except Exception as e:
            print(f"{RED}❌ Performance test failed: {e}{RESET}")
            return False
    
    def test_data_consistency(self) -> bool:
        """Test data consistency across multiple requests"""
        print(f"\n{BOLD}Testing Data Consistency{RESET}")
        
        try:
            # Make multiple requests and verify consistency
            responses = []
            for _ in range(3):
                response = requests.get(
                    f"{self.base_url}/api/v1/analytics/portfolio/{self.portfolio_id}/stress-test",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"{RED}❌ Request failed: {response.status_code}{RESET}")
                    return False
                
                responses.append(response.json())
            
            # Check if all responses are identical
            first = json.dumps(responses[0], sort_keys=True)
            all_same = all(json.dumps(r, sort_keys=True) == first for r in responses)
            
            if all_same:
                print(f"{GREEN}✅ Data consistent across {len(responses)} requests{RESET}")
            else:
                print(f"{RED}❌ Data inconsistency detected{RESET}")
                return False
            
            # If data is available, check calculation date format
            if responses[0].get("available") and responses[0].get("data"):
                calc_date = responses[0]["data"].get("calculation_date")
                if calc_date:
                    try:
                        # Verify date format YYYY-MM-DD
                        datetime.strptime(calc_date, "%Y-%m-%d")
                        print(f"{GREEN}✅ Calculation date format valid: {calc_date}{RESET}")
                    except ValueError:
                        print(f"{RED}❌ Invalid date format: {calc_date} (expected YYYY-MM-DD){RESET}")
                        return False
            
            return True
            
        except Exception as e:
            print(f"{RED}❌ Consistency test failed: {e}{RESET}")
            return False
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Run all tests and return results"""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}Stress Test API Test Suite (3.0.3.14){RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        
        if not self.authenticate():
            print(f"\n{RED}Cannot proceed without authentication{RESET}")
            return 0, 1
        
        tests = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Scenario Filtering", self.test_scenario_filtering),
            ("Impact Calculations", self.test_impact_calculations),
            ("Sorting", self.test_sorting),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("Data Consistency", self.test_data_consistency),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    self.results.append((test_name, "PASSED"))
                else:
                    failed += 1
                    self.results.append((test_name, "FAILED"))
            except Exception as e:
                failed += 1
                self.results.append((test_name, f"FAILED: {e}"))
                print(f"{RED}❌ {test_name} encountered an error: {e}{RESET}")
        
        return passed, failed
    
    def print_summary(self, passed: int, failed: int):
        """Print test summary"""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}Test Summary{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        
        total = passed + failed
        
        for test_name, result in self.results:
            if result == "PASSED":
                print(f"{GREEN}✅ {test_name}: {result}{RESET}")
            else:
                print(f"{RED}❌ {test_name}: {result}{RESET}")
        
        print(f"\n{BOLD}Results:{RESET}")
        print(f"  Total Tests: {total}")
        print(f"  {GREEN}Passed: {passed}{RESET}")
        print(f"  {RED}Failed: {failed}{RESET}")
        
        if failed == 0:
            print(f"\n{GREEN}{BOLD}🎉 All tests passed!{RESET}")
        else:
            print(f"\n{RED}{BOLD}⚠️ Some tests failed{RESET}")
        
        # Return exit code
        return 0 if failed == 0 else 1


def main():
    """Main execution"""
    try:
        tester = StressTestAPITestSuite()
        passed, failed = tester.run_all_tests()
        exit_code = tester.print_summary(passed, failed)
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()