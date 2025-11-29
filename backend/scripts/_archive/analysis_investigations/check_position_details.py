"""Check position quantities and values for Individual portfolio"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from uuid import UUID

async def check_positions():
    indiv_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == indiv_id)
            .order_by(Position.symbol)
        )
        positions = result.scalars().all()

        print("=" * 100)
        print("INDIVIDUAL INVESTOR PORTFOLIO - POSITION DETAILS")
        print("=" * 100)
        print()
        print(f"{'Symbol':<10} {'Qty':>10} {'Entry $':>12} {'Last $':>12} {'Entry Val':>15} {'Market Val':>15} {'P&L':>15}")
        print("-" * 100)

        total_entry_value = 0
        total_market_value = 0
        total_pnl = 0

        for pos in positions:
            qty = float(pos.quantity)
            entry_price = float(pos.entry_price) if pos.entry_price else 0
            last_price = float(pos.last_price) if pos.last_price else 0
            entry_value = qty * entry_price
            market_value = qty * last_price
            pnl = market_value - entry_value

            total_entry_value += entry_value
            total_market_value += market_value
            total_pnl += pnl

            print(f"{pos.symbol:<10} {qty:>10.2f} {entry_price:>12.2f} {last_price:>12.2f} {entry_value:>15.2f} {market_value:>15.2f} {pnl:>15.2f}")

        print("-" * 100)
        print(f"{'TOTAL':<10} {'':<10} {'':<12} {'':<12} {total_entry_value:>15.2f} {total_market_value:>15.2f} {total_pnl:>15.2f}")
        print()
        print("=" * 100)
        print("ANALYSIS:")
        print(f"  Initial Investment (Entry Values):  ${total_entry_value:,.2f}")
        print(f"  Current Market Value:                ${total_market_value:,.2f}")
        print(f"  Total P&L:                           ${total_pnl:,.2f}")
        print()
        print(f"  Expected Equity (Entry + P&L):       ${total_entry_value + total_pnl:,.2f}")
        print(f"  Actual Equity from API:              $545,900.36")
        print()
        print(f"  For 100% invested portfolio:")
        print(f"    - Market Value should = Equity")
        print(f"    - Cash should = $0")
        print("=" * 100)

asyncio.run(check_positions())
