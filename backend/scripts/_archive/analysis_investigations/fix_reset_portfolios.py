"""
Fix the two portfolios with reset equity balances
"""
import asyncio
from datetime import date
from sqlalchemy import select, and_, delete
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.batch.pnl_calculator import pnl_calculator


async def fix_portfolios():
    print("\n" + "=" * 80)
    print("FIXING RESET PORTFOLIOS")
    print("=" * 80 + "\n")

    # Portfolio IDs that need fixing
    portfolios_to_fix = [
        ("e23ab931-a033-edfe-ed4f-9d02474780b4", "High Net Worth"),
        ("fcd71196-e93e-f000-5a74-31a9eead3118", "Hedge Fund Style")
    ]

    today = date(2025, 11, 3)

    for portfolio_id, name in portfolios_to_fix:
        print(f"\nFixing: {name}")
        print("-" * 80)

        async with AsyncSessionLocal() as db:
            # Delete Nov 3 snapshot
            delete_query = delete(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date == today
                )
            )
            result = await db.execute(delete_query)
            await db.commit()
            print(f"  1. Deleted {result.rowcount} snapshot(s)")

            # Re-calculate with fix
            success = await pnl_calculator.calculate_portfolio_pnl(
                portfolio_id=portfolio_id,
                calculation_date=today,
                db=db
            )

            if success:
                # Verify
                verify_query = select(PortfolioSnapshot).where(
                    and_(
                        PortfolioSnapshot.portfolio_id == portfolio_id,
                        PortfolioSnapshot.snapshot_date == today
                    )
                )
                verify_result = await db.execute(verify_query)
                new_snapshot = verify_result.scalar_one_or_none()

                if new_snapshot:
                    print(f"  2. Created new snapshot")
                    print(f"     Equity: ${new_snapshot.equity_balance:,.2f}")
                    print(f"     ✅ SUCCESS")
                else:
                    print(f"     ❌ Failed to create snapshot")
            else:
                print(f"  2. ❌ P&L calculation failed")

    print("\n" + "=" * 80)
    print("DONE - Run check_all_portfolios_equity.py to verify")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(fix_portfolios())
