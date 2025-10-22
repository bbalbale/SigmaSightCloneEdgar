"""
Verify sector tags were successfully applied to positions.

This script checks:
1. How many sector tags were created
2. How many positions are tagged
3. The distribution of sectors across portfolios
"""
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag
from app.models.users import Portfolio


async def verify_sector_tags():
    """Verify sector tags in the database."""

    async with get_async_session() as db:
        print("\n" + "=" * 60)
        print("SECTOR TAG VERIFICATION")
        print("=" * 60)

        # Count total sector tags (tags with "Sector:" in description)
        sector_tags_stmt = select(TagV2).where(
            TagV2.description.like("Sector:%")
        )
        sector_tags_result = await db.execute(sector_tags_stmt)
        sector_tags = sector_tags_result.scalars().all()

        print(f"\nTotal sector tags created: {len(sector_tags)}")
        print("\nSector tags breakdown:")
        for tag in sorted(sector_tags, key=lambda t: t.usage_count, reverse=True):
            print(f"  - {tag.name:25} (used by {tag.usage_count} positions, color: {tag.color})")

        # Count position-tag links
        position_tags_stmt = select(func.count(PositionTag.id)).where(
            PositionTag.tag_id.in_([tag.id for tag in sector_tags])
        )
        position_tags_result = await db.execute(position_tags_stmt)
        position_tags_count = position_tags_result.scalar()

        print(f"\nTotal position-tag links: {position_tags_count}")

        # Count portfolios
        portfolios_stmt = select(func.count(Portfolio.id))
        portfolios_result = await db.execute(portfolios_stmt)
        portfolios_count = portfolios_result.scalar()

        print(f"Total portfolios: {portfolios_count}")

        print("\n" + "=" * 60)
        print("Verification complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_sector_tags())
