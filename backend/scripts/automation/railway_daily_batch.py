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

from app.core.logging import get_logger
from app.batch.batch_orchestrator import batch_orchestrator

logger = get_logger(__name__)


async def main():
    """Main entry point for daily batch job."""
    job_start = datetime.datetime.now()

    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║       SIGMASIGHT DAILY BATCH WORKFLOW - STARTING             ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info(f"Timestamp: {job_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
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

        # Log completion summary
        logger.info("=" * 60)
        logger.info("DAILY BATCH JOB COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Start Time:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"End Time:      {job_end.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        logger.info(f"")
        logger.info(f"Results: {results}")
        logger.info("=" * 60)

        # Check for success
        if results.get('success'):
            logger.info("✅ All operations completed successfully")
            sys.exit(0)
        else:
            logger.warning(f"⚠️ Job completed with issues: {results.get('message', 'Unknown error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("⚠️ Job interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: Daily batch job failed")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
