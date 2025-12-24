"""
Refresh market data in Core DB with unadjusted prices.
Date range: 2024-01-01 to 2025-12-23
"""
import asyncio
import sys
import os
from datetime import date
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 23)


async def get_all_symbols(conn) -> list:
    """Get all unique symbols from market_data_cache."""
    query = """
        SELECT DISTINCT symbol
        FROM market_data_cache
        WHERE symbol IS NOT NULL
        ORDER BY symbol
    """
    rows = await conn.fetch(query)
    return [r['symbol'] for r in rows]


async def delete_existing_data(conn, symbols: list):
    """Delete existing market data for the date range."""
    print(f"Deleting existing data for {len(symbols)} symbols from {START_DATE} to {END_DATE}...")

    deleted = await conn.execute("""
        DELETE FROM market_data_cache
        WHERE symbol = ANY($1)
        AND date >= $2
        AND date <= $3
    """, symbols, START_DATE, END_DATE)

    print(f"Deleted: {deleted}")


async def fetch_and_insert_data(conn, symbols: list):
    """Fetch new data from YFinance and insert into database."""
    import yfinance as yf
    from datetime import timedelta

    print(f"\nFetching data for {len(symbols)} symbols...")
    print(f"Date range: {START_DATE} to {END_DATE}")

    # Process in batches of 50
    batch_size = 50
    total_inserted = 0

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        print(f"\nBatch {batch_num}/{total_batches}: Fetching {len(batch)} symbols...")

        try:
            # Fetch from yfinance with auto_adjust=False
            data = yf.download(
                tickers=batch,
                start=START_DATE.strftime('%Y-%m-%d'),
                end=(END_DATE + timedelta(days=1)).strftime('%Y-%m-%d'),  # exclusive end
                progress=False,
                auto_adjust=False,  # Use unadjusted prices
                threads=True,
                group_by='ticker'
            )

            if data.empty:
                print(f"  No data returned for batch")
                continue

            # Prepare records for insertion
            records = []

            # Handle single vs multiple ticker response
            if len(batch) == 1:
                symbol = batch[0]
                for idx, row in data.iterrows():
                    try:
                        close = row['Close']
                        if hasattr(close, 'item'):
                            close = close.item()
                        if close and str(close) != 'nan':
                            records.append((
                                symbol,
                                idx.date() if hasattr(idx, 'date') else idx,
                                Decimal(str(close)),
                                'yfinance'
                            ))
                    except:
                        continue
            else:
                for symbol in batch:
                    try:
                        if symbol not in data.columns.get_level_values(0):
                            continue
                        ticker_data = data[symbol]
                        for idx, row in ticker_data.iterrows():
                            try:
                                close = row['Close']
                                if hasattr(close, 'item'):
                                    close = close.item()
                                if close and str(close) != 'nan':
                                    records.append((
                                        symbol,
                                        idx.date() if hasattr(idx, 'date') else idx,
                                        Decimal(str(close)),
                                        'yfinance'
                                    ))
                            except:
                                continue
                    except Exception as e:
                        print(f"  Error processing {symbol}: {e}")
                        continue

            # Insert records
            if records:
                await conn.executemany("""
                    INSERT INTO market_data_cache (id, symbol, date, close, data_source, created_at, updated_at)
                    VALUES (gen_random_uuid(), $1, $2, $3, $4, NOW(), NOW())
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        close = EXCLUDED.close,
                        data_source = EXCLUDED.data_source,
                        updated_at = NOW()
                """, records)

                total_inserted += len(records)
                print(f"  Inserted/updated {len(records)} records")

        except Exception as e:
            print(f"  Batch error: {e}")
            continue

    return total_inserted


async def main():
    print("=" * 80)
    print("REFRESH MARKET DATA - Core DB")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print("Using: auto_adjust=False (unadjusted prices)")
    print("=" * 80)

    conn = await asyncpg.connect(CORE_DB_URL)

    try:
        # Get all symbols
        symbols = await get_all_symbols(conn)
        print(f"\nFound {len(symbols)} unique symbols")

        # Delete existing data
        await delete_existing_data(conn, symbols)

        # Fetch and insert new data
        total = await fetch_and_insert_data(conn, symbols)

        print("\n" + "=" * 80)
        print(f"COMPLETE: Inserted/updated {total} total records")
        print("=" * 80)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
