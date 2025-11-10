#!/usr/bin/env python
"""Check hedge fund portfolio long/short exposure."""

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


async def check_hedge_fund():
    async with get_async_session() as db:
        portfolio = (await db.execute(
            select(Portfolio).where(Portfolio.name == 'Demo Hedge Fund Style Investor Portfolio')
        )).scalar_one()

        positions = list((await db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )).scalars().all())

        print('=' * 80)
        print('HEDGE FUND PORTFOLIO EXPOSURE ANALYSIS')
        print('=' * 80)
        print()

        # Calculate long and short exposures
        long_value = Decimal('0')
        short_value = Decimal('0')

        long_positions = []
        short_positions = []

        for pos in positions:
            value = pos.quantity * pos.entry_price
            if pos.quantity > 0:
                long_value += value
                if pos.investment_class == 'PUBLIC':  # Exclude options
                    long_positions.append((pos.symbol, pos.quantity, pos.entry_price, value))
            elif pos.quantity < 0:
                short_value += value
                short_positions.append((pos.symbol, pos.quantity, pos.entry_price, value))

        total_value = long_value + short_value  # short_value is negative

        print(f'Portfolio NAV: ${total_value:,.2f}')
        print()
        print(f'Long Exposure:  ${long_value:,.2f}  ({long_value / total_value * 100:.1f}% of NAV)')
        print(f'Short Exposure: ${short_value:,.2f}  ({abs(short_value) / total_value * 100:.1f}% of NAV)')
        print(f'Net Exposure:   ${total_value:,.2f}  ({total_value / total_value * 100:.1f}% of NAV)')
        print(f'Gross Exposure: ${long_value + abs(short_value):,.2f}  ({(long_value + abs(short_value)) / total_value * 100:.1f}% of NAV)')
        print()

        print('LONG POSITIONS (PUBLIC stocks only):')
        print(f"  {'Symbol':8} {'Quantity':>10} {'Price':>12} {'Value':>16}")
        print('  ' + '-' * 48)
        for symbol, qty, price, value in sorted(long_positions, key=lambda x: x[3], reverse=True)[:10]:
            print(f'  {symbol:8} {qty:>10.0f} ${price:>10,.2f} ${value:>14,.2f}')
        print(f"  {'TOTAL':8} {' ':10} {' ':12} ${long_value:>14,.2f}")
        print()

        print('SHORT POSITIONS:')
        print(f"  {'Symbol':8} {'Quantity':>10} {'Price':>12} {'Value':>16}")
        print('  ' + '-' * 48)
        for symbol, qty, price, value in sorted(short_positions, key=lambda x: abs(x[3]), reverse=True):
            print(f'  {symbol:8} {qty:>10.0f} ${price:>10,.2f} ${value:>14,.2f}')
        print(f"  {'TOTAL':8} {' ':10} {' ':12} ${short_value:>14,.2f}")
        print()

        # Check constraint
        target_long = total_value * Decimal('1.0')  # 100% of NAV
        target_short = total_value * Decimal('0.5')  # 50% of NAV

        print('CONSTRAINT CHECK:')
        print(f'  Target Long: ${target_long:,.2f} (100% of NAV)')
        print(f'  Actual Long: ${long_value:,.2f} ({long_value / total_value * 100:.1f}% of NAV)')
        print(f'  Difference: ${long_value - target_long:+,.2f}')
        print()
        print(f'  Target Short: ${-target_short:,.2f} (50% of NAV)')
        print(f'  Actual Short: ${short_value:,.2f} ({abs(short_value) / total_value * 100:.1f}% of NAV)')
        print(f'  Difference: ${short_value - (-target_short):+,.2f}')


if __name__ == "__main__":
    asyncio.run(check_hedge_fund())
