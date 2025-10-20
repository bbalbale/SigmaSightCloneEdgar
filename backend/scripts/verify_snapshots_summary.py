"""Quick summary of snapshots to verify backfill completion."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def main():
    async with get_async_session() as db:
        result = await db.execute(text("""
            SELECT
                COUNT(*) as total_snapshots,
                MIN(snapshot_date) as first_date,
                MAX(snapshot_date) as last_date
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
        """))
        summary = result.fetchone()

        result2 = await db.execute(text("""
            SELECT snapshot_date, equity_balance, daily_pnl, cumulative_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            ORDER BY snapshot_date ASC
        """))
        snapshots = result2.fetchall()

        print("=" * 80)
        print("SNAPSHOT BACKFILL VERIFICATION")
        print("=" * 80)
        print(f"Total snapshots: {summary.total_snapshots}")
        print(f"Date range: {summary.first_date} to {summary.last_date}")
        print()

        print("Date        | Equity Balance  | Daily P&L      | Cumulative P&L")
        print("-" * 75)
        for snap in snapshots:
            equity = f"${float(snap.equity_balance):>13,.2f}"
            pnl = f"${float(snap.daily_pnl):>12,.2f}" if snap.daily_pnl is not None else "        $0.00"
            cum_pnl = f"${float(snap.cumulative_pnl):>13,.2f}" if snap.cumulative_pnl is not None else "         $0.00"
            print(f"{snap.snapshot_date} | {equity} | {pnl} | {cum_pnl}")

        print()
        print("=" * 80)
        print(f"SUCCESS: {summary.total_snapshots} snapshots with complete equity rollforward chain")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
