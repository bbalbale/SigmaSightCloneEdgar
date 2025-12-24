"""Check when snapshots were created in each database."""
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


async def get_snapshot_timestamps(conn, portfolio_id: str):
    """Get snapshot creation timestamps."""
    query = """
        SELECT
            snapshot_date,
            created_at,
            equity_balance,
            daily_pnl
        FROM portfolio_snapshots
        WHERE portfolio_id = $1
        ORDER BY snapshot_date
        LIMIT 10
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]


async def main():
    print("=" * 120)
    print("SNAPSHOT CREATION TIMESTAMPS: Core DB vs Legacy DB")
    print("=" * 120)

    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)

    try:
        core_snaps = await get_snapshot_timestamps(core_conn, DEMO_INDIVIDUAL_ID)
        legacy_snaps = await get_snapshot_timestamps(legacy_conn, DEMO_INDIVIDUAL_ID)

        print(f"\nDemo Individual Investor Portfolio ({DEMO_INDIVIDUAL_ID})")
        print()

        print("CORE DB snapshots:")
        print(f"{'Date':<12} {'Created At':<25} {'Equity':>15} {'Daily PnL':>12}")
        print("-" * 70)
        for snap in core_snaps[:5]:
            created = str(snap.get('created_at', 'N/A'))[:24]
            eq = Decimal(str(snap.get('equity_balance', 0) or 0))
            pnl = Decimal(str(snap.get('daily_pnl', 0) or 0))
            print(f"{snap['snapshot_date']} {created:<25} ${eq:>14,.2f} ${pnl:>+11,.2f}")

        print()
        print("LEGACY DB snapshots:")
        print(f"{'Date':<12} {'Created At':<25} {'Equity':>15} {'Daily PnL':>12}")
        print("-" * 70)
        for snap in legacy_snaps[:5]:
            created = str(snap.get('created_at', 'N/A'))[:24]
            eq = Decimal(str(snap.get('equity_balance', 0) or 0))
            pnl = Decimal(str(snap.get('daily_pnl', 0) or 0))
            print(f"{snap['snapshot_date']} {created:<25} ${eq:>14,.2f} ${pnl:>+11,.2f}")

        print()
        print("ANALYSIS:")
        if core_snaps and legacy_snaps:
            core_created = core_snaps[0].get('created_at')
            legacy_created = legacy_snaps[0].get('created_at')
            print(f"Core DB first snapshot created: {core_created}")
            print(f"Legacy DB first snapshot created: {legacy_created}")

            if core_created != legacy_created:
                print(f"\n*** SNAPSHOTS WERE CREATED AT DIFFERENT TIMES ***")
                print("This explains the P&L differences - market data may have")
                print("been different when each batch was run.")

    finally:
        await core_conn.close()
        await legacy_conn.close()


asyncio.run(main())
