"""Fix HNW portfolio by removing NULL equity snapshots"""
import asyncio
from datetime import date
from sqlalchemy import select, and_, delete
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from app.batch.pnl_calculator import pnl_calculator

async def fix_hnw():
    hnw_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'

    print("\n" + "=" * 80)
    print("FIXING HNW PORTFOLIO")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Delete snapshots with NULL equity (Oct 30, Nov 1, Nov 3)
        print("\n1. Deleting snapshots with NULL or reset equity:")
        print("-" * 80)

        delete_dates = [
            date(2025, 10, 30),
            date(2025, 11, 1),
            date(2025, 11, 3)
        ]

        for del_date in delete_dates:
            delete_query = delete(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == hnw_id,
                    PortfolioSnapshot.snapshot_date == del_date
                )
            )
            result = await db.execute(delete_query)
            await db.commit()
            print(f"   {del_date}: Deleted {result.rowcount} snapshot(s)")

        # Recreate Nov 3 snapshot
        print("\n2. Recreating Nov 3 snapshot with fix:")
        print("-" * 80)

        success = await pnl_calculator.calculate_portfolio_pnl(
            portfolio_id=hnw_id,
            calculation_date=date(2025, 11, 3),
            db=db
        )

        if success:
            # Verify
            verify_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == hnw_id,
                    PortfolioSnapshot.snapshot_date == date(2025, 11, 3)
                )
            )
            verify_result = await db.execute(verify_query)
            new_snapshot = verify_result.scalar_one_or_none()

            if new_snapshot and new_snapshot.equity_balance:
                print(f"   ✅ SUCCESS!")
                print(f"   New equity: ${new_snapshot.equity_balance:,.2f}")

                # Verify it's not the initial value
                initial = 2850000
                if abs(new_snapshot.equity_balance - initial) < 1.0:
                    print(f"   ⚠️  WARNING: Still at initial value!")
                else:
                    print(f"   ✅ Equity rolled forward correctly (not initial value)")
            else:
                print(f"   ❌ Failed - snapshot has NULL equity")
        else:
            print(f"   ❌ P&L calculation failed")

    print("\n" + "=" * 80)
    print("Done! Run check_all_portfolios_equity.py to verify all 3 are now OK.")
    print("=" * 80 + "\n")

asyncio.run(fix_hnw())
