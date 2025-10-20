"""
Fix the Oct 14 snapshot by deleting and recreating it with proper equity rollforward.
"""
import asyncio
from sqlalchemy import text
from datetime import date
from app.database import get_async_session
from app.calculations.snapshots import create_portfolio_snapshot


async def main():
    print("=" * 80)
    print("FIX OCT 14 SNAPSHOT")
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"
    oct_14 = date(2025, 10, 14)

    async with get_async_session() as db:
        # Step 1: Check current Oct 14 snapshot
        result = await db.execute(text("""
            SELECT snapshot_date, equity_balance, daily_pnl, cumulative_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = :portfolio_id
            AND snapshot_date = :date
        """), {"portfolio_id": portfolio_id, "date": oct_14})

        current_snapshot = result.fetchone()

        if current_snapshot:
            print(f"Current Oct 14 snapshot:")
            print(f"  Equity Balance: ${float(current_snapshot.equity_balance):,.2f}")
            print(f"  Daily P&L: ${float(current_snapshot.daily_pnl):,.2f}")
            print(f"  Cumulative P&L: ${float(current_snapshot.cumulative_pnl):,.2f}")
            print()

            # Step 2: Delete the incorrect snapshot
            print("Deleting incorrect snapshot...")
            await db.execute(text("""
                DELETE FROM portfolio_snapshots
                WHERE portfolio_id = :portfolio_id
                AND snapshot_date = :date
            """), {"portfolio_id": portfolio_id, "date": oct_14})
            await db.commit()
            print("Deleted!")
            print()

        else:
            print("No Oct 14 snapshot found - nothing to fix")
            return

        # Step 3: Recreate with proper rollforward
        print("Recreating snapshot with proper equity rollforward...")
        result = await create_portfolio_snapshot(db, portfolio_id, oct_14)

        if result.get('success'):
            snapshot = result['snapshot']
            print(f"SUCCESS!")
            print()
            print(f"New Oct 14 snapshot:")
            print(f"  Equity Balance: ${float(snapshot.equity_balance):,.2f}")
            print(f"  Daily P&L: ${float(snapshot.daily_pnl):,.2f}")
            print(f"  Cumulative P&L: ${float(snapshot.cumulative_pnl):,.2f}")
        else:
            print(f"FAILED: {result.get('message')}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
