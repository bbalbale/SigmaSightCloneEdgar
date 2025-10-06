"""
Migrate legacy position_tags -> strategy_tags.

Logic:
- For each legacy Tag (tags table), ensure a TagV2 exists for the same user+name (create if missing).
- For each row in position_tags, find the position's strategy_id and assign the corresponding TagV2 to that strategy.
- Skips rows where position has no strategy_id (should not happen post-backfill) or when user cannot be determined.

Usage:
  cd backend && .venv/Scripts/python.exe scripts/migrations/migrate_position_tags_to_strategy_tags.py --dry-run
"""
import asyncio
import argparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.models.positions import Tag as LegacyTag, position_tags, Position
from app.models.tags_v2 import TagV2
from app.models.strategies import StrategyTag


async def migrate(dry_run: bool = True) -> dict:
    stats = {"legacy_tags": 0, "created_tagv2": 0, "migrated_assignments": 0, "skipped": 0}
    async with get_async_session() as db:
        # Map (user_id, name) -> TagV2
        tagv2_map = {}

        # Load all legacy tags
        res = await db.execute(select(LegacyTag))
        legacy_tags = res.scalars().all()
        stats["legacy_tags"] = len(legacy_tags)

        # Ensure TagV2 rows exist
        for lt in legacy_tags:
            key = (lt.user_id, lt.name)
            if key in tagv2_map:
                continue
            v2_res = await db.execute(select(TagV2).where(TagV2.user_id == lt.user_id, TagV2.name == lt.name, TagV2.is_archived == False))
            v2 = v2_res.scalars().first()
            if not v2 and not dry_run:
                v2 = TagV2(user_id=lt.user_id, name=lt.name, color=(lt.color or "#4A90E2"))
                db.add(v2)
                await db.flush()
                stats["created_tagv2"] += 1
            if v2:
                tagv2_map[key] = v2

        # Fetch all position_tags rows
        res = await db.execute(select(position_tags.c.position_id, position_tags.c.tag_id))
        rows = res.all()

        # Build legacy tag id -> TagV2 mapping (via (user,name))
        legacy_map = {lt.id: tagv2_map.get((lt.user_id, lt.name)) for lt in legacy_tags}

        for position_id, legacy_tag_id in rows:
            # get position and its strategy
            pos_res = await db.execute(select(Position).where(Position.id == position_id))
            pos = pos_res.scalars().first()
            if not pos or not pos.strategy_id:
                stats["skipped"] += 1
                continue

            tag_v2 = legacy_map.get(legacy_tag_id)
            if not tag_v2:
                stats["skipped"] += 1
                continue

            if not dry_run:
                assoc_res = await db.execute(
                    select(StrategyTag).where(StrategyTag.strategy_id == pos.strategy_id, StrategyTag.tag_id == tag_v2.id)
                )
                if not assoc_res.scalars().first():
                    st = StrategyTag(strategy_id=pos.strategy_id, tag_id=tag_v2.id)
                    db.add(st)
                    stats["migrated_assignments"] += 1

        if not dry_run:
            await db.commit()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = asyncio.run(migrate(dry_run=args.dry_run))
    print(stats)


if __name__ == "__main__":
    main()

