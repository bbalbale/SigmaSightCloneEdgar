"""
Verify private investment positions in the High Net Worth portfolio.
"""

import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.users import Portfolio, User
from app.models.positions import Position

async def verify_private_positions():
    async with AsyncSessionLocal() as session:
        # Find HNW portfolio
        result = await session.execute(
            select(Portfolio)
            .join(User, Portfolio.user_id == User.id)
            .where(User.email == 'demo_hnw@sigmasight.com')
        )
        portfolio = result.scalars().first()

        # Count positions by investment class
        count_result = await session.execute(
            select(Position.investment_class, func.count(Position.id))
            .where(Position.portfolio_id == portfolio.id)
            .group_by(Position.investment_class)
            .order_by(Position.investment_class)
        )

        print('High Net Worth Portfolio - Position Summary:')
        print('-' * 50)
        total = 0
        for row in count_result:
            print(f'{row[0]:<15} {row[1]:>5} positions')
            total += row[1]
        print(f'{"TOTAL":<15} {total:>5} positions')

        # Show private positions details
        private_result = await session.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.investment_class == 'PRIVATE')
            .order_by(Position.symbol)
        )
        private_positions = private_result.scalars().all()

        print()
        print('Private Investment Positions:')
        print('-' * 50)
        for pos in private_positions:
            print(f'{pos.symbol:<25} {pos.investment_subtype:<20} ${pos.market_value:,.2f}')

        # Total value by investment class
        print()
        print('Portfolio Value by Investment Class:')
        print('-' * 50)

        all_positions_result = await session.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
        )
        all_positions = all_positions_result.scalars().all()

        value_by_class = {}
        for pos in all_positions:
            class_name = pos.investment_class or 'UNKNOWN'
            if class_name not in value_by_class:
                value_by_class[class_name] = 0
            if pos.market_value:
                value_by_class[class_name] += float(pos.market_value)

        total_value = sum(value_by_class.values())
        for class_name in sorted(value_by_class.keys()):
            value = value_by_class[class_name]
            pct = (value / total_value * 100) if total_value > 0 else 0
            print(f'{class_name:<15} ${value:>15,.2f}  ({pct:>5.1f}%)')
        print('-' * 50)
        print(f'{"TOTAL":<15} ${total_value:>15,.2f}  (100.0%)')

if __name__ == "__main__":
    asyncio.run(verify_private_positions())