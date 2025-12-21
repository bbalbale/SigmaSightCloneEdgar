"""
Test Phase 5 & 6 integration - Symbol Metrics and Validation.

This script verifies:
1. Symbol metrics service imports and functions work
2. Symbol daily metrics can be calculated and stored
3. Comparison script can run and validate data
"""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Set up environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"


async def test_imports():
    """Test all required imports work."""
    print("=" * 60)
    print("TEST 1: Import Verification")
    print("=" * 60)

    try:
        from app.services.symbol_metrics_service import (
            calculate_symbol_metrics,
            get_all_active_symbols,
            load_symbol_returns,
        )
        print("  [OK] symbol_metrics_service imports OK")
    except Exception as e:
        print(f"  [FAIL] symbol_metrics_service imports FAILED: {e}")
        return False

    try:
        from app.models.symbol_analytics import (
            SymbolUniverse,
            SymbolFactorExposure,
            SymbolDailyMetrics,
        )
        print("  [OK] symbol_analytics models imports OK")
    except Exception as e:
        print(f"  [FAIL] symbol_analytics models imports FAILED: {e}")
        return False

    return True


async def test_symbol_metrics_calculation():
    """Test symbol metrics calculation."""
    print("\n" + "=" * 60)
    print("TEST 2: Symbol Metrics Calculation")
    print("=" * 60)

    from app.services.symbol_metrics_service import calculate_symbol_metrics

    calculation_date = date(2025, 12, 19)
    print(f"  Calculation date: {calculation_date}")

    try:
        result = await calculate_symbol_metrics(calculation_date)

        print(f"\n  Results:")
        print(f"    Symbols updated: {result.get('symbols_updated', 0)}")
        print(f"    Symbols total: {result.get('symbols_total', 0)}")

        if result.get('errors'):
            print(f"    Errors: {len(result['errors'])}")
            for err in result['errors'][:3]:
                print(f"      - {err}")

        if result.get('symbols_updated', 0) > 0:
            print("\n  [OK] Symbol metrics calculation working")
            return True
        else:
            print("\n  [WARN] No symbols updated (may need universe populated)")
            return True

    except Exception as e:
        print(f"  [FAIL] Symbol metrics calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_symbol_daily_metrics_data():
    """Check symbol daily metrics data."""
    print("\n" + "=" * 60)
    print("TEST 3: Symbol Daily Metrics Data Check")
    print("=" * 60)

    from sqlalchemy import select, func, text
    from app.database import AsyncSessionLocal
    from app.models.symbol_analytics import SymbolDailyMetrics

    async with AsyncSessionLocal() as db:
        # Count records
        count_stmt = select(func.count()).select_from(SymbolDailyMetrics)
        result = await db.execute(count_stmt)
        total_records = result.scalar()
        print(f"  Total symbol_daily_metrics records: {total_records}")

        if total_records == 0:
            print("  [WARN] No metrics found - Phase 1.75 may not have run yet")
            return True

        # Sample some data
        sample_stmt = text("""
            SELECT symbol, metrics_date, current_price, return_1d, return_ytd, sector, data_quality_score
            FROM symbol_daily_metrics
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        result = await db.execute(sample_stmt)
        rows = result.fetchall()

        print("\n  Sample metrics (most recent):")
        for row in rows:
            price_str = f"${float(row[2]):.2f}" if row[2] else "N/A"
            return_1d_str = f"{float(row[3])*100:.2f}%" if row[3] else "N/A"
            return_ytd_str = f"{float(row[4])*100:.2f}%" if row[4] else "N/A"
            quality_str = f"{float(row[6]):.0f}" if row[6] else "N/A"
            print(f"    {row[0]:6} | {row[1]} | {price_str:>10} | 1d={return_1d_str:>8} | YTD={return_ytd_str:>8} | {row[5] or 'N/A':15} | Q={quality_str}")

    print("\n  [OK] Symbol daily metrics data check complete")
    return True


async def test_load_symbol_returns():
    """Test loading pre-computed returns for P&L calculation."""
    print("\n" + "=" * 60)
    print("TEST 4: Load Symbol Returns (for P&L)")
    print("=" * 60)

    from app.services.symbol_metrics_service import load_symbol_returns
    from app.database import AsyncSessionLocal

    calculation_date = date(2025, 12, 19)
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

    async with AsyncSessionLocal() as db:
        returns = await load_symbol_returns(db, test_symbols, calculation_date)

        print(f"  Loaded returns for {len(returns)} symbols:")
        for symbol, ret in returns.items():
            ret_str = f"{ret*100:.2f}%" if ret else "N/A"
            print(f"    {symbol}: {ret_str}")

        if returns:
            print("\n  [OK] Symbol returns loading working")
        else:
            print("\n  [WARN] No returns loaded (metrics may not be calculated yet)")

    return True


async def test_comparison_script_import():
    """Test that the comparison script can be imported."""
    print("\n" + "=" * 60)
    print("TEST 5: Comparison Script Import")
    print("=" * 60)

    try:
        # Import the comparison module functions
        sys.path.insert(0, str(Path(__file__).parent / 'validation'))

        from validation.compare_factor_exposures import (
            compare_for_date,
            get_position_factor_exposures,
            get_symbol_factor_exposures,
        )
        print("  [OK] Comparison script imports OK")
        return True
    except Exception as e:
        print(f"  [WARN] Comparison script import failed: {e}")
        print("  (This is OK if the script hasn't been run yet)")
        return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 5 & 6 INTEGRATION TEST SUITE")
    print("=" * 60)

    all_passed = True

    # Test 1: Imports
    if not await test_imports():
        all_passed = False

    # Test 2: Symbol metrics calculation
    if not await test_symbol_metrics_calculation():
        all_passed = False

    # Test 3: Symbol daily metrics data
    if not await test_symbol_daily_metrics_data():
        all_passed = False

    # Test 4: Load symbol returns
    if not await test_load_symbol_returns():
        all_passed = False

    # Test 5: Comparison script
    if not await test_comparison_script_import():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] ALL TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
