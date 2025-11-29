"""
Test the equity balance fix

This script will:
1. Show the current Nov 3 snapshot (should have $485K - the reset value)
2. Delete the Nov 3 snapshot
3. Re-run the P&L calculation for Nov 3 with the fix
4. Verify that equity now rolls forward from Oct 29 ($544K) instead of resetting to $485K
"""
import asyncio
from datetime import date
from sqlalchemy import select, and_, delete
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.batch.pnl_calculator import pnl_calculator


async def test_fix():
    async with get_async_session() as db:
        print("=" * 80)
        print("TESTING EQUITY BALANCE FIX")
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
        print(f"ID: {portfolio.id}")
        print(f"Initial Equity: ${portfolio.equity_balance:,.2f}")
        print()

        # Step 1: Show current Nov 3 snapshot
        print("STEP 1: Current Nov 3 snapshot (before fix)")
        print("-" * 80)

        nov_3_date = date(2025, 11, 3)
        current_snapshot_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == nov_3_date
            )
        )
        current_result = await db.execute(current_snapshot_query)
        current_snapshot = current_result.scalar_one_or_none()

        if current_snapshot:
            print(f"Date: {current_snapshot.snapshot_date}")
            print(f"Equity Balance: ${current_snapshot.equity_balance:,.2f}")
            print(f"Daily P&L: {current_snapshot.daily_pnl or 'NULL'}")
            print(f"Total Value: ${current_snapshot.total_value:,.2f}")
            print()

            if current_snapshot.equity_balance == portfolio.equity_balance:
                print("❌ CONFIRMED: Equity was reset to initial value!")
            else:
                print("✅ Equity is different from initial value")
        else:
            print("No Nov 3 snapshot found")
        print()

        # Step 2: Get Oct 29 snapshot (the last good one before the gap)
        print("STEP 2: Oct 29 snapshot (last snapshot before gap)")
        print("-" * 80)

        oct_29_date = date(2025, 10, 29)
        oct_29_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == oct_29_date
            )
        )
        oct_29_result = await db.execute(oct_29_query)
        oct_29_snapshot = oct_29_result.scalar_one_or_none()

        if oct_29_snapshot:
            print(f"Date: {oct_29_snapshot.snapshot_date}")
            print(f"Equity Balance: ${oct_29_snapshot.equity_balance:,.2f}")
            print(f"This should be used as the previous equity for Nov 3!")
        else:
            print("No Oct 29 snapshot found")
        print()

        # Step 3: Delete Nov 3 snapshot
        print("STEP 3: Deleting Nov 3 snapshot to recreate it")
        print("-" * 80)

        delete_query = delete(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == nov_3_date
            )
        )
        await db.execute(delete_query)
        await db.commit()
        print("✅ Deleted Nov 3 snapshot")
        print()

        # Step 4: Re-run P&L calculation with the fix
        print("STEP 4: Re-running P&L calculation for Nov 3 (with fix)")
        print("-" * 80)

        success = await pnl_calculator.calculate_portfolio_pnl(
            portfolio_id=portfolio.id,
            calculation_date=nov_3_date,
            db=db
        )

        if success:
            print("✅ P&L calculation completed")
        else:
            print("❌ P&L calculation failed")
        print()

        # Step 5: Check new Nov 3 snapshot
        print("STEP 5: New Nov 3 snapshot (after fix)")
        print("-" * 80)

        new_snapshot_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == nov_3_date
            )
        )
        new_result = await db.execute(new_snapshot_query)
        new_snapshot = new_result.scalar_one_or_none()

        if new_snapshot:
            print(f"Date: {new_snapshot.snapshot_date}")
            print(f"Equity Balance: ${new_snapshot.equity_balance:,.2f}")
            print(f"Daily P&L: ${new_snapshot.daily_pnl:,.2f}" if new_snapshot.daily_pnl else "Daily P&L: NULL")
            print(f"Total Value: ${new_snapshot.total_value:,.2f}")
            print()

            # Verify the fix worked
            if oct_29_snapshot and new_snapshot.equity_balance:
                expected_equity = oct_29_snapshot.equity_balance + (new_snapshot.daily_pnl or 0)

                print("VERIFICATION:")
                print(f"  Oct 29 Equity: ${oct_29_snapshot.equity_balance:,.2f}")
                print(f"  Nov 3 Daily P&L: ${new_snapshot.daily_pnl or 0:,.2f}")
                print(f"  Expected Nov 3 Equity: ${expected_equity:,.2f}")
                print(f"  Actual Nov 3 Equity: ${new_snapshot.equity_balance:,.2f}")
                print()

                # Check if equity is close to Oct 29 value (within reasonable P&L range)
                # It should NOT be $485K (the initial value)
                if abs(new_snapshot.equity_balance - portfolio.equity_balance) < 1.0:
                    print("❌ FAILED: Equity still reset to initial value!")
                elif abs(new_snapshot.equity_balance - oct_29_snapshot.equity_balance) < 100000:
                    print("✅ SUCCESS: Equity rolled forward from Oct 29!")
                    print(f"   Equity changed from ${oct_29_snapshot.equity_balance:,.2f} to ${new_snapshot.equity_balance:,.2f}")
                else:
                    print("⚠️  WARNING: Equity value seems unusual")
        else:
            print("❌ No new snapshot was created")

        print()
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_fix())
