"""
Compare Equity Snapshots Between Core DB and Legacy DB

Finds where the equity balance divergence begins by comparing
portfolio_snapshots day by day between the two databases.

Created: 2025-12-23
"""
import asyncio
import sys
import io
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

# Database connection strings
CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"

# Portfolios to skip (known issues)
SKIP_PORTFOLIOS = [
    'b1b4b838-1b42-5029-b06e-f5d6256196df',  # Futura - known incorrect starting equity in legacy
]


async def get_portfolios(conn) -> List[Dict]:
    """Get all portfolios."""
    query = """
        SELECT id, name, equity_balance
        FROM portfolios
        ORDER BY name
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def get_snapshots(conn, portfolio_id: str, start_date: Optional[date] = None) -> List[Dict]:
    """Get snapshots for a portfolio."""
    query = """
        SELECT
            snapshot_date,
            equity_balance,
            daily_pnl,
            cumulative_pnl,
            gross_exposure,
            net_exposure,
            long_value,
            short_value,
            total_value
        FROM portfolio_snapshots
        WHERE portfolio_id = $1
    """

    if start_date:
        query += " AND snapshot_date >= $2"
        query += " ORDER BY snapshot_date"
        rows = await conn.fetch(query, portfolio_id, start_date)
    else:
        query += " ORDER BY snapshot_date"
        rows = await conn.fetch(query, portfolio_id)

    return [dict(row) for row in rows]


async def compare_databases():
    """Main comparison function."""
    print("=" * 120)
    print("EQUITY SNAPSHOT COMPARISON: Core DB vs Legacy DB")
    print("=" * 120)

    # Connect to both databases
    print("\nConnecting to databases...")
    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)
    print("Connected.\n")

    try:
        # Get portfolios from both
        core_portfolios = await get_portfolios(core_conn)
        legacy_portfolios = await get_portfolios(legacy_conn)

        core_map = {str(p['id']): p for p in core_portfolios}
        legacy_map = {str(p['id']): p for p in legacy_portfolios}

        # Find common portfolios
        common_ids = set(core_map.keys()) & set(legacy_map.keys())

        for portfolio_id in sorted(common_ids):
            if portfolio_id in SKIP_PORTFOLIOS:
                print(f"\n[SKIPPED] {core_map[portfolio_id]['name']} - known starting equity issue")
                continue

            core_p = core_map[portfolio_id]
            legacy_p = legacy_map[portfolio_id]

            # Check if equity balances match
            core_equity = float(core_p.get('equity_balance', 0) or 0)
            legacy_equity = float(legacy_p.get('equity_balance', 0) or 0)

            if abs(core_equity - legacy_equity) < 1:
                # Skip portfolios that match
                continue

            print(f"\n{'='*120}")
            print(f"PORTFOLIO: {core_p['name']}")
            print(f"ID: {portfolio_id}")
            print(f"Current Equity - Core: ${core_equity:,.2f} | Legacy: ${legacy_equity:,.2f} | Delta: ${core_equity - legacy_equity:+,.2f}")
            print(f"{'='*120}")

            # Get snapshots from both
            core_snapshots = await get_snapshots(core_conn, portfolio_id)
            legacy_snapshots = await get_snapshots(legacy_conn, portfolio_id)

            if not core_snapshots and not legacy_snapshots:
                print("  No snapshots in either database.")
                continue

            # Create lookup by date
            core_snap_map = {s['snapshot_date']: s for s in core_snapshots}
            legacy_snap_map = {s['snapshot_date']: s for s in legacy_snapshots}

            all_dates = sorted(set(core_snap_map.keys()) | set(legacy_snap_map.keys()))

            print(f"\nSnapshots: Core={len(core_snapshots)}, Legacy={len(legacy_snapshots)}, Total Dates={len(all_dates)}")
            print()

            # Header
            print(f"{'Date':<12} | {'Core Equity':>14} | {'Legacy Equity':>14} | {'Delta':>12} | {'Core PnL':>12} | {'Legacy PnL':>12} | {'PnL Delta':>10} | {'Status':<15}")
            print("-" * 120)

            # Track where divergence starts
            divergence_started = False
            first_divergence_date = None
            cumulative_pnl_diff = 0

            for snap_date in all_dates:
                core_snap = core_snap_map.get(snap_date, {})
                legacy_snap = legacy_snap_map.get(snap_date, {})

                core_eq = float(core_snap.get('equity_balance', 0) or 0)
                legacy_eq = float(legacy_snap.get('equity_balance', 0) or 0)
                eq_delta = core_eq - legacy_eq

                core_pnl = float(core_snap.get('daily_pnl', 0) or 0)
                legacy_pnl = float(legacy_snap.get('daily_pnl', 0) or 0)
                pnl_delta = core_pnl - legacy_pnl

                cumulative_pnl_diff += pnl_delta

                # Determine status
                if not core_snap:
                    status = "MISSING CORE"
                elif not legacy_snap:
                    status = "MISSING LEGACY"
                elif abs(eq_delta) < 1:
                    status = "MATCH"
                else:
                    if not divergence_started:
                        divergence_started = True
                        first_divergence_date = snap_date
                        status = ">>> DIVERGE <<<"
                    else:
                        status = "DIVERGED"

                # Format output
                core_eq_str = f"${core_eq:,.2f}" if core_snap else "---"
                legacy_eq_str = f"${legacy_eq:,.2f}" if legacy_snap else "---"
                eq_delta_str = f"${eq_delta:+,.2f}" if (core_snap and legacy_snap) else "---"
                core_pnl_str = f"${core_pnl:+,.2f}" if core_snap else "---"
                legacy_pnl_str = f"${legacy_pnl:+,.2f}" if legacy_snap else "---"
                pnl_delta_str = f"${pnl_delta:+,.2f}" if (core_snap and legacy_snap) else "---"

                print(f"{snap_date} | {core_eq_str:>14} | {legacy_eq_str:>14} | {eq_delta_str:>12} | {core_pnl_str:>12} | {legacy_pnl_str:>12} | {pnl_delta_str:>10} | {status:<15}")

            # Summary
            print()
            if first_divergence_date:
                print(f"*** DIVERGENCE STARTED ON: {first_divergence_date} ***")
                print(f"*** CUMULATIVE P&L DIFFERENCE: ${cumulative_pnl_diff:+,.2f} ***")

                # Show details of the divergence date
                print(f"\n--- Details for {first_divergence_date} ---")
                core_snap = core_snap_map.get(first_divergence_date, {})
                legacy_snap = legacy_snap_map.get(first_divergence_date, {})

                fields = ['equity_balance', 'daily_pnl', 'cumulative_pnl', 'gross_exposure', 'net_exposure', 'long_value', 'short_value', 'total_value']
                print(f"{'Field':<20} {'Core':>18} {'Legacy':>18} {'Delta':>15}")
                print("-" * 75)
                for field in fields:
                    core_val = float(core_snap.get(field, 0) or 0)
                    legacy_val = float(legacy_snap.get(field, 0) or 0)
                    delta = core_val - legacy_val
                    print(f"{field:<20} {core_val:>18,.2f} {legacy_val:>18,.2f} {delta:>+15,.2f}")
            else:
                print("No divergence found - snapshots match!")

        # Overall summary
        print("\n" + "=" * 120)
        print("ANALYSIS COMPLETE")
        print("=" * 120)

    finally:
        await core_conn.close()
        await legacy_conn.close()
        print("\nDatabase connections closed.")


if __name__ == '__main__':
    asyncio.run(compare_databases())
