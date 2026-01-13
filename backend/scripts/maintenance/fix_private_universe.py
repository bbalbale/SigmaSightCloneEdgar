#!/usr/bin/env python3
"""
Mark private/alternative symbols as inactive in symbol_universe.

These symbols have no market data and should not be processed in V2 batch.
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

# Symbols that should be marked inactive (private/alternative - no market data)
PRIVATE_SYMBOLS = [
    # Private equity / alternatives
    "BX_PRIVATE_EQUITY",
    "TWO_SIGMA_FUND",
    "FO_GROWTH_PE",
    "FO_VC_SECONDARIES",
    "FO_PRIVATE_CREDIT",
    "FO_INFRASTRUCTURE",
    "FO_CRYPTO_DIGITAL",
    "FO_REAL_ASSET_REIT",
    # Real estate
    "RENTAL_CONDO",
    "RENTAL_SFH",
    "HOME_EQUITY",
    # Cash equivalents
    "MONEY_MARKET",
    "TREASURY_BILLS",
    # Crypto (custom identifiers)
    "CRYPTO_BTC_ETH",
    # Other custom identifiers
    "EQ5D6A2D8F",
    # Bad tickers (dot instead of dash)
    "BF.B",
]


async def fix_private_universe(dry_run: bool = True):
    print("=" * 70)
    print("  MARK PRIVATE SYMBOLS INACTIVE IN SYMBOL_UNIVERSE")
    print(f"  Mode: {'DRY RUN' if dry_run else 'UPDATE'}")
    print("=" * 70)
    print()

    total_fixed = 0

    async with get_async_session() as db:
        for symbol in PRIVATE_SYMBOLS:
            # Check if exists and is active
            r = await db.execute(
                text("SELECT symbol, is_active FROM symbol_universe WHERE symbol = :sym"),
                {"sym": symbol}
            )
            row = r.fetchone()

            if not row:
                print(f"  {symbol:25} NOT IN symbol_universe")
                continue

            if not row[1]:  # is_active = False
                print(f"  {symbol:25} Already inactive - OK")
                continue

            # Need to mark inactive
            if dry_run:
                print(f"  {symbol:25} active=True -> would mark INACTIVE")
            else:
                await db.execute(
                    text("UPDATE symbol_universe SET is_active = FALSE WHERE symbol = :sym"),
                    {"sym": symbol}
                )
                print(f"  {symbol:25} MARKED INACTIVE")
                total_fixed += 1

        if not dry_run and total_fixed > 0:
            await db.commit()

    print()
    print("=" * 70)
    if dry_run:
        print(f"  DRY RUN - Would mark {total_fixed} symbols inactive")
    else:
        print(f"  DONE - Marked {total_fixed} symbols inactive")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark private symbols inactive")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(fix_private_universe(dry_run=args.dry_run))
