"""
Check for combined strategies (strategies with multiple positions)
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.strategies import Strategy


async def check_combined_strategies():
    """Check for strategies that have multiple positions"""
    async with AsyncSessionLocal() as session:
        # Get all strategies with their position counts
        query = (
            select(
                Strategy.id,
                Strategy.name,
                Strategy.strategy_type,
                func.count(Position.id).label('position_count')
            )
            .outerjoin(Position, Position.strategy_id == Strategy.id)
            .group_by(Strategy.id, Strategy.name, Strategy.strategy_type)
        )

        result = await session.execute(query)
        strategies_with_counts = result.all()

        print("\n" + "="*80)
        print("STRATEGY ANALYSIS")
        print("="*80)

        combined_strategies = []
        single_strategies = []
        empty_strategies = []

        for strategy in strategies_with_counts:
            if strategy.position_count > 1:
                combined_strategies.append(strategy)
            elif strategy.position_count == 1:
                single_strategies.append(strategy)
            else:
                empty_strategies.append(strategy)

        # Print combined strategies (violations)
        if combined_strategies:
            print(f"\n[!] FOUND {len(combined_strategies)} COMBINED STRATEGIES (VIOLATIONS):")
            print("-" * 80)
            for s in combined_strategies:
                print(f"  Strategy ID: {s.id}")
                print(f"  Name: {s.name}")
                print(f"  Type: {s.strategy_type}")
                print(f"  Position Count: {s.position_count}")
                print("-" * 80)
        else:
            print("\n[OK] NO COMBINED STRATEGIES FOUND")

        # Print summary
        print(f"\nSUMMARY:")
        print(f"  Single Position Strategies: {len(single_strategies)}")
        print(f"  Combined Strategies (VIOLATIONS): {len(combined_strategies)}")
        print(f"  Empty Strategies: {len(empty_strategies)}")
        print(f"  Total Strategies: {len(strategies_with_counts)}")

        # Show details of single strategies if needed
        if single_strategies:
            print(f"\n[OK] {len(single_strategies)} strategies have exactly 1 position (CORRECT)")

        if empty_strategies:
            print(f"\n[WARNING] {len(empty_strategies)} strategies have 0 positions (may be orphaned)")
            for s in empty_strategies:
                print(f"    - {s.name} (ID: {s.id})")

        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(check_combined_strategies())
