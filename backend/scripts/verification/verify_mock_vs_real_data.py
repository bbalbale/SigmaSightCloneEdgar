#!/usr/bin/env python3
"""
Verify which endpoints return real vs mock data after batch processing
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import httpx

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test account
TEST_ACCOUNT = {
    "email": "demo_individual@sigmasight.com",
    "password": "demo12345",
    "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69"
}


class DataVerifier:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self) -> str:
        """Login and get JWT token"""
        response = await self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": TEST_ACCOUNT["email"], "password": TEST_ACCOUNT["password"]}
        )
        return response.json().get("access_token")
    
    async def check_historical_prices(self, token: str) -> Dict[str, Any]:
        """Check if historical prices are real or mock"""
        headers = {"Authorization": f"Bearer {token}"}
        portfolio_id = TEST_ACCOUNT["portfolio_id"]
        
        response = await self.client.get(
            f"{API_PREFIX}/data/prices/historical/{portfolio_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch: {response.status_code}"}
        
        data = response.json()
        analysis = {
            "endpoint": "prices/historical",
            "status": "unknown",
            "evidence": []
        }
        
        # Check for mock data patterns - new structure has "symbols" key
        if "symbols" in data:
            # Take first symbol's data
            symbols_data = data["symbols"]
            if symbols_data:
                first_symbol = list(symbols_data.keys())[0]
                symbol_data = symbols_data[first_symbol]
                
                # Get close prices
                close_prices = symbol_data.get("closes", [])[:10]  # First 10 prices
                
                if close_prices:
                    # Check if all prices are in the suspicious 200-206 range
                    if all(200 <= price <= 206 for price in close_prices):
                        analysis["status"] = "MOCK"
                        analysis["evidence"].append(f"All prices in 200-206 range: {close_prices[:5]}")
                    
                    # Check if prices are too round (multiples of 10)
                    elif all(price % 10 == 0 for price in close_prices):
                        analysis["status"] = "MOCK"
                        analysis["evidence"].append(f"Prices are suspiciously round: {close_prices[:5]}")
                    
                    # Check if prices have realistic variation
                    elif len(set(close_prices)) > 1 and min(close_prices) > 0:
                        price_range = max(close_prices) - min(close_prices)
                        avg_price = sum(close_prices) / len(close_prices)
                        variation_pct = (price_range / avg_price) * 100
                        
                        if variation_pct < 0.01:  # Less than 0.01% variation
                            analysis["status"] = "MOCK"
                            analysis["evidence"].append(f"Unrealistic low variation: {variation_pct:.4f}%")
                        else:
                            analysis["status"] = "REAL"
                            analysis["evidence"].append(f"Realistic price variation: {variation_pct:.2f}%")
                            analysis["evidence"].append(f"Price range: ${min(close_prices):.2f} - ${max(close_prices):.2f}")
                
        return analysis
    
    async def check_market_quotes(self, token: str) -> Dict[str, Any]:
        """Check if market quotes are real or mock"""
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await self.client.get(
            f"{API_PREFIX}/data/prices/quotes",
            headers=headers,
            params={"symbols": "AAPL,MSFT,GOOGL,TSLA,NVDA"}
        )
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch: {response.status_code}"}
        
        data = response.json()
        analysis = {
            "endpoint": "prices/quotes",
            "status": "unknown",
            "evidence": []
        }
        
        # Check response structure - multiple possible formats
        quotes = None
        if "data" in data:
            quotes = data["data"]
        elif "quotes" in data:
            quotes = data["quotes"]
        elif isinstance(data, (dict, list)):
            # Direct dictionary or list of quotes
            quotes = data
            
        if quotes:
            # Handle list or dict format
            if isinstance(quotes, list):
                # List of quotes
                if len(quotes) < 5:
                    analysis["status"] = "LIMITED"
                    analysis["evidence"].append(f"Only {len(quotes)} quotes returned (requested 5)")
                
                for quote in quotes:
                    if isinstance(quote, dict):
                        symbol = quote.get("symbol", "UNKNOWN")
                        price = quote.get("price", quote.get("current_price", 0))
                        if 100 <= price <= 200:
                            analysis["evidence"].append(f"{symbol}: Suspicious price range ${price}")
                        
                        if "timestamp" in quote or "updated_at" in quote:
                            analysis["evidence"].append(f"{symbol}: Has timestamp")
                        if "volume" in quote and quote["volume"] > 0:
                            analysis["evidence"].append(f"{symbol}: Has volume data")
            
            elif isinstance(quotes, dict):
                # Dictionary of quotes
                if len(quotes) < 5:
                    analysis["status"] = "LIMITED"
                    analysis["evidence"].append(f"Only {len(quotes)} symbols returned (requested 5)")
                
                for symbol, quote in quotes.items():
                    if isinstance(quote, dict):
                        price = quote.get("price", quote.get("current_price", 0))
                        if 100 <= price <= 200:
                            analysis["evidence"].append(f"{symbol}: Suspicious price range ${price}")
                        
                        if "timestamp" in quote or "updated_at" in quote:
                            analysis["evidence"].append(f"{symbol}: Has timestamp")
                        if "volume" in quote and quote["volume"] > 0:
                            analysis["evidence"].append(f"{symbol}: Has volume data")
            
            # Determine status based on evidence
            if any("Suspicious" in e for e in analysis["evidence"]):
                analysis["status"] = "MOCK"
            elif len(quotes) >= 5:
                analysis["status"] = "REAL"
            else:
                analysis["status"] = "LIMITED"
        
        return analysis
    
    async def check_portfolio_complete(self, token: str) -> Dict[str, Any]:
        """Check if portfolio complete endpoint has real data"""
        headers = {"Authorization": f"Bearer {token}"}
        portfolio_id = TEST_ACCOUNT["portfolio_id"]
        
        response = await self.client.get(
            f"{API_PREFIX}/data/portfolio/{portfolio_id}/complete",
            headers=headers
        )
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch: {response.status_code}"}
        
        data = response.json()
        analysis = {
            "endpoint": "portfolio/complete",
            "status": "unknown",
            "evidence": []
        }
        
        # Check cash_balance - handle different response structures
        portfolio_data = data
        if "data" in data:
            portfolio_data = data["data"]
        elif "portfolio" in data:
            portfolio_data = data["portfolio"]
            
        if portfolio_data:
            cash_balance = portfolio_data.get("cash_balance", None)
            
            if cash_balance == 0 or cash_balance is None:
                analysis["evidence"].append(f"cash_balance is {cash_balance} (likely hardcoded)")
                analysis["status"] = "PARTIAL"
            else:
                analysis["evidence"].append(f"cash_balance has value: ${cash_balance:,.2f}")
                analysis["status"] = "REAL"  # Non-zero cash balance indicates real calculation
            
            # Check if we have calculation data
            if "risk_metrics" in portfolio_data:
                analysis["evidence"].append("Has risk_metrics")
            if "factor_exposures" in portfolio_data:
                analysis["evidence"].append("Has factor_exposures")
            if "positions" in portfolio_data and len(portfolio_data["positions"]) > 0:
                analysis["evidence"].append(f"Has {len(portfolio_data['positions'])} positions")
                
            # Determine final status (only if not already set)
            if analysis["status"] == "unknown":
                if cash_balance != 0 and "positions" in portfolio_data:
                    analysis["status"] = "REAL"
                elif "positions" in portfolio_data:
                    analysis["status"] = "PARTIAL"
                else:
                    analysis["status"] = "MOCK"
        
        return analysis
    
    async def check_factor_etf_prices(self, token: str) -> Dict[str, Any]:
        """Check if factor ETF prices are real or mock"""
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await self.client.get(
            f"{API_PREFIX}/data/factors/etf-prices",
            headers=headers,
            params={"lookback_days": 30}
        )
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch: {response.status_code}"}
        
        data = response.json()
        analysis = {
            "endpoint": "factors/etf-prices",
            "status": "unknown",
            "evidence": []
        }
        
        # Handle different response structures
        etf_data = data
        if "data" in data:
            etf_data = data["data"]
        elif "etf_prices" in data:
            etf_data = data["etf_prices"]
            
        if etf_data:
            # Check if we have expected ETFs for 7-factor model
            # Note: QQQ is not part of the factor model, SLY is used for Size factor
            expected_etfs = ["SPY", "VTV", "VUG", "MTUM", "QUAL", "SLY", "USMV"]
            found_etfs = []
            
            for etf_symbol in expected_etfs:
                if etf_symbol in etf_data:
                    found_etfs.append(etf_symbol)
                    prices = etf_data[etf_symbol]
                    if isinstance(prices, list) and len(prices) > 0:
                        # Check first price
                        first_price = prices[0].get("close", prices[0].get("price", 0))
                        if 100 <= first_price <= 200:
                            analysis["evidence"].append(f"{etf_symbol}: Suspicious price range")
            
            analysis["evidence"].append(f"Found {len(found_etfs)}/{len(expected_etfs)} ETFs")
            
            # Determine status
            if len(found_etfs) == len(expected_etfs) and not any("Suspicious" in e for e in analysis["evidence"]):
                analysis["status"] = "REAL"
            elif len(found_etfs) > 0:
                analysis["status"] = "PARTIAL"
            else:
                analysis["status"] = "MOCK"
        
        return analysis
    
    async def run_verification(self):
        """Run all verification checks"""
        print("=" * 60)
        print("MOCK vs REAL DATA VERIFICATION")
        print("=" * 60)
        print()
        
        # Login
        token = await self.login()
        if not token:
            print("❌ Login failed")
            return
        
        print("✅ Login successful")
        print()
        
        # Run all checks
        checks = [
            self.check_historical_prices(token),
            self.check_market_quotes(token),
            self.check_portfolio_complete(token),
            self.check_factor_etf_prices(token)
        ]
        
        results = await asyncio.gather(*checks)
        
        # Print results
        print("VERIFICATION RESULTS:")
        print("-" * 40)
        
        real_count = 0
        mock_count = 0
        partial_count = 0
        
        for result in results:
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
                
            endpoint = result["endpoint"]
            status = result["status"]
            
            if status == "REAL":
                icon = "✅"
                real_count += 1
            elif status == "MOCK":
                icon = "🔴"
                mock_count += 1
            elif status == "PARTIAL":
                icon = "🟡"
                partial_count += 1
            else:
                icon = "❓"
            
            print(f"\n{icon} {endpoint}: {status}")
            
            if result["evidence"]:
                print("  Evidence:")
                for evidence in result["evidence"]:
                    print(f"    - {evidence}")
        
        # Summary
        print()
        print("=" * 60)
        print("SUMMARY:")
        print(f"  ✅ REAL DATA: {real_count} endpoints")
        print(f"  🟡 PARTIAL DATA: {partial_count} endpoints")
        print(f"  🔴 MOCK DATA: {mock_count} endpoints")
        print("=" * 60)
        
        return {
            "real": real_count,
            "partial": partial_count,
            "mock": mock_count
        }


async def main():
    """Main entry point"""
    async with DataVerifier() as verifier:
        results = await verifier.run_verification()
        
        # Return exit code based on results
        if results["mock"] > 0:
            return 1  # Still have mock data
        else:
            return 0  # All real data


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)