"""
Debug script to investigate daily P&L values in portfolio_snapshots table
"""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from datetime import datetime


async def check_snapshot_pnl():
    """Check portfolio snapshot P&L data"""
    async with get_async_session() as db:
        print("\n" + "="*80)
        print("PORTFOLIO SNAPSHOTS P&L ANALYSIS")
        print("="*80)

        # Get total snapshot count
        count_query = select(func.count(PortfolioSnapshot.id))
        count_result = await db.execute(count_query)
        total_snapshots = count_result.scalar()
        print(f"\nTotal snapshots in database: {total_snapshots}")

        # Get all portfolios
        portfolio_query = select(Portfolio)
        portfolio_result = await db.execute(portfolio_query)
        portfolios = portfolio_result.scalars().all()

        print(f"Total portfolios: {len(portfolios)}")
        print()

        # For each portfolio, get snapshots ordered by date
        for portfolio in portfolios:
            print(f"\n{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"Portfolio ID: {portfolio.id}")
            print(f"{'='*80}")

            # Get all snapshots for this portfolio, ordered by date
            snapshot_query = (
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(10)  # Get last 10 snapshots
            )
            snapshot_result = await db.execute(snapshot_query)
            snapshots = snapshot_result.scalars().all()

            if not snapshots:
                print("  ⚠️  No snapshots found for this portfolio")
                continue

            print(f"\nFound {len(snapshots)} recent snapshots:")
            print(f"\n{'Date':<12} {'Total Value':<15} {'Daily P&L':<15} {'Daily Ret%':<12} {'Cumul P&L':<15} {'Equity Bal':<15}")
            print("-" * 95)

            for snapshot in snapshots:
                date_str = snapshot.snapshot_date.strftime("%Y-%m-%d")
                total_value = f"${snapshot.total_value:,.2f}" if snapshot.total_value else "N/A"
                daily_pnl = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl is not None else "NULL"
                daily_return = f"{snapshot.daily_return * 100:.2f}%" if snapshot.daily_return is not None else "NULL"
                cumulative_pnl = f"${snapshot.cumulative_pnl:,.2f}" if snapshot.cumulative_pnl is not None else "NULL"
                equity_balance = f"${snapshot.equity_balance:,.2f}" if snapshot.equity_balance is not None else "NULL"

                print(f"{date_str:<12} {total_value:<15} {daily_pnl:<15} {daily_return:<12} {cumulative_pnl:<15} {equity_balance:<15}")

        # Check for duplicate dates or other issues
        print(f"\n\n{'='*80}")
        print("DATA QUALITY CHECKS")
        print("="*80)

        # Check for NULL daily_pnl values
        null_pnl_query = select(func.count(PortfolioSnapshot.id)).where(
            PortfolioSnapshot.daily_pnl.is_(None)
        )
        null_pnl_result = await db.execute(null_pnl_query)
        null_pnl_count = null_pnl_result.scalar()
        print(f"\nSnapshots with NULL daily_pnl: {null_pnl_count} / {total_snapshots}")

        # Check for NULL cumulative_pnl values
        null_cumul_query = select(func.count(PortfolioSnapshot.id)).where(
            PortfolioSnapshot.cumulative_pnl.is_(None)
        )
        null_cumul_result = await db.execute(null_cumul_query)
        null_cumul_count = null_cumul_result.scalar()
        print(f"Snapshots with NULL cumulative_pnl: {null_cumul_count} / {total_snapshots}")

        # Check for identical daily_pnl values (might indicate not updating)
        print("\n\nChecking for repeated P&L values (might indicate update issues):")
        for portfolio in portfolios:
            snapshot_query = (
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(5)
            )
            snapshot_result = await db.execute(snapshot_query)
            snapshots = snapshot_result.scalars().all()

            if len(snapshots) < 2:
                continue

            pnl_values = [s.daily_pnl for s in snapshots if s.daily_pnl is not None]
            total_values = [float(s.total_value) for s in snapshots]

            print(f"\n  Portfolio: {portfolio.name[:50]}")
            print(f"    Last {len(pnl_values)} daily P&L values: {[f'${v:,.2f}' if v else 'NULL' for v in pnl_values]}")
            print(f"    Last {len(total_values)} total values: {[f'${v:,.2f}' for v in total_values]}")

            # Check if all values are the same
            if len(set(pnl_values)) == 1 and len(pnl_values) > 1:
                print(f"    ⚠️  WARNING: All recent daily P&L values are identical!")

            if len(set(total_values)) == 1 and len(total_values) > 1:
                print(f"    ⚠️  WARNING: All recent total values are identical!")


if __name__ == "__main__":
    asyncio.run(check_snapshot_pnl())
