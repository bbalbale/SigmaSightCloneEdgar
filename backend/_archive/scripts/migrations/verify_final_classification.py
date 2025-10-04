#!/usr/bin/env python
"""
Verify final investment classification state.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.users import Portfolio
from sqlalchemy import select, func
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_classification():
    """Verify the final classification state."""
    async with AsyncSessionLocal() as db:
        logger.info("="*60)
        logger.info("FINAL INVESTMENT CLASSIFICATION STATUS")
        logger.info("="*60)

        # 1. Overall classification counts
        result = await db.execute(
            select(
                Position.investment_class,
                Position.investment_subtype,
                func.count(Position.id).label('count')
            ).group_by(Position.investment_class, Position.investment_subtype)
            .order_by(Position.investment_class, Position.investment_subtype)
        )
        classifications = result.all()

        logger.info("\n1. Overall Classification Summary:")
        total = 0
        for row in classifications:
            logger.info(f"   {row.investment_class or 'NULL'}/{row.investment_subtype or 'NONE'}: {row.count} positions")
            total += row.count
        logger.info(f"   TOTAL: {total} positions")

        # 2. By portfolio breakdown
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()

        logger.info("\n2. Portfolio-Level Breakdown:")
        for portfolio in portfolios:
            result = await db.execute(
                select(Position).where(Position.portfolio_id == portfolio.id)
            )
            positions = result.scalars().all()

            class_counts = {}
            for pos in positions:
                cls = pos.investment_class or 'UNCLASSIFIED'
                class_counts[cls] = class_counts.get(cls, 0) + 1

            logger.info(f"\n   {portfolio.name}:")
            logger.info(f"   Total positions: {len(positions)}")
            for cls in sorted(class_counts.keys()):
                logger.info(f"     {cls}: {class_counts[cls]} positions")

        # 3. Verify private positions
        result = await db.execute(
            select(Position).where(Position.investment_class == 'PRIVATE')
        )
        private_positions = result.scalars().all()

        if private_positions:
            logger.info(f"\n3. Private Positions Found: {len(private_positions)}")
            for pos in private_positions:
                logger.info(f"   - {pos.symbol} ({pos.investment_subtype})")

        # 4. Verify alternatives
        result = await db.execute(
            select(Position).where(Position.investment_class == 'ALTERNATIVES')
        )
        alt_positions = result.scalars().all()

        if alt_positions:
            logger.info(f"\n4. Alternative Positions Found: {len(alt_positions)}")
            for pos in alt_positions:
                logger.info(f"   - {pos.symbol} ({pos.investment_subtype})")

        # 5. Verify no unclassified
        result = await db.execute(
            select(func.count(Position.id)).where(Position.investment_class.is_(None))
        )
        unclassified = result.scalar()

        logger.info(f"\n5. Unclassified Positions: {unclassified}")
        if unclassified == 0:
            logger.info("   ✅ All positions have been classified")
        else:
            logger.warning(f"   ⚠️  {unclassified} positions remain unclassified")

        logger.info("\n" + "="*60)
        logger.info("Classification verification complete!")
        logger.info("="*60)


async def main():
    """Main function."""
    await verify_classification()


if __name__ == "__main__":
    asyncio.run(main())