"""
Backfill script to calculate and set direction and primary_investment_class
for existing strategies.

This script:
1. Fetches all strategies
2. For each strategy, fetches its positions
3. Calculates direction and primary_investment_class using StrategyService logic
4. Updates the strategy with calculated values

Usage:
    cd backend
    uv run python scripts/backfill_strategy_categorization.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Strategy, Position
from app.core.logging import get_logger

logger = get_logger(__name__)


def calculate_strategy_categorization(strategy_type: str, positions: list) -> dict:
    """
    Calculate direction and primary_investment_class for a strategy.
    This is a standalone version of the StrategyService method.

    Args:
        strategy_type: The type of strategy
        positions: List of positions in the strategy

    Returns:
        Dict with 'direction' and 'primary_investment_class' keys
    """
    if not positions:
        return {'direction': None, 'primary_investment_class': None}

    # Standalone strategies: Inherit from single position
    if len(positions) == 1:
        pos = positions[0]
        return {
            'direction': pos.position_type.value if hasattr(pos.position_type, 'value') else str(pos.position_type),
            'primary_investment_class': pos.investment_class
        }

    # Multi-leg strategies: Use strategy type mapping
    strategy_type_mapping = {
        'covered_call': {'direction': 'LONG', 'class': 'PUBLIC'},
        'protective_put': {'direction': 'LONG', 'class': 'PUBLIC'},
        'iron_condor': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
        'straddle': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
        'strangle': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
        'butterfly': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
        'pairs_trade': {'direction': 'NEUTRAL', 'class': 'PUBLIC'},
    }

    if strategy_type in strategy_type_mapping:
        mapping = strategy_type_mapping[strategy_type]
        return {
            'direction': mapping['direction'],
            'primary_investment_class': mapping['class']
        }

    # Fallback: Use position with largest absolute market value
    primary_position = max(
        positions,
        key=lambda p: abs(float(p.market_value or 0))
    )

    return {
        'direction': primary_position.position_type.value if hasattr(primary_position.position_type, 'value') else str(primary_position.position_type),
        'primary_investment_class': primary_position.investment_class
    }


async def backfill_strategies():
    """Main backfill function"""
    logger.info("Starting strategy categorization backfill...")

    async with AsyncSessionLocal() as db:
        try:
            # Fetch all strategies with their positions
            result = await db.execute(
                select(Strategy).options(selectinload(Strategy.positions))
            )
            strategies = result.scalars().all()

            total = len(strategies)
            updated = 0
            skipped = 0

            logger.info(f"Found {total} strategies to process")

            for strategy in strategies:
                # Skip if already has categorization
                if strategy.direction and strategy.primary_investment_class:
                    logger.debug(f"Strategy {strategy.id} already has categorization, skipping")
                    skipped += 1
                    continue

                # Calculate categorization
                positions = strategy.positions
                categorization = calculate_strategy_categorization(
                    strategy_type=strategy.strategy_type,
                    positions=positions
                )

                # Update strategy
                strategy.direction = categorization['direction']
                strategy.primary_investment_class = categorization['primary_investment_class']

                logger.info(
                    f"Updated strategy {strategy.id} ({strategy.name}): "
                    f"direction={categorization['direction']}, "
                    f"class={categorization['primary_investment_class']}"
                )
                updated += 1

            # Commit all updates
            await db.commit()

            logger.info(f"\n✅ Backfill complete!")
            logger.info(f"   Total strategies: {total}")
            logger.info(f"   Updated: {updated}")
            logger.info(f"   Skipped (already set): {skipped}")

        except Exception as e:
            logger.error(f"❌ Backfill failed: {e}")
            await db.rollback()
            raise


async def verify_backfill():
    """Verify the backfill by counting strategies with categorization"""
    logger.info("\nVerifying backfill results...")

    async with AsyncSessionLocal() as db:
        # Count total strategies
        result = await db.execute(select(Strategy))
        total = len(result.scalars().all())

        # Count strategies with categorization
        result = await db.execute(
            select(Strategy).where(
                Strategy.direction.isnot(None),
                Strategy.primary_investment_class.isnot(None)
            )
        )
        categorized = len(result.scalars().all())

        logger.info(f"Total strategies: {total}")
        logger.info(f"With categorization: {categorized}")

        if categorized == total:
            logger.info("✅ All strategies have categorization!")
        else:
            logger.warning(f"⚠️  {total - categorized} strategies still missing categorization")

        # Show sample by investment class
        logger.info("\nBreakdown by investment class:")
        for inv_class in ['PUBLIC', 'OPTIONS', 'PRIVATE']:
            result = await db.execute(
                select(Strategy).where(Strategy.primary_investment_class == inv_class)
            )
            count = len(result.scalars().all())
            logger.info(f"  {inv_class}: {count} strategies")


async def main():
    """Main entry point"""
    print("=" * 60)
    print("Strategy Categorization Backfill Script")
    print("=" * 60)

    try:
        await backfill_strategies()
        await verify_backfill()

        print("\n" + "=" * 60)
        print("✅ Backfill completed successfully!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Backfill failed: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
