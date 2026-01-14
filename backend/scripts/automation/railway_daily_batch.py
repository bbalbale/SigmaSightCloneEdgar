#!/usr/bin/env python3
"""
Railway Daily Automation Script

Runs after market close on trading days to sync data and calculate metrics.

Usage:
  uv run python scripts/automation/railway_daily_batch.py

Environment Variables Required:
  DATABASE_URL - PostgreSQL connection string
  POLYGON_API_KEY - Market data API key
  FMP_API_KEY - Financial Modeling Prep API key
  OPENAI_API_KEY - OpenAI API key for chat features

Workflow:
  Two-phase batch processing:
  - Phase 1: Symbol Batch (market data + factor calculations)
  - Phase 2: Portfolio Refresh (P&L + analytics)

  For on-demand processing (admin API, manual runs), use batch_orchestrator
  via the admin batch endpoint or scripts/batch_processing/run_batch.py.
"""

import os
import asyncio
import sys
from datetime import datetime as dt

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver")

# Add parent directory to path for imports
sys.path.insert(0, '/app')  # Railway container path
sys.path.insert(0, '.')      # Local development path

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.db.seed_factors import seed_factors

logger = get_logger(__name__)


async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch.

    This is critical because:
    1. Factor definitions must exist for analytics to save exposures
    2. Stress testing needs factor exposures to calculate scenario impacts
    3. seed_factors() is idempotent - won't duplicate existing factors
    """
    logger.info("Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("✅ Factor definitions verified/seeded")


async def run_daily_batch():
    """
    Run daily batch processing (symbol batch + portfolio refresh).

    This is the main batch logic for Railway nightly cron.
    """
    job_start = dt.now()

    print("=" * 60)
    print("  SIGMASIGHT DAILY BATCH - STARTING")
    print("=" * 60)
    print(f"Timestamp:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    sys.stdout.flush()

    # Ensure factor definitions exist
    await ensure_factor_definitions()

    symbol_result = None
    portfolio_result = None

    try:
        # Phase 1: Symbol Batch
        print("-" * 60)
        print("PHASE 1: SYMBOL BATCH")
        print("-" * 60)
        sys.stdout.flush()

        from app.batch.v2.symbol_batch_runner import run_symbol_batch
        symbol_result = await run_symbol_batch(
            target_date=None,  # Auto-detect most recent trading day
            backfill=True,     # Enable backfill for missed days
        )

        print(f"Symbol Batch Result: success={symbol_result.get('success')}")
        print(f"  Dates processed: {symbol_result.get('dates_processed', 0)}")
        print(f"  Dates failed: {symbol_result.get('dates_failed', 0)}")
        sys.stdout.flush()

        # Phase 2: Portfolio Refresh
        # Only skip if symbol batch FAILED (not just "nothing to do")
        symbol_success = symbol_result.get('success', False)

        if not symbol_success:
            print("-" * 60)
            print("PHASE 2: PORTFOLIO REFRESH - SKIPPED")
            print("-" * 60)
            print("[WARN] Skipping portfolio refresh due to symbol batch failure")
            sys.stdout.flush()
        else:
            # Always run portfolio refresh - it will check if snapshots are needed
            print("-" * 60)
            print("PHASE 2: PORTFOLIO REFRESH")
            print("-" * 60)
            sys.stdout.flush()

            from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh
            portfolio_result = await run_portfolio_refresh(
                target_date=None,            # Auto-detect most recent trading day
                wait_for_symbol_batch=False, # Already ran symbol batch above
                wait_for_onboarding=True,    # Wait for any pending onboarding
                backfill=True,               # Use data-driven check for missing snapshots
            )

            print(f"Portfolio Refresh Result: success={portfolio_result.get('success')}")
            # Handle both single-date and backfill result formats
            if 'dates_processed' in portfolio_result:
                # Backfill mode
                print(f"  Dates processed: {portfolio_result.get('dates_processed', 0)}")
                print(f"  Dates failed: {portfolio_result.get('dates_failed', 0)}")
                print(f"  Total snapshots: {portfolio_result.get('total_snapshots_created', 0)}")
            else:
                # Single-date mode
                print(f"  Portfolios processed: {portfolio_result.get('portfolios_processed', 0)}")
                print(f"  Snapshots created: {portfolio_result.get('snapshots_created', 0)}")

        sys.stdout.flush()

        # Calculate duration
        job_end = dt.now()
        duration = (job_end - job_start).total_seconds()

        # Print summary
        print("=" * 60)
        print("  SIGMASIGHT DAILY BATCH - COMPLETE")
        print("=" * 60)
        print(f"Duration:     {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Symbol Batch: {'SUCCESS' if symbol_result and symbol_result.get('success') else 'FAILED'}")
        print(f"Portfolio:    {'SUCCESS' if portfolio_result and portfolio_result.get('success') else 'SKIPPED/FAILED'}")
        print("=" * 60)
        sys.stdout.flush()

        # Return success status
        return symbol_result and symbol_result.get('success')

    except Exception as e:
        print(f"[FAIL] Batch error: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return False


async def main():
    """Main entry point for daily batch job."""
    try:
        success = await run_daily_batch()

        if success:
            print("✅ Daily batch completed successfully")
            sys.exit(0)
        else:
            print("❌ Daily batch failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("⚠️ Job interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        print(f"❌ FATAL ERROR: Daily batch job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
