"""
Focused diagnostic on equity balance reset issue

The problem: Equity balance was growing properly, but then reset to initial value
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.utils.trading_calendar import trading_calendar


async def diagnose():
    async with get_async_session() as db:
        print("=" * 80)
        print("EQUITY RESET DIAGNOSTIC")
        print("=" * 80)
        print()

        # Get demo individual portfolio
        portfolio_query = select(Portfolio).where(
            Portfolio.name.like("%Individual%")
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print("Portfolio not found!")
            return

        print(f"Portfolio: {portfolio.name}")
        print(f"Initial Equity Balance: ${portfolio.equity_balance:,.2f}")
        print()

        # Get all recent snapshots
        snapshots_query = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(15)
        )
        snapshots_result = await db.execute(snapshots_query)
        snapshots = list(snapshots_result.scalars().all())
        snapshots.reverse()  # Show oldest first

        print("SNAPSHOT TIMELINE (oldest to newest):")
        print("=" * 100)
        print(f"{'Date':<12} {'Equity':<18} {'Daily P&L':<15} {'Prev Equity':<18} {'Trading Day':<12}")
        print("=" * 100)

        for i, snapshot in enumerate(snapshots):
            equity = f"${snapshot.equity_balance:,.2f}" if snapshot.equity_balance else "NULL"
            pnl = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl else "NULL"

            # Calculate what previous equity should have been
            if i > 0:
                prev_snapshot = snapshots[i-1]
                prev_equity = f"${prev_snapshot.equity_balance:,.2f}" if prev_snapshot.equity_balance else "NULL"
            else:
                prev_equity = f"${portfolio.equity_balance:,.2f} (initial)"

            is_trading_day = trading_calendar.is_trading_day(snapshot.snapshot_date)
            trading_status = "YES" if is_trading_day else "NO"

            print(f"{snapshot.snapshot_date} {equity:<18} {pnl:<15} {prev_equity:<18} {trading_status:<12}")

            # Check for reset
            if snapshot.equity_balance == portfolio.equity_balance and i > 0:
                print(f"  ⚠️  RESET DETECTED: Equity went back to initial value!")

                # Check previous snapshot
                prev_date = trading_calendar.get_previous_trading_day(snapshot.snapshot_date)
                print(f"  Previous trading day should be: {prev_date}")

                prev_snap_exists = any(s.snapshot_date == prev_date for s in snapshots)
                if prev_snap_exists:
                    print(f"  ✅ Previous snapshot exists for {prev_date}")
                else:
                    print(f"  ❌ NO SNAPSHOT for previous trading day {prev_date}")
                    print(f"  This is why equity reset to initial value!")

        print("=" * 100)
        print()

        # Check for missing snapshots
        print("TRADING DAY GAP ANALYSIS:")
        print("=" * 80)

        if len(snapshots) >= 2:
            for i in range(1, len(snapshots)):
                current_date = snapshots[i].snapshot_date
                prev_snapshot_date = snapshots[i-1].snapshot_date

                # Get all trading days between
                days_between = []
                check_date = prev_snapshot_date + timedelta(days=1)
                while check_date < current_date:
                    if trading_calendar.is_trading_day(check_date):
                        days_between.append(check_date)
                    check_date += timedelta(days=1)

                if days_between:
                    print(f"\n⚠️  Gap detected between {prev_snapshot_date} and {current_date}:")
                    print(f"   Missing snapshots for trading days: {', '.join(str(d) for d in days_between)}")

                    # Check if equity reset occurred after this gap
                    if snapshots[i].equity_balance == portfolio.equity_balance:
                        print(f"   ❌ THIS GAP CAUSED THE EQUITY RESET!")

        print()
        print("=" * 80)
        print("ROOT CAUSE ANALYSIS:")
        print("=" * 80)
        print("""
When pnl_calculator runs:
1. It looks for the previous trading day's snapshot
2. If found: new_equity = prev_snapshot.equity_balance + daily_pnl ✅
3. If NOT found: new_equity = portfolio.equity_balance + daily_pnl ❌ (resets to initial)

Solution: Ensure snapshots are created for ALL trading days, or fix the
          fallback logic to find the most recent snapshot instead of
          resetting to initial equity.
        """)


if __name__ == "__main__":
    asyncio.run(diagnose())
