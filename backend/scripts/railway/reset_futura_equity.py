#!/usr/bin/env python
"""
Reset Futura Portfolio Equity Balance

This script:
1. Resets equity_balance to the original $5,800,000
2. Optionally deletes all snapshots so batch can recalculate correctly

Run on Railway: python scripts/railway/reset_futura_equity.py
"""
import asyncio
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def get_db_url():
    """Get database URL, ensuring asyncpg driver."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Fallback to Railway Core DB for local execution
        url = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
        return url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


# Original equity balance when portfolio was uploaded
ORIGINAL_EQUITY = Decimal("5000000.00")
PORTFOLIO_NAME = "Futura Test Portfolio"


async def reset_futura_equity():
    """Reset Futura portfolio equity and snapshots."""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    print("=" * 80)
    print("FUTURA PORTFOLIO EQUITY RESET")
    print("=" * 80)

    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # 1. Find the portfolio
        print("\n[1] FINDING PORTFOLIO:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            SELECT id, name, equity_balance
            FROM portfolios
            WHERE name ILIKE '%futura%'
        """))
        row = result.fetchone()

        if not row:
            print("  [X] Futura portfolio not found")
            await engine.dispose()
            return

        portfolio_id, name, current_equity = row
        print(f"  Portfolio: {name}")
        print(f"  ID: {portfolio_id}")
        print(f"  Current equity_balance: ${current_equity:,.2f}")
        print(f"  Target equity_balance:  ${ORIGINAL_EQUITY:,.2f}")

        # 2. Show current snapshots
        print("\n[2] CURRENT SNAPSHOTS:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            SELECT snapshot_date, equity_balance, daily_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = '{portfolio_id}'
            ORDER BY snapshot_date
        """))
        snapshots = result.fetchall()
        print(f"  Found {len(snapshots)} snapshots")
        for snap_date, equity, pnl in snapshots:
            pnl_val = float(pnl) if pnl else 0
            print(f"    {snap_date}: equity=${equity:,.2f}, daily_pnl=${pnl_val:,.2f}")

        # 3. Delete snapshots
        print("\n[3] DELETING SNAPSHOTS:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            DELETE FROM portfolio_snapshots
            WHERE portfolio_id = '{portfolio_id}'
            RETURNING id
        """))
        deleted = result.fetchall()
        print(f"  [OK] Deleted {len(deleted)} snapshots")

        # 4. Reset equity_balance
        print("\n[4] RESETTING EQUITY BALANCE:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            UPDATE portfolios
            SET equity_balance = {ORIGINAL_EQUITY}
            WHERE id = '{portfolio_id}'
            RETURNING equity_balance
        """))
        updated_row = result.fetchone()
        if updated_row:
            print(f"  [OK] Set equity_balance = ${updated_row[0]:,.2f} (confirmed via RETURNING)")
        else:
            print(f"  [WARN] UPDATE executed but no row returned - may not have matched")

        # 5. Verify
        print("\n[5] VERIFICATION:")
        print("-" * 50)
        result = await conn.execute(text(f"""
            SELECT equity_balance FROM portfolios WHERE id = '{portfolio_id}'
        """))
        new_equity = result.scalar()
        print(f"  New equity_balance: ${new_equity:,.2f}")

        result = await conn.execute(text(f"""
            SELECT COUNT(*) FROM portfolio_snapshots WHERE portfolio_id = '{portfolio_id}'
        """))
        snapshot_count = result.scalar()
        print(f"  Remaining snapshots: {snapshot_count}")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("RESET COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Deploy the P&L calculator fix (already committed)")
    print("2. Trigger a batch run to recalculate snapshots correctly")
    print("   POST /api/v1/admin/batch/run")


if __name__ == "__main__":
    asyncio.run(reset_futura_equity())
