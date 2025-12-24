"""
Compare Market Data Between Core DB and Legacy DB

Check if the price data differs between databases, which would explain
the daily P&L calculation differences.

Created: 2025-12-23
"""
import asyncio
import sys
import io
from datetime import date
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"

# Symbols from Demo Individual portfolio
DEMO_SYMBOLS = ['AAPL', 'AMZN', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'JPM', 'JNJ', 'V', 'VTI']


async def get_table_columns(conn, table_name):
    """Get column names for a table."""
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
    """
    rows = await conn.fetch(query, table_name)
    return [row['column_name'] for row in rows]


async def get_prices(conn, symbols, start_date, end_date):
    """Get prices for symbols in date range."""
    query = """
        SELECT
            symbol,
            date as price_date,
            close as close_price,
            open as open_price,
            high as high_price,
            low as low_price
        FROM market_data_cache
        WHERE symbol = ANY($1)
          AND date >= $2
          AND date <= $3
        ORDER BY symbol, date
    """
    rows = await conn.fetch(query, symbols, start_date, end_date)
    return [dict(row) for row in rows]


async def compare_market_data():
    print("=" * 140)
    print("MARKET DATA COMPARISON: Core DB vs Legacy DB")
    print("=" * 140)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        start_date = date(2025, 7, 1)
        end_date = date(2025, 7, 10)  # First 10 days

        core_prices = await get_prices(core_conn, DEMO_SYMBOLS, start_date, end_date)
        legacy_prices = await get_prices(legacy_conn, DEMO_SYMBOLS, start_date, end_date)

        # Create lookup
        core_map = {(p['symbol'], p['price_date']): p for p in core_prices}
        legacy_map = {(p['symbol'], p['price_date']): p for p in legacy_prices}

        all_keys = sorted(set(core_map.keys()) | set(legacy_map.keys()))

        print(f"\nComparing prices for: {', '.join(DEMO_SYMBOLS)}")
        print(f"Date range: {start_date} to {end_date}")
        print()

        # Header
        print(f"{'Symbol':<8} {'Date':<12} | {'Core Close':>12} | {'Legacy Close':>12} | {'Delta':>10} | {'Status':<15}")
        print("-" * 80)

        mismatches = 0
        for key in all_keys:
            symbol, price_date = key
            core = core_map.get(key, {})
            legacy = legacy_map.get(key, {})

            core_close = Decimal(str(core.get('close_price', 0) or 0))
            legacy_close = Decimal(str(legacy.get('close_price', 0) or 0))
            delta = core_close - legacy_close

            if not core:
                status = "MISSING CORE"
                mismatches += 1
            elif not legacy:
                status = "MISSING LEGACY"
                mismatches += 1
            elif abs(delta) < Decimal("0.01"):
                status = "MATCH"
            else:
                status = "DIFFERENT"
                mismatches += 1

            core_str = f"${core_close:.2f}" if core else "---"
            legacy_str = f"${legacy_close:.2f}" if legacy else "---"
            delta_str = f"${delta:+.4f}" if (core and legacy) else "---"

            # Only print if different or missing
            if status != "MATCH":
                print(f"{symbol:<8} {price_date} | {core_str:>12} | {legacy_str:>12} | {delta_str:>10} | {status:<15}")

        if mismatches == 0:
            print("ALL PRICES MATCH!")
        else:
            print(f"\n{mismatches} price differences found")

        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total price records checked: {len(all_keys)}")
        print(f"Core records: {len(core_prices)}")
        print(f"Legacy records: {len(legacy_prices)}")
        print(f"Mismatches: {mismatches}")

    finally:
        await core_conn.close()
        await legacy_conn.close()


if __name__ == '__main__':
    asyncio.run(compare_market_data())
