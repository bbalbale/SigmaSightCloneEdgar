"""
Cleanup July 1-15, 2025 data to test fresh batch run with historical data fetching
"""
import asyncio
from datetime import date
from sqlalchemy import delete, and_
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import (
    PositionMarketBeta,
    PositionInterestRateBeta,
    PositionFactorExposure,
    PositionVolatility
)
from app.models.batch_tracking import BatchRunTracking
from app.core.logging import get_logger

logger = get_logger(__name__)


async def cleanup_july_data():
    """Delete all July 1-15, 2025 analytics and snapshot data"""

    start_date = date(2025, 7, 1)
    end_date = date(2025, 7, 15)

    logger.info("=" * 80)
    logger.info(f"Cleaning up data for {start_date} to {end_date}")
    logger.info("=" * 80)

    async with AsyncSessionLocal() as db:

        # 1. Delete portfolio snapshots
        logger.info("\n1. Deleting portfolio snapshots...")
        result = await db.execute(
            delete(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.snapshot_date >= start_date,
                    PortfolioSnapshot.snapshot_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} portfolio snapshots")

        # 2. Delete market betas
        logger.info("\n2. Deleting market betas...")
        result = await db.execute(
            delete(PositionMarketBeta).where(
                and_(
                    PositionMarketBeta.calc_date >= start_date,
                    PositionMarketBeta.calc_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} market beta records")

        # 3. Delete IR betas
        logger.info("\n3. Deleting IR betas...")
        result = await db.execute(
            delete(PositionInterestRateBeta).where(
                and_(
                    PositionInterestRateBeta.calculation_date >= start_date,
                    PositionInterestRateBeta.calculation_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} IR beta records")

        # 4. Delete factor exposures
        logger.info("\n4. Deleting factor exposures...")
        result = await db.execute(
            delete(PositionFactorExposure).where(
                and_(
                    PositionFactorExposure.calculation_date >= start_date,
                    PositionFactorExposure.calculation_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} factor exposure records")

        # 5. Delete volatility metrics
        logger.info("\n5. Deleting volatility metrics...")
        result = await db.execute(
            delete(PositionVolatility).where(
                and_(
                    PositionVolatility.calculation_date >= start_date,
                    PositionVolatility.calculation_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} volatility records")

        # 6. Delete batch run tracking
        logger.info("\n6. Deleting batch run tracking...")
        result = await db.execute(
            delete(BatchRunTracking).where(
                and_(
                    BatchRunTracking.run_date >= start_date,
                    BatchRunTracking.run_date <= end_date
                )
            )
        )
        logger.info(f"   Deleted {result.rowcount} batch tracking records")

        # Commit all deletions
        await db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ July 1-15 data cleanup complete!")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(cleanup_july_data())
