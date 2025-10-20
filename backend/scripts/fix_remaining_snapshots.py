"""
Fix Oct 15-17 snapshots to maintain proper equity rollforward chain.
"""
import asyncio
from sqlalchemy import text
from datetime import date
from app.database import get_async_session
from app.calculations.snapshots import create_portfolio_snapshot


async def main():
    print("=" * 80)
    print("FIX OCT 15-17 SNAPSHOTS")
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"
    dates_to_fix = [date(2025, 10, 15), date(2025, 10, 16), date(2025, 10, 17)]

    async with get_async_session() as db:
        for fix_date in dates_to_fix:
            print(f"Fixing {fix_date}...")

            # Delete the old snapshot
            await db.execute(text("""
                DELETE FROM portfolio_snapshots
                WHERE portfolio_id = :portfolio_id
                AND snapshot_date = :date
            """), {"portfolio_id": portfolio_id, "date": fix_date})
            await db.commit()

            # Recreate with proper rollforward
            result = await create_portfolio_snapshot(db, portfolio_id, fix_date)

            if result.get('success'):
                snapshot = result['snapshot']
                print(f"  Equity: ${float(snapshot.equity_balance):,.2f}, P&L: ${float(snapshot.daily_pnl):,.2f}")
            else:
                print(f"  FAILED: {result.get('message')}")

            print()

    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
