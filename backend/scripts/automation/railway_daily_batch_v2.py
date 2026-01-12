#!/usr/bin/env python3
"""
Railway Daily Batch V2 - Unified Entry Point

Replacement for railway_daily_batch.py when BATCH_V2_ENABLED=true.
Runs the V2 two-phase batch architecture in sequence:
  1. Symbol Batch: Process all symbols (prices, factors, profiles)
  2. Portfolio Refresh: Create snapshots for all portfolios

Usage:
  uv run python scripts/automation/railway_daily_batch_v2.py

Environment Variables Required:
  BATCH_V2_ENABLED=true   - Must be enabled for V2 mode
  DATABASE_URL            - PostgreSQL connection string
  POLYGON_API_KEY         - Market data API key
  FMP_API_KEY             - Financial Modeling Prep API key

Railway Cron Configuration:
  Schedule: 0 2 * * 1-5  (9 PM ET = 2 AM UTC next day, weekdays only)
  Command: uv run python scripts/automation/railway_daily_batch_v2.py

V2 Architecture Benefits:
  - O(symbols) instead of O(users x symbols x dates)
  - Instant onboarding (< 5 seconds vs 15-30 minutes)
  - Reuses cached symbol data for all portfolios
  - Two-phase processing with clear separation
"""

import os
import sys
import asyncio
from datetime import datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("[OK] Converted DATABASE_URL to use asyncpg driver")

# Add parent directory to path for imports
sys.path.insert(0, '/app')  # Railway container path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def check_v2_enabled():
    """
    Verify V2 batch mode is enabled.

    This script should only run when BATCH_V2_ENABLED=true.
    If V1 mode, the legacy railway_daily_batch.py should be used instead.
    """
    if not settings.BATCH_V2_ENABLED:
        print("=" * 60)
        print("[SKIP] V2 BATCH MODE NOT ENABLED")
        print("=" * 60)
        print("BATCH_V2_ENABLED=false detected.")
        print("")
        print("To use V2 batch, set BATCH_V2_ENABLED=true")
        print("")
        print("For V1 mode, use:")
        print("  uv run python scripts/automation/railway_daily_batch.py")
        print("=" * 60)
        sys.exit(0)  # Exit 0 = graceful skip (not an error)


async def run_symbol_batch():
    """Run V2 symbol batch (Phase 1)."""
    from app.batch.v2.symbol_batch_runner import run_symbol_batch as _run_symbol_batch

    print("-" * 60)
    print("PHASE 1: SYMBOL BATCH")
    print("-" * 60)

    result = await _run_symbol_batch(
        target_date=None,  # Auto-detect most recent trading day
        backfill=True,     # Enable backfill for missed days
    )

    print(f"Symbol Batch Result: success={result.get('success')}")
    print(f"  Dates processed: {result.get('dates_processed', 0)}")
    print(f"  Dates failed: {result.get('dates_failed', 0)}")

    return result


async def run_portfolio_refresh():
    """Run V2 portfolio refresh (Phase 2)."""
    from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh as _run_portfolio_refresh

    print("-" * 60)
    print("PHASE 2: PORTFOLIO REFRESH")
    print("-" * 60)

    result = await _run_portfolio_refresh(
        target_date=None,           # Auto-detect most recent trading day
        wait_for_symbol_batch=False, # Already ran symbol batch above
        wait_for_onboarding=True,    # Wait for any pending onboarding
    )

    print(f"Portfolio Refresh Result: success={result.get('success')}")
    print(f"  Portfolios processed: {result.get('portfolios_processed', 0)}")
    print(f"  Snapshots created: {result.get('snapshots_created', 0)}")

    return result


async def main():
    """Main entry point for V2 daily batch."""
    # Check V2 mode is enabled
    check_v2_enabled()

    job_start = datetime.now()

    print("=" * 60)
    print("  SIGMASIGHT DAILY BATCH V2 - STARTING")
    print("=" * 60)
    print(f"Timestamp:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"V2 Enabled:   {settings.BATCH_V2_ENABLED}")
    print("=" * 60)

    symbol_result = None
    portfolio_result = None

    try:
        # Phase 1: Symbol Batch
        symbol_result = await run_symbol_batch()

        # Phase 2: Portfolio Refresh (only if symbol batch succeeded)
        if symbol_result.get('success'):
            portfolio_result = await run_portfolio_refresh()
        else:
            print("[WARN] Skipping portfolio refresh due to symbol batch failure")

        # Calculate duration
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        # Print summary
        print("=" * 60)
        print("  SIGMASIGHT DAILY BATCH V2 - COMPLETE")
        print("=" * 60)
        print(f"Duration:     {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Symbol Batch: {'SUCCESS' if symbol_result and symbol_result.get('success') else 'FAILED'}")
        print(f"Portfolio:    {'SUCCESS' if portfolio_result and portfolio_result.get('success') else 'SKIPPED/FAILED'}")
        print("=" * 60)

        # Determine exit code
        if symbol_result and symbol_result.get('success'):
            if portfolio_result and portfolio_result.get('success'):
                print("[OK] V2 batch completed successfully")
                sys.exit(0)
            else:
                print("[WARN] V2 batch completed with portfolio refresh issues")
                sys.exit(1)
        else:
            print("[FAIL] V2 batch failed at symbol batch phase")
            sys.exit(1)

    except KeyboardInterrupt:
        print("[WARN] V2 batch interrupted by user (Ctrl+C)")
        sys.exit(130)

    except Exception as e:
        print(f"[FAIL] FATAL ERROR: V2 batch failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
