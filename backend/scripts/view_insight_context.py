"""
View the context data from the stored insight to see what Claude actually received.
"""
import asyncio
import json
from sqlalchemy import text
from app.database import get_async_session


async def view_insight():
    async with get_async_session() as db:
        # Get the most recent insight
        result = await db.execute(text("""
            SELECT
                title,
                severity,
                summary,
                context_data->>'portfolio_id' as portfolio_id,
                context_data->'portfolio_summary'->>'name' as portfolio_name,
                context_data->'portfolio_summary'->>'equity_balance' as equity_balance,
                context_data->'snapshot'->>'total_value' as total_value,
                context_data->'snapshot'->>'daily_pnl' as daily_pnl,
                context_data->'summary_stats'->>'total_value' as stats_total_value,
                created_at
            FROM ai_insights
            ORDER BY created_at DESC
            LIMIT 1
        """))

        row = result.fetchone()

        if row:
            print("=== LATEST INSIGHT ===")
            print(f"Title: {row.title}")
            print(f"Severity: {row.severity}")
            print(f"Created: {row.created_at}")
            print()
            print("=== DATA CLAUDE RECEIVED ===")
            print(f"Portfolio: {row.portfolio_name}")
            print(f"Portfolio ID: {row.portfolio_id}")
            print(f"Equity Balance: ${float(row.equity_balance):,.2f}" if row.equity_balance else "Equity Balance: None")
            print(f"Total Value (snapshot): ${float(row.total_value):,.2f}" if row.total_value else "Total Value: None")
            print(f"Total Value (stats): ${float(row.stats_total_value):,.2f}" if row.stats_total_value else "Stats Total Value: None")
            print(f"Daily P&L: ${float(row.daily_pnl):,.2f}" if row.daily_pnl else "Daily P&L: None")
            print()

            if row.equity_balance and row.total_value:
                equity = float(row.equity_balance)
                value = float(row.total_value)
                diff = equity - value
                pct = (diff / equity) * 100

                print("=== CLAUDE'S CALCULATION ===")
                print(f"Equity Balance - Total Value = {equity:,.2f} - {value:,.2f} = ${diff:,.2f}")
                print(f"Percentage: {pct:.1f}%")
                print()

            print("=== INSIGHT SUMMARY ===")
            print(row.summary)
        else:
            print("No insights found!")


if __name__ == "__main__":
    asyncio.run(view_insight())
