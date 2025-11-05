#!/usr/bin/env python3
"""Test script for rate limiting and pagination improvements."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import asyncio
import time
from datetime import date, timedelta
from app.services.market_data_service import market_data_service
from app.services.rate_limiter import polygon_rate_limiter
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)

# Verify API key is loaded
print(f"\n🔑 Polygon API Key loaded: {'Yes' if settings.POLYGON_API_KEY else 'No'}")
if settings.POLYGON_API_KEY:
    print(f"   Key starts with: {settings.POLYGON_API_KEY[:10]}...")
else:
    print("   ⚠️  Please ensure POLYGON_API_KEY is set in .env file")
    sys.exit(1)


async def test_rate_limiting():
    """Test rate limiting with multiple API calls."""
    print("\n🧪 Testing Rate Limiting with Historical Data\n")
    
    # Test symbols
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    print(f"Testing with {len(symbols)} symbols...")
    print(f"Plan: {polygon_rate_limiter.plan} ({polygon_rate_limiter.requests_per_minute} requests/minute)")
    print("-" * 50)
    
    start_time = time.time()
    
    # Test historical price fetching (this works on Starter plan)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    results = await market_data_service.fetch_stock_prices(
        symbols, 
        start_date=start_date,
        end_date=end_date
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ Fetched data for {len(results)} symbols in {elapsed:.2f} seconds")
    print(f"Average rate: {len(symbols)/elapsed:.2f} requests/second")
    
    # Show rate limiter stats
    stats = polygon_rate_limiter.stats
    print(f"\nRate Limiter Stats:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Average rate: {stats['average_rate']:.3f} req/s")
    print(f"  Current tokens: {stats['current_tokens']:.2f}")
    
    # Display sample data
    print("\nSample data fetched:")
    for symbol, prices in results.items():
        if prices:
            print(f"  {symbol}: {len(prices)} days of data")
            latest = prices[-1]
            print(f"    Latest: {latest['date']} - Close: ${latest['close']}")


async def test_pagination():
    """Test pagination handling for large date ranges."""
    print("\n\n🧪 Testing Pagination\n")
    
    # Test with a large date range that might trigger pagination
    symbol = 'AAPL'
    start_date = date.today() - timedelta(days=365)  # 1 year of data
    end_date = date.today()
    
    print(f"Fetching 1 year of data for {symbol}...")
    print(f"Date range: {start_date} to {end_date}")
    print("-" * 50)
    
    start_time = time.time()
    
    # Fetch historical data (may trigger pagination)
    result = await market_data_service.fetch_stock_prices(
        [symbol], 
        start_date=start_date,
        end_date=end_date
    )
    
    elapsed = time.time() - start_time
    
    if symbol in result:
        price_data = result[symbol]
        print(f"\n✅ Fetched {len(price_data)} daily price records in {elapsed:.2f} seconds")
        
        if price_data:
            print(f"First date: {price_data[0]['date']}")
            print(f"Last date: {price_data[-1]['date']}")
            
            # Check for gaps (weekends/holidays should be missing)
            trading_days = len(price_data)
            calendar_days = (end_date - start_date).days
            print(f"\nTrading days: {trading_days}")
            print(f"Calendar days: {calendar_days}")
            print(f"Ratio: {trading_days/calendar_days:.2%} (expected ~70% for trading days)")


async def test_options_pagination():
    """Test pagination for options chain data."""
    print("\n\n🧪 Testing Options Chain Pagination\n")
    
    symbol = 'SPY'  # SPY has many option contracts
    
    print(f"Fetching options chain for {symbol}...")
    print("(SPY typically has 1000+ contracts)")
    print("-" * 50)
    
    start_time = time.time()
    
    # Fetch options chain
    options = await market_data_service.fetch_options_chain(symbol)
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ Fetched {len(options)} option contracts in {elapsed:.2f} seconds")
    
    if options:
        # Group by expiration
        expirations = {}
        for opt in options:
            exp = opt['expiration_date']
            expirations[exp] = expirations.get(exp, 0) + 1
        
        print(f"Unique expiration dates: {len(expirations)}")
        print("\nFirst 5 expirations:")
        for exp, count in sorted(expirations.items())[:5]:
            print(f"  {exp}: {count} contracts")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Market Data Service - Rate Limiting & Pagination Tests")
    print("=" * 60)
    
    try:
        await test_rate_limiting()
        await test_pagination()
        await test_options_pagination()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
