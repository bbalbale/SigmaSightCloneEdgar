"""
Compare Seed Data Between Core DB and Legacy DB

Investigates why equity_balance values differ between the two databases.
Shows the current seed file values vs actual database values.

Created: 2025-12-23
"""
import asyncio
import sys
import io
from datetime import date
from typing import Dict, List, Any
from decimal import Decimal

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

# Database connection strings
CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"

# Expected seed values from current seed file (seed_demo_portfolios.py)
EXPECTED_SEED_VALUES = {
    "Demo Individual Investor Portfolio": Decimal("485000.00"),
    "Demo High Net Worth Investor Portfolio": Decimal("2850000.00"),
    "Demo Hedge Fund Style Investor Portfolio": Decimal("3200000.00"),
    "Demo Family Office Public Growth": Decimal("1250000.00"),
    "Demo Family Office Private Opportunities": Decimal("950000.00"),
}


async def get_portfolios_with_details(conn) -> List[Dict]:
    """Get all portfolios with detailed information."""
    query = """
        SELECT
            p.id,
            p.name,
            p.equity_balance,
            p.created_at,
            p.updated_at,
            u.email as user_email,
            (SELECT COUNT(*) FROM positions WHERE portfolio_id = p.id) as position_count,
            (SELECT SUM(quantity * entry_price) FROM positions WHERE portfolio_id = p.id) as total_entry_value
        FROM portfolios p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.name
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def get_first_snapshot(conn, portfolio_id: str) -> Dict:
    """Get the first snapshot for a portfolio."""
    query = """
        SELECT
            snapshot_date,
            equity_balance,
            daily_pnl,
            cumulative_pnl
        FROM portfolio_snapshots
        WHERE portfolio_id = $1
        ORDER BY snapshot_date ASC
        LIMIT 1
    """
    row = await conn.fetchrow(query, portfolio_id)
    return dict(row) if row else {}


async def compare_seed_data():
    """Main comparison function."""
    print("=" * 120)
    print("SEED DATA COMPARISON: Core DB vs Legacy DB vs Expected Seed Values")
    print("=" * 120)

    # Connect to both databases
    print("\nConnecting to databases...")
    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)
    print("Connected.\n")

    try:
        # Get portfolios from both
        core_portfolios = await get_portfolios_with_details(core_conn)
        legacy_portfolios = await get_portfolios_with_details(legacy_conn)

        core_map = {p['name']: p for p in core_portfolios}
        legacy_map = {p['name']: p for p in legacy_portfolios}

        all_names = sorted(set(core_map.keys()) | set(legacy_map.keys()) | set(EXPECTED_SEED_VALUES.keys()))

        print("=" * 120)
        print("PORTFOLIO EQUITY BALANCE COMPARISON")
        print("=" * 120)
        print()

        # Header
        print(f"{'Portfolio Name':<45} | {'Expected':>14} | {'Core DB':>14} | {'Legacy DB':>14} | {'Core Match':>10} | {'Legacy Match':>12}")
        print("-" * 120)

        for name in all_names:
            expected = EXPECTED_SEED_VALUES.get(name, Decimal("0"))
            core_p = core_map.get(name, {})
            legacy_p = legacy_map.get(name, {})

            core_eq = Decimal(str(core_p.get('equity_balance', 0) or 0))
            legacy_eq = Decimal(str(legacy_p.get('equity_balance', 0) or 0))

            core_match = "YES" if abs(core_eq - expected) < 1 else "NO"
            legacy_match = "YES" if abs(legacy_eq - expected) < 1 else "NO"

            if not core_p:
                core_eq_str = "NOT FOUND"
            else:
                core_eq_str = f"${core_eq:,.2f}"

            if not legacy_p:
                legacy_eq_str = "NOT FOUND"
            else:
                legacy_eq_str = f"${legacy_eq:,.2f}"

            print(f"{name[:44]:<45} | ${expected:>13,.2f} | {core_eq_str:>14} | {legacy_eq_str:>14} | {core_match:>10} | {legacy_match:>12}")

        # Detailed comparison for mismatched portfolios
        print()
        print("=" * 120)
        print("DETAILED ANALYSIS OF MISMATCHED PORTFOLIOS")
        print("=" * 120)

        for name in all_names:
            expected = EXPECTED_SEED_VALUES.get(name, Decimal("0"))
            core_p = core_map.get(name, {})
            legacy_p = legacy_map.get(name, {})

            if not core_p or not legacy_p:
                continue

            core_eq = Decimal(str(core_p.get('equity_balance', 0) or 0))
            legacy_eq = Decimal(str(legacy_p.get('equity_balance', 0) or 0))

            # Only show if there's a mismatch
            if abs(core_eq - legacy_eq) < 1:
                continue

            portfolio_id = str(core_p['id'])

            print(f"\n{'='*120}")
            print(f"PORTFOLIO: {name}")
            print(f"ID: {portfolio_id}")
            print(f"{'='*120}")

            # Basic comparison
            print(f"\n{'Field':<25} {'Expected':>18} {'Core DB':>18} {'Legacy DB':>18} {'Delta (C-L)':>15}")
            print(f"{'-'*25} {'-'*18} {'-'*18} {'-'*18} {'-'*15}")

            print(f"{'equity_balance':<25} ${expected:>17,.2f} ${core_eq:>17,.2f} ${legacy_eq:>17,.2f} ${core_eq - legacy_eq:>+14,.2f}")

            # Entry value comparison
            core_entry = Decimal(str(core_p.get('total_entry_value', 0) or 0))
            legacy_entry = Decimal(str(legacy_p.get('total_entry_value', 0) or 0))
            print(f"{'total_entry_value':<25} {'---':>18} ${core_entry:>17,.2f} ${legacy_entry:>17,.2f} ${core_entry - legacy_entry:>+14,.2f}")

            # Position count
            core_pos = core_p.get('position_count', 0)
            legacy_pos = legacy_p.get('position_count', 0)
            print(f"{'position_count':<25} {'---':>18} {core_pos:>18} {legacy_pos:>18} {core_pos - legacy_pos:>+15}")

            # Timestamps
            core_created = str(core_p.get('created_at', 'N/A'))[:19]
            legacy_created = str(legacy_p.get('created_at', 'N/A'))[:19]
            core_updated = str(core_p.get('updated_at', 'N/A'))[:19]
            legacy_updated = str(legacy_p.get('updated_at', 'N/A'))[:19]
            print(f"\n{'created_at':<25} {'---':>18} {core_created:>18} {legacy_created:>18}")
            print(f"{'updated_at':<25} {'---':>18} {core_updated:>18} {legacy_updated:>18}")

            # First snapshot comparison
            print(f"\n--- First Snapshot ---")
            core_snap = await get_first_snapshot(core_conn, portfolio_id)

            # Get legacy portfolio ID (might be different)
            legacy_id = str(legacy_p['id'])
            legacy_snap = await get_first_snapshot(legacy_conn, legacy_id)

            if core_snap or legacy_snap:
                core_snap_date = str(core_snap.get('snapshot_date', 'N/A')) if core_snap else 'N/A'
                legacy_snap_date = str(legacy_snap.get('snapshot_date', 'N/A')) if legacy_snap else 'N/A'
                core_snap_eq = Decimal(str(core_snap.get('equity_balance', 0) or 0)) if core_snap else Decimal("0")
                legacy_snap_eq = Decimal(str(legacy_snap.get('equity_balance', 0) or 0)) if legacy_snap else Decimal("0")

                print(f"{'First Snapshot Date':<25} {'---':>18} {core_snap_date:>18} {legacy_snap_date:>18}")
                print(f"{'Snapshot equity_balance':<25} {'---':>18} ${core_snap_eq:>17,.2f} ${legacy_snap_eq:>17,.2f} ${core_snap_eq - legacy_snap_eq:>+14,.2f}")

        # Summary and analysis
        print("\n" + "=" * 120)
        print("ANALYSIS SUMMARY")
        print("=" * 120)

        print("""
Key Findings:
1. The EXPECTED seed values shown above are from the CURRENT seed_demo_portfolios.py file
2. The Core DB should match these expected values (it was reseeded with the corrected data)
3. The Legacy DB may have OLDER seed data from before corrections were made

Root Cause Investigation:
- If Core DB matches Expected but Legacy DB doesn't:
  The Legacy DB was seeded with an OLDER version of the seed file
  that had different equity_balance values.

- If neither matches Expected:
  Both databases were seeded with older versions, or the seed file
  was modified after the databases were seeded.

Resolution Options:
1. Reseed the Legacy DB with the current seed file (if Legacy should match Core)
2. Accept the difference (if Legacy is intentionally different for comparison)
3. Manually update equity_balance values in the database that needs correction
""")

    finally:
        await core_conn.close()
        await legacy_conn.close()
        print("\nDatabase connections closed.")


if __name__ == '__main__':
    asyncio.run(compare_seed_data())
