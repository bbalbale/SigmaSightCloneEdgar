"""Test Phase 1.75 (Symbol Metrics) on Railway to identify errors."""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set DATABASE_URL for Railway Core DB
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def test_phase_175():
    print("=" * 60)
    print("Testing Phase 1.75 (Symbol Metrics) on Railway")
    print("=" * 60)

    # Step 1: Test import
    print("\n1. Testing import...")
    try:
        from app.services.symbol_metrics_service import calculate_symbol_metrics
        print("   [OK] Import successful")
    except Exception as e:
        print(f"   [FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Test symbol fetching
    print("\n2. Testing get_all_active_symbols...")
    try:
        from app.services.symbol_metrics_service import get_all_active_symbols
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            symbols = await get_all_active_symbols(db)
            print(f"   [OK] Found {len(symbols)} symbols")
    except Exception as e:
        print(f"   [FAIL] get_all_active_symbols failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Test bulk_fetch_prices
    print("\n3. Testing bulk_fetch_prices...")
    try:
        from app.services.symbol_metrics_service import bulk_fetch_prices

        test_symbols = symbols[:10]  # Just test first 10
        test_date = date(2025, 12, 20)

        async with AsyncSessionLocal() as db:
            prices = await bulk_fetch_prices(db, test_symbols, test_date, None)
            print(f"   [OK] Fetched prices for {len(prices)} symbols")
            # Show a sample
            for sym, data in list(prices.items())[:2]:
                print(f"       {sym}: close={data.get('close')}")
    except Exception as e:
        print(f"   [FAIL] bulk_fetch_prices failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Test bulk_fetch_factor_exposures
    print("\n4. Testing bulk_fetch_factor_exposures...")
    try:
        from app.services.symbol_metrics_service import bulk_fetch_factor_exposures

        async with AsyncSessionLocal() as db:
            factors = await bulk_fetch_factor_exposures(db, test_symbols, test_date)
            print(f"   [OK] Fetched factors for {len(factors)} symbols")
    except Exception as e:
        print(f"   [FAIL] bulk_fetch_factor_exposures failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Test bulk_upsert_metrics
    print("\n5. Testing bulk_upsert_metrics with small sample...")
    try:
        from app.services.symbol_metrics_service import bulk_upsert_metrics
        from datetime import datetime, timezone

        # Create a test metric
        test_metrics = [{
            'symbol': 'AAPL',
            'metrics_date': test_date,
            'current_price': 250.0,
            'return_1d': 0.01,
            'return_mtd': 0.05,
            'return_ytd': 0.25,
            'return_1m': 0.03,
            'return_3m': 0.10,
            'return_1y': 0.30,
            'market_cap': 3000000000000.0,
            'enterprise_value': None,
            'pe_ratio': 30.0,
            'ps_ratio': None,
            'pb_ratio': None,
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'company_name': 'Apple Inc.',
            'factor_value': 0.5,
            'factor_growth': 0.8,
            'factor_momentum': 0.6,
            'factor_quality': 0.9,
            'factor_size': -0.2,
            'factor_low_vol': 0.3,
            'factor_growth_value_spread': 0.3,
            'factor_momentum_spread': 0.4,
            'factor_size_spread': -0.1,
            'factor_quality_spread': 0.5,
            'data_quality_score': 80.0,
            'updated_at': datetime.now(timezone.utc),
        }]

        async with AsyncSessionLocal() as db:
            count = await bulk_upsert_metrics(db, test_metrics)
            await db.commit()
            print(f"   [OK] Upserted {count} metrics")
    except Exception as e:
        print(f"   [FAIL] bulk_upsert_metrics failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 6: Run full calculate_symbol_metrics on a small sample
    print("\n6. Testing calculate_symbol_metrics (full run)...")
    try:
        result = await calculate_symbol_metrics(
            calculation_date=date(2025, 12, 20),
            price_cache=None
        )
        print(f"   [OK] Result: {result}")
    except Exception as e:
        print(f"   [FAIL] calculate_symbol_metrics failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_phase_175())
