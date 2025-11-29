"""
Fix equity balance for all three demo portfolios

This will:
1. Check current equity status for all portfolios
2. Delete today's snapshots (Nov 3, 2025)
3. Re-run P&L calculation with the fix
4. Verify all portfolios now have correct equity rollforward
"""
import asyncio
from datetime import date
from sqlalchemy import select, and_, delete
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.batch.pnl_calculator import pnl_calculator


async def fix_all():
    async with get_async_session() as db:
        print("=" * 80)
        print("FIXING EQUITY BALANCE FOR ALL PORTFOLIOS")
        print("=" * 80)
        print()

        # Get all active portfolios
        portfolios_query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        portfolios_result = await db.execute(portfolios_query)
        portfolios = portfolios_result.scalars().all()

        print(f"Found {len(portfolios)} portfolios to fix")
        print()

        today = date(2025, 11, 3)  # Nov 3, 2025

        for portfolio in portfolios:
            print("=" * 80)
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"Initial Equity: ${portfolio.equity_balance:,.2f}")
            print("=" * 80)

            # Step 1: Check current Nov 3 snapshot
            print("\n1. Current Nov 3 snapshot (before fix):")
            print("-" * 80)

            current_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date == today
                )
            )
            current_result = await db.execute(current_query)
            current_snapshot = current_result.scalar_one_or_none()

            if current_snapshot:
                print(f"  Equity Balance: ${current_snapshot.equity_balance:,.2f}")
                print(f"  Daily P&L: {current_snapshot.daily_pnl or 'NULL'}")
                print(f"  Total Value: ${current_snapshot.total_value:,.2f}")

                if abs(current_snapshot.equity_balance - portfolio.equity_balance) < 1.0:
                    print(f"  ❌ PROBLEM: Equity reset to initial value!")
                else:
                    print(f"  ✅ Equity looks correct")
            else:
                print(f"  No Nov 3 snapshot found")

            # Step 2: Get most recent snapshot before today
            print("\n2. Most recent snapshot before Nov 3:")
            print("-" * 80)

            prev_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date < today
                )
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

            prev_result = await db.execute(prev_query)
            prev_snapshot = prev_result.scalar_one_or_none()

            if prev_snapshot:
                print(f"  Date: {prev_snapshot.snapshot_date}")
                print(f"  Equity Balance: ${prev_snapshot.equity_balance:,.2f}")
                print(f"  This should be used for Nov 3 calculation!")
            else:
                print(f"  No previous snapshot found")

            # Step 3: Delete Nov 3 snapshot
            print("\n3. Deleting Nov 3 snapshot:")
            print("-" * 80)

            delete_query = delete(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date == today
                )
            )
            result = await db.execute(delete_query)
            await db.commit()
            print(f"  ✅ Deleted {result.rowcount} snapshot(s)")

            # Step 4: Re-run P&L calculation
            print("\n4. Re-running P&L calculation with fix:")
            print("-" * 80)

            success = await pnl_calculator.calculate_portfolio_pnl(
                portfolio_id=portfolio.id,
                calculation_date=today,
                db=db
            )

            if success:
                print(f"  ✅ P&L calculation completed")
            else:
                print(f"  ❌ P&L calculation failed")

            # Step 5: Verify new snapshot
            print("\n5. New Nov 3 snapshot (after fix):")
            print("-" * 80)

            new_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date == today
                )
            )
            new_result = await db.execute(new_query)
            new_snapshot = new_result.scalar_one_or_none()

            if new_snapshot:
                print(f"  Equity Balance: ${new_snapshot.equity_balance:,.2f}")
                print(f"  Daily P&L: ${new_snapshot.daily_pnl:,.2f}" if new_snapshot.daily_pnl else "  Daily P&L: NULL")
                print(f"  Total Value: ${new_snapshot.total_value:,.2f}")

                # Verify fix
                if abs(new_snapshot.equity_balance - portfolio.equity_balance) < 1.0:
                    print(f"\n  ❌ FAILED: Equity still reset to initial!")
                elif prev_snapshot and abs(new_snapshot.equity_balance - prev_snapshot.equity_balance) < 100000:
                    print(f"\n  ✅ SUCCESS: Equity rolled forward correctly!")
                    print(f"     Previous: ${prev_snapshot.equity_balance:,.2f}")
                    print(f"     Current:  ${new_snapshot.equity_balance:,.2f}")
                    change = new_snapshot.equity_balance - prev_snapshot.equity_balance
                    print(f"     Change:   ${change:,.2f}")
                else:
                    print(f"\n  ⚠️  Equity different but may need review")
            else:
                print(f"  ❌ No new snapshot created")

            print("\n")

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\nFixed {len(portfolios)} portfolios")
        print("Verify equity balances are now rolling forward correctly.")
        print()


if __name__ == "__main__":
    asyncio.run(fix_all())
