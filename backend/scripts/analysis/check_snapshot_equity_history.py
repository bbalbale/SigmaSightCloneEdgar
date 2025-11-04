"""Check snapshot equity rollforward history"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from uuid import UUID

async def check_snapshots():
    indiv_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == indiv_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(10)
        )
        snapshots = result.scalars().all()

        print("=" * 120)
        print("INDIVIDUAL INVESTOR PORTFOLIO - SNAPSHOT EQUITY HISTORY (Last 10)")
        print("=" * 120)
        print()
        print(f"{'Date':<12} {'Equity':>15} {'Long Val':>15} {'Daily P&L':>15} {'Cumulative P&L':>15} {'Equity Change':>15}")
        print("-" * 120)

        prev_equity = None
        for snap in reversed(snapshots):
            equity = float(snap.equity_balance) if snap.equity_balance else 0
            long_val = float(snap.long_value) if snap.long_value else 0
            daily_pnl = float(snap.daily_pnl) if snap.daily_pnl else 0
            cumul_pnl = float(snap.cumulative_pnl) if snap.cumulative_pnl else 0

            equity_change = (equity - prev_equity) if prev_equity is not None else 0

            print(f"{snap.snapshot_date} {equity:>15,.2f} {long_val:>15,.2f} {daily_pnl:>15,.2f} {cumul_pnl:>15,.2f} {equity_change:>15,.2f}")

            prev_equity = equity

        print()
        print("=" * 120)
        print("VALIDATION:")
        print()

        latest = snapshots[0]
        equity = float(latest.equity_balance) if latest.equity_balance else 0
        long_val = float(latest.long_value) if latest.long_value else 0
        cumul_pnl = float(latest.cumulative_pnl) if latest.cumulative_pnl else 0

        print(f"  Latest Snapshot ({latest.snapshot_date}):")
        print(f"    Equity Balance:       ${equity:,.2f}")
        print(f"    Long Value:           ${long_val:,.2f}")
        print(f"    Cumulative P&L:       ${cumul_pnl:,.2f}")
        print()
        print(f"  Current Position Data:")
        print(f"    Entry Values:         $484,860.00")
        print(f"    Market Value:         $465,225.45")
        print(f"    Position P&L:         $-19,634.55")
        print()
        print(f"  Expected Equity:        $484,860.00 (entry) + $-19,634.55 (P&L) = $465,225.45")
        print(f"  Actual Equity:          ${equity:,.2f}")
        print(f"  Difference:             ${equity - 465225.45:,.2f} ❌")
        print()
        print("=" * 120)

asyncio.run(check_snapshots())
