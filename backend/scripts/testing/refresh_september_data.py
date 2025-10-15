#!/usr/bin/env python
"""
Refresh market data for September 29, 2025 and surrounding dates

This script fetches fresh price data from the market data provider to overwrite
any corrupted data in the database.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.models.market_data import MarketDataCache
from app.services.market_data_service import MarketDataService
from app.config import settings


async def refresh_september_data():
    """Fetch fresh data for Sept 28-30, 2025 for all symbols"""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("Refreshing September 2025 Market Data")
        print("=" * 80)
        print()

        # Get all unique symbols from market_data_cache
        query = select(MarketDataCache.symbol).distinct()
        result = await db.execute(query)
        symbols = [row[0] for row in result.all()]

        print(f"Found {len(symbols)} unique symbols in database")
        print(f"Symbols: {', '.join(sorted(symbols)[:10])}{'...' if len(symbols) > 10 else ''}")
        print()

        # Define date range (Sept 28-30, 2025)
        # Using a 3-day window to ensure we get good data around the problematic date
        target_date = date(2025, 9, 29)
        start_date = target_date - timedelta(days=1)  # Sept 28
        end_date = target_date + timedelta(days=1)    # Sept 30

        print(f"Fetching fresh data for: {start_date} to {end_date}")
        print()

        # Initialize market data service
        market_service = MarketDataService()

        # Track results
        updated_count = 0
        error_count = 0

        # Fetch all symbols at once using hybrid method
        print("Fetching historical data for all symbols...")
        print()

        result = await market_service.fetch_historical_data_hybrid(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )

        print(f"API returned data for {len(result)} symbols")
        print()

        # Process results for each symbol
        for i, symbol in enumerate(symbols, 1):
            try:
                print(f"[{i}/{len(symbols)}] Processing {symbol}...", end=" ")

                if symbol not in result or not result[symbol]:
                    print("❌ No data returned from API")
                    error_count += 1
                    continue

                prices = result[symbol]

                # Store/update data in database
                for price_data in prices:
                    # Use PostgreSQL upsert to overwrite existing data
                    stmt = insert(MarketDataCache).values(
                        symbol=symbol,
                        date=price_data['date'],
                        open=price_data.get('open'),
                        high=price_data.get('high'),
                        low=price_data.get('low'),
                        close=price_data['close'],
                        volume=price_data.get('volume'),
                        data_source=price_data.get('data_source', 'FMP')
                    )

                    # On conflict (symbol, date), UPDATE all fields
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['symbol', 'date'],
                        set_={
                            'open': stmt.excluded.open,
                            'high': stmt.excluded.high,
                            'low': stmt.excluded.low,
                            'close': stmt.excluded.close,
                            'volume': stmt.excluded.volume,
                            'data_source': stmt.excluded.data_source,
                            'updated_at': func.now()
                        }
                    )

                    await db.execute(stmt)

                await db.commit()

                print(f"✅ Updated {len(prices)} records")
                updated_count += len(prices)

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                error_count += 1
                await db.rollback()
                continue

        print()
        print("=" * 80)
        print("REFRESH COMPLETE")
        print("=" * 80)
        print(f"Symbols processed: {len(symbols)}")
        print(f"Records updated: {updated_count}")
        print(f"Errors: {error_count}")
        print()

        # Verify the updated data for NVDA and META
        print("=" * 80)
        print("Verifying NVDA and META data on Sept 29, 2025")
        print("=" * 80)
        print()

        for symbol in ['NVDA', 'META']:
            query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date == target_date
            )
            result = await db.execute(query)
            record = result.scalar_one_or_none()

            if record:
                print(f"{symbol} on {target_date}:")
                print(f"  Open:  ${float(record.open):.2f}")
                print(f"  High:  ${float(record.high):.2f}")
                print(f"  Low:   ${float(record.low):.2f}")
                print(f"  Close: ${float(record.close):.2f}")
                print(f"  Volume: {record.volume:,}")
                print(f"  Source: {record.data_source}")
            else:
                print(f"{symbol} on {target_date}: ⚠️  No data found")
            print()

    await engine.dispose()


if __name__ == "__main__":
    print("Starting September data refresh...")
    print()
    asyncio.run(refresh_september_data())
    print("Done!")
