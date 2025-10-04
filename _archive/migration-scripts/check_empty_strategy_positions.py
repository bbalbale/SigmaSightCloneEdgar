"""
Check for positions with empty/orphaned strategies
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.strategies import Strategy


async def check_empty_strategy_positions():
    """Check for positions that reference empty strategies"""
    async with AsyncSessionLocal() as session:
        # Get all empty strategies (strategies with 0 positions)
        empty_strategy_ids = [
            'f3e40e0f-3462-4eff-8991-1f0059f76eae',
            'c232c239-2409-448b-9202-afb5388e58f5',
            '15328021-dfe1-4d63-8588-3f719b0839d2',
            '524c1b09-bb38-4f99-bd9c-03783fe1bd5d',
            'a8d860bf-e4b3-4b56-819e-3892ae2b23d5',
            '527d09ba-5b75-4252-8604-c82e24d91165',
            '52406477-0baa-4152-a5a4-e1e9b7d5183c'
        ]

        print("\n" + "="*80)
        print("CHECKING POSITIONS WITH EMPTY STRATEGIES")
        print("="*80)

        for strategy_id in empty_strategy_ids:
            # Get the strategy
            strategy_result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = strategy_result.scalar_one_or_none()

            if not strategy:
                print(f"\n[WARNING] Strategy {strategy_id} not found in database")
                continue

            # Get positions that reference this strategy
            position_result = await session.execute(
                select(Position).where(Position.strategy_id == strategy_id)
            )
            positions = position_result.scalars().all()

            print(f"\nStrategy: {strategy.name} (ID: {strategy_id})")
            print(f"  Positions found: {len(positions)}")

            if positions:
                for pos in positions:
                    print(f"    - {pos.symbol} ({pos.position_type}) - Position ID: {pos.id}")
            else:
                print("    (No positions reference this strategy)")

        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(check_empty_strategy_positions())
