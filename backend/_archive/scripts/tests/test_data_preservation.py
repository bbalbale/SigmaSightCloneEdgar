#!/usr/bin/env python
"""
Test script to verify that historical data preservation is working
After implementing Section 6.1 changes
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.market_data import MarketDataCache
from app.services.market_data_service import MarketDataService

async def test_data_preservation():
    """Test that historical data is preserved, not overwritten"""
    print("=" * 80)
    print("📊 Testing Historical Data Preservation (Section 6.1)")
    print("=" * 80)
    
    async with get_async_session() as db:
        service = MarketDataService()
        test_symbol = "AAPL"
        
        # Step 1: Check current data coverage
        print(f"\n1️⃣ Checking current data for {test_symbol}...")
        stmt = select(
            func.count(MarketDataCache.date).label('count'),
            func.min(MarketDataCache.date).label('min_date'),
            func.max(MarketDataCache.date).label('max_date')
        ).where(MarketDataCache.symbol == test_symbol)
        
        result = await db.execute(stmt)
        before = result.one()
        print(f"   Before: {before.count} days, from {before.min_date} to {before.max_date}")
        
        # Step 2: Get a sample of existing data to verify preservation
        print(f"\n2️⃣ Sampling existing data to verify preservation...")
        sample_stmt = select(
            MarketDataCache.date,
            MarketDataCache.close
        ).where(
            MarketDataCache.symbol == test_symbol
        ).order_by(MarketDataCache.date.desc()).limit(5)
        
        sample_result = await db.execute(sample_stmt)
        original_samples = {row.date: row.close for row in sample_result}
        print("   Sample prices before fetch:")
        for dt, price in sorted(original_samples.items(), reverse=True):
            print(f"     {dt}: ${price}")
        
        # Step 3: Fetch data (should preserve existing, add new)
        print(f"\n3️⃣ Fetching 30 days of data for {test_symbol}...")
        stats = await service.bulk_fetch_and_cache(db, [test_symbol], days_back=30)
        print(f"   Fetch stats: {stats}")
        
        # Step 4: Check data coverage after fetch
        print(f"\n4️⃣ Checking data coverage after fetch...")
        result = await db.execute(stmt)
        after = result.one()
        print(f"   After: {after.count} days, from {after.min_date} to {after.max_date}")
        
        # Step 5: Verify original data was preserved
        print(f"\n5️⃣ Verifying original data was preserved...")
        preserved_stmt = select(
            MarketDataCache.date,
            MarketDataCache.close
        ).where(
            MarketDataCache.symbol == test_symbol,
            MarketDataCache.date.in_(original_samples.keys())
        )
        
        preserved_result = await db.execute(preserved_stmt)
        preserved_samples = {row.date: row.close for row in preserved_result}
        
        all_preserved = True
        for dt, original_price in original_samples.items():
            preserved_price = preserved_samples.get(dt)
            if preserved_price != original_price:
                print(f"   ❌ Data changed for {dt}: {original_price} -> {preserved_price}")
                all_preserved = False
            else:
                print(f"   ✅ Data preserved for {dt}: ${original_price}")
        
        # Step 6: Test ensure_data_coverage function
        print(f"\n6️⃣ Testing ensure_data_coverage() function...")
        coverage_result = await service.ensure_data_coverage(db, test_symbol, min_days=20)
        print(f"   Coverage result: {coverage_result}")
        
        # Step 7: Summary
        print("\n" + "=" * 80)
        print("📊 Test Summary:")
        print(f"   • Data before: {before.count} days")
        print(f"   • Data after: {after.count} days")
        print(f"   • New records: {after.count - before.count}")
        print(f"   • Data preserved: {'✅ YES' if all_preserved else '❌ NO'}")
        
        if stats.get('records_skipped', 0) > 0:
            print(f"   • Records skipped (already existed): {stats.get('records_skipped')}")
            print(f"   • Records inserted (new): {stats.get('records_inserted')}")
        
        print("=" * 80)
        
        return all_preserved

if __name__ == "__main__":
    success = asyncio.run(test_data_preservation())
    exit(0 if success else 1)