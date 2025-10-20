"""Check all snapshots to verify equity rollforward is working."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def check():
    async with get_async_session() as db:
        result = await db.execute(text("""
            SELECT
                snapshot_date,
                total_value,
                equity_balance,
                daily_pnl,
                cumulative_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            ORDER BY snapshot_date ASC
        """))

        rows = result.fetchall()

        if rows:
            print(f"=== ALL SNAPSHOTS FOR HNW PORTFOLIO ===")
            print(f"Found {len(rows)} snapshots\n")

            for i, row in enumerate(rows, 1):
                print(f"Snapshot {i}: {row.snapshot_date}")
                print(f"  Total Value:      ${float(row.total_value):,.2f}" if row.total_value else "  Total Value: None")
                print(f"  Equity Balance:   ${float(row.equity_balance):,.2f}" if row.equity_balance else "  Equity Balance: None")
                print(f"  Daily P&L:        ${float(row.daily_pnl):,.2f}" if row.daily_pnl else "  Daily P&L: None")
                print(f"  Cumulative P&L:   ${float(row.cumulative_pnl):,.2f}" if row.cumulative_pnl else "  Cumulative P&L: None")

                # Check equity rollforward
                if i > 1 and row.equity_balance and rows[i-2].equity_balance and row.daily_pnl is not None:
                    expected_equity = float(rows[i-2].equity_balance) + float(row.daily_pnl)
                    actual_equity = float(row.equity_balance)
                    diff = actual_equity - expected_equity

                    if abs(diff) > 0.01:  # Allow for small rounding
                        print(f"  ⚠️  EQUITY MISMATCH: Expected ${expected_equity:,.2f}, Got ${actual_equity:,.2f} (diff: ${diff:,.2f})")
                    else:
                        print(f"  ✅ Equity rolled forward correctly from ${float(rows[i-2].equity_balance):,.2f}")

                print()
        else:
            print("No snapshots found!")


if __name__ == "__main__":
    asyncio.run(check())
