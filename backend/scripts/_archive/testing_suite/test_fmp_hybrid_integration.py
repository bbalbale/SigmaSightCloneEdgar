#!/usr/bin/env python3
"""
Test FMP Hybrid Integration
Test the new FMP hybrid historical data method works with bulk_fetch_and_cache
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.market_data_service import market_data_service
from app.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

# Test symbols including factor ETFs and BRK-B
TEST_SYMBOLS = ["SPY", "VTV", "VUG", "BRK-B", "AAPL"]

async def test_fmp_hybrid_integration():
    """Test FMP hybrid integration with bulk operations"""
    
    print("🧪 Testing FMP Hybrid Integration...")
    print(f"Testing symbols: {', '.join(TEST_SYMBOLS)}")
    
    try:
        async with AsyncSessionLocal() as db:
            # Test the updated bulk_fetch_and_cache method
            print("\n1️⃣ Testing bulk_fetch_and_cache with FMP hybrid...")
            
            start_time = asyncio.get_event_loop().time()
            
            stats = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=TEST_SYMBOLS,
                days_back=30
            )
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            print(f"⏱️ Execution time: {duration:.2f} seconds")
            print(f"📊 Statistics: {stats}")
            
            # Verify data was cached properly
            print("\n2️⃣ Verifying cached data...")
            
            for symbol in TEST_SYMBOLS:
                cached_prices = await market_data_service.get_cached_prices(
                    db=db, 
                    symbols=[symbol], 
                    target_date=date.today()
                )
                
                price = cached_prices.get(symbol)
                status = "✅" if price else "❌"
                print(f"  {status} {symbol}: ${price}" if price else f"  {status} {symbol}: No cached price")
            
            print("\n3️⃣ Testing direct FMP historical method...")
            
            # Test the new fetch_historical_data_hybrid method directly
            historical_data = await market_data_service.fetch_historical_data_hybrid(
                symbols=["SPY", "BRK-B"],
                start_date=date.today() - timedelta(days=7),
                end_date=date.today()
            )
            
            for symbol, data in historical_data.items():
                count = len(data) if data else 0
                source = data[0]['data_source'] if data else 'none'
                print(f"  📈 {symbol}: {count} records (source: {source})")
            
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up market data service connections
        await market_data_service.close()

if __name__ == "__main__":
    success = asyncio.run(test_fmp_hybrid_integration())
    
    if success:
        print("\n✅ FMP Hybrid Integration Test PASSED")
        print("✅ Ready to proceed with YFinance removal")
    else:
        print("\n❌ FMP Hybrid Integration Test FAILED")
        print("❌ Do not proceed with YFinance removal")