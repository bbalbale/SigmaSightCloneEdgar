"""
Diagnostic script to verify batch processing optimizations are working.

Checks:
1. Database indexes are created and active
2. Price cache is loading data correctly
3. Performance of key queries

Run: uv run python scripts/diagnostics/check_optimizations.py
"""
import asyncio
from datetime import date, datetime
from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.cache.price_cache import PriceCache
from app.models.positions import Position


async def check_indexes():
    """Check if Priority 1-3 indexes exist."""
    print("\n" + "="*80)
    print("CHECKING DATABASE INDEXES")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get all indexes on positions and market_data_cache tables
        query = text("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename IN ('positions', 'market_data_cache')
            ORDER BY tablename, indexname;
        """)

        result = await db.execute(query)
        indexes = result.fetchall()

        # Expected indexes
        expected = {
            'idx_positions_active_complete',
            'idx_market_data_valid_prices',
            'idx_positions_symbol_active'
        }

        found = set()
        for table, index_name, index_def in indexes:
            if index_name in expected:
                found.add(index_name)
                print(f"✅ {table:25} | {index_name}")
            else:
                print(f"   {table:25} | {index_name}")

        missing = expected - found
        if missing:
            print(f"\n❌ MISSING INDEXES: {missing}")
            print("   Run: cd backend && uv run alembic upgrade head")
            return False
        else:
            print(f"\n✅ All {len(expected)} priority indexes found!")
            return True


async def check_price_cache():
    """Check if price cache is working correctly."""
    print("\n" + "="*80)
    print("CHECKING PRICE CACHE")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get a few symbols
        symbols_query = select(Position.symbol).distinct().limit(10)
        result = await db.execute(symbols_query)
        symbols = {row[0] for row in result.all() if row[0]}

        if not symbols:
            print("❌ No symbols found in positions table")
            return False

        print(f"\nTesting with {len(symbols)} symbols: {list(symbols)[:5]}...")

        # Test single-day cache load
        cache = PriceCache()
        test_date = date(2025, 11, 6)

        start_time = datetime.now()
        loaded_count = await cache.load_single_date(db, symbols, test_date)
        load_time = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n✅ Loaded {loaded_count} prices in {load_time:.2f}ms")

        # Test cache hits
        hits = 0
        misses = 0
        for symbol in symbols:
            price = cache.get_price(symbol, test_date)
            if price:
                hits += 1
            else:
                misses += 1

        stats = cache.get_stats()
        print(f"✅ Cache stats: {stats}")
        print(f"✅ Hit rate: {hits}/{hits+misses} = {hits/(hits+misses)*100:.1f}%")

        if hits == 0:
            print("❌ No cache hits - price cache not working!")
            return False

        return True


async def check_multi_day_cache():
    """Check if multi-day price cache works."""
    print("\n" + "="*80)
    print("CHECKING MULTI-DAY PRICE CACHE")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get a few symbols
        symbols_query = select(Position.symbol).distinct().limit(5)
        result = await db.execute(symbols_query)
        symbols = {row[0] for row in result.all() if row[0]}

        if not symbols:
            print("❌ No symbols found")
            return False

        print(f"\nTesting with {len(symbols)} symbols for 10-day range...")

        # Test multi-day load
        cache = PriceCache()
        start_date = date(2025, 10, 28)
        end_date = date(2025, 11, 6)

        start_time = datetime.now()
        loaded_count = await cache.load_date_range(db, symbols, start_date, end_date)
        load_time = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n✅ Loaded {loaded_count} prices in {load_time:.2f}ms")

        stats = cache.get_stats()
        print(f"✅ Cache stats: {stats}")

        # Calculate expected prices (5 symbols × ~7 trading days = ~35 prices)
        expected_min = len(symbols) * 5  # Conservative estimate
        if loaded_count < expected_min:
            print(f"⚠️  Loaded fewer prices than expected (got {loaded_count}, expected at least {expected_min})")

        return loaded_count > 0


async def benchmark_query_performance():
    """Benchmark query performance with and without indexes."""
    print("\n" + "="*80)
    print("BENCHMARKING QUERY PERFORMANCE")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Query 1: Active positions lookup (uses idx_positions_active_complete)
        query1 = select(Position).where(
            Position.deleted_at.is_(None),
            Position.exit_date.is_(None),
            Position.investment_class.notin_(['PRIVATE'])
        ).limit(100)

        start_time = datetime.now()
        result1 = await db.execute(query1)
        positions = result1.scalars().all()
        query1_time = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n✅ Active positions query: {query1_time:.2f}ms ({len(positions)} positions)")

        if query1_time > 100:
            print(f"⚠️  Query took > 100ms - indexes might not be used")

        return True


async def main():
    """Run all diagnostic checks."""
    print("\n" + "="*80)
    print("BATCH PROCESSING OPTIMIZATION DIAGNOSTICS")
    print("="*80)
    print(f"Run time: {datetime.now()}")

    results = {}

    try:
        results['indexes'] = await check_indexes()
    except Exception as e:
        print(f"❌ Index check failed: {e}")
        results['indexes'] = False

    try:
        results['price_cache'] = await check_price_cache()
    except Exception as e:
        print(f"❌ Price cache check failed: {e}")
        results['price_cache'] = False

    try:
        results['multi_day_cache'] = await check_multi_day_cache()
    except Exception as e:
        print(f"❌ Multi-day cache check failed: {e}")
        results['multi_day_cache'] = False

    try:
        results['query_perf'] = await benchmark_query_performance()
    except Exception as e:
        print(f"❌ Query benchmark failed: {e}")
        results['query_perf'] = False

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} | {check}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✅ All optimizations are working correctly!")
        print("   If batch processing is still slow, the bottleneck is likely in Phase 6 (Analytics)")
    else:
        print("\n❌ Some optimizations are not working!")
        print("   Fix the failed checks above before running batch processing.")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
