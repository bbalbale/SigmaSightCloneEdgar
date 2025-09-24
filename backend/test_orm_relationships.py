#!/usr/bin/env python
"""Test ORM relationships with actual database queries."""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models import (
    User, Portfolio, Position, Strategy, StrategyLeg,
    StrategyTag, TagV2, StrategyType
)


async def test_strategy_relationships():
    """Test that strategy relationships work with database queries."""
    print("Testing Strategy ORM relationships...")
    print("-" * 50)

    async with get_async_session() as db:
        try:
            # 1. Test loading strategies with positions (eager loading)
            print("\n1. Loading strategies with positions...")
            query = select(Strategy).options(
                selectinload(Strategy.positions)
            ).limit(3)
            result = await db.execute(query)
            strategies = result.scalars().all()

            for strategy in strategies:
                print(f"   Strategy: {strategy.name}")
                # Access positions through relationship (now eagerly loaded)
                positions = strategy.positions
                print(f"   - Has {len(positions) if positions else 0} positions")

            # 2. Test loading positions with strategy (eager loading)
            print("\n2. Loading positions with their strategy...")
            query = select(Position).options(
                selectinload(Position.strategy)
            ).where(Position.strategy_id != None).limit(3)
            result = await db.execute(query)
            positions = result.scalars().all()

            for position in positions:
                print(f"   Position: {position.symbol}")
                if position.strategy:
                    print(f"   - Strategy: {position.strategy.name}")

            # 3. Test portfolio with strategies (eager loading)
            print("\n3. Loading portfolio with strategies...")
            query = select(Portfolio).options(
                selectinload(Portfolio.strategies)
            ).limit(1)
            result = await db.execute(query)
            portfolio = result.scalars().first()

            if portfolio:
                print(f"   Portfolio: {portfolio.name}")
                strategies = portfolio.strategies
                print(f"   - Has {len(strategies) if strategies else 0} strategies")

            # 4. Count strategies by type
            print("\n4. Counting strategies by type...")
            query = select(
                Strategy.strategy_type,
                func.count(Strategy.id).label('count')
            ).group_by(Strategy.strategy_type)
            result = await db.execute(query)
            counts = result.all()

            for strategy_type, count in counts:
                print(f"   - {strategy_type}: {count} strategies")

            print("\n" + "=" * 50)
            print("SUCCESS: All ORM relationships working!")
            print("=" * 50)

            return True

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_tag_relationships():
    """Test TagV2 relationships with database queries."""
    print("\nTesting TagV2 ORM relationships...")
    print("-" * 50)

    async with get_async_session() as db:
        try:
            # 1. Test loading users with tags_v2 (eager loading)
            print("\n1. Loading users with TagV2...")
            query = select(User).options(
                selectinload(User.tags_v2)
            ).limit(1)
            result = await db.execute(query)
            user = result.scalars().first()

            if user:
                print(f"   User: {user.email}")
                tags = user.tags_v2
                print(f"   - Has {len(tags) if tags else 0} TagV2 tags")

            # 2. Check if we can query TagV2 table
            print("\n2. Checking TagV2 table...")
            query = select(func.count(TagV2.id))
            result = await db.execute(query)
            tag_count = result.scalar()
            print(f"   - Found {tag_count} tags in tags_v2 table")

            # 3. Check StrategyTag relationships
            print("\n3. Checking StrategyTag relationships...")
            query = select(func.count(StrategyTag.id))
            result = await db.execute(query)
            strategy_tag_count = result.scalar()
            print(f"   - Found {strategy_tag_count} strategy-tag associations")

            print("\n" + "=" * 50)
            print("SUCCESS: Tag relationships working!")
            print("=" * 50)

            return True

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run all relationship tests."""
    print("=" * 50)
    print("Testing ORM Relationships with Database")
    print("=" * 50)

    # Test strategy relationships
    success1 = await test_strategy_relationships()

    # Test tag relationships
    success2 = await test_tag_relationships()

    if success1 and success2:
        print("\nSUCCESS: All ORM relationships verified!")
        return True
    else:
        print("\nFAILED: Some relationships not working properly")
        return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)