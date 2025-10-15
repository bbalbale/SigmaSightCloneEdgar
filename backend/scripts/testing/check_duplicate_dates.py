#!/usr/bin/env python
"""
Check for duplicate (symbol, date) records in market_data_cache

This should be IMPOSSIBLE due to unique constraint, but let's verify.
Also checks if there are aggregation issues.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.market_data import MarketDataCache
from app.config import settings


async def check_duplicates():
    """Check for duplicate date records"""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("Checking for duplicate (symbol, date) records in market_data_cache")
        print("=" * 80)
        print()

        # Check for duplicates - this query should return 0 rows if constraint is working
        duplicate_query = (
            select(
                MarketDataCache.symbol,
                MarketDataCache.date,
                func.count(MarketDataCache.id).label('count'),
                func.array_agg(MarketDataCache.close).label('prices'),
                func.array_agg(MarketDataCache.data_source).label('sources')
            )
            .group_by(MarketDataCache.symbol, MarketDataCache.date)
            .having(func.count(MarketDataCache.id) > 1)
        )

        result = await db.execute(duplicate_query)
        duplicates = result.all()

        if duplicates:
            print(f"❌ Found {len(duplicates)} (symbol, date) combinations with multiple records:")
            print()
            for dup in duplicates[:20]:  # Show first 20
                print(f"  {dup.symbol} on {dup.date}:")
                print(f"    Record count: {dup.count}")
                print(f"    Prices: {dup.prices}")
                print(f"    Sources: {dup.sources}")
                print()
        else:
            print("✅ No duplicate (symbol, date) records found")
            print("   Unique constraint is working correctly")

        print()

        # Check NVDA and META specifically on 9/29 and 9/30
        print("=" * 80)
        print("Checking NVDA and META on Sept 29-30, 2024")
        print("=" * 80)
        print()

        target_dates = [date(2024, 9, 29), date(2024, 9, 30)]
        symbols = ['NVDA', 'META']

        for symbol in symbols:
            for target_date in target_dates:
                query = select(MarketDataCache).where(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date == target_date
                )
                result = await db.execute(query)
                records = result.scalars().all()

                print(f"{symbol} on {target_date}:")
                if len(records) == 0:
                    print("  ⚠️  No data found")
                elif len(records) == 1:
                    rec = records[0]
                    print(f"  ✅ 1 record (as expected)")
                    print(f"     Close: ${rec.close}")
                    print(f"     Open: ${rec.open}, High: ${rec.high}, Low: ${rec.low}")
                    print(f"     Volume: {rec.volume}")
                    print(f"     Source: {rec.data_source}")
                else:
                    print(f"  ❌ {len(records)} records (DUPLICATE!)")
                    for i, rec in enumerate(records):
                        print(f"     Record {i+1}:")
                        print(f"       Close: ${rec.close}, Source: {rec.data_source}")
                print()

        # Check for price anomalies (300% moves)
        print("=" * 80)
        print("Checking for extreme single-day price moves in NVDA/META")
        print("=" * 80)
        print()

        for symbol in ['NVDA', 'META']:
            # Get September data
            query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date >= date(2024, 9, 1),
                MarketDataCache.date <= date(2024, 9, 30)
            ).order_by(MarketDataCache.date)

            result = await db.execute(query)
            records = result.scalars().all()

            print(f"{symbol} September 2024 prices:")
            prev_price = None
            for rec in records:
                price = float(rec.close)
                if prev_price:
                    pct_change = ((price - prev_price) / prev_price) * 100
                    flag = "⚠️" if abs(pct_change) > 20 else "  "
                    print(f"  {flag} {rec.date}: ${price:.2f} ({pct_change:+.1f}% from prev day)")
                else:
                    print(f"     {rec.date}: ${price:.2f}")
                prev_price = price
            print()

    await engine.dispose()


if __name__ == "__main__":
    print("Checking for duplicate dates and price anomalies...")
    print()
    asyncio.run(check_duplicates())
    print("Done!")
