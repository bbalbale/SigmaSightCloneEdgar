#!/usr/bin/env python3
"""
Railway Daily Automation Script

Runs after market close on trading days to sync data and calculate metrics.

Usage:
  uv run python scripts/automation/railway_daily_batch.py [--force]

Options:
  --force    Run even on non-trading days (for testing)

Environment Variables Required:
  DATABASE_URL - PostgreSQL connection string
  POLYGON_API_KEY - Market data API key
  FMP_API_KEY - Financial Modeling Prep API key
  OPENAI_API_KEY - OpenAI API key for chat features

Workflow:
  1. Check if today is a trading day (NYSE calendar)
  2. Run batch calculations for all portfolios (market data synced per-portfolio)
  3. Log completion summary

Phase 10.1 Change: Removed upfront market data sync to eliminate 4x duplication.
Market data is now synced once per portfolio by the batch orchestrator.
"""

import os
import asyncio
import sys
import argparse
import datetime
from typing import Dict, List, Any

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
from app.models.users import Portfolio
from sqlalchemy import select
from scripts.automation.trading_calendar import is_trading_day

logger = get_logger(__name__)


async def check_trading_day(force: bool = False) -> bool:
    """
    Check if today is a trading day.

    Args:
        force: If True, bypass trading day check

    Returns:
        True if should proceed with batch job, False otherwise
    """
    today = datetime.date.today()

    if force:
        logger.info(f"⚠️ FORCE MODE: Running batch job on {today} (may be non-trading day)")
        return True

    if is_trading_day(today):
        logger.info(f"✅ {today} is a trading day - proceeding with batch job")
        return True
    else:
        logger.info(f"⏭️ {today} is NOT a trading day - skipping batch job")
        logger.info(f"   (Use --force flag to run anyway)")
        return False


async def run_batch_calculations_step() -> List[Dict[str, Any]]:
    """
    Run batch calculations for all active portfolios.

    Returns:
        List of results for each portfolio

    Notes:
        Continues processing other portfolios if one fails
    """
    from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

    logger.info("=" * 60)
    logger.info("STEP 1: Batch Calculations (with per-portfolio market data sync)")
    logger.info("=" * 60)

    # Get all active portfolios
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.deleted_at.is_(None))
        )
        portfolios = list(result.scalars().all())

    if not portfolios:
        logger.warning("No active portfolios found")
        return []

    logger.info(f"Found {len(portfolios)} active portfolio(s) to process")

    results = []
    success_count = 0
    fail_count = 0

    # Phase 10.2: Define critical vs non-critical jobs
    CRITICAL_JOBS = ['market_data_update', 'portfolio_aggregation']

    for idx, portfolio in enumerate(portfolios, 1):
        logger.info(f"\n--- Portfolio {idx}/{len(portfolios)}: {portfolio.name} ({portfolio.id}) ---")

        try:
            start_time = datetime.datetime.now()

            # Run all 8 calculation engines
            batch_result = await batch_orchestrator_v2.run_daily_batch_sequence(
                portfolio_id=str(portfolio.id)
            )

            duration = (datetime.datetime.now() - start_time).total_seconds()

            # Phase 10.2: Inspect batch_result for failures
            failed_jobs = [j for j in batch_result if j.get('status') == 'failed']
            critical_failures = [j for j in failed_jobs if j.get('job_name') in CRITICAL_JOBS]
            non_critical_failures = [j for j in failed_jobs if j.get('job_name') not in CRITICAL_JOBS]

            if critical_failures:
                # Critical job failures = portfolio failure
                fail_count += 1
                failed_job_names = [j['job_name'] for j in critical_failures]
                logger.error(f"❌ Critical job failures for {portfolio.name}: {failed_job_names}")

                results.append({
                    "portfolio_id": str(portfolio.id),
                    "portfolio_name": portfolio.name,
                    "status": "failed",
                    "duration_seconds": duration,
                    "failed_jobs": failed_job_names,
                    "critical_failures": len(critical_failures),
                    "non_critical_failures": len(non_critical_failures),
                    "result": batch_result
                })
            else:
                # No critical failures = success (even if non-critical jobs failed)
                success_count += 1

                if non_critical_failures:
                    failed_job_names = [j['job_name'] for j in non_critical_failures]
                    logger.warning(f"⚠️ Non-critical job failures for {portfolio.name}: {failed_job_names}")
                    logger.info(f"✅ Batch complete for {portfolio.name} ({duration:.1f}s) - with warnings")
                else:
                    logger.info(f"✅ Batch complete for {portfolio.name} ({duration:.1f}s)")

                results.append({
                    "portfolio_id": str(portfolio.id),
                    "portfolio_name": portfolio.name,
                    "status": "success",
                    "duration_seconds": duration,
                    "failed_jobs": [j['job_name'] for j in non_critical_failures] if non_critical_failures else [],
                    "critical_failures": 0,
                    "non_critical_failures": len(non_critical_failures),
                    "result": batch_result
                })

        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()

            results.append({
                "portfolio_id": str(portfolio.id),
                "portfolio_name": portfolio.name,
                "status": "error",
                "duration_seconds": duration,
                "error": str(e),
                "failed_jobs": ["exception_raised"],
                "critical_failures": 1,
                "non_critical_failures": 0
            })

            fail_count += 1
            logger.error(f"❌ Batch failed for {portfolio.name}: {e}")
            logger.exception(e)
            # Continue to next portfolio

    logger.info(f"\n📊 Batch Summary: {success_count} succeeded, {fail_count} failed")
    return results


async def log_completion_summary(
    start_time: datetime.datetime,
    batch_results: List[Dict[str, Any]]
) -> None:
    """
    Log final completion summary.

    Phase 10.1: Removed market_data_result parameter (sync now per-portfolio).
    Phase 10.2: Enhanced with job-level failure details.

    Args:
        start_time: Job start timestamp
        batch_results: List of portfolio batch results
    """
    end_time = datetime.datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    success_count = sum(1 for r in batch_results if r["status"] == "success")
    fail_count = sum(1 for r in batch_results if r["status"] in ["failed", "error"])

    # Phase 10.2: Collect job-level failure details
    total_critical_failures = sum(r.get("critical_failures", 0) for r in batch_results)
    total_non_critical_failures = sum(r.get("non_critical_failures", 0) for r in batch_results)

    logger.info("=" * 60)
    logger.info("DAILY BATCH JOB COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Start Time:    {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End Time:      {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    logger.info(f"")
    logger.info(f"Portfolios:    {success_count} succeeded, {fail_count} failed")

    # Phase 10.2: Log job-level failure details
    if total_critical_failures > 0 or total_non_critical_failures > 0:
        logger.info(f"Job Failures:  {total_critical_failures} critical, {total_non_critical_failures} non-critical")

        # Log specific failed jobs per portfolio
        for result in batch_results:
            if result.get("failed_jobs"):
                portfolio_name = result.get("portfolio_name", "Unknown")
                failed_jobs = result.get("failed_jobs", [])
                logger.info(f"  - {portfolio_name}: {', '.join(failed_jobs)}")

    logger.info("=" * 60)

    # Exit with error code if any portfolios failed
    if fail_count > 0:
        logger.warning(f"⚠️ Job completed with {fail_count} portfolio failure(s)")
        sys.exit(1)
    else:
        logger.info("✅ All operations completed successfully")
        sys.exit(0)


async def main():
    """Main entry point for daily batch job."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Railway Daily Batch Job - Market Data Sync & Calculations'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force execution even on non-trading days'
    )
    args = parser.parse_args()

    job_start = datetime.datetime.now()

    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║       SIGMASIGHT DAILY BATCH WORKFLOW - STARTING             ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info(f"Timestamp: {job_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Force Mode: {'ENABLED' if args.force else 'DISABLED'}")

    try:
        # Step 0: Check trading day
        should_run = await check_trading_day(force=args.force)
        if not should_run:
            logger.info("Exiting: Not a trading day")
            sys.exit(0)

        # Step 1: Run batch calculations (includes per-portfolio market data sync)
        # Phase 10.1: Removed upfront market data sync to eliminate 4x duplication
        batch_results = await run_batch_calculations_step()

        # Step 2: Log completion summary
        await log_completion_summary(job_start, batch_results)

    except KeyboardInterrupt:
        logger.warning("⚠️ Job interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: Daily batch job failed")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
