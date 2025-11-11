#!/usr/bin/env python
"""
Scale Position Quantities to Match Target Exposure Percentages

Adjusts position quantities so that:
- Individual: 100% long exposure = $485,000
- HNW: 100% long exposure = $2,850,000
- Hedge Fund: 100% long + 50% short = $3,200,000 long + $1,600,000 short

This ensures position entry values exactly match the equity balance specifications.
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal, ROUND_DOWN

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position


async def scale_positions():
    """Scale position quantities to match target exposure percentages"""

    async with get_async_session() as db:
        print("=" * 100)
        print("SCALING POSITION QUANTITIES TO TARGET EXPOSURE")
        print("=" * 100)
        print()

        # Define targets: (email, portfolio_name_partial, equity_balance, long_target, short_target)
        targets = [
            ('demo_individual@sigmasight.com', None, Decimal('485000.00'), Decimal('485000.00'), Decimal('0')),
            ('demo_hnw@sigmasight.com', None, Decimal('2850000.00'), Decimal('2850000.00'), Decimal('0')),
            ('demo_hedgefundstyle@sigmasight.com', None, Decimal('3200000.00'), Decimal('3200000.00'), Decimal('1600000.00')),
            ('demo_familyoffice@sigmasight.com', 'Public Growth', Decimal('1250000.00'), Decimal('1250000.00'), Decimal('0')),
        ]

        for email, portfolio_name_partial, equity_balance, long_target, short_target in targets:
            user = (await db.execute(
                select(User).where(User.email == email)
            )).scalar_one()

            # Handle multiple portfolios for family office
            if portfolio_name_partial:
                portfolios = (await db.execute(
                    select(Portfolio).where(
                        Portfolio.user_id == user.id,
                        Portfolio.deleted_at.is_(None)
                    )
                )).scalars().all()

                portfolio = None
                for p in portfolios:
                    if portfolio_name_partial.lower() in p.name.lower():
                        portfolio = p
                        break

                if not portfolio:
                    print(f"[ERROR] Portfolio not found for {email} matching '{portfolio_name_partial}'")
                    print()
                    continue
            else:
                portfolio = (await db.execute(
                    select(Portfolio).where(
                        Portfolio.user_id == user.id,
                        Portfolio.deleted_at.is_(None)
                    )
                )).scalar_one()

            positions = (await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.deleted_at.is_(None)
                )
            )).scalars().all()

            # Calculate current exposures
            long_positions = [p for p in positions if p.quantity > 0]
            short_positions = [p for p in positions if p.quantity < 0]

            current_long = sum(p.quantity * p.entry_price for p in long_positions)
            current_short = sum(abs(p.quantity * p.entry_price) for p in short_positions)

            print(f"Portfolio: {portfolio.name}")
            print(f"  Current Long:  ${current_long:,.2f}")
            print(f"  Target Long:   ${long_target:,.2f}")
            print(f"  Current Short: ${current_short:,.2f}")
            print(f"  Target Short:  ${short_target:,.2f}")
            print()

            # Calculate scaling factors - ONLY scale down if over target
            if current_long > long_target:
                long_scale = long_target / current_long
                print(f"  Long Scale Factor:  {long_scale:.6f} (scaling DOWN)")
            else:
                long_scale = Decimal('1')
                print(f"  Long exposure already at or below target - no scaling needed")

            if current_short > short_target:
                short_scale = short_target / current_short
                print(f"  Short Scale Factor: {short_scale:.6f} (scaling DOWN)")
            else:
                short_scale = Decimal('1')
                print(f"  Short exposure already at or below target - no scaling needed")
            print()

            # Scale long positions (only if needed)
            if long_scale < Decimal('1'):
                print("  Scaling long positions DOWN...")
                for pos in long_positions:
                    old_qty = pos.quantity
                    new_qty = (pos.quantity * long_scale).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                    if new_qty != old_qty:
                        pos.quantity = new_qty
                        db.add(pos)
                        print(f"    {pos.symbol}: {old_qty} -> {new_qty}")

            # Scale short positions (only if needed)
            if short_positions and short_scale < Decimal('1'):
                print("  Scaling short positions DOWN...")
                for pos in short_positions:
                    old_qty = pos.quantity
                    # Keep negative sign, scale absolute value
                    new_qty = (pos.quantity * short_scale).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                    if new_qty != old_qty:
                        pos.quantity = new_qty
                        db.add(pos)
                        print(f"    {pos.symbol}: {old_qty} -> {new_qty}")

            # Verify new exposures
            new_long = sum(p.quantity * p.entry_price for p in long_positions)
            new_short = sum(abs(p.quantity * p.entry_price) for p in short_positions)

            print()
            print(f"  New Long Exposure:  ${new_long:,.2f} (target: ${long_target:,.2f})")
            print(f"  New Short Exposure: ${new_short:,.2f} (target: ${short_target:,.2f})")
            print(f"  New Gross Exposure: ${new_long + new_short:,.2f}")
            print()
            print("-" * 100)
            print()

        print("Committing changes...")
        await db.commit()
        print("[DONE] Position quantities scaled to target exposures")


if __name__ == "__main__":
    asyncio.run(scale_positions())
