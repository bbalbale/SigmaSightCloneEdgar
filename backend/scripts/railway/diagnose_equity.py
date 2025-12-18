#!/usr/bin/env python
"""
Equity Balance Diagnostic Script

Traces the equity balance history for a specific portfolio to diagnose
double-counting issues in the P&L calculator.

Run on Railway: python scripts/railway/diagnose_equity.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def get_db_url():
    """Get database URL, ensuring asyncpg driver."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return ""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async def run_equity_diagnostic():
    """Trace equity balance history."""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    print("=" * 80)
    print("EQUITY BALANCE DIAGNOSTIC REPORT")
    print("=" * 80)

    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # 1. Find Futura portfolio
        print("\n🔍 FINDING FUTURA PORTFOLIO:")
        print("-" * 50)
        result = await conn.execute(text("""
            SELECT id, name, equity_balance, created_at, updated_at
            FROM portfolios
            WHERE name ILIKE '%futura%'
        """))
        portfolios = result.fetchall()

        if not portfolios:
            print("  ❌ No Futura portfolio found")
            await engine.dispose()
            return

        for row in portfolios:
            portfolio_id, name, equity_balance, created_at, updated_at = row
            print(f"  Portfolio: {name}")
            print(f"  ID: {portfolio_id}")
            print(f"  Current equity_balance: ${equity_balance:,.2f}")
            print(f"  Created: {created_at}")
            print(f"  Updated: {updated_at}")

        portfolio_id = portfolios[0][0]

        # 2. Check all snapshots for this portfolio
        print("\n📸 SNAPSHOT HISTORY (chronological):")
        print("-" * 50)
        result = await conn.execute(text(f"""
            SELECT
                snapshot_date,
                equity_balance,
                daily_pnl,
                cumulative_pnl,
                daily_return,
                is_complete,
                created_at
            FROM portfolio_snapshots
            WHERE portfolio_id = '{portfolio_id}'
            ORDER BY snapshot_date ASC, created_at ASC
        """))
        snapshots = result.fetchall()

        if not snapshots:
            print("  No snapshots found")
        else:
            print(f"  Found {len(snapshots)} snapshots:")
            print()
            print(f"  {'Date':<12} {'Equity':<15} {'Daily P&L':<15} {'Cumulative':<15} {'Complete'}")
            print(f"  {'-'*12} {'-'*15} {'-'*15} {'-'*15} {'-'*8}")

            prev_equity = None
            for row in snapshots:
                snap_date, equity, daily_pnl, cumulative, daily_ret, is_complete, created = row
                equity_str = f"${equity:,.2f}" if equity else "NULL"
                daily_str = f"${daily_pnl:,.2f}" if daily_pnl else "NULL"
                cumul_str = f"${cumulative:,.2f}" if cumulative else "NULL"

                # Flag suspicious jumps
                flag = ""
                if prev_equity and equity:
                    jump = float(equity) - float(prev_equity)
                    if abs(jump) > 100000:  # Flag jumps > $100K
                        flag = f" ⚠️ JUMP: ${jump:+,.0f}"

                print(f"  {snap_date}  {equity_str:<15} {daily_str:<15} {cumul_str:<15} {is_complete}{flag}")
                prev_equity = equity

        # 3. Check positions and their unrealized P&L
        print("\n💰 POSITION ANALYSIS:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            SELECT
                symbol,
                quantity,
                entry_price,
                last_price,
                market_value,
                (COALESCE(last_price, 0) - COALESCE(entry_price, 0)) * quantity as unrealized_pnl,
                entry_date
            FROM positions
            WHERE portfolio_id = '{portfolio_id}'
              AND deleted_at IS NULL
            ORDER BY symbol
        """))
        positions = result.fetchall()

        total_entry_value = 0
        total_market_value = 0
        total_unrealized = 0

        print(f"  {'Symbol':<8} {'Qty':<10} {'Entry $':<12} {'Last $':<12} {'Unrealized P&L'}")
        print(f"  {'-'*8} {'-'*10} {'-'*12} {'-'*12} {'-'*15}")

        for row in positions:
            symbol, qty, entry, last, mkt_val, unrealized, entry_date = row
            entry_val = float(entry or 0) * float(qty or 0)
            total_entry_value += entry_val
            total_market_value += float(mkt_val or 0)
            total_unrealized += float(unrealized or 0)

            unrealized_str = f"${unrealized:+,.2f}" if unrealized else "N/A"
            entry_str = f"${entry:,.2f}" if entry else "N/A"
            last_str = f"${last:,.2f}" if last else "N/A"

            print(f"  {symbol:<8} {qty:<10.0f} {entry_str:<12} {last_str:<12} {unrealized_str}")

        print(f"\n  TOTALS:")
        print(f"    Total Entry Value:    ${total_entry_value:,.2f}")
        print(f"    Total Market Value:   ${total_market_value:,.2f}")
        print(f"    Total Unrealized P&L: ${total_unrealized:+,.2f}")

        # 4. Compare what equity SHOULD be
        print("\n🔢 EQUITY CALCULATION CHECK:")
        print("-" * 50)
        current_equity = float(portfolios[0][2])

        # If positions were bought with starting capital, equity should be:
        # Starting equity + cumulative realized P&L + capital flows
        # (Unrealized P&L is reflected in position market values, NOT in equity balance)

        print(f"  Current equity_balance:      ${current_equity:,.2f}")
        print(f"  Total position entry value:  ${total_entry_value:,.2f}")
        print(f"  Total unrealized P&L:        ${total_unrealized:+,.2f}")
        print()

        # Check if equity = entry_value + unrealized (which would be wrong)
        wrong_calc = total_entry_value + total_unrealized
        if abs(current_equity - wrong_calc) < 10000:  # Within $10K
            print(f"  ⚠️ ISSUE DETECTED: equity_balance ≈ entry_value + unrealized P&L")
            print(f"     This suggests unrealized P&L was incorrectly added to equity!")
            print(f"     Expected (wrong): ${wrong_calc:,.2f}")
            print(f"     Actual:           ${current_equity:,.2f}")

        # What should equity be? The original upload value
        print(f"\n  If portfolio was uploaded with $5.8M equity:")
        print(f"    Expected equity_balance: $5,800,000.00")
        print(f"    Actual equity_balance:   ${current_equity:,.2f}")
        print(f"    Difference:              ${current_equity - 5800000:+,.2f}")

        # 5. Check batch_run_tracking for clues
        print("\n📋 RECENT BATCH RUNS:")
        print("-" * 50)
        result = await conn.execute(text("""
            SELECT
                run_id,
                status,
                started_at,
                completed_at,
                portfolios_processed,
                error_message
            FROM batch_run_tracking
            ORDER BY started_at DESC
            LIMIT 10
        """))
        runs = result.fetchall()

        for row in runs:
            run_id, status, started, completed, processed, error = row
            print(f"  {started}: {status} - {processed} portfolios")
            if error:
                print(f"    Error: {error[:50]}...")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_equity_diagnostic())
