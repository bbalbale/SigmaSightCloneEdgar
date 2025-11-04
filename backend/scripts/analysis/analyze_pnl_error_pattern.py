"""
Analyze the error pattern in Position.unrealized_pnl to figure out what calculation was used
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from uuid import UUID

async def analyze_error_pattern():
    indiv_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == indiv_id)
            .order_by(Position.symbol)
        )
        positions = result.scalars().all()

        print("=" * 160)
        print("ANALYZING ERROR PATTERN IN Position.unrealized_pnl")
        print("=" * 160)
        print()
        print(f"{'Symbol':<10} {'Entry $':>10} {'Last $':>10} {'Qty':>8} {'Correct P&L':>12} {'DB P&L':>12} {'Error':>12} {'Error/Qty':>12} {'Theories':>50}")
        print("-" * 160)

        for pos in positions:
            qty = pos.quantity
            entry_price = pos.entry_price
            last_price = pos.last_price

            # Correct calculation
            correct_pnl = (last_price - entry_price) * qty

            # What's in DB
            db_pnl = pos.unrealized_pnl if pos.unrealized_pnl else Decimal('0')

            # Error
            error = db_pnl - correct_pnl
            error_per_share = error / qty if qty != 0 else Decimal('0')

            # Test theories
            theories = []

            # Theory 1: Used last_price instead of (last_price - entry_price)
            if abs(last_price * qty - db_pnl) < Decimal('0.01'):
                theories.append("last_price * qty")

            # Theory 2: Used entry_price instead of (last_price - entry_price)
            if abs(entry_price * qty - db_pnl) < Decimal('0.01'):
                theories.append("entry_price * qty")

            # Theory 3: Wrong sign on entry_price
            theory3 = (last_price + entry_price) * qty
            if abs(theory3 - db_pnl) < Decimal('0.01'):
                theories.append("(last + entry) * qty")

            # Theory 4: Using absolute value somewhere
            theory4 = abs(last_price - entry_price) * qty
            if abs(theory4 - db_pnl) < Decimal('0.01'):
                theories.append("abs(last - entry) * qty")

            # Theory 5: Per-share error equals entry_price (suggests entry_price used as delta)
            if abs(error_per_share - entry_price) < Decimal('0.01'):
                theories.append("ERROR = entry_price!")

            # Theory 6: Per-share error equals last_price
            if abs(error_per_share - last_price) < Decimal('0.01'):
                theories.append("ERROR = last_price!")

            theories_str = ", ".join(theories) if theories else "???"

            print(f"{pos.symbol:<10} {float(entry_price):>10.2f} {float(last_price):>10.2f} {float(qty):>8.0f} "
                  f"{float(correct_pnl):>12.2f} {float(db_pnl):>12.2f} {float(error):>12.2f} "
                  f"{float(error_per_share):>12.2f} {theories_str:<50}")

        print()
        print("=" * 160)
        print("HYPOTHESIS:")
        print("Looking at the error patterns to determine what calculation was used...")
        print("=" * 160)

asyncio.run(analyze_error_pattern())
