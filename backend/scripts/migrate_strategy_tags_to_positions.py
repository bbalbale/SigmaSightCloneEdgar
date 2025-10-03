"""
Data Migration Script: Migrate Strategy Tags to Position Tags

Migrates tag associations from the legacy strategy-based tagging system
to the new direct position tagging system.

This script:
1. Gets all strategies with tags
2. For each strategy, gets all positions
3. For each position × tag combination, creates a position_tag entry
4. Does NOT delete any strategy or strategy_tag data (backward compatibility)

Usage:
    uv run python scripts/migrate_strategy_tags_to_positions.py
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.strategies import Strategy, StrategyTag
from app.models.positions import Position
from app.models.position_tags import PositionTag
from app.models.tags_v2 import TagV2
from app.core.logging import get_logger

logger = get_logger(__name__)


async def migrate_strategy_tags_to_positions(db: AsyncSession):
    """
    Migrate all strategy tag associations to position tag associations.

    Returns:
        dict: Migration statistics
    """
    logger.info("Starting strategy tag to position tag migration")

    # Statistics
    stats = {
        "strategies_processed": 0,
        "strategies_with_tags": 0,
        "positions_processed": 0,
        "tags_migrated": 0,
        "duplicates_skipped": 0,
        "errors": 0
    }

    try:
        # Get all strategy tags
        strategy_tags_stmt = (
            select(StrategyTag)
            .join(TagV2, StrategyTag.tag_id == TagV2.id)
            .where(TagV2.is_archived == False)  # Only active tags
        )
        strategy_tags_result = await db.execute(strategy_tags_stmt)
        strategy_tags = strategy_tags_result.scalars().all()

        logger.info(f"Found {len(strategy_tags)} strategy tag assignments")

        # Build a map: strategy_id -> list of tag_ids
        strategy_tag_map = {}
        for st in strategy_tags:
            if st.strategy_id not in strategy_tag_map:
                strategy_tag_map[st.strategy_id] = []
            strategy_tag_map[st.strategy_id].append(st.tag_id)

        stats["strategies_with_tags"] = len(strategy_tag_map)
        logger.info(f"Found {len(strategy_tag_map)} strategies with tags")

        # Process each strategy
        for strategy_id, tag_ids in strategy_tag_map.items():
            stats["strategies_processed"] += 1

            # Get all positions in this strategy
            positions_stmt = select(Position).where(Position.strategy_id == strategy_id)
            positions_result = await db.execute(positions_stmt)
            positions = positions_result.scalars().all()

            if not positions:
                logger.warning(f"Strategy {strategy_id} has no positions, skipping")
                continue

            logger.info(f"Processing strategy {strategy_id}: {len(positions)} positions, {len(tag_ids)} tags")

            # Create position tag for each position × tag combination
            for position in positions:
                stats["positions_processed"] += 1

                for tag_id in tag_ids:
                    try:
                        # Check if this position-tag association already exists
                        existing_stmt = select(PositionTag).where(
                            PositionTag.position_id == position.id,
                            PositionTag.tag_id == tag_id
                        )
                        existing_result = await db.execute(existing_stmt)
                        existing = existing_result.scalar()

                        if existing:
                            stats["duplicates_skipped"] += 1
                            logger.debug(f"Position {position.id} already has tag {tag_id}, skipping")
                            continue

                        # Create new position tag
                        position_tag = PositionTag(
                            position_id=position.id,
                            tag_id=tag_id,
                            assigned_by=None  # Migration, no specific user
                        )
                        db.add(position_tag)
                        stats["tags_migrated"] += 1

                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(f"Error creating position tag for position {position.id}, tag {tag_id}: {e}")

        # Commit all changes
        await db.commit()
        logger.info("Migration committed successfully")

    except Exception as e:
        await db.rollback()
        logger.error(f"Migration failed: {e}")
        stats["errors"] += 1
        raise

    return stats


async def main():
    """Run the migration"""
    logger.info("=" * 80)
    logger.info("STRATEGY TAG TO POSITION TAG MIGRATION")
    logger.info("=" * 80)

    async with get_async_session() as db:
        stats = await migrate_strategy_tags_to_positions(db)

    # Print summary
    logger.info("=" * 80)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Strategies processed:        {stats['strategies_processed']}")
    logger.info(f"Strategies with tags:        {stats['strategies_with_tags']}")
    logger.info(f"Positions processed:         {stats['positions_processed']}")
    logger.info(f"Tags migrated:               {stats['tags_migrated']}")
    logger.info(f"Duplicates skipped:          {stats['duplicates_skipped']}")
    logger.info(f"Errors:                      {stats['errors']}")
    logger.info("=" * 80)

    if stats["errors"] > 0:
        logger.error("Migration completed with errors")
        return 1

    logger.info("Migration completed successfully!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
