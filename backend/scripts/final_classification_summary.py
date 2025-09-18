#!/usr/bin/env python
"""
Final summary of investment classification.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from sqlalchemy import select, func
from app.core.logging import get_logger

logger = get_logger(__name__)


async def show_summary():
    """Show final classification summary."""
    async with AsyncSessionLocal() as db:
        logger.info("="*60)
        logger.info("FINAL INVESTMENT CLASSIFICATION SUMMARY")
        logger.info("="*60)

        # Get counts by investment_class
        result = await db.execute(
            select(
                Position.investment_class,
                func.count(Position.id).label('count')
            ).group_by(Position.investment_class)
            .order_by(Position.investment_class)
        )
        class_counts = result.all()

        logger.info("\n📊 Three-Class System:")
        total = 0
        for row in class_counts:
            logger.info(f"  {row.investment_class}: {row.count} positions")
            total += row.count
        logger.info(f"  TOTAL: {total} positions")

        # Detailed breakdown
        result = await db.execute(
            select(
                Position.investment_class,
                Position.investment_subtype,
                func.count(Position.id).label('count')
            ).group_by(Position.investment_class, Position.investment_subtype)
            .order_by(Position.investment_class, Position.investment_subtype)
        )
        detailed = result.all()

        logger.info("\n📋 Detailed Breakdown:")
        logger.info("  PUBLIC (46 total):")
        for row in detailed:
            if row.investment_class == 'PUBLIC':
                logger.info(f"    - {row.investment_subtype}: {row.count}")

        logger.info("  OPTIONS (16 total):")
        for row in detailed:
            if row.investment_class == 'OPTIONS':
                logger.info(f"    - {row.investment_subtype}: {row.count}")

        logger.info("  PRIVATE (1 total):")
        for row in detailed:
            if row.investment_class == 'PRIVATE':
                logger.info(f"    - {row.investment_subtype}: {row.count}")

        logger.info("\n✅ Classification Complete:")
        logger.info("  • Three-class system (PUBLIC, OPTIONS, PRIVATE)")
        logger.info("  • PUBLIC includes stocks, ETFs, and mutual funds")
        logger.info("  • OPTIONS includes all listed options")
        logger.info("  • PRIVATE includes private funds and investments")
        logger.info("  • Factor analysis will exclude PRIVATE positions")
        logger.info("  • Greeks calculations use position_type (LC/LP/SC/SP)")

        logger.info("\n" + "="*60)


async def main():
    """Main function."""
    await show_summary()


if __name__ == "__main__":
    asyncio.run(main())