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

from app.database import get_async_session
from app.services.admin_fix_service import clear_calculations_comprehensive
from app.core.logging import get_logger

logger = get_logger(__name__)


async def clear_calculation_data():
    """Clear all calculated data from the database"""
    logger.info("=" * 80)
    logger.info("CLEARING CALCULATION DATA (Railway Production)")
    logger.info("=" * 80)

    async with get_async_session() as db:
        try:
            results = await clear_calculations_comprehensive(db)
            await db.commit()

            logger.info("\nCleared tables:")
            for label, count in results["tables"].items():
                logger.info(f"  - {label}: {count}")

            logger.info("\n" + "=" * 80)
            logger.info("CALCULATION DATA CLEARED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"\nCleared {results['grand_total_deleted']} total calculation records")
            logger.info("\nNOTE: Market data cache (historical_prices) was NOT cleared")
            logger.info("      Run batch processing to regenerate calculations")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error clearing calculation data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(clear_calculation_data())
