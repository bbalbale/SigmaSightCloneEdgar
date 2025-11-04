"""
Manual P&L Calculation - Individual Investor Portfolio
Calculate P&L for each position manually to verify database values
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from uuid import UUID

async def calculate_manual_pnl():
    indiv_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == indiv_id)
            .order_by(Position.symbol)
        )
        positions = result.scalars().all()

        print("=" * 140)
        print("MANUAL P&L CALCULATION - INDIVIDUAL INVESTOR PORTFOLIO")
        print("=" * 140)
        print()
        print(f"{'Symbol':<10} {'Qty':>10} {'Entry $':>12} {'Last $':>12} {'Entry Cost':>15} {'Market Val':>15} {'CORRECT P&L':>15} {'DB P&L':>15} {'Diff':>15}")
        print("-" * 140)

        total_entry_cost = Decimal('0')
        total_market_value = Decimal('0')
        total_correct_pnl = Decimal('0')
        total_db_pnl = Decimal('0')

        for pos in positions:
            qty = pos.quantity
            entry_price = pos.entry_price
            last_price = pos.last_price

            # Calculate entry cost
            entry_cost = qty * entry_price

            # Calculate current market value
            market_value = qty * last_price

            # Calculate CORRECT unrealized P&L
            correct_pnl = market_value - entry_cost

            # Get what's stored in database
            db_pnl = pos.unrealized_pnl if pos.unrealized_pnl else Decimal('0')

            # Calculate difference
            diff = db_pnl - correct_pnl

            # Accumulate totals
            total_entry_cost += entry_cost
            total_market_value += market_value
            total_correct_pnl += correct_pnl
            total_db_pnl += db_pnl

            # Print row
            print(f"{pos.symbol:<10} {float(qty):>10.2f} {float(entry_price):>12.2f} {float(last_price):>12.2f} "
                  f"{float(entry_cost):>15.2f} {float(market_value):>15.2f} {float(correct_pnl):>15.2f} "
                  f"{float(db_pnl):>15.2f} {float(diff):>15.2f}")

        print("-" * 140)
        print(f"{'TOTAL':<10} {'':<10} {'':<12} {'':<12} "
              f"{float(total_entry_cost):>15.2f} {float(total_market_value):>15.2f} {float(total_correct_pnl):>15.2f} "
              f"{float(total_db_pnl):>15.2f} {float(total_db_pnl - total_correct_pnl):>15.2f}")

        print()
        print("=" * 140)
        print("SUMMARY:")
        print(f"  Total Entry Cost:        ${float(total_entry_cost):>15,.2f}")
        print(f"  Total Market Value:      ${float(total_market_value):>15,.2f}")
        print(f"  CORRECT Total P&L:       ${float(total_correct_pnl):>15,.2f}")
        print(f"  DB Stored Total P&L:     ${float(total_db_pnl):>15,.2f}")
        print(f"  ERROR in DB:             ${float(total_db_pnl - total_correct_pnl):>15,.2f}")
        print()

        # What equity SHOULD be
        starting_equity = Decimal('485000.00')
        correct_current_equity = starting_equity + total_correct_pnl

        print("EQUITY CALCULATION:")
        print(f"  Starting Equity:         ${float(starting_equity):>15,.2f}")
        print(f"  Correct P&L:             ${float(total_correct_pnl):>15,.2f}")
        print(f"  Correct Current Equity:  ${float(correct_current_equity):>15,.2f}")
        print()
        print(f"  Cash (100% invested):    ${float(starting_equity - total_entry_cost):>15,.2f}")
        print("=" * 140)

asyncio.run(calculate_manual_pnl())
