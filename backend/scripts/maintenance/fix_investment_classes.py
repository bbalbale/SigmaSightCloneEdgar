#!/usr/bin/env python3
"""
Fix investment_class for positions that should be PRIVATE or OPTIONS.

Usage:
    # Dry run (show what would change)
    python scripts/maintenance/fix_investment_classes.py --dry-run

    # Actually fix
    python scripts/maintenance/fix_investment_classes.py

    # Local
    uv run python scripts/maintenance/fix_investment_classes.py --dry-run
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

# Symbols that should be PRIVATE (no market data - custom identifiers)
SHOULD_BE_PRIVATE = [
    "BX_PRIVATE_EQUITY",
    "RENTAL_CONDO",
    "FO_INFRASTRUCTURE",
    "HOME_EQUITY",
    "MONEY_MARKET",
    "FO_PRIVATE_CREDIT",
    "TREASURY_BILLS",
    "FO_CRYPTO_DIGITAL",
    "EQ5D6A2D8F",
]

# Symbols that should be OPTIONS (option contracts)
SHOULD_BE_OPTIONS = [
    "SPY250919C00460000",
    "NVDA251017C00800000",
    "AAPL250815P00200000",
    "VIX250716C00025000",
    "QQQ250815C00420000",
]


async def fix_investment_classes(dry_run: bool = True):
    """Fix investment_class for known problematic symbols."""

    print("=" * 70)
    print("  FIX INVESTMENT CLASSES")
    print(f"  Mode: {'DRY RUN (no changes)' if dry_run else 'UPDATE'}")
    print("=" * 70)
    print()

    total_fixed = 0

    async with get_async_session() as db:
        # Fix PRIVATE positions
        print("  PRIVATE positions (no market data):")
        print("  " + "-" * 66)
        for symbol in SHOULD_BE_PRIVATE:
            # Check current state
            result = await db.execute(
                select(Position.id, Position.symbol, Position.investment_class)
                .where(Position.symbol == symbol)
            )
            rows = result.fetchall()

            if not rows:
                print(f"    {symbol:25} NOT FOUND")
                continue

            for row in rows:
                pos_id, pos_symbol, current_class = row

                if current_class == "PRIVATE":
                    print(f"    {symbol:25} Already PRIVATE - OK")
                else:
                    current = current_class or "NULL"
                    if dry_run:
                        print(f"    {symbol:25} {current:10} -> PRIVATE (would fix)")
                    else:
                        await db.execute(
                            update(Position)
                            .where(Position.id == pos_id)
                            .values(investment_class="PRIVATE")
                        )
                        print(f"    {symbol:25} {current:10} -> PRIVATE (FIXED)")
                        total_fixed += 1

        print()
        print("  OPTIONS positions (option contracts):")
        print("  " + "-" * 66)
        for symbol in SHOULD_BE_OPTIONS:
            # Check current state
            result = await db.execute(
                select(Position.id, Position.symbol, Position.investment_class)
                .where(Position.symbol == symbol)
            )
            rows = result.fetchall()

            if not rows:
                print(f"    {symbol:25} NOT FOUND")
                continue

            for row in rows:
                pos_id, pos_symbol, current_class = row

                if current_class == "OPTIONS":
                    print(f"    {symbol:25} Already OPTIONS - OK")
                else:
                    current = current_class or "NULL"
                    if dry_run:
                        print(f"    {symbol:25} {current:10} -> OPTIONS (would fix)")
                    else:
                        await db.execute(
                            update(Position)
                            .where(Position.id == pos_id)
                            .values(investment_class="OPTIONS")
                        )
                        print(f"    {symbol:25} {current:10} -> OPTIONS (FIXED)")
                        total_fixed += 1

        if not dry_run:
            await db.commit()

    print()
    print("=" * 70)
    if dry_run:
        print("  DRY RUN COMPLETE - No changes made")
        print("  Run without --dry-run to apply fixes")
    else:
        print(f"  COMPLETE - Fixed {total_fixed} positions")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix investment_class for problematic positions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes"
    )
    args = parser.parse_args()

    asyncio.run(fix_investment_classes(dry_run=args.dry_run))
