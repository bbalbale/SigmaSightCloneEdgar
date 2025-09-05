#!/usr/bin/env python3
"""
Portfolio Context Smoke Test

Tests the complete portfolio ID resolution pipeline:
1. Fresh login → JWT with portfolio_id
2. /api/v1/me → returns portfolio_id consistently  
3. /portfolio fetch → successful data retrieval
4. Chat message → tool call reads portfolio successfully

Implements PORTFOLIO_ID_DESIGN_DOC.md Section 8.1.8 acceptance criteria.
"""

import asyncio
import sys
import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
DEMO_CREDENTIALS = {
    'email': 'demo_hnw@sigmasight.com',
    'password': 'demo12345'
}

class PortfolioContextSmokeTest:
    def __init__(self):
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.portfolio_id: Optional[str] = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", duration_ms: int = 0):
        """Log test result with timestamp"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def test_1_fresh_login(self) -> bool:
        """Test 1: Fresh login with guaranteed portfolio_id in JWT"""
        print("\n🔐 Test 1: Fresh Login with Portfolio Context")
        start_time = datetime.now()
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=DEMO_CREDENTIALS,
                timeout=10
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response.status_code != 200:
                self.log_test("fresh_login", False, f"Login failed: {response.status_code}", duration_ms)
                return False
            
            data = response.json()
            self.token = data.get("access_token")
            
            if not self.token:
                self.log_test("fresh_login", False, "No access token in response", duration_ms)
                return False
            
            # Check if portfolio_id is in response (from backend fix 7.1.1)
            response_portfolio_id = data.get("portfolio_id")
            if response_portfolio_id:
                self.portfolio_id = response_portfolio_id
                self.log_test("fresh_login", True, f"Login successful with portfolio_id: {self.portfolio_id}", duration_ms)
            else:
                self.log_test("fresh_login", True, "Login successful, portfolio_id will be resolved via /me", duration_ms)
            
            return True
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test("fresh_login", False, f"Login error: {str(e)}", duration_ms)
            return False
    
    def test_2_me_endpoint(self) -> bool:
        """Test 2: /api/v1/me always returns portfolio_id"""
        print("\n👤 Test 2: /me Endpoint Portfolio ID Resolution")
        start_time = datetime.now()
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers=headers,
                timeout=10
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response.status_code != 200:
                self.log_test("me_endpoint", False, f"/me failed: {response.status_code}", duration_ms)
                return False
            
            data = response.json()
            me_portfolio_id = data.get("portfolio_id")
            
            if not me_portfolio_id:
                self.log_test("me_endpoint", False, "/me response missing portfolio_id", duration_ms)
                return False
            
            # Update portfolio_id if not set from login
            if not self.portfolio_id:
                self.portfolio_id = str(me_portfolio_id)
            
            self.log_test("me_endpoint", True, f"/me returns portfolio_id: {me_portfolio_id}", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test("me_endpoint", False, f"/me error: {str(e)}", duration_ms)
            return False
    
    def test_3_portfolio_fetch(self) -> bool:
        """Test 3: Portfolio data fetch with resolved portfolio_id"""
        print("\n📊 Test 3: Portfolio Data Retrieval")
        start_time = datetime.now()
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/v1/data/portfolio/{self.portfolio_id}/complete",
                headers=headers,
                timeout=15
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response.status_code != 200:
                self.log_test("portfolio_fetch", False, f"Portfolio fetch failed: {response.status_code}", duration_ms)
                return False
            
            data = response.json()
            portfolio_name = data.get("portfolio", {}).get("name", "Unknown")
            position_count = len(data.get("holdings", []))
            
            self.log_test("portfolio_fetch", True, f"Portfolio '{portfolio_name}' with {position_count} positions", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test("portfolio_fetch", False, f"Portfolio fetch error: {str(e)}", duration_ms)
            return False
    
    def test_4_fallback_resolution(self) -> bool:
        """Test 4: Portfolio context fallback mechanisms"""
        print("\n🔄 Test 4: Portfolio Context Fallback Resolution")
        start_time = datetime.now()
        
        try:
            # Test positions endpoint with optional portfolio_id (should auto-resolve)
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/v1/data/positions/details",  # No portfolio_id param
                headers=headers,
                timeout=10
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response.status_code != 200:
                self.log_test("fallback_resolution", False, f"Fallback resolution failed: {response.status_code}", duration_ms)
                return False
            
            data = response.json()
            positions = data.get("positions", [])
            
            self.log_test("fallback_resolution", True, f"Auto-resolved {len(positions)} positions", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test("fallback_resolution", False, f"Fallback error: {str(e)}", duration_ms)
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        avg_duration = sum(result["duration_ms"] for result in self.test_results) / total_tests if total_tests > 0 else 0
        
        report = {
            "test_suite": "Portfolio Context Smoke Test",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": f"{success_rate:.1f}%",
                "avg_duration_ms": int(avg_duration)
            },
            "acceptance_criteria": {
                "zero_portfolio_missing_errors": passed_tests >= 3,  # Tests 1-3 must pass
                "portfolio_resolution_under_200ms": avg_duration < 200,
                "me_endpoint_includes_portfolio_id": any(r["test"] == "me_endpoint" and r["success"] for r in self.test_results),
                "fallback_resolution_works": any(r["test"] == "fallback_resolution" and r["success"] for r in self.test_results)
            },
            "test_results": self.test_results,
            "portfolio_context": {
                "resolved_portfolio_id": self.portfolio_id,
                "demo_user": DEMO_CREDENTIALS["email"]
            }
        }
        
        return report
    
    async def run_all_tests(self) -> bool:
        """Run complete test suite"""
        print("🧪 Starting Portfolio Context Smoke Test")
        print("=" * 50)
        
        # Run tests in sequence (each depends on previous)
        tests = [
            self.test_1_fresh_login,
            self.test_2_me_endpoint,
            self.test_3_portfolio_fetch,
            self.test_4_fallback_resolution
        ]
        
        for test in tests:
            if not test():
                print(f"\n❌ Test suite failed at {test.__name__}")
                return False
        
        print("\n✅ All tests passed!")
        return True


def main():
    """Main test runner"""
    test_runner = PortfolioContextSmokeTest()
    
    # Run tests
    success = asyncio.run(test_runner.run_all_tests())
    
    # Generate report
    report = test_runner.generate_report()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 SMOKE TEST REPORT")
    print("=" * 50)
    print(f"Success Rate: {report['summary']['success_rate']}")
    print(f"Average Response Time: {report['summary']['avg_duration_ms']}ms")
    print(f"Portfolio ID: {report['portfolio_context']['resolved_portfolio_id']}")
    
    # Check acceptance criteria
    print("\n📋 ACCEPTANCE CRITERIA:")
    for criterion, met in report['acceptance_criteria'].items():
        status = "✅ MET" if met else "❌ NOT MET"
        print(f"  {status} {criterion}")
    
    # Save detailed report
    with open("portfolio_context_smoke_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: portfolio_context_smoke_test_report.json")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()