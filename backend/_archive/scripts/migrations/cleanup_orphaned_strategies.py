"""
Cleanup orphaned standalone strategies (strategies with no positions)

This script finds and deletes standalone strategies that have no positions linked to them.
These are created when positions are combined into a new strategy but the old standalone
strategies aren't automatically deleted.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models import Strategy, Position
from app.core.logging import get_logger

logger = get_logger(__name__)


async def cleanup_orphaned_strategies():
    """Find and delete standalone strategies with no positions"""

    async with get_async_session() as db:
        # Find all standalone strategies
        result = await db.execute(
            select(Strategy).where(Strategy.strategy_type == 'standalone')
        )
        standalone_strategies = result.scalars().all()

        logger.info(f"Found {len(standalone_strategies)} standalone strategies")

        # Check which ones have no positions
        orphaned_ids = []
        for strategy in standalone_strategies:
            # Count positions linked to this strategy
            position_result = await db.execute(
                select(Position).where(Position.strategy_id == strategy.id)
            )
            positions = position_result.scalars().all()

            if len(positions) == 0:
                orphaned_ids.append(strategy.id)
                logger.info(f"  Found orphaned strategy: {strategy.name} (ID: {strategy.id})")

        if orphaned_ids:
            logger.info(f"\nDeleting {len(orphaned_ids)} orphaned standalone strategies...")

            # Delete orphaned strategies
            await db.execute(
                delete(Strategy).where(Strategy.id.in_(orphaned_ids))
            )
            await db.commit()

            logger.info(f"Successfully deleted {len(orphaned_ids)} orphaned strategies")
        else:
            logger.info("No orphaned strategies found")


if __name__ == "__main__":
    print("=" * 60)
    print("Orphaned Strategy Cleanup Script")
    print("=" * 60)

    asyncio.run(cleanup_orphaned_strategies())

    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("=" * 60)
