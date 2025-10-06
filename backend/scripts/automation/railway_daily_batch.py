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
  2. Sync latest market data from providers
  3. Run batch calculations for all portfolios
  4. Log completion summary
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


async def sync_market_data_step() -> Dict[str, Any]:
    """
    Sync latest market data from providers.

    Returns:
        Dict with sync results

    Raises:
        Exception if sync fails critically
    """
    from app.batch.market_data_sync import sync_market_data

    logger.info("=" * 60)
    logger.info("STEP 1: Market Data Sync")
    logger.info("=" * 60)

    try:
        start_time = datetime.datetime.now()
        await sync_market_data()
        duration = (datetime.datetime.now() - start_time).total_seconds()

        result = {
            "status": "success",
            "duration_seconds": duration
        }
        logger.info(f"✅ Market data sync complete ({duration:.1f}s)")
        return result

    except Exception as e:
        logger.error(f"❌ Market data sync failed: {e}")
        logger.exception(e)
        raise


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
    logger.info("STEP 2: Batch Calculations")
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

    for idx, portfolio in enumerate(portfolios, 1):
        logger.info(f"\n--- Portfolio {idx}/{len(portfolios)}: {portfolio.name} ({portfolio.id}) ---")

        try:
            start_time = datetime.datetime.now()

            # Run all 8 calculation engines
            batch_result = await batch_orchestrator_v2.run_daily_batch_sequence(
                portfolio_id=str(portfolio.id)
            )

            duration = (datetime.datetime.now() - start_time).total_seconds()

            results.append({
                "portfolio_id": str(portfolio.id),
                "portfolio_name": portfolio.name,
                "status": "success",
                "duration_seconds": duration,
                "result": batch_result
            })

            success_count += 1
            logger.info(f"✅ Batch complete for {portfolio.name} ({duration:.1f}s)")

        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()

            results.append({
                "portfolio_id": str(portfolio.id),
                "portfolio_name": portfolio.name,
                "status": "error",
                "duration_seconds": duration,
                "error": str(e)
            })

            fail_count += 1
            logger.error(f"❌ Batch failed for {portfolio.name}: {e}")
            logger.exception(e)
            # Continue to next portfolio

    logger.info(f"\n📊 Batch Summary: {success_count} succeeded, {fail_count} failed")
    return results


async def log_completion_summary(
    start_time: datetime.datetime,
    market_data_result: Dict[str, Any],
    batch_results: List[Dict[str, Any]]
) -> None:
    """
    Log final completion summary.

    Args:
        start_time: Job start timestamp
        market_data_result: Market data sync result
        batch_results: List of portfolio batch results
    """
    end_time = datetime.datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    success_count = sum(1 for r in batch_results if r["status"] == "success")
    fail_count = len(batch_results) - success_count

    logger.info("=" * 60)
    logger.info("DAILY BATCH JOB COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Start Time:    {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End Time:      {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    logger.info(f"")
    logger.info(f"Market Data Sync: {market_data_result['status']} ({market_data_result['duration_seconds']:.1f}s)")
    logger.info(f"Portfolios:       {success_count} succeeded, {fail_count} failed")
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

        # Step 1: Sync market data
        market_data_result = await sync_market_data_step()

        # Step 2: Run batch calculations
        batch_results = await run_batch_calculations_step()

        # Step 3: Log completion summary
        await log_completion_summary(job_start, market_data_result, batch_results)

    except KeyboardInterrupt:
        logger.warning("⚠️ Job interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: Daily batch job failed")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
