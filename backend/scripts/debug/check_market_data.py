#!/usr/bin/env python
"""
Check market data cache for TLT and other key symbols
Usage: python scripts/debug/check_market_data.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from sqlalchemy import select, func
from datetime import date


async def check_market_data():
    from app.database import get_async_session
    from app.models.market_data import MarketDataCache

    print("=" * 60)
    print("MARKET DATA CACHE CHECK")
    print("=" * 60)

    async with get_async_session() as db:
        # Check key symbols
        key_symbols = ['TLT', 'SPY', 'IWM', 'VUG', 'VTV', 'MTUM', 'QUAL', 'USMV']

        for symbol in key_symbols:
            count = await db.execute(
                select(func.count(MarketDataCache.id))
                .where(MarketDataCache.symbol == symbol)
            )
            count_val = count.scalar()

            if count_val > 0:
                min_date = await db.execute(
                    select(func.min(MarketDataCache.date))
                    .where(MarketDataCache.symbol == symbol)
                )
                max_date = await db.execute(
                    select(func.max(MarketDataCache.date))
                    .where(MarketDataCache.symbol == symbol)
                )
                print(f"{symbol}: {count_val} records, {min_date.scalar()} to {max_date.scalar()}")
            else:
                print(f"{symbol}: NO DATA")

        print()

        # Total records
        total = await db.execute(select(func.count(MarketDataCache.id)))
        print(f"Total market data records: {total.scalar()}")

        # Unique symbols
        symbols = await db.execute(select(func.count(func.distinct(MarketDataCache.symbol))))
        print(f"Unique symbols: {symbols.scalar()}")

        # Date range overall
        min_overall = await db.execute(select(func.min(MarketDataCache.date)))
        max_overall = await db.execute(select(func.max(MarketDataCache.date)))
        print(f"Overall date range: {min_overall.scalar()} to {max_overall.scalar()}")


if __name__ == "__main__":
    asyncio.run(check_market_data())
