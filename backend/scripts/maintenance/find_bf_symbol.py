#!/usr/bin/env python3
"""
Find where BF.B or BF-B symbols exist in the database.
"""

import asyncio
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


async def find_bf():
    print("=" * 60)
    print("  SEARCHING FOR BF SYMBOLS")
    print("=" * 60)
    print()

    async with get_async_session() as db:
        # Check positions
        print("  POSITIONS TABLE:")
        r = await db.execute(text("SELECT symbol, investment_class, position_type FROM positions WHERE UPPER(symbol) LIKE '%BF%'"))
        rows = r.fetchall()
        if rows:
            for row in rows:
                print(f"    {row[0]:20} class={row[1]} type={row[2]}")
        else:
            print("    No BF symbols found")

        print()
        print("  SYMBOL_UNIVERSE TABLE:")
        r = await db.execute(text("SELECT symbol, is_active FROM symbol_universe WHERE UPPER(symbol) LIKE '%BF%'"))
        rows = r.fetchall()
        if rows:
            for row in rows:
                print(f"    {row[0]:20} active={row[1]}")
        else:
            print("    No BF symbols found")

        print()
        print("  MARKET_DATA_CACHE TABLE:")
        r = await db.execute(text("SELECT DISTINCT symbol FROM market_data_cache WHERE UPPER(symbol) LIKE '%BF%' LIMIT 10"))
        rows = r.fetchall()
        if rows:
            for row in rows:
                print(f"    {row[0]}")
        else:
            print("    No BF symbols found")

        print()
        print("  COMPANY_PROFILES TABLE:")
        r = await db.execute(text("SELECT symbol, company_name FROM company_profiles WHERE UPPER(symbol) LIKE '%BF%'"))
        rows = r.fetchall()
        if rows:
            for row in rows:
                print(f"    {row[0]:20} {row[1]}")
        else:
            print("    No BF symbols found")

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(find_bf())
