import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.positions import Position

async def check():
    async with AsyncSessionLocal() as db:
        # Check user
        user_result = await db.execute(
            select(User).where(User.email == 'demo_familyoffice@sigmasight.com')
        )
        user = user_result.scalar_one_or_none()

        if user:
            print(f'User Found: {user.email}')
            print(f'User ID: {user.id}')

            # Check portfolios
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.user_id == user.id)
            )
            portfolios = portfolio_result.scalars().all()
            print(f'\nPortfolios: {len(portfolios)}')

            total_positions = 0
            for portfolio in portfolios:
                # Count positions
                position_count = await db.execute(
                    select(func.count(Position.id)).where(Position.portfolio_id == portfolio.id)
                )
                count = position_count.scalar()
                total_positions += count
                balance = float(portfolio.equity_balance) if portfolio.equity_balance else 0
                print(f'  - {portfolio.name}: {count} positions, ${balance:,.2f}')

            print(f'\nTotal Positions: {total_positions}')
        else:
            print('User not found')

asyncio.run(check())
