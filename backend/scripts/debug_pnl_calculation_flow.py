"""
Debug script to trace the P&L calculation flow during snapshot creation.
This will help identify why daily_pnl values are NULL.
"""
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from app.utils.trading_calendar import trading_calendar


async def debug_pnl_calculation_flow():
    """Debug the P&L calculation flow to find why daily_pnl is NULL"""
    async with get_async_session() as db:
        print("\n" + "="*80)
        print("P&L CALCULATION FLOW DEBUG")
        print("="*80)

        # Get all portfolios
        portfolio_query = select(Portfolio)
        portfolio_result = await db.execute(portfolio_query)
        portfolios = portfolio_result.scalars().all()

        for portfolio in portfolios:
            print(f"\n{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"Portfolio ID: {portfolio.id}")
            print(f"{'='*80}")

            # Get all snapshots for this portfolio, ordered by date
            snapshot_query = (
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.asc())
            )
            snapshot_result = await db.execute(snapshot_query)
            snapshots = snapshot_result.scalars().all()

            if not snapshots:
                print("  No snapshots found")
                continue

            print(f"\nFound {len(snapshots)} snapshots. Analyzing P&L calculation logic:\n")

            # For each snapshot, simulate the P&L calculation
            for i, snapshot in enumerate(snapshots):
                calc_date = snapshot.snapshot_date
                print(f"\nSnapshot #{i+1}: {calc_date}")
                print(f"  Current total_value: ${snapshot.total_value:,.2f}")
                print(f"  Current daily_pnl: {f'${snapshot.daily_pnl:,.2f}' if snapshot.daily_pnl is not None else 'NULL'}")
                print(f"  Current cumulative_pnl: {f'${snapshot.cumulative_pnl:,.2f}' if snapshot.cumulative_pnl is not None else 'NULL'}")

                # Check if it's a trading day
                is_trading_day = trading_calendar.is_trading_day(calc_date)
                print(f"  Is trading day: {is_trading_day}")

                if not is_trading_day:
                    print(f"  => Not a trading day, P&L calculation should be skipped")
                    continue

                # Get previous trading day
                prev_trading_day = trading_calendar.get_previous_trading_day(calc_date)
                print(f"  Previous trading day: {prev_trading_day}")

                if not prev_trading_day:
                    print(f"  => No previous trading day, P&L should be 0 (first snapshot)")
                    if snapshot.daily_pnl != Decimal('0'):
                        print(f"  WARNING: daily_pnl should be 0 but is {snapshot.daily_pnl}")
                    continue

                # Find previous snapshot
                prev_snapshot_query = select(PortfolioSnapshot).where(
                    and_(
                        PortfolioSnapshot.portfolio_id == portfolio.id,
                        PortfolioSnapshot.snapshot_date == prev_trading_day
                    )
                )
                prev_snapshot_result = await db.execute(prev_snapshot_query)
                prev_snapshot = prev_snapshot_result.scalar_one_or_none()

                if not prev_snapshot:
                    print(f"  => No previous snapshot found for {prev_trading_day}")
                    print(f"     P&L should be 0 (first snapshot in sequence)")
                    if snapshot.daily_pnl != Decimal('0'):
                        print(f"  WARNING: daily_pnl should be 0 but is {snapshot.daily_pnl}")
                    continue

                # Calculate what the P&L SHOULD be
                print(f"  Previous snapshot found:")
                print(f"    Previous total_value: ${prev_snapshot.total_value:,.2f}")
                print(f"    Previous cumulative_pnl: {f'${prev_snapshot.cumulative_pnl:,.2f}' if prev_snapshot.cumulative_pnl is not None else 'NULL'}")

                expected_daily_pnl = snapshot.total_value - prev_snapshot.total_value
                expected_daily_return = (expected_daily_pnl / prev_snapshot.total_value) if prev_snapshot.total_value != 0 else Decimal('0')
                expected_cumulative_pnl = (prev_snapshot.cumulative_pnl or Decimal('0')) + expected_daily_pnl

                print(f"\n  EXPECTED P&L (based on logic in snapshots.py):")
                print(f"    Expected daily_pnl: ${expected_daily_pnl:,.2f}")
                print(f"    Expected daily_return: {float(expected_daily_return) * 100:.4f}%")
                print(f"    Expected cumulative_pnl: ${expected_cumulative_pnl:,.2f}")

                print(f"\n  ACTUAL P&L (stored in database):")
                print(f"    Actual daily_pnl: {f'${snapshot.daily_pnl:,.2f}' if snapshot.daily_pnl is not None else 'NULL'}")
                print(f"    Actual daily_return: {f'{float(snapshot.daily_return) * 100:.4f}%' if snapshot.daily_return is not None else 'NULL'}")
                print(f"    Actual cumulative_pnl: {f'${snapshot.cumulative_pnl:,.2f}' if snapshot.cumulative_pnl is not None else 'NULL'}")

                # Check for discrepancies
                if snapshot.daily_pnl is None:
                    print(f"\n  ERROR: daily_pnl is NULL when it should be ${expected_daily_pnl:,.2f}")
                elif abs(snapshot.daily_pnl - expected_daily_pnl) > Decimal('0.01'):
                    print(f"\n  WARNING: P&L mismatch!")
                    print(f"    Difference: ${snapshot.daily_pnl - expected_daily_pnl:,.2f}")
                else:
                    print(f"\n  OK: P&L values match expected calculation")

        # Check for missing snapshots between dates
        print(f"\n\n{'='*80}")
        print("CHECKING FOR GAPS IN SNAPSHOT DATES")
        print("="*80)

        for portfolio in portfolios:
            snapshot_query = (
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.asc())
            )
            snapshot_result = await db.execute(snapshot_query)
            snapshots = snapshot_result.scalars().all()

            if len(snapshots) < 2:
                continue

            print(f"\n{portfolio.name}:")
            first_date = snapshots[0].snapshot_date
            last_date = snapshots[-1].snapshot_date

            # Get all trading days between first and last
            all_trading_days = []
            current_date = first_date
            while current_date <= last_date:
                if trading_calendar.is_trading_day(current_date):
                    all_trading_days.append(current_date)
                current_date += timedelta(days=1)

            # Check which trading days are missing snapshots
            snapshot_dates = {s.snapshot_date for s in snapshots}
            missing_dates = [d for d in all_trading_days if d not in snapshot_dates]

            print(f"  Date range: {first_date} to {last_date}")
            print(f"  Trading days in range: {len(all_trading_days)}")
            print(f"  Snapshots created: {len(snapshots)}")
            print(f"  Missing snapshots: {len(missing_dates)}")

            if missing_dates:
                print(f"  Missing snapshot dates (first 10): {missing_dates[:10]}")


if __name__ == "__main__":
    asyncio.run(debug_pnl_calculation_flow())
