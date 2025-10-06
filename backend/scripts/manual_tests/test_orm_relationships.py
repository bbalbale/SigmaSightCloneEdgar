#!/usr/bin/env python
"""Test key ORM relationships with actual database queries (position tagging focus)."""
import asyncio

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.models import User, Portfolio, Position, PositionTag, TagV2


async def test_position_relationships() -> bool:
    """Ensure position relationships (portfolio + position tags) work as expected."""
    print("Testing Position ORM relationships...")
    print("-" * 50)

    async with get_async_session() as db:
        try:
            # 1. Load positions with their position tags (eager loading)
            print("\n1. Loading positions with position tags...")
            query = select(Position).options(
                selectinload(Position.position_tags).selectinload(PositionTag.tag)
            ).limit(5)
            result = await db.execute(query)
            positions = result.scalars().all()

            for position in positions:
                print(f"   Position: {position.symbol}")
                tags = position.position_tags or []
                print(f"   - Attached tags: {len(tags)}")

            # 2. Load portfolios with their positions
            print("\n2. Loading portfolios with positions...")
            query = select(Portfolio).options(
                selectinload(Portfolio.positions)
            ).limit(3)
            result = await db.execute(query)
            portfolios = result.scalars().all()

            for portfolio in portfolios:
                print(f"   Portfolio: {portfolio.name}")
                print(f"   - Positions: {len(portfolio.positions or [])}")

            print("\nSUCCESS: Position relationships verified!")
            return True

        except Exception as exc:  # pragma: no cover - diagnostic script
            print(f"\nERROR: Position relationship check failed: {exc}")
            import traceback
            traceback.print_exc()
            return False


def _format_tag(tag: TagV2) -> str:
    return f"{tag.name} (archived={tag.is_archived})"


async def test_tag_relationships() -> bool:
    """Ensure TagV2 and PositionTag relationships behave correctly."""
    print("\nTesting Tag ORM relationships...")
    print("-" * 50)

    async with get_async_session() as db:
        try:
            # 1. Load users with their tags (eager loading)
            print("\n1. Loading users with TagV2 records...")
            query = select(User).options(selectinload(User.tags_v2)).limit(3)
            result = await db.execute(query)
            users = result.scalars().all()

            for user in users:
                tags = user.tags_v2 or []
                tag_names = ", ".join(_format_tag(tag) for tag in tags[:5])
                print(f"   User: {user.email} | Tags: {len(tags)} | Sample: {tag_names}")

            # 2. Count TagV2 rows
            print("\n2. Counting tags in tags_v2 table...")
            tag_count = await db.scalar(select(func.count(TagV2.id)))
            print(f"   - Found {tag_count} tags")

            # 3. Count PositionTag associations
            print("\n3. Counting position-tag associations...")
            position_tag_count = await db.scalar(select(func.count(PositionTag.id)))
            print(f"   - Found {position_tag_count} position-tag associations")

            print("\nSUCCESS: Tag relationships verified!")
            return True

        except Exception as exc:  # pragma: no cover - diagnostic script
            print(f"\nERROR: Tag relationship check failed: {exc}")
            import traceback
            traceback.print_exc()
            return False


async def main() -> bool:
    """Run all ORM relationship diagnostics."""
    print("=" * 50)
    print("Testing ORM Relationships with Database")
    print("=" * 50)

    positions_ok = await test_position_relationships()
    tags_ok = await test_tag_relationships()

    if positions_ok and tags_ok:
        print("\nSUCCESS: All ORM relationship checks passed!")
        return True

    print("\nFAILED: One or more relationship checks failed")
    return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
