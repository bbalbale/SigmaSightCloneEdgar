"""
Delete empty/orphaned strategies that have no positions
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.strategies import Strategy


async def delete_empty_strategies():
    """Delete strategies that have no positions"""
    async with AsyncSessionLocal() as session:
        # The 7 empty strategies to delete
        empty_strategy_ids = [
            'f3e40e0f-3462-4eff-8991-1f0059f76eae',  # Long Call NVDA251017C00800000
            'c232c239-2409-448b-9202-afb5388e58f5',  # Long NVDA
            '15328021-dfe1-4d63-8588-3f719b0839d2',  # MSFT
            '524c1b09-bb38-4f99-bd9c-03783fe1bd5d',  # Tech Combo Test
            'a8d860bf-e4b3-4b56-819e-3892ae2b23d5',  # NVDA Long
            '527d09ba-5b75-4252-8604-c82e24d91165',  # AAPL
            '52406477-0baa-4152-a5a4-e1e9b7d5183c'   # NVDA Pair
        ]

        print("\n" + "="*80)
        print("DELETING EMPTY/ORPHANED STRATEGIES")
        print("="*80)

        deleted_count = 0

        for strategy_id in empty_strategy_ids:
            # Get the strategy
            strategy_result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = strategy_result.scalar_one_or_none()

            if not strategy:
                print(f"\n[SKIP] Strategy {strategy_id} not found (may have been deleted already)")
                continue

            print(f"\n[DELETING] {strategy.name} (ID: {strategy_id})")

            # Delete the strategy
            await session.delete(strategy)
            deleted_count += 1

        # Commit all deletions
        await session.commit()

        print("\n" + "="*80)
        print(f"DELETION COMPLETE - Deleted {deleted_count} empty strategies")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(delete_empty_strategies())
