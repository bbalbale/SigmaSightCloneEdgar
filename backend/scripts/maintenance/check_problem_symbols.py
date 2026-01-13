#!/usr/bin/env python3
"""
Check investment_class for problematic symbols.

Usage:
    # Railway SSH
    python scripts/maintenance/check_problem_symbols.py

    # Local
    uv run python scripts/maintenance/check_problem_symbols.py
"""

import asyncio
import sys
import os

# Windows asyncpg fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, text
from app.database import get_async_session
from app.models.positions import Position

# Problematic symbols from the batch run
PROBLEM_SYMBOLS = [
    "BX_PRIVATE_EQUITY",
    "RENTAL_CONDO",
    "FO_INFRASTRUCTURE",
    "HOME_EQUITY",
    "MONEY_MARKET",
    "FO_PRIVATE_CREDIT",
    "TREASURY_BILLS",
    "FO_CRYPTO_DIGITAL",
    "SPY250919C00460000",
    "NVDA251017C00800000",
    "AAPL250815P00200000",
    "VIX250716C00025000",
    "QQQ250815C00420000",
    "BF.B",
    "EQ5D6A2D8F",
]


async def check_symbols():
    """Check investment_class for problematic symbols."""

    print("=" * 70)
    print("  CHECKING INVESTMENT CLASS FOR PROBLEMATIC SYMBOLS")
    print("=" * 70)
    print()

    async with get_async_session() as db:
        for symbol in PROBLEM_SYMBOLS:
            result = await db.execute(
                select(
                    Position.symbol,
                    Position.investment_class,
                    Position.position_type,
                    Position.name
                ).where(Position.symbol == symbol)
            )
            rows = result.fetchall()

            if not rows:
                print(f"  {symbol:25} NOT FOUND in positions table")
            else:
                for row in rows:
                    inv_class = row[1] or "NULL"
                    pos_type = row[2] or "NULL"
                    name = row[3] or ""
                    print(f"  {symbol:25} class={inv_class:10} type={pos_type:10} name={name[:30]}")

    print()
    print("=" * 70)
    print("  RECOMMENDATIONS:")
    print("=" * 70)
    print()
    print("  Symbols that should be PRIVATE (no market data):")
    print("    - BX_PRIVATE_EQUITY, RENTAL_CONDO, FO_INFRASTRUCTURE")
    print("    - HOME_EQUITY, MONEY_MARKET, FO_PRIVATE_CREDIT")
    print("    - TREASURY_BILLS, FO_CRYPTO_DIGITAL, EQ5D6A2D8F")
    print()
    print("  Symbols that should be OPTIONS (expired):")
    print("    - SPY250919C00460000, NVDA251017C00800000")
    print("    - AAPL250815P00200000, VIX250716C00025000, QQQ250815C00420000")
    print()
    print("  Special cases:")
    print("    - BF.B: Brown-Forman Class B - ticker with dot (may need escaping)")
    print()


if __name__ == "__main__":
    asyncio.run(check_symbols())
