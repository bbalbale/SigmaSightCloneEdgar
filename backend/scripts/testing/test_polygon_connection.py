#!/usr/bin/env python3
"""
Test script to verify Polygon.io API connection and fetch a single symbol
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.config import settings


async def test_polygon_connection():
    """Test basic Polygon.io connectivity"""
    print("Testing Polygon.io API Connection")
    print("=" * 50)
    
    # Check if API key is configured
    if not settings.POLYGON_API_KEY:
        print("❌ No Polygon API key configured!")
        print("Please set POLYGON_API_KEY in your .env file")
        return False
    
    print(f"✓ API key configured: {settings.POLYGON_API_KEY[:8]}...")
    
    # Test fetching data for a single symbol (SPY)
    test_symbol = "SPY"
    print(f"\nTesting data fetch for {test_symbol}")
    
    try:
        async with AsyncSessionLocal() as db:
            print("✓ Database connection established")
            
            # Try to fetch current price first
            print("Fetching current price...")
            current_prices = await market_data_service.fetch_current_prices([test_symbol])
            
            if test_symbol in current_prices and current_prices[test_symbol]:
                print(f"✓ Current price fetch successful: ${current_prices[test_symbol]}")
            else:
                print(f"⚠ Current price fetch returned no data for {test_symbol}")
            
            # Try to fetch historical data
            print("Fetching historical data (90 days)...")
            result = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=[test_symbol],
                days_back=90
            )
            
            print(f"✓ Historical data fetch result: {result}")
            
            # Check what was actually stored in database
            from app.models.market_data import MarketDataCache
            from sqlalchemy import select, func
            
            stmt = select(func.count(MarketDataCache.id)).where(
                MarketDataCache.symbol == test_symbol.upper()
            )
            result = await db.execute(stmt)
            count = result.scalar()
            
            print(f"✓ Records in database for {test_symbol}: {count}")
            
            if count > 0:
                # Get date range
                stmt = select(
                    func.min(MarketDataCache.date),
                    func.max(MarketDataCache.date)
                ).where(MarketDataCache.symbol == test_symbol.upper())
                
                result = await db.execute(stmt)
                min_date, max_date = result.one()
                print(f"✓ Date range: {min_date} to {max_date}")
                
                return True
            else:
                print("❌ No data was stored in the database")
                return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_polygon_connection())
    sys.exit(0 if success else 1)