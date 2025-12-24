"""
Diagnose P&L Difference - Manual Calculation

Calculate P&L manually for 2025-07-02 using raw data from both databases
to find exactly where the $2.80 difference comes from.

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

DEMO_INDIVIDUAL_ID = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"
CALC_DATE = date(2025, 7, 2)
PREV_DATE = date(2025, 7, 1)


async def get_positions(conn, portfolio_id: str):
    """Get positions for portfolio."""
    query = """
        SELECT
            id,
            symbol,
            quantity,
            entry_price,
            investment_class,
            position_type
        FROM positions
        WHERE portfolio_id = $1
          AND deleted_at IS NULL
        ORDER BY symbol
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]


async def get_price(conn, symbol: str, price_date: date):
    """Get closing price for symbol on date."""
    query = """
        SELECT close
        FROM market_data_cache
        WHERE symbol = $1 AND date = $2
    """
    row = await conn.fetchrow(query, symbol, price_date)
    return Decimal(str(row['close'])) if row else None


async def diagnose():
    print("=" * 120)
    print(f"MANUAL P&L CALCULATION FOR {CALC_DATE}")
    print("=" * 120)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        # Get positions (should be identical)
        core_positions = await get_positions(core_conn, DEMO_INDIVIDUAL_ID)
        legacy_positions = await get_positions(legacy_conn, DEMO_INDIVIDUAL_ID)

        print(f"\nPositions: Core={len(core_positions)}, Legacy={len(legacy_positions)}")

        # Calculate P&L manually for each position
        print(f"\n{'Symbol':<10} | {'Qty':>12} | {'Prev (C)':>12} | {'Prev (L)':>12} | {'Curr (C)':>12} | {'Curr (L)':>12} | {'PnL (C)':>12} | {'PnL (L)':>12} | {'Delta':>10}")
        print("-" * 120)

        core_total_pnl = Decimal('0')
        legacy_total_pnl = Decimal('0')

        for core_pos in core_positions:
            symbol = core_pos['symbol']
            quantity = Decimal(str(core_pos['quantity']))
            inv_class = core_pos.get('investment_class', '')

            # Skip PRIVATE positions (no daily P&L)
            if inv_class and str(inv_class).upper() == 'PRIVATE':
                print(f"{symbol:<10} | {'PRIVATE - SKIPPED':>80}")
                continue

            # Get prices from BOTH databases
            core_prev_price = await get_price(core_conn, symbol, PREV_DATE)
            core_curr_price = await get_price(core_conn, symbol, CALC_DATE)
            legacy_prev_price = await get_price(legacy_conn, symbol, PREV_DATE)
            legacy_curr_price = await get_price(legacy_conn, symbol, CALC_DATE)

            # Calculate P&L
            if core_prev_price and core_curr_price:
                core_pnl = (core_curr_price - core_prev_price) * quantity
            else:
                core_pnl = Decimal('0')

            if legacy_prev_price and legacy_curr_price:
                legacy_pnl = (legacy_curr_price - legacy_prev_price) * quantity
            else:
                legacy_pnl = Decimal('0')

            delta = core_pnl - legacy_pnl
            core_total_pnl += core_pnl
            legacy_total_pnl += legacy_pnl

            # Format prices
            cp_str = f"${core_prev_price:.4f}" if core_prev_price else "N/A"
            cc_str = f"${core_curr_price:.4f}" if core_curr_price else "N/A"
            lp_str = f"${legacy_prev_price:.4f}" if legacy_prev_price else "N/A"
            lc_str = f"${legacy_curr_price:.4f}" if legacy_curr_price else "N/A"

            # Highlight if prices differ
            price_diff = ""
            if core_prev_price != legacy_prev_price:
                price_diff = " ***PREV DIFF***"
            if core_curr_price != legacy_curr_price:
                price_diff += " ***CURR DIFF***"

            print(f"{symbol:<10} | {quantity:>12.2f} | {cp_str:>12} | {lp_str:>12} | {cc_str:>12} | {lc_str:>12} | ${core_pnl:>11.2f} | ${legacy_pnl:>11.2f} | ${delta:>+9.2f}{price_diff}")

        print("-" * 120)
        print(f"{'TOTAL':<10} | {' ':>12} | {' ':>12} | {' ':>12} | {' ':>12} | {' ':>12} | ${core_total_pnl:>11.2f} | ${legacy_total_pnl:>11.2f} | ${core_total_pnl - legacy_total_pnl:>+9.2f}")

        # Compare with actual snapshots
        print(f"\n--- Comparison with Actual Snapshots ---")

        core_snap = await core_conn.fetchrow(
            "SELECT daily_pnl FROM portfolio_snapshots WHERE portfolio_id = $1 AND snapshot_date = $2",
            DEMO_INDIVIDUAL_ID, CALC_DATE
        )
        legacy_snap = await legacy_conn.fetchrow(
            "SELECT daily_pnl FROM portfolio_snapshots WHERE portfolio_id = $1 AND snapshot_date = $2",
            DEMO_INDIVIDUAL_ID, CALC_DATE
        )

        print(f"Core snapshot daily_pnl:   ${Decimal(str(core_snap['daily_pnl'])):,.2f}")
        print(f"Legacy snapshot daily_pnl: ${Decimal(str(legacy_snap['daily_pnl'])):,.2f}")
        print(f"Snapshot delta:            ${Decimal(str(core_snap['daily_pnl'])) - Decimal(str(legacy_snap['daily_pnl'])):+,.2f}")

        print(f"\nManually calculated Core:   ${core_total_pnl:,.2f}")
        print(f"Manually calculated Legacy: ${legacy_total_pnl:,.2f}")
        print(f"Manual delta:               ${core_total_pnl - legacy_total_pnl:+,.2f}")

        if abs(core_total_pnl - Decimal(str(core_snap['daily_pnl']))) > 1:
            print(f"\n*** WARNING: Core manual calc differs from snapshot! ***")
        if abs(legacy_total_pnl - Decimal(str(legacy_snap['daily_pnl']))) > 1:
            print(f"\n*** WARNING: Legacy manual calc differs from snapshot! ***")

    finally:
        await core_conn.close()
        await legacy_conn.close()


asyncio.run(diagnose())
