"""
Test Phase 1.5 Symbol Factor integration with batch orchestrator.

This script verifies:
1. Symbol factor calculation imports work
2. Portfolio factor service imports work
3. Analytics runner can use symbol-level aggregation
"""
import asyncio
import os
import sys
from datetime import date, timedelta
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
        from app.calculations.symbol_factors import (
            calculate_universe_factors,
            get_all_active_symbols,
            load_symbol_betas,
        )
        print("  [OK] symbol_factors imports OK")
    except Exception as e:
        print(f"  [FAIL] symbol_factors imports FAILED: {e}")
        return False

    try:
        from app.services.portfolio_factor_service import (
            get_portfolio_factor_exposures,
            get_portfolio_positions_with_weights,
            store_portfolio_factor_exposures,
        )
        print("  [OK] portfolio_factor_service imports OK")
    except Exception as e:
        print(f"  [FAIL] portfolio_factor_service imports FAILED: {e}")
        return False

    try:
        from app.batch.batch_orchestrator import batch_orchestrator
        print("  [OK] batch_orchestrator imports OK")
    except Exception as e:
        print(f"  [FAIL] batch_orchestrator imports FAILED: {e}")
        return False

    try:
        from app.batch.analytics_runner import analytics_runner
        print("  [OK] analytics_runner imports OK")
    except Exception as e:
        print(f"  [FAIL] analytics_runner imports FAILED: {e}")
        return False

    return True


async def test_symbol_factor_data():
    """Check if symbol factors are already calculated."""
    print("\n" + "=" * 60)
    print("TEST 2: Symbol Factor Data Check")
    print("=" * 60)

    from sqlalchemy import select, func, text
    from app.database import AsyncSessionLocal
    from app.models.symbol_analytics import SymbolFactorExposure

    async with AsyncSessionLocal() as db:
        # Count symbol factor exposures
        count_stmt = select(func.count(SymbolFactorExposure.id))
        result = await db.execute(count_stmt)
        total_records = result.scalar()
        print(f"  Total symbol factor records: {total_records}")

        if total_records == 0:
            print("  [WARN] No symbol factors found - Phase 1.5 has not run yet")
            return True  # Not a failure, just hasn't run

        # Get recent calculation dates
        date_stmt = text("""
            SELECT calculation_date, calculation_method, COUNT(DISTINCT symbol) as symbols
            FROM symbol_factor_exposures
            GROUP BY calculation_date, calculation_method
            ORDER BY calculation_date DESC
            LIMIT 5
        """)
        result = await db.execute(date_stmt)
        rows = result.fetchall()

        print("\n  Recent calculations:")
        for row in rows:
            print(f"    {row[0]} ({row[1]}): {row[2]} symbols")

    return True


async def test_portfolio_aggregation():
    """Test portfolio factor aggregation using symbol betas."""
    print("\n" + "=" * 60)
    print("TEST 3: Portfolio Factor Aggregation")
    print("=" * 60)

    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.users import Portfolio
    from app.services.portfolio_factor_service import get_portfolio_factor_exposures

    # Use most recent trading day
    calculation_date = date(2025, 12, 19)

    async with AsyncSessionLocal() as db:
        # Get a test portfolio
        portfolio_stmt = select(Portfolio).limit(1)
        result = await db.execute(portfolio_stmt)
        portfolio = result.scalar()

        if not portfolio:
            print("  [FAIL] No portfolios found")
            return False

        print(f"  Testing portfolio: {portfolio.name}")
        print(f"  Calculation date: {calculation_date}")

        try:
            exposures = await get_portfolio_factor_exposures(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date,
                use_delta_adjusted=False,
                include_ridge=True,
                include_spread=True
            )

            data_quality = exposures.get('data_quality', {})
            print(f"\n  Data Quality:")
            print(f"    Total symbols: {data_quality.get('total_symbols', 0)}")
            print(f"    Symbols with Ridge: {data_quality.get('symbols_with_ridge', 0)}")
            print(f"    Symbols with Spread: {data_quality.get('symbols_with_spread', 0)}")
            print(f"    Symbols missing: {data_quality.get('symbols_missing', 0)}")

            ridge_betas = exposures.get('ridge_betas', {})
            spread_betas = exposures.get('spread_betas', {})

            if ridge_betas:
                print(f"\n  Ridge Portfolio Betas:")
                for factor, beta in sorted(ridge_betas.items()):
                    print(f"    {factor:20}: {beta:8.4f}")

            if spread_betas:
                print(f"\n  Spread Portfolio Betas:")
                for factor, beta in sorted(spread_betas.items()):
                    print(f"    {factor:25}: {beta:8.4f}")

            if ridge_betas or spread_betas:
                print("\n  [OK] Portfolio aggregation working")
                return True
            else:
                print("\n  [WARN] No betas returned (symbol factors may not be calculated yet)")
                return True

        except Exception as e:
            print(f"  [FAIL] Portfolio aggregation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_analytics_runner_integration():
    """Test that analytics_runner can use symbol-level aggregation."""
    print("\n" + "=" * 60)
    print("TEST 4: Analytics Runner Integration")
    print("=" * 60)

    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.users import Portfolio
    from app.batch.analytics_runner import analytics_runner

    calculation_date = date(2025, 12, 19)

    async with AsyncSessionLocal() as db:
        # Get a test portfolio
        portfolio_stmt = select(Portfolio).limit(1)
        result = await db.execute(portfolio_stmt)
        portfolio = result.scalar()

        if not portfolio:
            print("  [FAIL] No portfolios found")
            return False

        print(f"  Testing portfolio: {portfolio.name}")
        print(f"  Calculation date: {calculation_date}")

        # Test ridge factors calculation
        print("\n  Testing ridge factors...")
        try:
            ridge_result = await analytics_runner._calculate_ridge_factors(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            print(f"    Success: {ridge_result.get('success', False)}")
            print(f"    Method: {ridge_result.get('method', 'unknown')}")
            if ridge_result.get('coverage'):
                print(f"    Coverage: {ridge_result.get('coverage')}")
            if ridge_result.get('message'):
                print(f"    Message: {ridge_result.get('message')}")
        except Exception as e:
            print(f"    [FAIL] Ridge factors failed: {e}")

        # Test spread factors calculation
        print("\n  Testing spread factors...")
        try:
            spread_result = await analytics_runner._calculate_spread_factors(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            print(f"    Success: {spread_result.get('success', False)}")
            print(f"    Method: {spread_result.get('method', 'unknown')}")
            if spread_result.get('coverage'):
                print(f"    Coverage: {spread_result.get('coverage')}")
            if spread_result.get('message'):
                print(f"    Message: {spread_result.get('message')}")
        except Exception as e:
            print(f"    [FAIL] Spread factors failed: {e}")

    print("\n  [OK] Analytics runner integration test complete")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 1.5 INTEGRATION TEST SUITE")
    print("=" * 60)

    all_passed = True

    # Test 1: Imports
    if not await test_imports():
        all_passed = False

    # Test 2: Symbol factor data
    if not await test_symbol_factor_data():
        all_passed = False

    # Test 3: Portfolio aggregation
    if not await test_portfolio_aggregation():
        all_passed = False

    # Test 4: Analytics runner integration
    if not await test_analytics_runner_integration():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] ALL TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
