"""
Update strategy names to remove "Long"/"Short" prefixes and clear descriptions.
"""
import asyncio
import logging
from sqlalchemy import select, update
from app.database import get_async_session
from app.models.strategies import Strategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_strategy_names():
    """Update strategy names to remove Long/Short prefixes."""

    async with get_async_session() as db:
        try:
            # Get all standalone strategies that aren't closed
            query = select(Strategy).where(
                Strategy.strategy_type == 'standalone',
                Strategy.closed_at.is_(None)
            )
            result = await db.execute(query)
            strategies = result.scalars().all()

            logger.info(f"Found {len(strategies)} standalone strategies to update")

            updated_count = 0
            for strategy in strategies:
                # Remove "Long ", "Short ", "Long Call ", etc. prefixes
                original_name = strategy.name
                new_name = original_name

                prefixes = ['Long Call ', 'Long Put ', 'Short Call ', 'Short Put ', 'Long ', 'Short ']
                for prefix in prefixes:
                    if new_name.startswith(prefix):
                        new_name = new_name[len(prefix):]
                        break

                # Update if name changed
                if new_name != original_name:
                    strategy.name = new_name
                    strategy.description = None
                    updated_count += 1
                    logger.info(f"Updated: '{original_name}' -> '{new_name}'")
                elif strategy.description and 'Standalone strategy' in strategy.description:
                    # Clear description even if name didn't change
                    strategy.description = None
                    updated_count += 1
                    logger.info(f"Cleared description for: '{strategy.name}'")

            if updated_count > 0:
                await db.commit()
                logger.info(f"✅ Successfully updated {updated_count} strategies")
            else:
                logger.info("No strategies needed updating")

        except Exception as e:
            logger.error(f"Error updating strategies: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(update_strategy_names())
