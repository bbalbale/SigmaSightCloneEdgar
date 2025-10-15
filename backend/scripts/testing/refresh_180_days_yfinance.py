#!/usr/bin/env python
"""
Refresh 180 days of historical market data using YFinance

This script fetches 180 days of price data from YFinance to overwrite
any corrupted or missing data in the database.

NOTE: This script now uses the shared fetch_historical_data module
to avoid code duplication with the seeding process.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.market_data import MarketDataCache
from app.config import settings
from app.db.fetch_historical_data import (
    fetch_and_store_historical_data,
    filter_stock_symbols
)


async def refresh_180_days_data():
    """Fetch 180 days of fresh data using YFinance"""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("Refreshing 180 Days of Market Data (YFinance)")
        print("=" * 80)
        print()

        # Get all unique symbols from market_data_cache (stocks only, not options)
        query = select(MarketDataCache.symbol).distinct()
        result = await db.execute(query)
        all_symbols = [row[0] for row in result.all()]

        # Filter out options symbols (they typically have 15+ characters with dates)
        stock_symbols = await filter_stock_symbols(all_symbols)

        print(f"Found {len(all_symbols)} total symbols, {len(stock_symbols)} are stocks/ETFs")
        print(f"Symbols: {', '.join(sorted(stock_symbols)[:15])}{'...' if len(stock_symbols) > 15 else ''}")
        print()

        # Fetch and store 180 days using shared function
        records_per_symbol = await fetch_and_store_historical_data(
            db=db,
            symbols=stock_symbols,
            days=180,
            batch_size=10
        )

        # Summary
        successful = sum(1 for count in records_per_symbol.values() if count > 0)
        total_records = sum(records_per_symbol.values())

        print()
        print("=" * 80)
        print("REFRESH COMPLETE")
        print("=" * 80)
        print(f"Symbols processed: {len(stock_symbols)}")
        print(f"Symbols updated: {successful}")
        print(f"Total records updated: {total_records}")
        print(f"Errors: {len(stock_symbols) - successful}")
        print()

        # Verify the updated data for NVDA and META on Sept 29
        print("=" * 80)
        print("Verifying NVDA and META data around Sept 29, 2025")
        print("=" * 80)
        print()

        target_dates = [date(2025, 9, 28), date(2025, 9, 29), date(2025, 9, 30)]

        for symbol in ['NVDA', 'META']:
            print(f"{symbol}:")
            for target_date in target_dates:
                query = select(MarketDataCache).where(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date == target_date
                )
                result = await db.execute(query)
                record = result.scalar_one_or_none()

                if record:
                    print(f"  {target_date}: Close=${float(record.close):.2f}, "
                          f"Volume={record.volume:,}, Source={record.data_source}")
                else:
                    print(f"  {target_date}: ⚠️  No data found")
            print()

    await engine.dispose()


if __name__ == "__main__":
    print("Starting 180-day data refresh using YFinance...")
    print()
    asyncio.run(refresh_180_days_data())
    print("Done!")
