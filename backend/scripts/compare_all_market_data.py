"""
Compare ALL market data between databases for Demo Individual symbols.
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

# ALL symbols from Demo Individual portfolio
ALL_SYMBOLS = ['AAPL', 'AMZN', 'BND', 'FCNTX', 'FMAGX', 'FXNAX', 'GOOGL', 'JNJ', 'JPM', 'MSFT', 'NVDA', 'TSLA', 'V', 'VNQ', 'VTI', 'VTIAX']


async def get_prices(conn, symbol: str, start_date: date, end_date: date):
    """Get all prices for a symbol in date range."""
    query = """
        SELECT date, close
        FROM market_data_cache
        WHERE symbol = $1 AND date >= $2 AND date <= $3
        ORDER BY date
    """
    rows = await conn.fetch(query, symbol, start_date, end_date)
    return {row['date']: Decimal(str(row['close'])) for row in rows}


async def main():
    print("=" * 100)
    print("FULL MARKET DATA COMPARISON: All Demo Individual Symbols")
    print("=" * 100)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        start_date = date(2025, 7, 1)
        end_date = date(2025, 7, 5)

        print(f"\nDate range: {start_date} to {end_date}")
        print()

        symbols_with_diff = []
        symbols_match = []

        for symbol in ALL_SYMBOLS:
            core_prices = await get_prices(core_conn, symbol, start_date, end_date)
            legacy_prices = await get_prices(legacy_conn, symbol, start_date, end_date)

            has_diff = False
            for d in sorted(set(core_prices.keys()) | set(legacy_prices.keys())):
                core_p = core_prices.get(d)
                legacy_p = legacy_prices.get(d)

                if core_p != legacy_p:
                    has_diff = True
                    if symbol not in symbols_with_diff:
                        symbols_with_diff.append(symbol)
                        print(f"\n{symbol}:")

                    core_str = f"${core_p:.4f}" if core_p else "MISSING"
                    legacy_str = f"${legacy_p:.4f}" if legacy_p else "MISSING"
                    diff = (core_p - legacy_p) if (core_p and legacy_p) else Decimal('0')
                    print(f"  {d}: Core={core_str}, Legacy={legacy_str}, Delta=${diff:+.4f}")

            if not has_diff:
                symbols_match.append(symbol)

        print(f"\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print(f"\nSymbols with IDENTICAL prices: {len(symbols_match)}")
        print(f"  {', '.join(symbols_match)}")
        print(f"\nSymbols with DIFFERENT prices: {len(symbols_with_diff)}")
        print(f"  {', '.join(symbols_with_diff)}")

        if symbols_with_diff:
            print(f"\n*** ROOT CAUSE: Market data differs for {len(symbols_with_diff)} symbols ***")
            print("This explains the P&L differences between databases.")

    finally:
        await core_conn.close()
        await legacy_conn.close()


asyncio.run(main())
