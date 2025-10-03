"""
Separate combined strategies - give each position its own standalone strategy
NO POSITIONS ARE DELETED - only strategy assignments are changed
"""
import asyncio
import sys
from pathlib import Path
import uuid

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.strategies import Strategy


async def separate_combined_strategies():
    """Separate combined strategies into individual strategies per position"""
    async with AsyncSessionLocal() as session:
        # The 4 combined strategies
        combined_strategy_ids = [
            '59d201b5-4f13-4a0a-9957-acba75c986ea',  # ETF Combo
            'c4b10ea1-c83f-43ed-adee-a5c4ac76d307',  # Pairs
            '94a3bdbe-d316-4303-8f62-49fd1e2986f8',  # Tech Pair
            'd5648025-9e84-44f5-a297-77b579fa4aed'   # NVDA Pair
        ]

        print("\n" + "="*80)
        print("SEPARATING COMBINED STRATEGIES")
        print("="*80)

        total_positions_processed = 0
        total_new_strategies = 0

        for strategy_id in combined_strategy_ids:
            # Get the old combined strategy
            strategy_result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            old_strategy = strategy_result.scalar_one_or_none()

            if not old_strategy:
                print(f"\n[WARNING] Strategy {strategy_id} not found")
                continue

            # Get all positions in this combined strategy
            position_result = await session.execute(
                select(Position).where(Position.strategy_id == strategy_id)
            )
            positions = position_result.scalars().all()

            print(f"\n[PROCESSING] {old_strategy.name}")
            print(f"  Found {len(positions)} positions to separate")

            # Create a new standalone strategy for each position
            for pos in positions:
                # Create new strategy name based on position
                if pos.investment_class == 'OPTION':
                    new_strategy_name = f"{pos.symbol}"
                else:
                    new_strategy_name = f"{pos.symbol}"

                # Create new standalone strategy
                new_strategy = Strategy(
                    id=uuid.uuid4(),
                    portfolio_id=old_strategy.portfolio_id,
                    strategy_type='standalone',
                    name=new_strategy_name,
                    description=f"Auto-generated from separated combined strategy: {old_strategy.name}",
                    is_synthetic=False,
                    direction=pos.position_type.value if hasattr(pos.position_type, 'value') else str(pos.position_type),
                    primary_investment_class=pos.investment_class,
                    created_by=old_strategy.created_by
                )

                session.add(new_strategy)
                await session.flush()  # Get the new strategy ID

                # Update position to point to new strategy
                pos.strategy_id = new_strategy.id

                print(f"    - Created strategy '{new_strategy_name}' for position {pos.symbol}")
                total_new_strategies += 1
                total_positions_processed += 1

            # Delete the old combined strategy
            await session.delete(old_strategy)
            print(f"  [DELETED] Old combined strategy '{old_strategy.name}'")

        # Commit all changes
        await session.commit()

        print("\n" + "="*80)
        print("SEPARATION COMPLETE")
        print(f"  Total positions processed: {total_positions_processed}")
        print(f"  New standalone strategies created: {total_new_strategies}")
        print(f"  Old combined strategies deleted: {len(combined_strategy_ids)}")
        print("  NO POSITIONS WERE DELETED")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(separate_combined_strategies())
