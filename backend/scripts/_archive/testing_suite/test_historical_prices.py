#!/usr/bin/env python3
"""Test the historical prices endpoint to understand its data structure and content"""

import asyncio
import json
import sys
from pathlib import Path
import httpx

sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

TEST_ACCOUNT = {
    "email": "demo_individual@sigmasight.com",
    "password": "demo12345",
    "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69"
}


async def test_historical_prices():
    """Test historical prices endpoint"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Login
        response = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": TEST_ACCOUNT["email"], "password": TEST_ACCOUNT["password"]}
        )
        token = response.json().get("access_token")
        
        if not token:
            print("❌ Login failed")
            return
        
        print("✅ Login successful")
        print()
        
        # Get historical prices
        headers = {"Authorization": f"Bearer {token}"}
        portfolio_id = TEST_ACCOUNT["portfolio_id"]
        
        response = await client.get(
            f"{API_PREFIX}/data/prices/historical/{portfolio_id}",
            headers=headers,
            params={"lookback_days": 10}  # Just 10 days for analysis
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch historical prices: {response.status_code}")
            return
        
        data = response.json()
        
        print("=" * 60)
        print("HISTORICAL PRICES ENDPOINT ANALYSIS")
        print("=" * 60)
        print()
        
        # Check metadata
        if "metadata" in data:
            print("📊 Metadata:")
            for key, value in data["metadata"].items():
                print(f"  - {key}: {value}")
            print()
        
        # Analyze price data
        if "symbols" in data:
            symbols = data["symbols"]
            print(f"📈 Found {len(symbols)} symbols with data")
            print()
            
            # Check first symbol in detail
            if symbols:
                first_symbol = list(symbols.keys())[0]
                symbol_data = symbols[first_symbol]
                
                print(f"🔍 Detailed Analysis of {first_symbol}:")
                print(f"  - Data points: {len(symbol_data.get('dates', []))}")
                
                # Check if this looks like mock data
                if "closes" in symbol_data:
                    closes = symbol_data["closes"][:10]
                    print(f"  - First 10 close prices: {[round(p, 2) for p in closes]}")
                    
                    # Check for patterns indicating mock data
                    price_range = max(closes) - min(closes)
                    avg_price = sum(closes) / len(closes)
                    variation_pct = (price_range / avg_price) * 100
                    
                    print(f"  - Price range: ${min(closes):.2f} - ${max(closes):.2f}")
                    print(f"  - Variation: {variation_pct:.2f}%")
                    
                    # Check if prices follow suspicious patterns
                    if all(200 <= p <= 206 for p in closes):
                        print("  ⚠️  WARNING: Prices in 200-206 range (known mock pattern)")
                    
                    # Check for random walk pattern (sign of mock data)
                    price_changes = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
                    positive_changes = sum(1 for c in price_changes if c > 0)
                    negative_changes = sum(1 for c in price_changes if c < 0)
                    
                    print(f"  - Price changes: {positive_changes} up, {negative_changes} down")
                    
                    # If changes are too evenly distributed, likely mock
                    if abs(positive_changes - negative_changes) <= 1:
                        print("  ⚠️  WARNING: Price changes too evenly distributed (likely mock)")
                    
                    # Check for volume data
                    if "volume" in symbol_data:
                        volumes = symbol_data["volume"][:10]
                        unique_volumes = len(set(volumes))
                        if unique_volumes == 1:
                            print(f"  ⚠️  WARNING: All volumes identical ({volumes[0]}) - likely mock")
                        else:
                            print(f"  - Volume variation: {unique_volumes} unique values")
                
                # Check high/low relationship
                if "high" in symbol_data and "low" in symbol_data and "close" in symbol_data:
                    highs = symbol_data["high"][:5]
                    lows = symbol_data["low"][:5]
                    closes = symbol_data["close"][:5]
                    
                    # Check if high/low are just close * fixed percentage (mock pattern)
                    mock_high = all(abs(h/c - 1.01) < 0.0001 for h, c in zip(highs, closes))
                    mock_low = all(abs(l/c - 0.99) < 0.0001 for l, c in zip(lows, closes))
                    
                    if mock_high and mock_low:
                        print("  ⚠️  WARNING: High/Low are exactly ±1% of close (mock pattern)")
                
                print()
                
                # Check a few more symbols
                print("📊 Summary of all symbols:")
                for symbol in list(symbols.keys())[:5]:
                    symbol_data = symbols[symbol]
                    if "closes" in symbol_data:
                        closes = symbol_data["closes"]
                        print(f"  - {symbol}: ${closes[0]:.2f} → ${closes[-1]:.2f} ({len(closes)} points)")
        
        print()
        print("=" * 60)
        print("CONCLUSION:")
        
        # Final determination
        mock_indicators = 0
        real_indicators = 0
        
        if "symbols" in data and data["symbols"]:
            first_data = next(iter(data["symbols"].values()))
            
            # Check for mock indicators
            if "volume" in first_data and len(set(first_data["volume"])) == 1:
                mock_indicators += 1
                print("🔴 Fixed volume values - MOCK")
            
            if "high" in first_data and "close" in first_data:
                if all(abs(h/c - 1.01) < 0.0001 for h, c in zip(first_data["high"][:5], first_data["close"][:5])):
                    mock_indicators += 1
                    print("🔴 High/Low are fixed percentages - MOCK")
            
            # Check for real indicators
            if "dates" in first_data and len(first_data["dates"]) > 0:
                real_indicators += 1
                print("🟢 Has date series")
            
            if "closes" in first_data and len(set(first_data["closes"])) > 1:
                real_indicators += 1
                print("🟢 Has price variation")
        
        if mock_indicators > real_indicators:
            print("\n❌ VERDICT: This endpoint returns MOCK DATA")
        elif real_indicators > mock_indicators:
            print("\n⚠️  VERDICT: Mixed - has real structure but mock content")
        else:
            print("\n❓ VERDICT: Unable to determine")
        
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_historical_prices())