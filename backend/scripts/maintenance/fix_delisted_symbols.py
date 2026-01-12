#!/usr/bin/env python3
"""
Fix Delisted and Renamed Symbols

Handles:
1. SGEN, HZNP - Mark as inactive (delisted)
2. SQ → XYZ - Ticker rename (Block Inc.)

Usage:
    # Dry run (show what would change)
    uv run python scripts/maintenance/fix_delisted_symbols.py --dry-run

    # Apply changes
    uv run python scripts/maintenance/fix_delisted_symbols.py

    # Run on Railway
    railway run python scripts/maintenance/fix_delisted_symbols.py
"""

import asyncio
import argparse
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession


# Symbols to mark as inactive (delisted)
DELISTED_SYMBOLS = ['SGEN', 'HZNP']

# Ticker renames: old_symbol -> new_symbol
RENAMED_SYMBOLS = {
    'SQ': 'XYZ',
}


async def fix_delisted_symbols(db: AsyncSession, dry_run: bool = True) -> dict:
    """Mark delisted symbols as inactive in symbol_universe."""
    results = {"delisted": [], "not_found": []}

    for symbol in DELISTED_SYMBOLS:
        # Check if exists
        check = await db.execute(
            text("SELECT symbol, is_active FROM symbol_universe WHERE symbol = :symbol"),
            {"symbol": symbol}
        )
        row = check.fetchone()

        if row:
            if dry_run:
                print(f"  [DRY RUN] Would mark {symbol} as inactive (currently is_active={row[1]})")
            else:
                await db.execute(
                    text("UPDATE symbol_universe SET is_active = false WHERE symbol = :symbol"),
                    {"symbol": symbol}
                )
                print(f"  [OK] Marked {symbol} as inactive")
            results["delisted"].append(symbol)
        else:
            print(f"  [SKIP] {symbol} not found in symbol_universe")
            results["not_found"].append(symbol)

    return results


async def fix_renamed_symbols(db: AsyncSession, dry_run: bool = True) -> dict:
    """Update renamed symbols across all relevant tables."""
    results = {"renamed": [], "errors": []}

    tables_to_update = [
        "symbol_universe",
        "positions",
        "company_profiles",
        "market_data_cache",
        "symbol_factor_exposures",
    ]

    for old_symbol, new_symbol in RENAMED_SYMBOLS.items():
        print(f"\n  Renaming {old_symbol} → {new_symbol}:")

        for table in tables_to_update:
            try:
                # Check if old symbol exists in table
                check = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE symbol = :symbol"),
                    {"symbol": old_symbol}
                )
                count = check.scalar()

                if count and count > 0:
                    if dry_run:
                        print(f"    [DRY RUN] Would update {count} rows in {table}")
                    else:
                        await db.execute(
                            text(f"UPDATE {table} SET symbol = :new WHERE symbol = :old"),
                            {"old": old_symbol, "new": new_symbol}
                        )
                        print(f"    [OK] Updated {count} rows in {table}")
                else:
                    print(f"    [SKIP] No {old_symbol} in {table}")

            except Exception as e:
                # Table might not exist
                print(f"    [SKIP] {table}: {e}")

        results["renamed"].append(f"{old_symbol} → {new_symbol}")

    return results


async def main(dry_run: bool = True):
    """Main entry point."""
    from app.database import get_async_session

    print("=" * 60)
    print("  FIX DELISTED AND RENAMED SYMBOLS")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY CHANGES'}")
    print()

    async with get_async_session() as db:
        # Fix delisted symbols
        print("1. Marking delisted symbols as inactive:")
        delisted_results = await fix_delisted_symbols(db, dry_run)

        # Fix renamed symbols
        print("\n2. Updating renamed symbols:")
        renamed_results = await fix_renamed_symbols(db, dry_run)

        if not dry_run:
            await db.commit()
            print("\n[OK] Changes committed to database")
        else:
            print("\n[DRY RUN] No changes made. Run without --dry-run to apply.")

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"Delisted: {delisted_results['delisted']}")
    print(f"Renamed: {renamed_results['renamed']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix delisted and renamed symbols")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
