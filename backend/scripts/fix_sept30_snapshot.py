"""Fix Sept 30 snapshot equity_balance to enable proper rollforward."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def fix():
    async with get_async_session() as db:
        # Get the Sept 30 snapshot
        result = await db.execute(text("""
            SELECT
                snapshot_date,
                total_value,
                equity_balance,
                daily_pnl,
                cumulative_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            AND snapshot_date = '2025-09-30'
        """))

        row = result.fetchone()

        if row:
            print("=== CURRENT SEPT 30 SNAPSHOT ===")
            print(f"Date: {row.snapshot_date}")
            print(f"Total Value: ${float(row.total_value):,.2f}" if row.total_value else "Total Value: None")
            print(f"Equity Balance: {row.equity_balance}")
            print(f"Daily P&L: {row.daily_pnl}")
            print(f"Cumulative P&L: {row.cumulative_pnl}")
            print()

            # Get Portfolio starting equity
            result2 = await db.execute(text("""
                SELECT equity_balance
                FROM portfolios
                WHERE id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            """))
            portfolio_row = result2.fetchone()
            starting_equity = float(portfolio_row.equity_balance)

            print(f"Portfolio starting equity (Day 0): ${starting_equity:,.2f}")
            print()

            # Since Sept 30 appears to be the first snapshot, equity should equal starting equity
            # (no previous snapshot to roll from, no P&L yet calculated)
            print("=== PROPOSED FIX ===")
            print(f"Set Sept 30 equity_balance to: ${starting_equity:,.2f}")
            print(f"(This is the starting equity, since Sept 30 appears to be the first snapshot)")
            print()

            # Apply fix
            confirm = input("Apply this fix? (yes/no): ")
            if confirm.lower() == 'yes':
                await db.execute(text("""
                    UPDATE portfolio_snapshots
                    SET equity_balance = :equity,
                        daily_pnl = 0,
                        cumulative_pnl = 0
                    WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
                    AND snapshot_date = '2025-09-30'
                """), {"equity": starting_equity})

                await db.commit()
                print("✅ Sept 30 snapshot fixed!")
                print()
                print("Now Oct 14 snapshot should roll forward properly.")
                print("You may want to delete Oct 14 snapshot and re-run batch to recalculate with P&L.")
            else:
                print("Fix cancelled.")
        else:
            print("No Sept 30 snapshot found!")


if __name__ == "__main__":
    asyncio.run(fix())
