#!/usr/bin/env python
"""
Run Batch Processing on Railway Production
Runs batch calculations for all portfolios to generate P&L and analytics

Usage:
    railway run --service SigmaSight-BE python scripts/railway/run_batch_railway.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import Portfolio
from app.batch.batch_orchestrator import batch_orchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_batch_processing():
    """Run batch processing for all portfolios on Railway"""
    logger.info("=" * 80)
    logger.info("BATCH PROCESSING (Railway Production)")
    logger.info("=" * 80)

    # Count portfolios (separate session, closed before batch runs)
    # FIX: Close session BEFORE calling batch orchestrator to avoid session interference
    # where equity_balance updates weren't persisting correctly on daily runs.
    async with get_async_session() as db:
        portfolio_count = await db.execute(select(func.count(Portfolio.id)))
        total_portfolios = portfolio_count.scalar()
    # Session is now CLOSED before batch processing starts

    logger.info(f"\nFound {total_portfolios} portfolios to process")

    # Run batch processing for all portfolios
    logger.info("\nStarting batch processing...")
    logger.info("This will:")
    logger.info("  - Phase 0: Company profile sync (beta values, sector, industry)")
    logger.info("  - Phase 1: Collect market data (1-year lookback)")
    logger.info("  - Phase 2: Collect fundamental data")
    logger.info("  - Phase 3: Calculate P&L and snapshots")
    logger.info("  - Phase 4: Update position market values")
    logger.info("  - Phase 5: Restore sector tags")
    logger.info("  - Phase 6: Calculate risk analytics (betas, factors, correlations)")

    try:
        # Use the correct batch orchestrator method with automatic backfill
        # Called OUTSIDE any session context - orchestrator manages its own sessions
        result = await batch_orchestrator.run_daily_batch_with_backfill()

        logger.info("\n" + "=" * 80)
        logger.info("BATCH PROCESSING COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Result: {result.get('message', 'Success')}")
        logger.info("\nNext steps:")
        logger.info("  1. Verify calculations via frontend")
        logger.info("  2. Check data quality endpoint: /api/v1/data/portfolio/{id}/data-quality")

    except Exception as e:
        logger.error(f"Error running batch processing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_batch_processing())
