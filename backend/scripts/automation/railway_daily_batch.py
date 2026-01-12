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
  The batch orchestrator handles everything:
  - Trading day detection and adjustment
  - Phase 0: Company profile sync (on final date only)
  - Phase 1: Market data collection
  - Phase 2: Fundamental data collection
  - Phase 3: P&L calculation & snapshots
  - Phase 4: Position market value updates
  - Phase 5: Sector tag restoration
  - Phase 6: Risk analytics

Phase 11.1 Change: Simplified to use batch orchestrator directly.
All trading day logic, company profile sync, and batch processing is now
handled by the batch orchestrator's run_daily_batch_with_backfill() method.
This eliminates code duplication and ensures Railway uses the same code path
as local batch processing (scripts/batch_processing/run_batch.py).
"""

import os
import asyncio
import sys
import datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver")

# Add parent directory to path for imports
sys.path.insert(0, '/app')  # Railway container path
sys.path.insert(0, '.')      # Local development path

from app.config import settings
from app.core.logging import get_logger
from app.batch.batch_orchestrator import batch_orchestrator
from app.database import AsyncSessionLocal
from app.db.seed_factors import seed_factors

logger = get_logger(__name__)


async def run_v2_batch():
    """
    Run V2 batch logic directly (symbol batch + portfolio refresh).

    This is called when BATCH_V2_ENABLED=true instead of V1 legacy batch.
    """
    from datetime import datetime as dt

    job_start = dt.now()

    print("=" * 60)
    print("  SIGMASIGHT DAILY BATCH V2 - STARTING")
    print("=" * 60)
    print(f"Timestamp:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"V2 Enabled:   True")
    print("=" * 60)
    sys.stdout.flush()

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

        # Phase 2: Portfolio Refresh (only if symbol batch succeeded)
        if symbol_result.get('success'):
            print("-" * 60)
            print("PHASE 2: PORTFOLIO REFRESH")
            print("-" * 60)
            sys.stdout.flush()

            from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh
            portfolio_result = await run_portfolio_refresh(
                target_date=None,            # Auto-detect most recent trading day
                wait_for_symbol_batch=False, # Already ran symbol batch above
                wait_for_onboarding=True,    # Wait for any pending onboarding
            )

            print(f"Portfolio Refresh Result: success={portfolio_result.get('success')}")
            print(f"  Portfolios processed: {portfolio_result.get('portfolios_processed', 0)}")
            print(f"  Snapshots created: {portfolio_result.get('snapshots_created', 0)}")
        else:
            print("[WARN] Skipping portfolio refresh due to symbol batch failure")

        sys.stdout.flush()

        # Calculate duration
        job_end = dt.now()
        duration = (job_end - job_start).total_seconds()

        # Print summary
        print("=" * 60)
        print("  SIGMASIGHT DAILY BATCH V2 - COMPLETE")
        print("=" * 60)
        print(f"Duration:     {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Symbol Batch: {'SUCCESS' if symbol_result and symbol_result.get('success') else 'FAILED'}")
        print(f"Portfolio:    {'SUCCESS' if portfolio_result and portfolio_result.get('success') else 'SKIPPED/FAILED'}")
        print("=" * 60)
        sys.stdout.flush()

        # Return success status
        return symbol_result and symbol_result.get('success')

    except Exception as e:
        print(f"[FAIL] V2 batch error: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return False


def check_v2_guard():
    """
    V2 Architecture Guard: Redirect to V2 batch when enabled.

    When BATCH_V2_ENABLED=true, this script runs the V2 batch logic directly
    instead of V1 legacy batch. This allows seamless migration without
    changing Railway cron configuration.
    """
    if settings.BATCH_V2_ENABLED:
        print("=" * 60)
        print("[V2] V2 BATCH MODE ENABLED - RUNNING V2 BATCH")
        print("=" * 60)
        sys.stdout.flush()

        # Run V2 batch directly
        success = asyncio.run(run_v2_batch())

        if success:
            print("[OK] V2 batch completed successfully")
            sys.exit(0)
        else:
            print("[FAIL] V2 batch failed")
            sys.exit(1)


async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch.

    This is critical because:
    1. Factor definitions must exist for analytics_runner to save exposures
    2. Stress testing needs factor exposures to calculate scenario impacts
    3. seed_factors() is idempotent - won't duplicate existing factors
    """
    logger.info("Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("✅ Factor definitions verified/seeded")


async def main():
    """Main entry point for daily batch job."""
    # V2 Guard: Exit early if V2 batch mode is enabled
    check_v2_guard()

    job_start = datetime.datetime.now()

    # Use print() for critical messages - logger.info() doesn't show in Railway logs
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       SIGMASIGHT DAILY BATCH WORKFLOW - STARTING (V1)        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"Timestamp: {job_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        # Ensure factor definitions exist before running batch
        await ensure_factor_definitions()

        # Run the batch orchestrator - it handles everything:
        # - Trading day detection and adjustment (to previous trading day if needed)
        # - Phase 0: Company profile sync (on final date only)
        # - Phase 1: Market data collection (1-year lookback)
        # - Phase 2: Fundamental data collection (earnings-driven)
        # - Phase 3: P&L calculation & snapshots (equity rollforward)
        # - Phase 4: Position market value updates (for analytics accuracy)
        # - Phase 5: Sector tag restoration (auto-tag from company profiles)
        # - Phase 6: Risk analytics (betas, factors, volatility, correlations)

        logger.info("Starting batch orchestrator with automatic backfill...")
        results = await batch_orchestrator.run_daily_batch_with_backfill()

        # Calculate total duration
        job_end = datetime.datetime.now()
        total_duration = (job_end - job_start).total_seconds()

        # Print completion summary - use print() for Railway visibility
        print("=" * 60)
        print("DAILY BATCH JOB COMPLETE")
        print("=" * 60)
        print(f"Start Time:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:      {job_end.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        print(f"Results: {results}")
        print("=" * 60)

        # Check for success
        if results.get('success'):
            print("✅ All operations completed successfully")
            sys.exit(0)
        else:
            print(f"⚠️ Job completed with issues: {results.get('message', 'Unknown error')}")
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
