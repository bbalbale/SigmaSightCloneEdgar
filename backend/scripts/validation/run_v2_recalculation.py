#!/usr/bin/env python
"""
Run V2 Batch Recalculation for Validation

This script runs the V2 batch processing (Symbol Batch + Portfolio Refresh)
for a date range to recalculate P&L and metrics after clearing old calculations.

Usage:
    python scripts/validation/run_v2_recalculation.py

Process for each trading day:
    1. run_symbol_batch() - Phase 0 (valuations), Phase 1 (market data), Phase 3 (factors)
    2. run_portfolio_refresh() - Phase 3 (P&L), Phase 4 (correlations), Phase 5 (factor agg), Phase 6 (stress)

Note: Market data is NOT re-fetched since we preserved market_data_cache.
      The batch will use existing cached prices for calculations.
"""
import sys
import asyncio
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

# CRITICAL: Windows + asyncpg compatibility fix - MUST be before any async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set environment variables BEFORE importing app modules
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'
os.environ['AI_DATABASE_URL'] = 'postgresql+asyncpg://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway'

# Date range for validation
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 1, 12)

# Import app's trading calendar (has holiday detection)
from app.core.trading_calendar import get_trading_days_between, is_trading_day


async def run_v2_batch_for_date(calc_date: date) -> dict:
    """
    Run V2 batch (Symbol Batch + Portfolio Refresh) for a single date.

    Returns:
        Dict with results from both phases
    """
    from app.batch.v2.symbol_batch_runner import run_symbol_batch
    from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh

    results = {
        "date": calc_date.isoformat(),
        "symbol_batch": None,
        "portfolio_refresh": None,
        "success": False,
    }

    # Phase 1: Symbol Batch
    print(f"    [Symbol Batch] Running...")
    sys.stdout.flush()

    try:
        symbol_result = await run_symbol_batch(
            target_date=calc_date,
            backfill=False,  # Only run for this specific date
        )
        results["symbol_batch"] = symbol_result
        symbol_success = symbol_result.get("success", False)
        print(f"    [Symbol Batch] {'SUCCESS' if symbol_success else 'FAILED'}")
        if not symbol_success:
            print(f"      Error: {symbol_result.get('error', symbol_result.get('message', 'Unknown'))}")
        sys.stdout.flush()
    except Exception as e:
        print(f"    [Symbol Batch] ERROR: {e}")
        results["symbol_batch"] = {"success": False, "error": str(e)}
        symbol_success = False
        sys.stdout.flush()

    # Phase 2: Portfolio Refresh (only if symbol batch succeeded)
    if symbol_success:
        print(f"    [Portfolio Refresh] Running...")
        sys.stdout.flush()

        try:
            portfolio_result = await run_portfolio_refresh(
                target_date=calc_date,
                wait_for_symbol_batch=False,  # We just ran it above
                wait_for_onboarding=False,    # No onboarding in progress
            )
            results["portfolio_refresh"] = portfolio_result
            portfolio_success = portfolio_result.get("success", False)
            print(f"    [Portfolio Refresh] {'SUCCESS' if portfolio_success else 'FAILED'}")
            if portfolio_success:
                print(f"      Snapshots: {portfolio_result.get('snapshots_created', 0)}")
                print(f"      Correlations: {portfolio_result.get('correlations_calculated', 0)}")
                print(f"      Stress Tests: {portfolio_result.get('stress_tests_calculated', 0)}")
            else:
                print(f"      Error: {portfolio_result.get('error', portfolio_result.get('message', 'Unknown'))}")
            sys.stdout.flush()

            results["success"] = portfolio_success
        except Exception as e:
            print(f"    [Portfolio Refresh] ERROR: {e}")
            results["portfolio_refresh"] = {"success": False, "error": str(e)}
            sys.stdout.flush()
    else:
        print(f"    [Portfolio Refresh] SKIPPED (symbol batch failed)")
        sys.stdout.flush()

    return results


async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch."""
    from app.database import AsyncSessionLocal
    from app.db.seed_factors import seed_factors

    print("Ensuring factor definitions exist...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    print("  Factor definitions verified/seeded")


async def main():
    """Main entry point."""
    print("=" * 70)
    print("V2 BATCH RECALCULATION FOR VALIDATION")
    print("=" * 70)
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print()

    # Get trading days (uses app's trading calendar with holiday detection)
    trading_days = get_trading_days_between(START_DATE, END_DATE)
    print(f"Trading days to process: {len(trading_days)}")
    for td in trading_days:
        print(f"  - {td} ({td.strftime('%A')})")
    print()

    # Ensure factor definitions exist
    await ensure_factor_definitions()
    print()

    # Process each trading day
    all_results = []
    success_count = 0
    fail_count = 0

    start_time = datetime.now()

    for i, calc_date in enumerate(trading_days, 1):
        print("-" * 70)
        print(f"Processing {calc_date} ({i}/{len(trading_days)})")
        print("-" * 70)
        sys.stdout.flush()

        date_start = datetime.now()
        result = await run_v2_batch_for_date(calc_date)
        date_duration = (datetime.now() - date_start).total_seconds()

        result["duration_seconds"] = date_duration
        all_results.append(result)

        if result["success"]:
            success_count += 1
            print(f"  [OK] Completed in {date_duration:.1f}s")
        else:
            fail_count += 1
            print(f"  [FAIL] Failed after {date_duration:.1f}s")

        print()
        sys.stdout.flush()

    total_duration = (datetime.now() - start_time).total_seconds()

    # Print summary
    print("=" * 70)
    print("V2 BATCH RECALCULATION COMPLETE")
    print("=" * 70)
    print(f"Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"Trading Days Processed: {len(trading_days)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print()

    if fail_count > 0:
        print("Failed dates:")
        for result in all_results:
            if not result["success"]:
                print(f"  - {result['date']}")
        print()

    # Per-date summary
    print("Per-date summary:")
    for result in all_results:
        status = "[OK]" if result["success"] else "[FAIL]"
        snapshots = result.get("portfolio_refresh", {}).get("snapshots_created", 0) if result.get("portfolio_refresh") else 0
        print(f"  {status} {result['date']}: {snapshots} snapshots, {result.get('duration_seconds', 0):.1f}s")

    print()


if __name__ == "__main__":
    asyncio.run(main())
