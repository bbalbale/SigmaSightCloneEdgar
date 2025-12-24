"""
Find the Exact Divergence Point for Demo Individual Portfolio

Since the first snapshot is identical ($485,000), we need to find where
the P&L calculations started to diverge.

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

# Demo Individual Investor Portfolio ID
DEMO_INDIVIDUAL_ID = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"


async def get_snapshots(conn, portfolio_id: str):
    """Get all snapshots ordered by date."""
    query = """
        SELECT
            snapshot_date,
            equity_balance,
            daily_pnl,
            cumulative_pnl
        FROM portfolio_snapshots
        WHERE portfolio_id = $1
        ORDER BY snapshot_date
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]


async def find_divergence():
    print("=" * 140)
    print("FINDING DIVERGENCE POINT: Demo Individual Investor Portfolio")
    print("=" * 140)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        core_snaps = await get_snapshots(core_conn, DEMO_INDIVIDUAL_ID)
        legacy_snaps = await get_snapshots(legacy_conn, DEMO_INDIVIDUAL_ID)

        core_map = {s['snapshot_date']: s for s in core_snaps}
        legacy_map = {s['snapshot_date']: s for s in legacy_snaps}

        all_dates = sorted(set(core_map.keys()) | set(legacy_map.keys()))

        print(f"\nTotal snapshots: Core={len(core_snaps)}, Legacy={len(legacy_snaps)}")
        print()

        # Header
        print(f"{'Date':<12} | {'Core Equity':>15} | {'Legacy Equity':>15} | {'Eq Delta':>12} | {'Core PnL':>12} | {'Legacy PnL':>12} | {'PnL Delta':>10} | {'Status':<20}")
        print("-" * 140)

        diverged = False
        first_divergence = None

        for snap_date in all_dates[:50]:  # First 50 days
            core = core_map.get(snap_date, {})
            legacy = legacy_map.get(snap_date, {})

            core_eq = Decimal(str(core.get('equity_balance', 0) or 0))
            legacy_eq = Decimal(str(legacy.get('equity_balance', 0) or 0))
            eq_delta = core_eq - legacy_eq

            core_pnl = Decimal(str(core.get('daily_pnl', 0) or 0))
            legacy_pnl = Decimal(str(legacy.get('daily_pnl', 0) or 0))
            pnl_delta = core_pnl - legacy_pnl

            # Determine status
            if not core:
                status = "MISSING CORE"
            elif not legacy:
                status = "MISSING LEGACY"
            elif abs(eq_delta) < 1:
                status = "MATCH"
            else:
                if not diverged:
                    diverged = True
                    first_divergence = snap_date
                    status = ">>> FIRST DIVERGENCE <<<"
                else:
                    status = "DIVERGED"

            core_eq_str = f"${core_eq:,.2f}" if core else "---"
            legacy_eq_str = f"${legacy_eq:,.2f}" if legacy else "---"
            eq_delta_str = f"${eq_delta:+,.2f}" if (core and legacy) else "---"
            core_pnl_str = f"${core_pnl:+,.2f}" if core else "---"
            legacy_pnl_str = f"${legacy_pnl:+,.2f}" if legacy else "---"
            pnl_delta_str = f"${pnl_delta:+,.2f}" if (core and legacy) else "---"

            print(f"{snap_date} | {core_eq_str:>15} | {legacy_eq_str:>15} | {eq_delta_str:>12} | {core_pnl_str:>12} | {legacy_pnl_str:>12} | {pnl_delta_str:>10} | {status:<20}")

        if first_divergence:
            print()
            print(f"*** FIRST DIVERGENCE: {first_divergence} ***")

            # Get details for day before and day of divergence
            idx = all_dates.index(first_divergence)
            if idx > 0:
                prev_date = all_dates[idx - 1]
                print(f"\n--- Day BEFORE divergence: {prev_date} ---")
                core = core_map.get(prev_date, {})
                legacy = legacy_map.get(prev_date, {})
                print(f"Core:   equity=${Decimal(str(core.get('equity_balance', 0))):.2f}, daily_pnl=${Decimal(str(core.get('daily_pnl', 0))):.2f}")
                print(f"Legacy: equity=${Decimal(str(legacy.get('equity_balance', 0))):.2f}, daily_pnl=${Decimal(str(legacy.get('daily_pnl', 0))):.2f}")

            print(f"\n--- Day OF divergence: {first_divergence} ---")
            core = core_map.get(first_divergence, {})
            legacy = legacy_map.get(first_divergence, {})
            print(f"Core:   equity=${Decimal(str(core.get('equity_balance', 0))):.2f}, daily_pnl=${Decimal(str(core.get('daily_pnl', 0))):.2f}")
            print(f"Legacy: equity=${Decimal(str(legacy.get('equity_balance', 0))):.2f}, daily_pnl=${Decimal(str(legacy.get('daily_pnl', 0))):.2f}")
            print(f"Difference: daily_pnl delta = ${Decimal(str(core.get('daily_pnl', 0))) - Decimal(str(legacy.get('daily_pnl', 0))):.2f}")

    finally:
        await core_conn.close()
        await legacy_conn.close()


if __name__ == '__main__':
    asyncio.run(find_divergence())
