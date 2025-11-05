#!/usr/bin/env python3
"""Test which Polygon.io endpoints are available on free tier."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import asyncio
from datetime import date, timedelta
from polygon import RESTClient
from app.config import settings

# Initialize client
client = RESTClient(api_key=settings.POLYGON_API_KEY)


def test_endpoints():
    """Test various Polygon endpoints to see what's available."""
    print("🔍 Testing Polygon.io Free Tier Endpoints\n")
    print(f"API Key: {settings.POLYGON_API_KEY[:10]}...\n")
    
    # Test 1: Aggregates (Bars) - Usually available on free tier
    print("1. Testing Aggregates (Daily Bars)...")
    try:
        bars = client.get_aggs(
            ticker="AAPL",
            multiplier=1,
            timespan="day",
            from_="2024-01-01",
            to="2024-01-10",
            adjusted=True,
            sort="asc",
            limit=10
        )
        bars_list = list(bars)
        print(f"   ✅ Success! Got {len(bars_list)} bars")
        if bars_list:
            print(f"   Sample: Date={bars_list[0].timestamp}, Close=${bars_list[0].close}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n2. Testing Last Trade...")
    try:
        last_trade = client.get_last_trade(ticker="AAPL")
        print(f"   ✅ Success! Price=${last_trade.price}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n3. Testing Previous Close...")
    try:
        prev_close = client.get_previous_close("AAPL")
        print(f"   ✅ Success! Close=${prev_close.close}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n4. Testing Ticker Details...")
    try:
        details = client.get_ticker_details("AAPL")
        print(f"   ✅ Success! Name={details.name}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n5. Testing Options Contracts...")
    try:
        contracts = list(client.list_options_contracts(
            underlying_ticker="AAPL",
            limit=5
        ))
        print(f"   ✅ Success! Got {len(contracts)} contracts")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n6. Testing Snapshot...")
    try:
        snapshot = client.get_snapshot_all("stocks")
        tickers = list(snapshot)[:5]  # Get first 5
        print(f"   ✅ Success! Got snapshots")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n7. Testing Grouped Daily (Previous Close for all tickers)...")
    try:
        grouped = client.get_grouped_daily_aggs(date="2024-01-02")
        results = list(grouped)[:5]
        print(f"   ✅ Success! Got {len(results)} results")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "="*50)
    print("Summary: Free tier typically includes:")
    print("- ✅ Aggregates/Bars (historical daily data)")
    print("- ✅ Previous Close")
    print("- ✅ Ticker Details")
    print("- ❌ Real-time data (last trade, snapshots)")
    print("- ❌ Options data")
    print("- ❌ Grouped daily data")


if __name__ == "__main__":
    test_endpoints()
