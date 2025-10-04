"""
Show positions in combined strategies
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


async def show_combined_strategy_positions():
    """Show positions in each combined strategy"""
    async with AsyncSessionLocal() as session:
        # The 4 combined strategies
        combined_strategy_ids = [
            '59d201b5-4f13-4a0a-9957-acba75c986ea',  # ETF Combo
            'c4b10ea1-c83f-43ed-adee-a5c4ac76d307',  # Pairs
            '94a3bdbe-d316-4303-8f62-49fd1e2986f8',  # Tech Pair
            'd5648025-9e84-44f5-a297-77b579fa4aed'   # NVDA Pair
        ]

        print("\n" + "="*80)
        print("COMBINED STRATEGIES - POSITION DETAILS")
        print("="*80)

        for strategy_id in combined_strategy_ids:
            # Get the strategy
            strategy_result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = strategy_result.scalar_one_or_none()

            if not strategy:
                print(f"\n[WARNING] Strategy {strategy_id} not found")
                continue

            # Get positions
            position_result = await session.execute(
                select(Position).where(Position.strategy_id == strategy_id)
            )
            positions = position_result.scalars().all()

            print(f"\nStrategy: {strategy.name}")
            print(f"  Strategy ID: {strategy_id}")
            print(f"  Type: {strategy.strategy_type}")
            print(f"  Position Count: {len(positions)}")
            print(f"  Positions:")

            for pos in positions:
                print(f"    - Position ID: {pos.id}")
                print(f"      Symbol: {pos.symbol}")
                print(f"      Type: {pos.position_type}")
                print(f"      Quantity: {pos.quantity}")
                print(f"      Investment Class: {pos.investment_class}")
                if pos.underlying_symbol:
                    print(f"      Underlying: {pos.underlying_symbol}")
                print()

        print("="*80)


if __name__ == "__main__":
    asyncio.run(show_combined_strategy_positions())
