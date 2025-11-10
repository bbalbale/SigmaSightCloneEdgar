#!/usr/bin/env python
"""
Fix hedge fund portfolio to meet 100% long / 50% short constraint.

Target:
- Starting Equity: $3,200,000 (just below)
- Long Exposure: 100% of equity = $3,200,000
- Short Exposure: 50% of equity = $1,600,000
- NAV (Net Exposure): Long - Short = $1,600,000 (50% of equity)

Note: Equity is the starting capital. NAV is the net market exposure.
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio


async def fix_hedge_fund():
    async with get_async_session() as db:
        portfolio = (await db.execute(
            select(Portfolio).where(Portfolio.name == 'Demo Hedge Fund Style Investor Portfolio')
        )).scalar_one()

        positions = list((await db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )).scalars().all())

        print('=' * 80)
        print('FIXING HEDGE FUND EXPOSURE TO 100% LONG / 50% SHORT')
        print('=' * 80)
        print()

        # Current state
        long_value = sum(pos.quantity * pos.entry_price for pos in positions if pos.quantity > 0)
        short_value = sum(pos.quantity * pos.entry_price for pos in positions if pos.quantity < 0)
        current_nav = long_value + short_value  # Net exposure

        # Equity = Long + Short (where short is negative)
        # For leverage, we need to back-calculate what equity would support this
        # Assuming target is 100% long, 50% short: Equity = (Long + Short) / 0.5
        # Actually, Long - |Short| = NAV, and if Long=100% and Short=50%, then NAV=50% of Equity
        # So Equity = NAV / 0.5
        current_equity_implied = current_nav / Decimal('0.5')

        print('CURRENT STATE:')
        print(f'  Long: ${long_value:,.2f}')
        print(f'  Short: ${short_value:,.2f}')
        print(f'  NAV (Net Exposure): ${current_nav:,.2f}')
        print(f'  Implied Equity: ${current_equity_implied:,.2f}')
        print(f'  Long as % of implied equity: {long_value/current_equity_implied*100:.1f}%')
        print(f'  Short as % of implied equity: {abs(short_value)/current_equity_implied*100:.1f}%')
        print()

        # Target state
        target_equity = Decimal('3199900.00')  # Just below $3.2M
        target_long = target_equity * Decimal('1.0')  # 100% of equity
        target_short = target_equity * Decimal('0.5')  # 50% of equity
        target_nav = target_long - target_short  # NAV = Long - |Short|

        print('TARGET STATE:')
        print(f'  Target Equity: ${target_equity:,.2f}')
        print(f'  Long: ${target_long:,.2f} (100% of equity)')
        print(f'  Short: ${-target_short:,.2f} (50% of equity)')
        print(f'  NAV (Net Exposure): ${target_nav:,.2f} (50% of equity)')
        print()

        # Calculate scale factors
        long_scale = target_long / long_value
        short_scale = target_short / abs(short_value)

        print('SCALE FACTORS:')
        print(f'  Long positions: {long_scale:.6f} (reduce by {(1-long_scale)*100:.1f}%)')
        print(f'  Short positions: {short_scale:.6f} (reduce by {(1-short_scale)*100:.1f}%)')
        print()

        # Apply scaling to quantities (keep prices at June 30 values)
        print('ADJUSTING QUANTITIES:')
        print(f"  {'Symbol':10} {'Old Qty':>10} {'New Qty':>10} {'Price':>12} {'New Value':>16}")
        print('  ' + '-' * 60)

        for pos in positions:
            old_qty = pos.quantity

            if pos.quantity > 0:
                # Scale down long positions
                new_qty = (pos.quantity * long_scale).quantize(Decimal('1'))
            elif pos.quantity < 0:
                # Scale down short positions (make less negative)
                new_qty = (pos.quantity * short_scale).quantize(Decimal('1'))
            else:
                # Options with 0 quantity
                new_qty = pos.quantity

            if new_qty != old_qty and pos.entry_price > 0:
                pos.quantity = new_qty
                db.add(pos)
                new_value = new_qty * pos.entry_price
                print(f'  {pos.symbol:10} {old_qty:>10.0f} {new_qty:>10.0f} ${pos.entry_price:>10,.2f} ${new_value:>14,.2f}')

        # Verify new state
        new_long = sum(pos.quantity * pos.entry_price for pos in positions if pos.quantity > 0)
        new_short = sum(pos.quantity * pos.entry_price for pos in positions if pos.quantity < 0)
        new_nav = new_long + new_short

        print()
        print('NEW STATE:')
        print(f'  Long: ${new_long:,.2f}')
        print(f'  Short: ${new_short:,.2f}')
        print(f'  NAV (Net Exposure): ${new_nav:,.2f}')
        print(f'  Long as % of equity: {new_long/target_equity*100:.1f}%')
        print(f'  Short as % of equity: {abs(new_short)/target_equity*100:.1f}%')
        print(f'  NAV as % of equity: {new_nav/target_equity*100:.1f}%')
        print()

        print('VERIFICATION:')
        print(f'  Target Equity: ${target_equity:,.2f}')
        print()
        print(f'  Target Long (100% of equity): ${target_long:,.2f}')
        print(f'  Actual Long: ${new_long:,.2f}')
        print(f'  Difference: ${new_long - target_long:+,.2f}')
        print()
        print(f'  Target Short (50% of equity): ${-target_short:,.2f}')
        print(f'  Actual Short: ${new_short:,.2f}')
        print(f'  Difference: ${new_short - (-target_short):+,.2f}')
        print()
        print(f'  Target NAV (50% of equity): ${target_nav:,.2f}')
        print(f'  Actual NAV: ${new_nav:,.2f}')
        print(f'  Difference: ${new_nav - target_nav:+,.2f}')
        print()

        response = input('Apply these changes? (yes/no): ')

        if response.lower() == 'yes':
            await db.commit()
            print('[OK] Changes committed')
        else:
            await db.rollback()
            print('[CANCELLED] Changes rolled back')


if __name__ == "__main__":
    asyncio.run(fix_hedge_fund())
