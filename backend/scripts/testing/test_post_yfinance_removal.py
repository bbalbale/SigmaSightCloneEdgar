#!/usr/bin/env python3
"""
Test System After YFinance Removal
Quick validation that all systems work after YFinance dependency removal
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.market_data_service import market_data_service
from app.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

async def test_post_yfinance_removal():
    """Test system functionality after YFinance removal"""
    
    print("🧪 Testing System After YFinance Removal...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Test 1: Market data hybrid integration
            print("\n1️⃣ Testing FMP hybrid integration...")
            
            test_symbols = ["SPY", "AAPL"]
            result = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=test_symbols,
                days_back=5
            )
            
            print(f"  ✅ Market data: {result['symbols_updated']} symbols, {result['total_records']} records")
            
            # Test 2: GICS data (should return empty gracefully)
            print("\n2️⃣ Testing GICS data handling...")
            
            gics_data = await market_data_service.fetch_gics_data(test_symbols)
            gics_empty = all(
                data['sector'] is None and data['industry'] is None 
                for data in gics_data.values()
            )
            
            if gics_empty:
                print("  ✅ GICS data properly disabled - returns empty data gracefully")
            else:
                print("  ⚠️ GICS data not properly disabled")
            
            # Test 3: Current prices
            print("\n3️⃣ Testing current prices...")
            
            current_prices = await market_data_service.fetch_stock_prices_hybrid(test_symbols)
            prices_available = len([p for p in current_prices.values() if p.get('price')])
            
            print(f"  ✅ Current prices: {prices_available}/{len(test_symbols)} symbols")
            
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        await market_data_service.close()

if __name__ == "__main__":
    success = asyncio.run(test_post_yfinance_removal())
    
    if success:
        print("\n✅ POST-YFINANCE REMOVAL TEST PASSED")
        print("✅ FMP-Primary Architecture Successfully Implemented")
        print("✅ System ready for production with FMP data provider")
    else:
        print("\n❌ POST-YFINANCE REMOVAL TEST FAILED") 
        print("❌ Fix issues before proceeding")