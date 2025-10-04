"""
Check position-tag relationships in the database
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models.position_tags import PositionTag
from app.models.positions import Position
from app.models.tags_v2 import TagV2

async def check_position_tags():
    async with get_async_session() as session:
        print("\n" + "="*60)
        print("CHECKING POSITION-TAG RELATIONSHIPS")
        print("="*60)

        # Check if position_tags table has any data
        result = await session.execute(
            select(PositionTag)
            .options(
                selectinload(PositionTag.position),
                selectinload(PositionTag.tag)
            )
        )
        position_tags = result.scalars().all()

        print(f"\n[SUCCESS] Total position-tag relationships: {len(position_tags)}")

        if position_tags:
            print("\n[INFO] Position-Tag Relationships:")
            print("-" * 40)
            for pt in position_tags[:10]:  # Show first 10
                pos_symbol = pt.position.symbol if pt.position else "Unknown"
                tag_name = pt.tag.name if pt.tag else "Unknown"
                print(f"  * Position: {pos_symbol:10} | Tag: {tag_name:20} | Assigned: {pt.assigned_at}")

            if len(position_tags) > 10:
                print(f"  ... and {len(position_tags) - 10} more relationships")
        else:
            print("\n[WARNING] No position-tag relationships found in database!")

        # Check positions with tags
        result = await session.execute(
            select(Position)
            .options(selectinload(Position.position_tags).selectinload(PositionTag.tag))
            .filter(Position.position_tags.any())
        )
        positions_with_tags = result.scalars().all()

        print(f"\n[INFO] Positions with tags: {len(positions_with_tags)}")

        if positions_with_tags:
            print("\n[INFO] Positions and their tags:")
            print("-" * 40)
            for pos in positions_with_tags[:5]:  # Show first 5
                tags = [pt.tag.name for pt in pos.position_tags if pt.tag]
                print(f"  * {pos.symbol:10} | Tags: {', '.join(tags)}")

        # Check all available tags
        result = await session.execute(select(TagV2))
        all_tags = result.scalars().all()

        print(f"\n[INFO] Total available tags: {len(all_tags)}")
        if all_tags:
            print("\n[INFO] Available tags:")
            for tag in all_tags[:10]:
                print(f"  * ID: {tag.id} | Name: {tag.name} | Color: {tag.color}")

        # Check raw SQL count
        result = await session.execute(text("SELECT COUNT(*) FROM position_tags"))
        raw_count = result.scalar()
        print(f"\n[INFO] Raw SQL count of position_tags: {raw_count}")

if __name__ == "__main__":
    asyncio.run(check_position_tags())