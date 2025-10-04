"""
Backfill script: create standalone strategies for positions missing strategy_id.

Usage:
  backend/.venv/Scripts/python.exe backend/scripts/backfill_strategies.py [--dry-run] [--batch-size 200]

The script is idempotent and only processes positions where strategy_id IS NULL.
"""
import asyncio
import argparse
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.models import Position
from app.services.strategy_service import StrategyService


async def count_unassigned(db) -> int:
    q = select(Position).where(Position.strategy_id.is_(None))
    res = await db.execute(q)
    return len(res.scalars().all())


async def fetch_batch(db, limit: int) -> List[Position]:
    q = (
        select(Position)
        .where(Position.strategy_id.is_(None))
        .order_by(Position.created_at)
        .limit(limit)
    )
    res = await db.execute(q)
    return res.scalars().all()


async def backfill(dry_run: bool = False, batch_size: int = 200) -> int:
    processed = 0
    async with get_async_session() as db:
        service = StrategyService(db)

        remaining = await count_unassigned(db)
        print(f"Positions without strategy_id: {remaining}")
        if dry_run or remaining == 0:
            return 0

        while True:
            batch = await fetch_batch(db, batch_size)
            if not batch:
                break

            for pos in batch:
                await service.auto_create_standalone_strategy(pos)
                processed += 1

            # refresh remaining count periodically
            remaining = await count_unassigned(db)
            print(f"Processed batch: {len(batch)}, remaining: {remaining}")

    print(f"Backfill complete. Created standalone strategies: {processed}")
    return processed


def main():
    parser = argparse.ArgumentParser(description="Backfill standalone strategies for existing positions")
    parser.add_argument("--dry-run", action="store_true", help="Show counts only; do not modify data")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size for processing")
    args = parser.parse_args()

    asyncio.run(backfill(dry_run=args.dry_run, batch_size=args.batch_size))


if __name__ == "__main__":
    main()

