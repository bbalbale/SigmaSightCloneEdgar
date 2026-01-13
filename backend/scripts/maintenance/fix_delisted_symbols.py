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


async def fix_renamed_symbols(dry_run: bool = True) -> dict:
    """Update renamed symbols across all relevant tables.

    Uses separate sessions per table to avoid transaction cascade failures.
    """
    from app.database import get_async_session

    results = {"renamed": [], "errors": [], "updated_tables": []}

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
                # Use separate session for each table to avoid cascade failures
                async with get_async_session() as db:
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
                            await db.commit()
                            print(f"    [OK] Updated {count} rows in {table}")
                            results["updated_tables"].append(table)
                    else:
                        print(f"    [SKIP] No {old_symbol} in {table}")

            except Exception as e:
                # Table might not exist or other error - continue with next table
                print(f"    [ERROR] {table}: {e}")
                results["errors"].append(f"{table}: {str(e)}")

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

    # Fix delisted symbols (uses its own session)
    print("1. Marking delisted symbols as inactive:")
    async with get_async_session() as db:
        delisted_results = await fix_delisted_symbols(db, dry_run)
        if not dry_run:
            await db.commit()

    # Fix renamed symbols (each table uses its own session)
    print("\n2. Updating renamed symbols:")
    renamed_results = await fix_renamed_symbols(dry_run)

    if dry_run:
        print("\n[DRY RUN] No changes made. Run without --dry-run to apply.")
    else:
        print("\n[OK] All changes committed to database")

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"Delisted: {delisted_results['delisted']}")
    print(f"Renamed: {renamed_results['renamed']}")
    if renamed_results.get('updated_tables'):
        print(f"Tables updated: {renamed_results['updated_tables']}")
    if renamed_results.get('errors'):
        print(f"Errors: {renamed_results['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix delisted and renamed symbols")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
