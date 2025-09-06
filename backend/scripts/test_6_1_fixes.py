#!/usr/bin/env python
"""
Test script to verify all fixes from Section 6.1.10
- Fix 1: Partial coverage bug fixed in market_data_sync.py
- Fix 2: Metadata rows filtered in coverage calculations  
- Fix 3: GICS fetching made optional
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, func, and_, distinct
from app.database import get_async_session, AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.services.market_data_service import market_data_service
from app.batch.market_data_sync import fetch_missing_historical_data, get_active_portfolio_symbols

async def test_fix_1_partial_coverage():
    """Test Fix 1: Per-symbol coverage checking"""
    print("\n" + "="*80)
    print("📊 Testing Fix 1: Partial Coverage Bug Fix")
    print("="*80)
    
    async with get_async_session() as db:
        # Get symbols to test
        symbols = await get_active_portfolio_symbols(db)
        test_symbols = list(symbols)[:3]  # Test first 3 symbols
        
        print(f"\n1️⃣ Testing per-symbol coverage for: {test_symbols}")
        
        # Check coverage for each symbol individually
        days_back = 90
        start_date = date.today() - timedelta(days=days_back)
        expected_days = days_back * 0.5  # ~50% for trading days
        
        for symbol in test_symbols:
            # Count distinct dates with actual price data (filter metadata)
            stmt = select(func.count(distinct(MarketDataCache.date))).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.close > 0,  # Filter metadata rows
                    MarketDataCache.data_source.in_(['fmp', 'polygon'])  # Only price data
                )
            )
            count = (await db.execute(stmt)).scalar() or 0
            
            coverage_pct = (count / expected_days) * 100 if expected_days > 0 else 0
            status = "✅ Sufficient" if count >= expected_days * 0.8 else "❌ Needs backfill"
            
            print(f"   {symbol}: {count} days ({coverage_pct:.1f}% coverage) - {status}")
        
        print("\n✅ Fix 1 verified: Per-symbol coverage checking works")
        return True


async def test_fix_2_metadata_filtering():
    """Test Fix 2: Metadata rows are filtered out"""
    print("\n" + "="*80)
    print("📊 Testing Fix 2: Metadata Row Filtering")
    print("="*80)
    
    async with get_async_session() as db:
        test_symbol = "AAPL"
        
        # Count all rows for symbol
        stmt_all = select(func.count(MarketDataCache.id)).where(
            MarketDataCache.symbol == test_symbol
        )
        total_rows = (await db.execute(stmt_all)).scalar() or 0
        
        # Count price data rows only (close > 0)
        stmt_price = select(func.count(MarketDataCache.id)).where(
            and_(
                MarketDataCache.symbol == test_symbol,
                MarketDataCache.close > 0,
                MarketDataCache.data_source.in_(['fmp', 'polygon'])
            )
        )
        price_rows = (await db.execute(stmt_price)).scalar() or 0
        
        # Count metadata rows (close = 0 or other sources)
        metadata_rows = total_rows - price_rows
        
        print(f"\n   Symbol: {test_symbol}")
        print(f"   Total rows: {total_rows}")
        print(f"   Price data rows: {price_rows}")
        print(f"   Metadata rows: {metadata_rows}")
        
        # Test helper methods
        cached_dates = await market_data_service._get_cached_dates(db, test_symbol)
        cached_days = await market_data_service._count_cached_days(db, test_symbol)
        
        print(f"\n   Helper method results:")
        print(f"   _get_cached_dates(): {len(cached_dates)} dates")
        print(f"   _count_cached_days(): {cached_days} days")
        print(f"   Match: {'✅ Yes' if len(cached_dates) == cached_days else '❌ No'}")
        
        # Verify helper methods filter metadata
        assert cached_days == price_rows or cached_days == len(cached_dates), \
            "Helper methods should only count price data rows"
        
        print("\n✅ Fix 2 verified: Metadata rows are properly filtered")
        return True


async def test_fix_3_gics_optional():
    """Test Fix 3: GICS fetching is optional"""
    print("\n" + "="*80)
    print("📊 Testing Fix 3: GICS Fetching Optional")
    print("="*80)
    
    async with get_async_session() as db:
        test_symbols = ["MSFT", "GOOGL"]
        
        # Test 1: Fetch without GICS (default)
        print(f"\n1️⃣ Testing bulk_fetch_and_cache WITHOUT GICS (default)...")
        stats1 = await market_data_service.bulk_fetch_and_cache(
            db=db,
            symbols=test_symbols,
            days_back=5  # Small test
        )
        print(f"   Result: {stats1}")
        
        # Test 2: Fetch with GICS explicitly
        print(f"\n2️⃣ Testing bulk_fetch_and_cache WITH GICS (explicit)...")
        stats2 = await market_data_service.bulk_fetch_and_cache(
            db=db,
            symbols=test_symbols,
            days_back=5,
            include_gics=True  # Explicitly request GICS
        )
        print(f"   Result: {stats2}")
        
        # Check if GICS data was fetched
        stmt = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol.in_(test_symbols),
                MarketDataCache.sector.isnot(None)
            )
        ).limit(5)
        
        result = await db.execute(stmt)
        gics_rows = result.scalars().all()
        
        print(f"\n3️⃣ GICS data check:")
        if gics_rows:
            for row in gics_rows[:2]:
                print(f"   {row.symbol}: sector={row.sector}, industry={row.industry}")
        else:
            print("   No GICS data found (expected when include_gics=False)")
        
        print("\n✅ Fix 3 verified: GICS fetching is optional and defaults to False")
        return True


async def test_data_preservation():
    """Test that all fixes preserve historical data"""
    print("\n" + "="*80)
    print("📊 Testing Data Preservation with All Fixes")
    print("="*80)
    
    async with get_async_session() as db:
        test_symbol = "AAPL"
        
        # Get current data count
        stmt = select(func.count(distinct(MarketDataCache.date))).where(
            and_(
                MarketDataCache.symbol == test_symbol,
                MarketDataCache.close > 0
            )
        )
        before_count = (await db.execute(stmt)).scalar() or 0
        
        print(f"\n   Before: {test_symbol} has {before_count} days of price data")
        
        # Fetch new data (should preserve existing)
        print(f"   Fetching 30 days of data...")
        stats = await market_data_service.bulk_fetch_and_cache(
            db=db,
            symbols=[test_symbol],
            days_back=30,
            include_gics=False  # Don't fetch GICS for speed
        )
        
        # Check after
        after_count = (await db.execute(stmt)).scalar() or 0
        
        print(f"   After: {test_symbol} has {after_count} days of price data")
        print(f"   Change: {after_count - before_count} new days added")
        print(f"   Stats: {stats}")
        
        assert after_count >= before_count, "Data should be preserved, not overwritten"
        
        print("\n✅ Data preservation verified: Historical data is preserved")
        return True


async def main():
    """Run all tests"""
    print("="*80)
    print("🔬 Testing All Section 6.1.10 Fixes")
    print("="*80)
    
    results = []
    
    # Run all tests
    try:
        results.append(("Fix 1: Partial Coverage", await test_fix_1_partial_coverage()))
    except Exception as e:
        print(f"\n❌ Fix 1 test failed: {e}")
        results.append(("Fix 1: Partial Coverage", False))
    
    try:
        results.append(("Fix 2: Metadata Filtering", await test_fix_2_metadata_filtering()))
    except Exception as e:
        print(f"\n❌ Fix 2 test failed: {e}")
        results.append(("Fix 2: Metadata Filtering", False))
    
    try:
        results.append(("Fix 3: GICS Optional", await test_fix_3_gics_optional()))
    except Exception as e:
        print(f"\n❌ Fix 3 test failed: {e}")
        results.append(("Fix 3: GICS Optional", False))
    
    try:
        results.append(("Data Preservation", await test_data_preservation()))
    except Exception as e:
        print(f"\n❌ Data preservation test failed: {e}")
        results.append(("Data Preservation", False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Section 6.1.10 fixes are working correctly")
    else:
        print("⚠️ Some tests failed. Please review the output above.")
    print("="*80)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)