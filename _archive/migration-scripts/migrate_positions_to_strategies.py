#!/usr/bin/env python
"""Migrate existing positions to strategies.

This script creates standalone strategies for all existing positions
that don't already have a strategy assigned.
"""
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text, select
from app.database import get_async_session
from app.models.positions import Position, PositionType
from app.models.strategies import Strategy, StrategyLeg, StrategyType
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_strategy_name(position_type: str, symbol: str) -> str:
    """Generate a descriptive name for a standalone strategy."""
    # Just use the symbol without the position type prefix
    return symbol


async def migrate_positions():
    """Create standalone strategies for all positions without strategies."""

    async with get_async_session() as db:
        try:
            logger.info("Starting position to strategy migration...")

            # Get all positions without strategies
            query = select(Position).where(
                Position.strategy_id == None,
                Position.deleted_at == None
            )
            result = await db.execute(query)
            positions = result.scalars().all()

            logger.info(f"Found {len(positions)} positions without strategies")

            if not positions:
                logger.info("No positions to migrate")
                return

            # Group positions by portfolio for better logging
            portfolio_positions = {}
            for position in positions:
                if position.portfolio_id not in portfolio_positions:
                    portfolio_positions[position.portfolio_id] = []
                portfolio_positions[position.portfolio_id].append(position)

            strategies_created = 0
            for portfolio_id, portfolio_pos_list in portfolio_positions.items():
                logger.info(f"Processing portfolio {portfolio_id} with {len(portfolio_pos_list)} positions")

                for position in portfolio_pos_list:
                    # Create standalone strategy
                    strategy_id = uuid4()
                    strategy_name = get_strategy_name(
                        position.position_type.value if hasattr(position.position_type, 'value') else str(position.position_type),
                        position.symbol
                    )

                    # Insert strategy
                    insert_strategy = text("""
                        INSERT INTO strategies (
                            id,
                            portfolio_id,
                            strategy_type,
                            name,
                            description,
                            is_synthetic,
                            total_cost_basis,
                            created_at,
                            updated_at,
                            created_by
                        ) VALUES (
                            :strategy_id,
                            :portfolio_id,
                            :strategy_type,
                            :name,
                            :description,
                            :is_synthetic,
                            :cost_basis,
                            :created_at,
                            :updated_at,
                            :created_by
                        )
                    """)

                    await db.execute(insert_strategy, {
                        'strategy_id': strategy_id,
                        'portfolio_id': position.portfolio_id,
                        'strategy_type': StrategyType.STANDALONE.value,
                        'name': strategy_name,
                        'description': f"Standalone strategy for {position.symbol}",
                        'is_synthetic': False,
                        'cost_basis': float(position.entry_price * position.quantity) if position.entry_price else None,
                        'created_at': position.created_at,
                        'updated_at': datetime.utcnow(),
                        'created_by': None  # System migration
                    })

                    # Update position with strategy_id
                    update_position = text("""
                        UPDATE positions
                        SET strategy_id = :strategy_id
                        WHERE id = :position_id
                    """)

                    await db.execute(update_position, {
                        'strategy_id': strategy_id,
                        'position_id': position.id
                    })

                    # Create strategy_legs entry
                    insert_leg = text("""
                        INSERT INTO strategy_legs (
                            strategy_id,
                            position_id,
                            leg_type,
                            leg_order
                        ) VALUES (
                            :strategy_id,
                            :position_id,
                            :leg_type,
                            :leg_order
                        )
                    """)

                    await db.execute(insert_leg, {
                        'strategy_id': strategy_id,
                        'position_id': position.id,
                        'leg_type': 'single',
                        'leg_order': 0
                    })

                    strategies_created += 1
                    logger.info(f"  Created strategy '{strategy_name}' for position {position.symbol}")

            # Commit all changes
            await db.commit()

            logger.info(f"Migration completed successfully!")
            logger.info(f"Created {strategies_created} standalone strategies")

            # Verify migration
            verify_query = text("""
                SELECT COUNT(*) FROM positions
                WHERE strategy_id IS NULL
                AND deleted_at IS NULL
            """)
            result = await db.execute(verify_query)
            remaining = result.scalar()

            if remaining == 0:
                logger.info("SUCCESS: All positions now have strategies")
            else:
                logger.warning(f"WARNING: {remaining} positions still without strategies")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await db.rollback()
            raise


async def verify_migration():
    """Verify the migration was successful."""
    async with get_async_session() as db:
        # Count strategies
        strategies_query = text("SELECT COUNT(*) FROM strategies")
        result = await db.execute(strategies_query)
        strategy_count = result.scalar()

        # Count strategy_legs
        legs_query = text("SELECT COUNT(*) FROM strategy_legs")
        result = await db.execute(legs_query)
        legs_count = result.scalar()

        # Count positions with strategies
        positions_query = text("""
            SELECT COUNT(*) FROM positions
            WHERE strategy_id IS NOT NULL
            AND deleted_at IS NULL
        """)
        result = await db.execute(positions_query)
        positions_with_strategies = result.scalar()

        print("\nMigration Verification:")
        print(f"  Total strategies: {strategy_count}")
        print(f"  Total strategy_legs: {legs_count}")
        print(f"  Positions with strategies: {positions_with_strategies}")

        # Get sample strategies
        sample_query = text("""
            SELECT s.name, s.strategy_type, COUNT(sl.position_id) as leg_count
            FROM strategies s
            LEFT JOIN strategy_legs sl ON s.id = sl.strategy_id
            GROUP BY s.id, s.name, s.strategy_type
            LIMIT 5
        """)
        result = await db.execute(sample_query)
        samples = result.fetchall()

        if samples:
            print("\nSample strategies created:")
            for sample in samples:
                print(f"  - {sample.name} ({sample.strategy_type}): {sample.leg_count} leg(s)")


if __name__ == "__main__":
    asyncio.run(migrate_positions())
    asyncio.run(verify_migration())