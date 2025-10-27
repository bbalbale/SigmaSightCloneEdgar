"""
Test script to verify the historical snapshot fix.
This will create snapshots for multiple dates and verify P&L is calculated correctly.
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, delete
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from app.calculations.snapshots import create_portfolio_snapshot


async def test_historical_snapshot_fix():
    """Test creating snapshots with historical prices"""
    async with get_async_session() as db:
        print("\n" + "="*80)
        print("TESTING HISTORICAL SNAPSHOT FIX")
        print("="*80)

        # Get Individual Investor portfolio
        portfolio_query = select(Portfolio).where(
            Portfolio.name.ilike("%Individual Investor%")
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print("Portfolio not found")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")

        # Delete existing snapshots from Oct 19-23 to test fresh
        test_dates = [
            date(2025, 10, 21),
            date(2025, 10, 22),
            date(2025, 10, 23),
        ]

        print(f"\nDeleting existing test snapshots for {len(test_dates)} dates...")
        delete_stmt = delete(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio.id,
            PortfolioSnapshot.snapshot_date.in_(test_dates)
        )
        await db.execute(delete_stmt)
        await db.commit()
        print("✓ Old snapshots deleted")

        # Create new snapshots using historical prices
        print(f"\nCreating snapshots with historical prices:")
        print(f"{'Date':<15} {'Total Value':<18} {'Daily P&L':<15} {'Status':<10}")
        print("-" * 70)

        results = []
        for test_date in test_dates:
            result = await create_portfolio_snapshot(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=test_date
            )

            if result['success']:
                snapshot = result['snapshot']
                total_value_str = f"${snapshot.total_value:,.2f}"
                daily_pnl_str = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl is not None else "NULL"
                status = "✓"
            else:
                total_value_str = "FAILED"
                daily_pnl_str = "N/A"
                status = "✗"

            print(f"{str(test_date):<15} {total_value_str:<18} {daily_pnl_str:<15} {status:<10}")
            results.append(result)

        await db.commit()

        # Verify P&L calculation
        print(f"\n\nVERIFYING P&L CALCULATION:")
        print("="*80)

        # Get the created snapshots
        verify_query = (
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date.in_(test_dates)
            )
            .order_by(PortfolioSnapshot.snapshot_date.asc())
        )
        verify_result = await db.execute(verify_query)
        snapshots = verify_result.scalars().all()

        print(f"\n{'Date':<15} {'Total Value':<18} {'Daily P&L':<18} {'Cumul P&L':<18}")
        print("-" * 80)

        prev_value = None
        for snapshot in snapshots:
            date_str = str(snapshot.snapshot_date)
            total_value_str = f"${snapshot.total_value:,.2f}"
            daily_pnl_str = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl is not None else "NULL"
            cumul_pnl_str = f"${snapshot.cumulative_pnl:,.2f}" if snapshot.cumulative_pnl is not None else "NULL"

            print(f"{date_str:<15} {total_value_str:<18} {daily_pnl_str:<18} {cumul_pnl_str:<18}")

            # Verify calculation
            if prev_value is not None:
                expected_pnl = snapshot.total_value - prev_value
                if snapshot.daily_pnl is not None:
                    diff = abs(float(snapshot.daily_pnl) - float(expected_pnl))
                    if diff > 0.01:
                        print(f"  ⚠ WARNING: P&L mismatch! Expected ${expected_pnl:,.2f}, got ${snapshot.daily_pnl:,.2f}")

            prev_value = snapshot.total_value

        # Check if values are different (not frozen)
        total_values = [float(s.total_value) for s in snapshots]
        unique_values = len(set(total_values))

        print(f"\n\nRESULTS:")
        print("="*80)
        if unique_values > 1:
            print(f"✓ SUCCESS: Snapshots have {unique_values} different total values")
            print(f"  Values: {[f'${v:,.2f}' for v in total_values]}")
            print(f"\n✓ Historical price lookup is working correctly!")
        else:
            print(f"✗ FAILURE: All snapshots have the same value: ${total_values[0]:,.2f}")
            print(f"  Historical prices may not be available in market_data_cache")

        # Check P&L calculations
        null_pnl_count = sum(1 for s in snapshots if s.daily_pnl is None)
        if null_pnl_count == 0:
            print(f"✓ All {len(snapshots)} snapshots have calculated daily_pnl")
        else:
            print(f"⚠ {null_pnl_count}/{len(snapshots)} snapshots have NULL daily_pnl")


if __name__ == "__main__":
    asyncio.run(test_historical_snapshot_fix())
