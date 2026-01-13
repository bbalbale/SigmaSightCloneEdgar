#!/usr/bin/env python3
"""
Fix BF.B in symbol_universe - mark as inactive (BF-B already exists).

The correct Yahoo Finance ticker is BF-B, which already exists.
BF.B should be marked inactive to prevent duplicate processing.
"""

import asyncio
import argparse
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


async def fix_bfb(dry_run: bool = True):
    print("=" * 60)
    print("  FIX BF.B IN SYMBOL_UNIVERSE")
    print(f"  Mode: {'DRY RUN' if dry_run else 'UPDATE'}")
    print("=" * 60)
    print()

    async with get_async_session() as db:
        # Check current state
        r = await db.execute(text("SELECT symbol, is_active FROM symbol_universe WHERE symbol IN ('BF.B', 'BF-B')"))
        rows = r.fetchall()

        print("  Current state:")
        for row in rows:
            print(f"    {row[0]:10} is_active={row[1]}")

        # Mark BF.B as inactive
        if dry_run:
            print()
            print("  Would mark BF.B as inactive (is_active=False)")
        else:
            await db.execute(text("UPDATE symbol_universe SET is_active = FALSE WHERE symbol = 'BF.B'"))
            await db.commit()
            print()
            print("  Marked BF.B as inactive")

        # Also clean up company_profiles (optional - delete the empty one)
        if not dry_run:
            await db.execute(text("DELETE FROM company_profiles WHERE symbol = 'BF.B'"))
            await db.commit()
            print("  Deleted BF.B from company_profiles (empty record)")

    print()
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix BF.B in symbol_universe")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    asyncio.run(fix_bfb(dry_run=args.dry_run))
