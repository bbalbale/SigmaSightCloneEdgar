"""
Audit HNW Portfolio - Debug portfolio value discrepancies
"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.positions import Position
from sqlalchemy import select


async def audit_hnw_portfolio():
    async with AsyncSessionLocal() as db:
        portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'  # HNW

        stmt = select(Position).where(Position.portfolio_id == portfolio_id)
        result = await db.execute(stmt)
        positions = result.scalars().all()

        print(f'Total positions in database: {len(positions)}\n')
        print(f'{"Symbol":<25} | {"Qty":>12} | {"Entry $":>10} | {"Last $":>10} | {"Market Value":>15} | Class')
        print('='*100)

        total_by_class = {}

        for p in positions:
            price = float(p.last_price) if p.last_price else float(p.entry_price)
            mv = float(p.quantity) * price
            inv_class = p.investment_class or 'NULL'

            if inv_class not in total_by_class:
                total_by_class[inv_class] = 0
            total_by_class[inv_class] += mv

            print(f'{p.symbol:<25} | {float(p.quantity):>12,.2f} | {float(p.entry_price):>10,.2f} | {price:>10,.2f} | ${mv:>14,.2f} | {inv_class}')

        print('='*100)
        for inv_class, total in sorted(total_by_class.items()):
            if total > 0:
                print(f'{inv_class} Total: ${total:>,.2f}')

        grand_total = sum(total_by_class.values())
        print(f'\nGRAND TOTAL: ${grand_total:>,.2f}')
        print(f'Expected:    $2,850,000.00')
        print(f'Difference:  ${grand_total - 2850000:>,.2f}')


if __name__ == '__main__':
    asyncio.run(audit_hnw_portfolio())
