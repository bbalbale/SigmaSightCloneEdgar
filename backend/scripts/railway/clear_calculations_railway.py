#!/usr/bin/env python
"""
Clear Calculation Data on Railway Production
Clears snapshots, factor exposures, greeks, and correlations WITHOUT touching market data cache

Usage:
    railway run --service SigmaSight-BE python scripts/railway/clear_calculations_railway.py
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
from app.core.logging import get_logger

logger = get_logger(__name__)


async def clear_calculation_data():
    """Clear all calculated data from the database"""
    logger.info("=" * 80)
    logger.info("CLEARING CALCULATION DATA (Railway Production)")
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

            logger.info(f"\nBefore deletion:")
            logger.info(f"  Position Greeks: {greeks_before}")
            logger.info(f"  Position Factor Exposures: {factors_before}")
            logger.info(f"  Correlation Calculations: {corr_before}")
            logger.info(f"  Portfolio Snapshots: {snapshots_before}")

            # Delete calculation data
            logger.info("\nDeleting calculation data...")

            await db.execute(delete(PositionGreeks))
            logger.info("  ✓ Cleared position_greeks")

            await db.execute(delete(PositionFactorExposure))
            logger.info("  ✓ Cleared position_factor_exposures")

            await db.execute(delete(CorrelationCalculation))
            logger.info("  ✓ Cleared correlation_calculations")

            await db.execute(delete(PortfolioSnapshot))
            logger.info("  ✓ Cleared portfolio_snapshots")

            # Commit changes
            await db.commit()

            logger.info("\n" + "=" * 80)
            logger.info("CALCULATION DATA CLEARED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"\nCleared {greeks_before + factors_before + corr_before + snapshots_before} total calculation records")
            logger.info("\nNOTE: Market data cache (historical_prices) was NOT cleared")
            logger.info("      Run batch processing to regenerate calculations")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error clearing calculation data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(clear_calculation_data())
