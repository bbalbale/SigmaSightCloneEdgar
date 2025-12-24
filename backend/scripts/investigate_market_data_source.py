"""
Investigate WHY market data differs and for WHICH dates.
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

# Symbols that showed differences
DIFF_SYMBOLS = ['BND', 'FCNTX', 'FMAGX', 'FXNAX', 'VNQ', 'VTI', 'VTIAX']
# Symbols that matched
MATCH_SYMBOLS = ['AAPL', 'MSFT']


async def get_market_data_details(conn, symbol: str, limit: int = 10):
    """Get market data with source info."""
    query = """
        SELECT
            date,
            close,
            data_source,
            created_at,
            updated_at
        FROM market_data_cache
        WHERE symbol = $1
        ORDER BY date DESC
        LIMIT $2
    """
    rows = await conn.fetch(query, symbol, limit)
    return [dict(row) for row in rows]


async def count_differences(core_conn, legacy_conn, symbol: str):
    """Count how many dates have different prices."""
    query = """
        SELECT date, close FROM market_data_cache WHERE symbol = $1 ORDER BY date
    """
    core_rows = await core_conn.fetch(query, symbol)
    legacy_rows = await legacy_conn.fetch(query, symbol)

    core_map = {row['date']: Decimal(str(row['close'])) for row in core_rows}
    legacy_map = {row['date']: Decimal(str(row['close'])) for row in legacy_rows}

    all_dates = sorted(set(core_map.keys()) | set(legacy_map.keys()))

    diff_count = 0
    match_count = 0
    first_diff_date = None
    last_diff_date = None

    for d in all_dates:
        core_p = core_map.get(d)
        legacy_p = legacy_map.get(d)

        if core_p != legacy_p:
            diff_count += 1
            if first_diff_date is None:
                first_diff_date = d
            last_diff_date = d
        else:
            match_count += 1

    return {
        'total_dates': len(all_dates),
        'diff_count': diff_count,
        'match_count': match_count,
        'first_diff': first_diff_date,
        'last_diff': last_diff_date,
        'core_count': len(core_map),
        'legacy_count': len(legacy_map)
    }


async def main():
    print("=" * 120)
    print("MARKET DATA SOURCE INVESTIGATION")
    print("=" * 120)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        # Check data source for differing symbols
        print("\n" + "=" * 80)
        print("DATA SOURCE COMPARISON FOR DIFFERING SYMBOLS")
        print("=" * 80)

        for symbol in DIFF_SYMBOLS[:3]:  # Check first 3
            print(f"\n--- {symbol} ---")

            core_data = await get_market_data_details(core_conn, symbol, 3)
            legacy_data = await get_market_data_details(legacy_conn, symbol, 3)

            print(f"\nCORE DB (most recent 3 dates):")
            print(f"{'Date':<12} {'Close':>12} {'Source':<15} {'Created At':<25}")
            for row in core_data:
                src = row.get('data_source') or 'NULL'
                created = str(row.get('created_at', 'N/A'))[:24]
                print(f"{row['date']} ${Decimal(str(row['close'])):>11.4f} {src:<15} {created}")

            print(f"\nLEGACY DB (most recent 3 dates):")
            print(f"{'Date':<12} {'Close':>12} {'Source':<15} {'Created At':<25}")
            for row in legacy_data:
                src = row.get('data_source') or 'NULL'
                created = str(row.get('created_at', 'N/A'))[:24]
                print(f"{row['date']} ${Decimal(str(row['close'])):>11.4f} {src:<15} {created}")

        # Check data source for matching symbols
        print("\n" + "=" * 80)
        print("DATA SOURCE COMPARISON FOR MATCHING SYMBOLS")
        print("=" * 80)

        for symbol in MATCH_SYMBOLS:
            print(f"\n--- {symbol} ---")

            core_data = await get_market_data_details(core_conn, symbol, 2)
            legacy_data = await get_market_data_details(legacy_conn, symbol, 2)

            print(f"CORE:   Source={core_data[0].get('data_source') if core_data else 'N/A'}")
            print(f"LEGACY: Source={legacy_data[0].get('data_source') if legacy_data else 'N/A'}")

        # Count differences across all dates
        print("\n" + "=" * 80)
        print("DATE RANGE ANALYSIS")
        print("=" * 80)

        print(f"\n{'Symbol':<10} {'Total':>8} {'Diff':>8} {'Match':>8} {'First Diff':<12} {'Last Diff':<12}")
        print("-" * 70)

        for symbol in DIFF_SYMBOLS + MATCH_SYMBOLS[:2]:
            stats = await count_differences(core_conn, legacy_conn, symbol)
            first_diff = str(stats['first_diff']) if stats['first_diff'] else 'N/A'
            last_diff = str(stats['last_diff']) if stats['last_diff'] else 'N/A'
            print(f"{symbol:<10} {stats['total_dates']:>8} {stats['diff_count']:>8} {stats['match_count']:>8} {first_diff:<12} {last_diff:<12}")

        # Check if there's a pattern by date
        print("\n" + "=" * 80)
        print("CHECKING FOR DATE PATTERN")
        print("=" * 80)

        # Get all VTI data to see the full picture
        symbol = 'VTI'
        query = """
            SELECT date, close FROM market_data_cache WHERE symbol = $1 ORDER BY date
        """
        core_rows = await core_conn.fetch(query, symbol)
        legacy_rows = await legacy_conn.fetch(query, symbol)

        core_map = {row['date']: Decimal(str(row['close'])) for row in core_rows}
        legacy_map = {row['date']: Decimal(str(row['close'])) for row in legacy_rows}

        print(f"\n{symbol} - First 10 dates:")
        print(f"{'Date':<12} {'Core':>12} {'Legacy':>12} {'Delta':>10} {'Status'}")
        print("-" * 60)

        all_dates = sorted(set(core_map.keys()) | set(legacy_map.keys()))
        for d in all_dates[:10]:
            core_p = core_map.get(d)
            legacy_p = legacy_map.get(d)
            if core_p and legacy_p:
                delta = core_p - legacy_p
                status = "MATCH" if abs(delta) < Decimal('0.001') else "DIFF"
            else:
                delta = Decimal('0')
                status = "MISSING"
            print(f"{d} ${core_p or 0:>11.4f} ${legacy_p or 0:>11.4f} ${delta:>+9.4f} {status}")

    finally:
        await core_conn.close()
        await legacy_conn.close()


asyncio.run(main())
