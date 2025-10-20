"""View all portfolio snapshots to see equity_balance progression."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def view_all():
    async with get_async_session() as db:
        # Get ALL snapshots for HNW portfolio
        result = await db.execute(text("""
            SELECT
                snapshot_date,
                total_value,
                equity_balance,
                cash_value,
                long_value,
                short_value,
                daily_pnl,
                cumulative_pnl,
                num_positions,
                created_at
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            ORDER BY snapshot_date ASC
        """))

        rows = result.fetchall()

        print("=" * 100)
        print(f"PORTFOLIO SNAPSHOTS - High Net Worth Portfolio")
        print(f"Found {len(rows)} snapshots")
        print("=" * 100)
        print()

        if rows:
            for i, row in enumerate(rows, 1):
                print(f"#{i} - {row.snapshot_date} (created: {row.created_at})")
                print(f"  Total Value:      ${float(row.total_value):,.2f}" if row.total_value else "  Total Value:      None")
                print(f"  Equity Balance:   ${float(row.equity_balance):,.2f}" if row.equity_balance else "  Equity Balance:   None")
                print(f"  Cash:             ${float(row.cash_value):,.2f}" if row.cash_value else "  Cash:             None")
                print(f"  Long Value:       ${float(row.long_value):,.2f}" if row.long_value else "  Long Value:       None")
                print(f"  Short Value:      ${float(row.short_value):,.2f}" if row.short_value else "  Short Value:      None")
                print(f"  Daily P&L:        ${float(row.daily_pnl):,.2f}" if row.daily_pnl is not None else "  Daily P&L:        None")
                print(f"  Cumulative P&L:   ${float(row.cumulative_pnl):,.2f}" if row.cumulative_pnl is not None else "  Cumulative P&L:   None")
                print(f"  Positions:        {row.num_positions}")
                print()

            print("=" * 100)
            print("SUMMARY")
            print("=" * 100)
            print(f"Date range: {rows[0].snapshot_date} to {rows[-1].snapshot_date}")
            print(f"Total snapshots: {len(rows)}")

            # Count how many have equity_balance
            equity_count = sum(1 for r in rows if r.equity_balance is not None)
            print(f"Snapshots with equity_balance: {equity_count}/{len(rows)}")

            # Check for gaps
            if len(rows) > 1:
                from datetime import timedelta
                first_date = rows[0].snapshot_date
                last_date = rows[-1].snapshot_date
                total_days = (last_date - first_date).days + 1
                print(f"Days covered: {total_days} days")
                print(f"Missing: {total_days - len(rows)} days")

        else:
            print("No snapshots found!")

        print()

        # Also check Portfolio table equity_balance (Day 0)
        result2 = await db.execute(text("""
            SELECT equity_balance, created_at
            FROM portfolios
            WHERE id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
        """))
        portfolio_row = result2.fetchone()

        if portfolio_row:
            print("=" * 100)
            print("PORTFOLIO TABLE (Day 0 Starting Equity)")
            print("=" * 100)
            print(f"Starting Equity: ${float(portfolio_row.equity_balance):,.2f}" if portfolio_row.equity_balance else "Starting Equity: None")
            print(f"Portfolio created: {portfolio_row.created_at}")


if __name__ == "__main__":
    asyncio.run(view_all())
