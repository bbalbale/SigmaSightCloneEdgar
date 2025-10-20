"""Check snapshot equity_balance field."""
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
                cash_value,
                long_value,
                short_value,
                daily_pnl,
                cumulative_pnl
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            ORDER BY snapshot_date DESC
            LIMIT 1
        """))

        row = result.fetchone()

        if row:
            print("=== LATEST SNAPSHOT ===")
            print(f"Date: {row.snapshot_date}")
            print(f"Total Value: ${float(row.total_value):,.2f}" if row.total_value else "Total Value: None")
            print(f"Equity Balance: ${float(row.equity_balance):,.2f}" if row.equity_balance else "Equity Balance: None")
            print(f"Cash: ${float(row.cash_value):,.2f}" if row.cash_value else "Cash: None")
            print(f"Long Value: ${float(row.long_value):,.2f}" if row.long_value else "Long Value: None")
            print(f"Short Value: ${float(row.short_value):,.2f}" if row.short_value else "Short Value: None")
            print(f"Daily P&L: ${float(row.daily_pnl):,.2f}" if row.daily_pnl else "Daily P&L: None")
            print(f"Cumulative P&L: ${float(row.cumulative_pnl):,.2f}" if row.cumulative_pnl else "Cumulative P&L: None")
            print()

            # Now get Portfolio starting equity
            result2 = await db.execute(text("""
                SELECT equity_balance
                FROM portfolios
                WHERE id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            """))
            portfolio_row = result2.fetchone()

            if portfolio_row:
                starting_equity = float(portfolio_row.equity_balance)
                print(f"=== PORTFOLIO DATA ===")
                print(f"Starting Equity (Day 0): ${starting_equity:,.2f}")
                print()

                if row.equity_balance:
                    current_equity = float(row.equity_balance)
                    diff = current_equity - starting_equity
                    pct = (diff / starting_equity * 100)
                    print(f"=== EQUITY CHANGE ===")
                    print(f"Current Equity: ${current_equity:,.2f}")
                    print(f"Starting Equity: ${starting_equity:,.2f}")
                    print(f"Change: ${diff:,.2f} ({pct:.2f}%)")
        else:
            print("No snapshot found!")


if __name__ == "__main__":
    asyncio.run(check())
