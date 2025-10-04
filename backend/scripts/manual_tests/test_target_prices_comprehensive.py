#!/usr/bin/env python
"""Comprehensive Target Price API Testing Suite"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

class TargetPriceAPITester:
    def __init__(self):
        self.token = None
        self.portfolio_id = None
        self.created_target_ids = []
        self.test_results = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with formatting"""
        icons = {"INFO": "📘", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        print(f"{icons.get(level, '📝')} {message}")

    def test_endpoint(self, name: str, method: str, endpoint: str,
                      headers: Optional[Dict] = None,
                      data: Optional[Any] = None,
                      params: Optional[Dict] = None,
                      expected_status: int = 200) -> Optional[Dict]:
        """Test a single endpoint"""
        self.log(f"Testing: {method} {endpoint}", "INFO")

        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
            elif method == "POST":
                response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(f"{BASE_URL}{endpoint}", headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(f"{BASE_URL}{endpoint}", headers=headers)
            else:
                self.log(f"Unknown method: {method}", "ERROR")
                return None

            success = response.status_code == expected_status
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "status": response.status_code,
                "expected": expected_status,
                "success": success
            })

            if success:
                self.log(f"✓ {name}: Status {response.status_code}", "SUCCESS")
                try:
                    return response.json() if response.text else {}
                except:
                    return {"text": response.text}
            else:
                self.log(f"✗ {name}: Expected {expected_status}, got {response.status_code}", "ERROR")
                self.log(f"  Response: {response.text[:200]}", "ERROR")
                return None

        except Exception as e:
            self.log(f"✗ {name}: Exception - {str(e)}", "ERROR")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "success": False
            })
            return None

    def setup_authentication(self):
        """Setup authentication and get portfolio ID"""
        self.log("=== AUTHENTICATION SETUP ===", "INFO")

        # Login
        login_data = {"email": EMAIL, "password": PASSWORD}
        result = self.test_endpoint(
            "Authentication",
            "POST",
            "/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            data=login_data
        )

        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log(f"Token obtained: {self.token[:50]}...", "SUCCESS")

            # Get user info
            headers = {"Authorization": f"Bearer {self.token}"}
            user_info = self.test_endpoint(
                "Get Current User",
                "GET",
                "/api/v1/auth/me",
                headers=headers
            )

            if user_info and "portfolio_id" in user_info:
                self.portfolio_id = user_info["portfolio_id"]
                self.log(f"Portfolio ID: {self.portfolio_id}", "SUCCESS")
                return True

        self.log("Authentication failed", "ERROR")
        return False

    def test_list_target_prices(self):
        """Test GET /target-prices/{portfolio_id}"""
        self.log("\n=== TEST: LIST TARGET PRICES ===", "INFO")
        headers = {"Authorization": f"Bearer {self.token}"}

        # Test without filters
        result = self.test_endpoint(
            "List All Target Prices",
            "GET",
            f"/api/v1/target-prices/{self.portfolio_id}",
            headers=headers
        )

        if result and isinstance(result, list):
            self.log(f"Found {len(result)} target prices", "SUCCESS")
            if result:
                first = result[0]
                self.log(f"Sample: {first.get('symbol')} - EOY: {first.get('target_price_eoy')}", "INFO")

        # Test with symbol filter
        result = self.test_endpoint(
            "List with Symbol Filter",
            "GET",
            f"/api/v1/target-prices/{self.portfolio_id}",
            headers=headers,
            params={"symbol": "AAPL"}
        )

        if result:
            self.log(f"Filtered results: {len(result)} for AAPL", "SUCCESS")

    def test_create_target_price(self):
        """Test POST /target-prices/{portfolio_id}"""
        self.log("\n=== TEST: CREATE TARGET PRICE ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        target_data = {
            "symbol": "TEST1",
            "position_type": "LONG",
            "target_price_eoy": 150.00,
            "target_price_next_year": 180.00,
            "downside_target_price": 120.00,
            "current_price": 140.00
        }

        result = self.test_endpoint(
            "Create Single Target Price",
            "POST",
            f"/api/v1/target-prices/{self.portfolio_id}",
            headers=headers,
            data=target_data
        )

        if result and "id" in result:
            self.created_target_ids.append(result["id"])
            self.log(f"Created target price ID: {result['id']}", "SUCCESS")
            self.log(f"Expected Return EOY: {result.get('expected_return_eoy')}%", "INFO")
            return result["id"]
        return None

    def test_get_single_target(self, target_id: str):
        """Test GET /target-prices/target/{id}"""
        self.log("\n=== TEST: GET SINGLE TARGET PRICE ===", "INFO")
        headers = {"Authorization": f"Bearer {self.token}"}

        result = self.test_endpoint(
            "Get Single Target Price",
            "GET",
            f"/api/v1/target-prices/target/{target_id}",
            headers=headers
        )

        if result:
            self.log(f"Retrieved: {result.get('symbol')} - Current: ${result.get('current_price')}", "SUCCESS")

    def test_update_target(self, target_id: str):
        """Test PUT /target-prices/target/{id}"""
        self.log("\n=== TEST: UPDATE TARGET PRICE ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        update_data = {
            "target_price_eoy": 160.00,
            "target_price_next_year": 190.00
        }

        result = self.test_endpoint(
            "Update Target Price",
            "PUT",
            f"/api/v1/target-prices/target/{target_id}",
            headers=headers,
            data=update_data
        )

        if result:
            self.log(f"Updated EOY target to: ${result.get('target_price_eoy')}", "SUCCESS")
            self.log(f"New Expected Return: {result.get('expected_return_eoy')}%", "INFO")

    def test_bulk_create(self):
        """Test POST /target-prices/{portfolio_id}/bulk"""
        self.log("\n=== TEST: BULK CREATE ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        bulk_data = {
            "target_prices": [
                {
                    "symbol": "BULK1",
                    "position_type": "LONG",
                    "target_price_eoy": 100.00,
                    "target_price_next_year": 110.00,
                    "downside_target_price": 80.00,
                    "current_price": 95.00
                },
                {
                    "symbol": "BULK2",
                    "position_type": "SHORT",
                    "target_price_eoy": 50.00,
                    "target_price_next_year": 45.00,
                    "downside_target_price": 60.00,
                    "current_price": 55.00
                }
            ]
        }

        result = self.test_endpoint(
            "Bulk Create Target Prices",
            "POST",
            f"/api/v1/target-prices/{self.portfolio_id}/bulk",
            headers=headers,
            data=bulk_data
        )

        if result and "created" in result:
            self.log(f"Created {result['created']} target prices", "SUCCESS")
            if "target_prices" in result:
                for tp in result["target_prices"]:
                    self.created_target_ids.append(tp["id"])

    def test_bulk_update(self):
        """Test PUT /target-prices/{portfolio_id}/bulk-update"""
        self.log("\n=== TEST: BULK UPDATE ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        update_data = {
            "updates": [
                {
                    "symbol": "BULK1",
                    "position_type": "LONG",
                    "target_price_eoy": 105.00
                },
                {
                    "symbol": "BULK2",
                    "position_type": "SHORT",
                    "target_price_eoy": 48.00
                }
            ]
        }

        result = self.test_endpoint(
            "Bulk Update Target Prices",
            "PUT",
            f"/api/v1/target-prices/{self.portfolio_id}/bulk-update",
            headers=headers,
            data=update_data
        )

        if result and "updated" in result:
            self.log(f"Updated {result['updated']} target prices", "SUCCESS")

    def test_csv_export(self):
        """Test POST /target-prices/{portfolio_id}/export"""
        self.log("\n=== TEST: CSV EXPORT ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        export_data = {
            "format": "csv",
            "include_metadata": False
        }

        result = self.test_endpoint(
            "Export to CSV",
            "POST",
            f"/api/v1/target-prices/{self.portfolio_id}/export",
            headers=headers,
            data=export_data
        )

        if result and "csv" in result:
            csv_content = result["csv"]
            lines = csv_content.split('\n')
            self.log(f"Exported {len(lines)-1} rows (including header)", "SUCCESS")
            self.log(f"First line: {lines[0][:100]}...", "INFO")

    def test_csv_import(self):
        """Test POST /target-prices/{portfolio_id}/import-csv"""
        self.log("\n=== TEST: CSV IMPORT ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Simple CSV content
        csv_content = """symbol,position_type,target_price_eoy,target_price_next_year,downside_target_price,current_price
CSV1,LONG,200.00,220.00,180.00,190.00
CSV2,LONG,150.00,165.00,135.00,145.00"""

        import_data = {
            "csv_content": csv_content,
            "update_existing": False
        }

        result = self.test_endpoint(
            "Import from CSV",
            "POST",
            f"/api/v1/target-prices/{self.portfolio_id}/import-csv",
            headers=headers,
            data=import_data
        )

        if result:
            self.log(f"Import results: Created={result.get('created', 0)}, Updated={result.get('updated', 0)}", "SUCCESS")
            if result.get("errors"):
                self.log(f"Errors: {result['errors']}", "WARNING")

    def test_delete_target(self, target_id: str):
        """Test DELETE /target-prices/target/{id}"""
        self.log("\n=== TEST: DELETE TARGET PRICE ===", "INFO")
        headers = {"Authorization": f"Bearer {self.token}"}

        result = self.test_endpoint(
            "Delete Target Price",
            "DELETE",
            f"/api/v1/target-prices/target/{target_id}",
            headers=headers
        )

        if result:
            self.log(f"Deleted: {result.get('deleted', 0)} records", "SUCCESS")

    def test_error_handling(self):
        """Test error handling scenarios"""
        self.log("\n=== TEST: ERROR HANDLING ===", "INFO")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Test duplicate creation
        duplicate_data = {
            "symbol": "TEST1",
            "position_type": "LONG",
            "target_price_eoy": 200.00
        }

        self.test_endpoint(
            "Duplicate Creation (Should Fail)",
            "POST",
            f"/api/v1/target-prices/{self.portfolio_id}",
            headers=headers,
            data=duplicate_data,
            expected_status=400
        )

        # Test invalid UUID
        self.test_endpoint(
            "Invalid UUID (Should Fail)",
            "GET",
            "/api/v1/target-prices/invalid-uuid",
            headers=headers,
            expected_status=422
        )

        # Test unauthorized access
        self.test_endpoint(
            "Unauthorized Access (Should Fail)",
            "GET",
            f"/api/v1/target-prices/{self.portfolio_id}",
            expected_status=401
        )

    def cleanup(self):
        """Clean up created test data"""
        self.log("\n=== CLEANUP ===", "INFO")
        headers = {"Authorization": f"Bearer {self.token}"}

        for target_id in self.created_target_ids:
            try:
                response = requests.delete(
                    f"{BASE_URL}/api/v1/target-prices/target/{target_id}",
                    headers=headers
                )
                if response.status_code == 200:
                    self.log(f"Cleaned up target ID: {target_id}", "SUCCESS")
            except:
                pass

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get("success"))
        failed = total - passed

        self.log(f"Total Tests: {total}", "INFO")
        self.log(f"Passed: {passed}", "SUCCESS")
        if failed > 0:
            self.log(f"Failed: {failed}", "ERROR")

        if failed > 0:
            self.log("\nFailed Tests:", "ERROR")
            for result in self.test_results:
                if not result.get("success"):
                    error_msg = result.get('error') or f"Status {result.get('status')}"
                    self.log(f"  - {result['name']}: {error_msg}", "ERROR")

        self.log(f"\nSuccess Rate: {(passed/total)*100:.1f}%", "INFO")

    def run_all_tests(self):
        """Run complete test suite"""
        self.log("🚀 Starting Target Price API Comprehensive Test Suite", "INFO")
        self.log(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log(f"Base URL: {BASE_URL}", "INFO")
        self.log(f"Test User: {EMAIL}", "INFO")
        self.log("="*60, "INFO")

        # Setup
        if not self.setup_authentication():
            self.log("Authentication failed. Cannot proceed with tests.", "ERROR")
            return False

        # Run all tests
        self.test_list_target_prices()

        # Create and test CRUD operations
        target_id = self.test_create_target_price()
        if target_id:
            self.test_get_single_target(target_id)
            self.test_update_target(target_id)

        # Bulk operations
        self.test_bulk_create()
        self.test_bulk_update()

        # Import/Export
        self.test_csv_export()
        self.test_csv_import()

        # Error handling
        self.test_error_handling()

        # Delete test (do this last)
        if target_id:
            self.test_delete_target(target_id)

        # Cleanup
        self.cleanup()

        # Summary
        self.print_summary()

        return all(r.get("success", False) for r in self.test_results if "Fail" not in r.get("name", ""))

if __name__ == "__main__":
    tester = TargetPriceAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)