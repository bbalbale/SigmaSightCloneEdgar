#!/usr/bin/env python3
"""
Comprehensive test script for Raw Data APIs (/api/v1/data/)
Tests all endpoints against 3 demo accounts to verify REAL data vs mock data
Generates detailed report: RAW_DATA_API_TEST_RESULTS.md

Author: SigmaSight Team
Date: 2025-08-26
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.database import get_async_session, AsyncSessionLocal
from app.models.users import User, Portfolio

setup_logging()
logger = get_logger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Demo accounts to test
TEST_ACCOUNTS = [
    {
        "email": "demo_individual@sigmasight.com",
        "password": "demo12345",
        "name": "Individual Investor",
        "expected_positions": 16
    },
    {
        "email": "demo_hnw@sigmasight.com",
        "password": "demo12345",
        "name": "High Net Worth",
        "expected_positions": 17
    },
    {
        "email": "demo_hedgefundstyle@sigmasight.com",
        "password": "demo12345",
        "name": "Hedge Fund Style",
        "expected_positions": 30
    }
]

# Endpoints to test - ONLY /data/ namespace endpoints from API_SPECIFICATIONS_V1.4.4.md
RAW_DATA_ENDPOINTS = [
    "portfolio/{id}/complete",
    "portfolio/{id}/data-quality",
    "positions/details",  # Requires portfolio_id as query param
    "prices/historical/{id}",
    "prices/quotes",
    "factors/etf-prices"
]

# Known portfolio IDs for demo accounts (hardcoded since no /data/portfolios endpoint exists)
# These will be fetched from database
DEMO_PORTFOLIOS = {
    "demo_individual@sigmasight.com": None,  # Will be populated
    "demo_hnw@sigmasight.com": None,  # Will be populated
    "demo_hedgefundstyle@sigmasight.com": None  # Will be populated
}


class RawDataAPITester:
    """Test harness for Raw Data APIs"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.results = []
        self.tokens = {}
        self.portfolios = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self, email: str, password: str) -> Optional[str]:
        """Login and get JWT token"""
        try:
            response = await self.client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                logger.error(f"Login failed for {email}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Login error for {email}: {e}")
            return None
    
    async def test_endpoint(
        self, 
        token: str, 
        endpoint: str, 
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Test a single endpoint"""
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            start_time = datetime.now()
            
            if method == "GET":
                response = await self.client.get(
                    f"{API_PREFIX}/data/{endpoint}",
                    headers=headers,
                    params=params
                )
            elif method == "POST":
                response = await self.client.post(
                    f"{API_PREFIX}/data/{endpoint}",
                    headers=headers,
                    json=json_data
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                data = response.json()
                result["data"] = data
                result["data_size"] = len(json.dumps(data))
                
                # Analyze data quality
                result["analysis"] = self.analyze_response_data(endpoint, data)
            else:
                result["error"] = response.text
                
            return result
            
        except Exception as e:
            logger.error(f"Error testing {endpoint}: {e}")
            return {
                "endpoint": endpoint,
                "success": False,
                "error": str(e)
            }
    
    def analyze_response_data(self, endpoint: str, data: Any) -> Dict[str, Any]:
        """Analyze response data for quality issues"""
        analysis = {
            "has_data": bool(data),
            "issues": [],
            "warnings": []
        }
        
        # Check for mock data indicators
        if "historical" in endpoint or "prices" in endpoint:
            # Check if prices look random/mock
            if isinstance(data, dict) and "data" in data:
                prices = data["data"]
                if isinstance(prices, list) and len(prices) > 0:
                    # Check for suspiciously round numbers
                    if all(isinstance(p.get("close"), (int, float)) and 
                          p.get("close") % 10 == 0 for p in prices[:5]):
                        analysis["issues"].append("Prices appear to be mock data (too round)")
                    
                    # Check for random patterns
                    if len(prices) > 10:
                        closes = [p.get("close", 0) for p in prices[:10]]
                        if all(100 <= c <= 200 for c in closes):
                            analysis["warnings"].append("Prices in suspicious range (100-200)")
        
        # Check for hardcoded values
        if "portfolio" in endpoint:
            if isinstance(data, dict):
                if data.get("cash_balance") == 0:
                    analysis["issues"].append("cash_balance is hardcoded to 0")
                    
                if "data" in data:
                    for item in data["data"]:
                        if isinstance(item, dict) and item.get("cash_balance") == 0:
                            analysis["issues"].append("cash_balance is hardcoded to 0")
        
        # Check for TODO or stub responses
        if isinstance(data, dict):
            if "TODO" in str(data) or "todo" in str(data).lower():
                analysis["issues"].append("Response contains TODO markers")
            
            if data.get("message", "").startswith("TODO"):
                analysis["issues"].append("Endpoint returns TODO stub")
        
        # Check for null/missing critical fields
        if "risk_metrics" in endpoint:
            if isinstance(data, dict) and "data" in data:
                metrics = data["data"]
                if not metrics or metrics.get("beta") is None:
                    analysis["issues"].append("Missing critical risk metrics")
        
        if "factor_exposures" in endpoint:
            if isinstance(data, dict) and "data" in data:
                exposures = data["data"]
                if not exposures:
                    analysis["issues"].append("No factor exposures returned")
                elif isinstance(exposures, list):
                    for exp in exposures:
                        if exp.get("exposure_value") is None:
                            analysis["warnings"].append("Missing exposure values")
        
        # Check Greeks for options
        if "positions" in endpoint:
            if isinstance(data, dict) and "data" in data:
                positions = data["data"]
                for pos in positions:
                    if pos.get("position_type") in ["LC", "LP", "SC", "SP"]:
                        if not pos.get("greeks") or pos["greeks"].get("delta") is None:
                            analysis["warnings"].append("Options positions missing Greeks")
        
        return analysis
    
    async def get_portfolio_ids(self):
        """Get portfolio IDs for all demo accounts from database"""
        async with AsyncSessionLocal() as db:
            for account in TEST_ACCOUNTS:
                stmt = select(User).where(User.email == account["email"])
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    stmt = select(Portfolio).where(Portfolio.user_id == user.id)
                    result = await db.execute(stmt)
                    portfolio = result.scalar_one_or_none()
                    
                    if portfolio:
                        DEMO_PORTFOLIOS[account["email"]] = str(portfolio.id)
                        logger.info(f"Found portfolio {portfolio.id} for {account['email']}")
                    else:
                        logger.warning(f"No portfolio found for {account['email']}")
                else:
                    logger.warning(f"User not found: {account['email']}")
    
    async def test_all_accounts(self):
        """Test all endpoints for all demo accounts"""
        # First get portfolio IDs from database
        await self.get_portfolio_ids()
        
        report_lines = [
            "# Raw Data API Test Results - /data/ Namespace Only",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"\nServer: {BASE_URL}",
            f"\nTesting ONLY /api/v1/data/ endpoints per API_SPECIFICATIONS_V1.4.4.md",
            "\n---\n"
        ]
        
        for account in TEST_ACCOUNTS:
            logger.info(f"Testing account: {account['name']}")
            report_lines.append(f"\n## Account: {account['name']}")
            report_lines.append(f"Email: {account['email']}")
            report_lines.append(f"Expected Positions: {account['expected_positions']}\n")
            
            # Login
            token = await self.login(account["email"], account["password"])
            if not token:
                report_lines.append("❌ **Login Failed**\n")
                continue
            
            report_lines.append("✅ **Login Successful**\n")
            
            # Get portfolio ID for this account
            portfolio_id = DEMO_PORTFOLIOS.get(account["email"])
            
            if not portfolio_id:
                report_lines.append("❌ **No portfolio found in database for this user**\n")
                continue
                
            report_lines.append(f"\n### Portfolio ID: {portfolio_id}\n")
                
            # Test each endpoint
            for endpoint_template in RAW_DATA_ENDPOINTS:
                endpoint = endpoint_template.replace("{id}", portfolio_id)
                
                # Special handling for endpoints with query parameters
                params = None
                if endpoint == "prices/quotes":
                    params = {"symbols": "AAPL,MSFT,GOOGL"}
                elif endpoint == "positions/details":
                    params = {"portfolio_id": portfolio_id}
                elif endpoint == "factors/etf-prices":
                    params = {"lookback_days": 30}
                
                result = await self.test_endpoint(token, endpoint, params=params)
                
                report_lines.append(f"\n#### Endpoint: /api/v1/data/{endpoint}")
                
                if result["success"]:
                    report_lines.append(f"- ✅ Status: {result['status_code']}")
                    report_lines.append(f"- Response Time: {result['response_time_ms']:.1f}ms")
                    report_lines.append(f"- Data Size: {result.get('data_size', 0):,} bytes")
                    
                    analysis = result.get("analysis", {})
                    
                    if analysis.get("issues"):
                        report_lines.append("\n**🔴 Critical Issues:**")
                        for issue in analysis["issues"]:
                            report_lines.append(f"- {issue}")
                    
                    if analysis.get("warnings"):
                        report_lines.append("\n**🟡 Warnings:**")
                        for warning in analysis["warnings"]:
                            report_lines.append(f"- {warning}")
                    
                    if not analysis.get("issues") and not analysis.get("warnings"):
                        report_lines.append("- 🟢 **No issues detected**")
                else:
                    report_lines.append(f"- ❌ **Failed**: {result.get('error', 'Unknown error')}")
            
            report_lines.append("\n---\n")
        
        # Summary section
        report_lines.append("\n## Summary of /data/ Namespace Endpoints\n")
        report_lines.append(f"### Endpoints Tested: {len(RAW_DATA_ENDPOINTS)}")
        for endpoint in RAW_DATA_ENDPOINTS:
            report_lines.append(f"- /api/v1/data/{endpoint}")
        
        report_lines.append("\n### Known Issues to Verify:")
        report_lines.append("1. **cash_balance** - Check if hardcoded to 0")
        report_lines.append("2. **Historical prices** - Verify if using real vs mock data")
        report_lines.append("3. **Market quotes** - Check if real-time or simulated")
        report_lines.append("4. **Greeks calculations** - Verify options positions have Greeks")
        report_lines.append("\n### Data Quality Issues:")
        report_lines.append("1. Factor ETF prices are mock data")
        report_lines.append("2. Some risk metrics may be placeholder values")
        report_lines.append("3. Correlation matrices might be simplified")
        
        report_lines.append("\n### Recommendations:")
        report_lines.append("1. **Priority 1**: Implement real market data connection")
        report_lines.append("2. **Priority 2**: Fix cash_balance implementation")
        report_lines.append("3. **Priority 3**: Calculate real Greeks for options")
        report_lines.append("4. **Priority 4**: Implement proper factor analysis")
        
        # Save report
        report_path = Path(__file__).parent.parent / "RAW_DATA_API_TEST_RESULTS.md"
        report_path.write_text("\n".join(report_lines))
        logger.info(f"Report saved to: {report_path}")
        
        return report_lines


async def main():
    """Run comprehensive Raw Data API tests"""
    logger.info("Starting Raw Data API comprehensive testing")
    
    async with RawDataAPITester() as tester:
        try:
            report = await tester.test_all_accounts()
            
            # Print summary to console
            print("\n" + "="*60)
            print("RAW DATA API TEST COMPLETED")
            print("="*60)
            print(f"Report saved to: RAW_DATA_API_TEST_RESULTS.md")
            print("\nQuick Summary:")
            
            # Count issues
            critical_count = sum(1 for line in report if "🔴" in line)
            warning_count = sum(1 for line in report if "🟡" in line)
            success_count = sum(1 for line in report if "🟢" in line)
            
            print(f"- 🟢 Success indicators: {success_count}")
            print(f"- 🟡 Warnings found: {warning_count}")
            print(f"- 🔴 Critical issues: {critical_count}")
            
            if critical_count > 0:
                print("\n⚠️ CRITICAL ISSUES DETECTED - Raw Data APIs need significant work")
                return 1
            else:
                print("\n✅ No critical issues found")
                return 0
                
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            print(f"\n❌ Test execution failed: {e}")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)