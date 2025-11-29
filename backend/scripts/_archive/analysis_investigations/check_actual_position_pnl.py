"""Check what Position table is actually showing for P&L"""
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

        print("=" * 120)
        print("INDIVIDUAL INVESTOR PORTFOLIO - ACTUAL POSITION DATA FROM DATABASE")
        print("=" * 120)
        print()
        print(f"{'Symbol':<10} {'Qty':>10} {'Entry $':>12} {'Last $':>12} {'Market Val':>15} {'Unrealized P&L':>15} {'Realized P&L':>15}")
        print("-" * 120)

        total_market_value = 0
        total_unrealized_pnl = 0
        total_realized_pnl = 0

        for pos in positions:
            market_val = float(pos.market_value) if pos.market_value else 0
            unrealized = float(pos.unrealized_pnl) if pos.unrealized_pnl else 0
            realized = float(pos.realized_pnl) if pos.realized_pnl else 0

            total_market_value += market_val
            total_unrealized_pnl += unrealized
            total_realized_pnl += realized

            qty = float(pos.quantity)
            entry = float(pos.entry_price) if pos.entry_price else 0
            last = float(pos.last_price) if pos.last_price else 0

            print(f"{pos.symbol:<10} {qty:>10.2f} {entry:>12.2f} {last:>12.2f} {market_val:>15.2f} {unrealized:>15.2f} {realized:>15.2f}")

        print("-" * 120)
        print(f"{'TOTAL':<10} {'':<10} {'':<12} {'':<12} {total_market_value:>15.2f} {total_unrealized_pnl:>15.2f} {total_realized_pnl:>15.2f}")
        print()
        print("=" * 120)
        print("ANALYSIS:")
        print(f"  Position.market_value total:     ${total_market_value:,.2f}")
        print(f"  Position.unrealized_pnl total:   ${total_unrealized_pnl:,.2f}")
        print(f"  Position.realized_pnl total:     ${total_realized_pnl:,.2f}")
        print()
        print(f"  What equity SHOULD be (for 100% invested):")
        print(f"    = Market Value = ${total_market_value:,.2f}")
        print()
        print(f"  What API is currently returning:")
        print(f"    Equity: $485,000.00")
        print(f"    This creates phantom cash of: ${485000 - total_market_value:,.2f}")
        print("=" * 120)

asyncio.run(check_positions())
