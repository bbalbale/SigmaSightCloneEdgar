#!/usr/bin/env python
"""
Seed Demo Portfolios on Railway Production
Seeds all 5 demo portfolios with corrected June 30, 2025 market data

Usage:
    railway run --service SigmaSight-BE python scripts/railway/seed_portfolios_railway.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from app.database import get_async_session
from app.db.seed_demo_portfolios import create_demo_users, seed_demo_portfolios
from app.core.logging import get_logger

logger = get_logger(__name__)


async def seed_railway_portfolios():
    """Seed demo portfolios on Railway"""
    logger.info("=" * 80)
    logger.info("SEEDING DEMO PORTFOLIOS (Railway Production)")
    logger.info("=" * 80)

    async with get_async_session() as db:
        try:
            # Create demo users first
            logger.info("\n1. Creating demo users...")
            await create_demo_users(db)

            # Seed all portfolios
            logger.info("\n2. Seeding demo portfolios...")
            await seed_demo_portfolios(db)

            # Commit changes
            await db.commit()

            logger.info("\n" + "=" * 80)
            logger.info("SEEDING COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info("\nNext steps:")
            logger.info("  1. Run batch processing to calculate P&L and analytics")
            logger.info("  2. Verify data via frontend at sigmasight-fe-production.up.railway.app")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error seeding portfolios: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_railway_portfolios())
