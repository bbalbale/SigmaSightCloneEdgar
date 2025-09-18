#!/usr/bin/env python
"""
Fix classification to use only three classes: PUBLIC, OPTIONS, PRIVATE.
GLD and DJP are ETFs and should be PUBLIC, not ALTERNATIVES.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fix_classification():
    """Fix positions incorrectly classified as ALTERNATIVES - they should be PUBLIC."""
    async with AsyncSessionLocal() as db:
        # Find positions incorrectly classified as ALTERNATIVES
        result = await db.execute(
            select(Position).where(Position.investment_class == 'ALTERNATIVES')
        )
        alternatives_positions = result.scalars().all()

        logger.info(f"Found {len(alternatives_positions)} positions classified as ALTERNATIVES")

        if alternatives_positions:
            logger.info("\nReclassifying to PUBLIC (these are ETFs):")
            for pos in alternatives_positions:
                logger.info(f"  - {pos.symbol}: ALTERNATIVES -> PUBLIC")
                pos.investment_class = 'PUBLIC'
                pos.investment_subtype = 'ETF'  # More accurate than 'STOCK'

            await db.commit()
            logger.info(f"\n✅ Reclassified {len(alternatives_positions)} positions to PUBLIC/ETF")

        # Verify final state - should only have PUBLIC, OPTIONS, and PRIVATE
        result = await db.execute(
            select(Position.investment_class, Position.investment_subtype)
            .distinct()
        )
        classifications = result.all()

        logger.info("\n" + "="*60)
        logger.info("FINAL CLASSIFICATION TYPES:")
        unique_classes = set()
        for row in classifications:
            unique_classes.add(row.investment_class)
            logger.info(f"  - {row.investment_class}/{row.investment_subtype}")

        logger.info(f"\nUnique investment classes: {sorted(unique_classes)}")

        if len(unique_classes) <= 3:
            logger.info("✅ Successfully using 3-class system (PUBLIC, OPTIONS, PRIVATE)")
        else:
            logger.warning(f"⚠️ Found {len(unique_classes)} classes, expected 3")

        # Show counts by class
        from sqlalchemy import func
        result = await db.execute(
            select(
                Position.investment_class,
                func.count(Position.id).label('count')
            ).group_by(Position.investment_class)
            .order_by(Position.investment_class)
        )
        counts = result.all()

        logger.info("\nFinal counts by investment_class:")
        for row in counts:
            logger.info(f"  {row.investment_class}: {row.count} positions")


async def main():
    """Main function."""
    await fix_classification()


if __name__ == "__main__":
    asyncio.run(main())