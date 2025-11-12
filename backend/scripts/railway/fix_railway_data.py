#!/usr/bin/env python
"""
Complete Railway Data Fix - ALL-IN-ONE
Clears calculations, seeds portfolios, and runs batch processing in one command

Usage:
    railway run --service SigmaSight-BE python scripts/railway/fix_railway_data.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from sqlalchemy import select, delete, func
from app.database import get_async_session
from app.models.market_data import PositionGreeks, PositionFactorExposure
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from app.db.seed_demo_portfolios import create_demo_users, seed_demo_portfolios
from app.batch.batch_orchestrator import batch_orchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fix_railway_data():
    """Complete data fix: clear calculations, seed portfolios, run batch"""
    logger.info("=" * 80)
    logger.info("RAILWAY PRODUCTION DATA FIX - COMPLETE WORKFLOW")
    logger.info("=" * 80)

    # STEP 1: Clear old calculations
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1/3: CLEARING OLD CALCULATIONS")
    logger.info("=" * 80)

    async with get_async_session() as db:
        try:
            # Count before deletion
            greeks_count = await db.execute(select(func.count(PositionGreeks.id)))
            greeks_before = greeks_count.scalar()

            factor_count = await db.execute(select(func.count(PositionFactorExposure.id)))
            factors_before = factor_count.scalar()

            corr_count = await db.execute(select(func.count(CorrelationCalculation.id)))
            corr_before = corr_count.scalar()

            snapshot_count = await db.execute(select(func.count(PortfolioSnapshot.id)))
            snapshots_before = snapshot_count.scalar()

            total_calculations = greeks_before + factors_before + corr_before + snapshots_before

            logger.info(f"\nFound {total_calculations} calculation records to clear:")
            logger.info(f"  - Position Greeks: {greeks_before}")
            logger.info(f"  - Position Factor Exposures: {factors_before}")
            logger.info(f"  - Correlation Calculations: {corr_before}")
            logger.info(f"  - Portfolio Snapshots: {snapshots_before}")

            # Delete calculation data
            logger.info("\nClearing calculation data...")
            await db.execute(delete(PositionGreeks))
            await db.execute(delete(PositionFactorExposure))
            await db.execute(delete(CorrelationCalculation))
            await db.execute(delete(PortfolioSnapshot))

            await db.commit()
            logger.info(f"✓ Cleared {total_calculations} calculation records")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error clearing calculations: {e}")
            raise

    # STEP 2: Seed portfolios with corrected data
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2/3: SEEDING PORTFOLIOS WITH CORRECTED DATA")
    logger.info("=" * 80)

    async with get_async_session() as db:
        try:
            # Create demo users
            logger.info("\nCreating demo users...")
            await create_demo_users(db)

            # Seed portfolios
            logger.info("\nSeeding demo portfolios with June 30, 2025 market data...")
            await seed_demo_portfolios(db)

            await db.commit()
            logger.info("✓ Portfolios seeded successfully")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error seeding portfolios: {e}")
            raise

    # STEP 3: Run batch processing
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3/3: RUNNING BATCH PROCESSING")
    logger.info("=" * 80)

    try:
        async with get_async_session() as db:
            # Count portfolios
            portfolio_count = await db.execute(select(func.count(Portfolio.id)))
            total_portfolios = portfolio_count.scalar()
            logger.info(f"\nProcessing {total_portfolios} portfolios...")

        logger.info("\nBatch processing phases:")
        logger.info("  - Phase 0: Company profile sync (beta values, sector, industry)")
        logger.info("  - Phase 1: Market data collection (1-year lookback)")
        logger.info("  - Phase 2: Fundamental data collection")
        logger.info("  - Phase 3: P&L calculation & snapshots")
        logger.info("  - Phase 4: Position market value updates")
        logger.info("  - Phase 5: Sector tag restoration")
        logger.info("  - Phase 6: Risk analytics (betas, factors, correlations)")

        # Use the correct batch orchestrator method with automatic backfill
        result = await batch_orchestrator.run_daily_batch_with_backfill()

        logger.info(f"✓ Batch processing completed: {result.get('message', 'Success')}")

    except Exception as e:
        logger.error(f"Error running batch processing: {e}")
        raise

    # FINAL SUMMARY
    logger.info("\n" + "=" * 80)
    logger.info("RAILWAY DATA FIX COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
    logger.info("\nWhat was done:")
    logger.info(f"  1. Cleared {total_calculations} old calculation records")
    logger.info(f"  2. Seeded {total_portfolios} portfolios with corrected June 30, 2025 data")
    logger.info(f"  3. Ran batch processing to generate P&L and analytics")
    logger.info("\nNext steps:")
    logger.info("  1. Visit: https://sigmasight-fe-production.up.railway.app")
    logger.info("  2. Login with: demo_hnw@sigmasight.com / demo12345")
    logger.info("  3. Verify portfolio shows correct data and P&L")
    logger.info("\nExpected results:")
    logger.info("  - Demo HNW: 39 positions, correct YTD P&L")
    logger.info("  - Demo Hedge Fund: 30 positions, correct YTD P&L")
    logger.info("  - Demo Family Office: 12 + 9 positions (2 portfolios)")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(fix_railway_data())
