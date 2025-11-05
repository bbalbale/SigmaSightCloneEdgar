#!/usr/bin/env python3
"""
Complete authentication testing script for SigmaSight backend.
Tests all authentication flows including registration, login, token refresh, and protected routes.
"""

import asyncio
import httpx
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"

# Test data
import time
TEST_USER = {
    "email": f"test_auth_{int(time.time())}@example.com",
    "password": "testpassword123",
    "full_name": "Test Auth User"
}

DEMO_USER = {
    "email": "demo_individual@sigmasight.com",
    "password": "demo12345"
}

INVALID_USER = {
    "email": "nonexistent@example.com",
    "password": "wrongpassword"
}


class AuthTester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL)
        self.token = None
        self.results = []
        
    async def close(self):
        await self.client.aclose()
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        print(f"\n{status}: {test_name}")
        if details:
            print(f"  Details: {details}")
    
    async def test_registration(self):
        """Test user registration flow"""
        print("\n" + "="*50)
        print("Testing User Registration")
        print("="*50)
        
        # Test successful registration
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                json=TEST_USER
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "User Registration - Success",
                    True,
                    f"Created user: {data['email']}, User ID: {data['id']}"
                )
            else:
                self.log_result(
                    "User Registration - Success",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
        except Exception as e:
            self.log_result("User Registration - Success", False, str(e))
        
        # Test duplicate registration
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                json=TEST_USER
            )
            
            if response.status_code == 400:
                self.log_result(
                    "User Registration - Duplicate Prevention",
                    True,
                    "Correctly rejected duplicate email"
                )
            else:
                self.log_result(
                    "User Registration - Duplicate Prevention",
                    False,
                    f"Expected 400, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("User Registration - Duplicate Prevention", False, str(e))
        
        # Test invalid email
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": "invalid-email",
                    "password": "password123",
                    "full_name": "Invalid Email"
                }
            )
            
            if response.status_code == 422:
                self.log_result(
                    "User Registration - Email Validation",
                    True,
                    "Correctly rejected invalid email format"
                )
            else:
                self.log_result(
                    "User Registration - Email Validation",
                    False,
                    f"Expected 422, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("User Registration - Email Validation", False, str(e))
        
        # Test short password
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": "short@example.com",
                    "password": "short",
                    "full_name": "Short Password"
                }
            )
            
            if response.status_code == 422:
                self.log_result(
                    "User Registration - Password Validation",
                    True,
                    "Correctly rejected short password"
                )
            else:
                self.log_result(
                    "User Registration - Password Validation",
                    False,
                    f"Expected 422, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("User Registration - Password Validation", False, str(e))
    
    async def test_login(self):
        """Test login flow"""
        print("\n" + "="*50)
        print("Testing User Login")
        print("="*50)
        
        # Test successful login with test user
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.log_result(
                    "Login - Test User Success",
                    True,
                    f"Token type: {data['token_type']}, User: {data['email']}"
                )
            else:
                self.log_result(
                    "Login - Test User Success",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
        except Exception as e:
            self.log_result("Login - Test User Success", False, str(e))
        
        # Test successful login with demo user
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                json=DEMO_USER
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Login - Demo User Success",
                    True,
                    f"Demo user logged in: {data['email']}"
                )
            else:
                self.log_result(
                    "Login - Demo User Success",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
        except Exception as e:
            self.log_result("Login - Demo User Success", False, str(e))
        
        # Test invalid credentials
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                json=INVALID_USER
            )
            
            if response.status_code == 401:
                self.log_result(
                    "Login - Invalid Credentials",
                    True,
                    "Correctly rejected invalid credentials"
                )
            else:
                self.log_result(
                    "Login - Invalid Credentials",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Login - Invalid Credentials", False, str(e))
        
        # Test wrong password
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": "wrongpassword"
                }
            )
            
            if response.status_code == 401:
                self.log_result(
                    "Login - Wrong Password",
                    True,
                    "Correctly rejected wrong password"
                )
            else:
                self.log_result(
                    "Login - Wrong Password",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Login - Wrong Password", False, str(e))
    
    async def test_token_refresh(self):
        """Test token refresh"""
        print("\n" + "="*50)
        print("Testing Token Refresh")
        print("="*50)
        
        if not self.token:
            self.log_result("Token Refresh", False, "No token available from login")
            return
        
        # Test successful refresh
        try:
            response = await self.client.post(
                "/api/v1/auth/refresh",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                self.log_result(
                    "Token Refresh - Success",
                    True,
                    f"New token generated, different from old: {new_token != self.token}"
                )
                self.token = new_token  # Update to new token
            else:
                self.log_result(
                    "Token Refresh - Success",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
        except Exception as e:
            self.log_result("Token Refresh - Success", False, str(e))
        
        # Test refresh without token
        try:
            response = await self.client.post("/api/v1/auth/refresh")
            
            if response.status_code in [401, 403]:
                self.log_result(
                    "Token Refresh - No Token",
                    True,
                    f"Correctly rejected request without token (status: {response.status_code})"
                )
            else:
                self.log_result(
                    "Token Refresh - No Token",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Token Refresh - No Token", False, str(e))
        
        # Test refresh with invalid token
        try:
            response = await self.client.post(
                "/api/v1/auth/refresh",
                headers={"Authorization": "Bearer invalid_token_here"}
            )
            
            if response.status_code == 401:
                self.log_result(
                    "Token Refresh - Invalid Token",
                    True,
                    "Correctly rejected invalid token"
                )
            else:
                self.log_result(
                    "Token Refresh - Invalid Token",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Token Refresh - Invalid Token", False, str(e))
    
    async def test_protected_routes(self):
        """Test access to protected routes"""
        print("\n" + "="*50)
        print("Testing Protected Routes")
        print("="*50)
        
        # Test /auth/me endpoint with valid token
        if self.token:
            try:
                response = await self.client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        "Protected Route - /auth/me with Token",
                        True,
                        f"User info retrieved: {data['email']}"
                    )
                else:
                    self.log_result(
                        "Protected Route - /auth/me with Token",
                        False,
                        f"Status: {response.status_code}, Error: {response.text}"
                    )
            except Exception as e:
                self.log_result("Protected Route - /auth/me with Token", False, str(e))
        
        # Test /auth/me without token
        try:
            response = await self.client.get("/api/v1/auth/me")
            
            if response.status_code in [401, 403]:
                self.log_result(
                    "Protected Route - /auth/me without Token",
                    True,
                    f"Correctly rejected request without token (status: {response.status_code})"
                )
            else:
                self.log_result(
                    "Protected Route - /auth/me without Token",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Protected Route - /auth/me without Token", False, str(e))
        
        # Test portfolio endpoint with token
        if self.token:
            try:
                response = await self.client.get(
                    "/api/v1/portfolio/summary",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                
                if response.status_code == 200:
                    self.log_result(
                        "Protected Route - Portfolio with Token",
                        True,
                        "Successfully accessed portfolio endpoint"
                    )
                else:
                    self.log_result(
                        "Protected Route - Portfolio with Token",
                        False,
                        f"Status: {response.status_code}, Error: {response.text}"
                    )
            except Exception as e:
                self.log_result("Protected Route - Portfolio with Token", False, str(e))
        
        # Test portfolio endpoint without token
        try:
            response = await self.client.get("/api/v1/portfolio/summary")
            
            if response.status_code in [401, 403]:
                self.log_result(
                    "Protected Route - Portfolio without Token",
                    True,
                    f"Correctly rejected portfolio access without token (status: {response.status_code})"
                )
            else:
                self.log_result(
                    "Protected Route - Portfolio without Token",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("Protected Route - Portfolio without Token", False, str(e))
    
    async def test_jwt_validation(self):
        """Test JWT token validation edge cases"""
        print("\n" + "="*50)
        print("Testing JWT Validation")
        print("="*50)
        
        # Test malformed token
        try:
            response = await self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer malformed.token.here"}
            )
            
            if response.status_code == 401:
                self.log_result(
                    "JWT Validation - Malformed Token",
                    True,
                    "Correctly rejected malformed token"
                )
            else:
                self.log_result(
                    "JWT Validation - Malformed Token",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
        except Exception as e:
            self.log_result("JWT Validation - Malformed Token", False, str(e))
        
        # Test token with wrong signature (if we can create one)
        # This would require knowing the secret key format
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
    
    async def run_all_tests(self):
        """Run all authentication tests"""
        print("\n🔐 SigmaSight Authentication Testing Suite")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Testing against: {BASE_URL}")
        
        await self.test_registration()
        await self.test_login()
        await self.test_token_refresh()
        await self.test_protected_routes()
        await self.test_jwt_validation()
        
        self.print_summary()


async def main():
    """Main test runner"""
    tester = AuthTester()
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
