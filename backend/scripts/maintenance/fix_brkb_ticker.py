#!/usr/bin/env python3
"""
Fix BRK.B ticker to BRK-B (Yahoo Finance format)

Usage:
    python scripts/maintenance/fix_brkb_ticker.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


OLD_SYMBOL = "BRK.B"
NEW_SYMBOL = "BRK-B"

TABLES_TO_UPDATE = [
    "symbol_universe",
    "positions",
    "company_profiles",
    "market_data_cache",
    "symbol_factor_exposures",
]


async def main():
    print("=" * 60)
    print(f"  FIX TICKER: {OLD_SYMBOL} → {NEW_SYMBOL}")
    print("=" * 60)

    for table in TABLES_TO_UPDATE:
        async with get_async_session() as db:
            try:
                # Check if OLD symbol exists
                old_check = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE symbol = :symbol"),
                    {"symbol": OLD_SYMBOL}
                )
                old_count = old_check.scalar() or 0

                if old_count == 0:
                    print(f"  [SKIP] No {OLD_SYMBOL} in {table}")
                    continue

                # Check if NEW symbol already exists
                new_check = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE symbol = :symbol"),
                    {"symbol": NEW_SYMBOL}
                )
                new_count = new_check.scalar() or 0

                if new_count > 0:
                    # New symbol exists - delete old symbol rows
                    await db.execute(
                        text(f"DELETE FROM {table} WHERE symbol = :old"),
                        {"old": OLD_SYMBOL}
                    )
                    await db.commit()
                    print(f"  [OK] {NEW_SYMBOL} exists, DELETED {old_count} {OLD_SYMBOL} rows in {table}")
                else:
                    # New symbol doesn't exist - rename
                    await db.execute(
                        text(f"UPDATE {table} SET symbol = :new WHERE symbol = :old"),
                        {"old": OLD_SYMBOL, "new": NEW_SYMBOL}
                    )
                    await db.commit()
                    print(f"  [OK] Renamed {old_count} rows in {table}: {OLD_SYMBOL} → {NEW_SYMBOL}")

            except Exception as e:
                await db.rollback()
                print(f"  [ERROR] {table}: {e}")

    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
