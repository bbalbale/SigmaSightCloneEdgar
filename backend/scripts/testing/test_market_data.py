#!/usr/bin/env python3
"""
Manual testing script for Market Data Service
Run this to quickly test the market data implementations
"""
import asyncio
import sys
import os
from datetime import date, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.market_data_service import MarketDataService
from app.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()

async def test_polygon_connection():
    """Test basic Polygon.io connection"""
    print("🔍 Testing Polygon.io connection...")
    
    if not settings.POLYGON_API_KEY or settings.POLYGON_API_KEY == 'your_polygon_api_key_here':
        print("❌ No Polygon API key configured in .env file")
        print("   Add your API key to .env: POLYGON_API_KEY=your_key_here")
        return False
    
    service = MarketDataService()
    
    try:
        # Test current price fetch
        current_prices = await service.fetch_current_prices(['AAPL'])
        if current_prices.get('AAPL'):
            print(f"✅ Polygon.io connection successful")
            print(f"   AAPL current price: ${current_prices['AAPL']}")
            return True
        else:
            print("⚠️  Polygon.io connection working but no price returned")
            return False
    except Exception as e:
        print(f"❌ Polygon.io connection failed: {str(e)}")
        return False


async def test_yfinance_connection():
    """Test YFinance connection for GICS data"""
    print("\n🔍 Testing YFinance connection...")
    
    service = MarketDataService()
    
    try:
        gics_data = await service.fetch_gics_data(['AAPL'])
        aapl_gics = gics_data.get('AAPL', {})
        
        if aapl_gics.get('sector'):
            print(f"✅ YFinance connection successful")
            print(f"   AAPL sector: {aapl_gics['sector']}")
            print(f"   AAPL industry: {aapl_gics['industry']}")
            return True
        else:
            print("⚠️  YFinance connection working but no GICS data returned")
            return False
    except Exception as e:
        print(f"❌ YFinance connection failed: {str(e)}")
        return False


async def test_historical_data():
    """Test historical data fetching"""
    print("\n🔍 Testing historical data fetching...")
    
    service = MarketDataService()
    
    try:
        start_date = date.today() - timedelta(days=5)
        end_date = date.today()
        
        historical_data = await service.fetch_stock_prices(
            ['AAPL'], 
            start_date=start_date, 
            end_date=end_date
        )
        
        aapl_data = historical_data.get('AAPL', [])
        
        if aapl_data:
            print(f"✅ Historical data fetch successful")
            print(f"   Retrieved {len(aapl_data)} data points for AAPL")
            latest = aapl_data[-1]
            print(f"   Latest close: ${latest['close']} on {latest['date']}")
            return True
        else:
            print("⚠️  No historical data returned (may be weekend/holiday)")
            return False
    except Exception as e:
        print(f"❌ Historical data fetch failed: {str(e)}")
        return False


async def test_options_chain():
    """Test options chain data fetching"""
    print("\n🔍 Testing options chain data...")
    
    service = MarketDataService()
    
    try:
        options_data = await service.fetch_options_chain('AAPL')
        
        if options_data:
            print(f"✅ Options chain fetch successful")
            print(f"   Retrieved {len(options_data)} option contracts for AAPL")
            
            # Show a sample contract
            sample = options_data[0]
            print(f"   Sample: {sample['ticker']} ({sample['contract_type']} strike ${sample['strike_price']})")
            return True
        else:
            print("⚠️  No options data returned")
            return False
    except Exception as e:
        print(f"❌ Options chain fetch failed: {str(e)}")
        return False


async def test_database_integration():
    """Test database integration (requires running database)"""
    print("\n🔍 Testing database integration...")
    
    try:
        from app.database import AsyncSessionLocal
        from app.models.market_data import MarketDataCache
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            # Test database connection
            stmt = select(MarketDataCache).limit(1)
            result = await db.execute(stmt)
            
            print("✅ Database connection successful")
            
            # Test market data service with database
            service = MarketDataService()
            
            test_symbols = ['AAPL']
            cached_prices = await service.get_cached_prices(db, test_symbols)
            
            print(f"   Cached price check completed for {test_symbols}")
            if cached_prices.get('AAPL'):
                print(f"   Found cached price for AAPL: ${cached_prices['AAPL']}")
            else:
                print("   No cached price found (database may be empty)")
            
            return True
            
    except Exception as e:
        print(f"❌ Database integration failed: {str(e)}")
        print("   Make sure PostgreSQL is running and database is migrated")
        return False


async def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 SigmaSight Market Data Service Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run all tests
    test_results.append(await test_polygon_connection())
    test_results.append(await test_yfinance_connection())
    test_results.append(await test_historical_data())
    test_results.append(await test_options_chain())
    test_results.append(await test_database_integration())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"   ✅ Passed: {passed}/{total}")
    print(f"   ❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Market data service is ready.")
    else:
        print(f"\n⚠️  Some tests failed. Check the errors above.")
        print("   Common issues:")
        print("   - Missing API key in .env file")
        print("   - Database not running or not migrated")
        print("   - Network connectivity issues")
    
    return passed == total


async def quick_test():
    """Quick test for basic functionality"""
    print("⚡ Quick Market Data Test")
    print("-" * 30)
    
    # Just test API connections
    polygon_ok = await test_polygon_connection()
    yfinance_ok = await test_yfinance_connection()
    
    if polygon_ok and yfinance_ok:
        print("\n✅ Quick test passed! APIs are working.")
    else:
        print("\n❌ Quick test failed. Check API keys and connectivity.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(run_comprehensive_test())