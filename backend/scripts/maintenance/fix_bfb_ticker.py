#!/usr/bin/env python3
"""
Fix BF.B ticker to BF-B (Yahoo Finance format).

Yahoo Finance uses dashes instead of dots for class shares.
BF.B (Brown-Forman Class B) -> BF-B

Usage:
    # Dry run
    python scripts/maintenance/fix_bfb_ticker.py --dry-run

    # Actually fix
    python scripts/maintenance/fix_bfb_ticker.py
"""

import asyncio
import argparse
import sys
import os

# Windows asyncpg fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, update
from app.database import get_async_session
from app.models.positions import Position


async def fix_bfb_ticker(dry_run: bool = True):
    """Fix BF.B ticker to BF-B."""

    print("=" * 50)
    print("  FIX BF.B -> BF-B")
    print(f"  Mode: {'DRY RUN' if dry_run else 'UPDATE'}")
    print("=" * 50)
    print()

    async with get_async_session() as db:
        # Find positions with BF.B
        result = await db.execute(
            select(Position.id, Position.symbol, Position.portfolio_id)
            .where(Position.symbol == "BF.B")
        )
        rows = result.fetchall()

        if not rows:
            print("  No positions found with symbol BF.B")
            return

        print(f"  Found {len(rows)} position(s) with BF.B:")
        for row in rows:
            pos_id, symbol, portfolio_id = row
            print(f"    ID: {pos_id}, Portfolio: {portfolio_id}")

        if dry_run:
            print()
            print("  Would update symbol from BF.B to BF-B")
        else:
            await db.execute(
                update(Position)
                .where(Position.symbol == "BF.B")
                .values(symbol="BF-B")
            )
            await db.commit()
            print()
            print(f"  Updated {len(rows)} position(s) from BF.B to BF-B")

    print()
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix BF.B ticker to BF-B")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    asyncio.run(fix_bfb_ticker(dry_run=args.dry_run))
