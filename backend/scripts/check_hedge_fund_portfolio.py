"""
Check Hedge Fund Portfolio Data
"""
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.market_data import FactorExposure

async def main():
    async with AsyncSessionLocal() as db:
        # Get hedge fund portfolio
        stmt = select(Portfolio).join(User).where(User.email == 'demo_hedgefundstyle@sigmasight.com')
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print('Portfolio not found')
            return

        print(f'Portfolio: {portfolio.name}')
        print(f'ID: {portfolio.id}')

        # Get positions by investment class
        positions_stmt = select(
            Position.investment_class,
            func.count(Position.id).label('count'),
            func.sum(Position.market_value).label('total_value')
        ).where(
            Position.portfolio_id == portfolio.id
        ).group_by(Position.investment_class)

        positions_result = await db.execute(positions_stmt)
        positions_by_class = positions_result.all()

        print(f'\nPositions by Investment Class:')
        for inv_class, count, total_value in positions_by_class:
            print(f'  {inv_class}: {count} positions, ${total_value:,.2f}')

        # Check factor exposures
        exposures_stmt = select(func.count(FactorExposure.id)).where(
            FactorExposure.portfolio_id == portfolio.id
        )
        exposures_result = await db.execute(exposures_stmt)
        exposure_count = exposures_result.scalar()

        print(f'\nFactor Exposures: {exposure_count}')

        # Get all positions details
        all_positions_stmt = select(Position).where(Position.portfolio_id == portfolio.id)
        all_positions_result = await db.execute(all_positions_stmt)
        all_positions = all_positions_result.scalars().all()

        print(f'\nAll Positions ({len(all_positions)} total):')
        for pos in all_positions:
            print(f'  {pos.symbol:10s} {pos.position_type.name:6s} {pos.investment_class:10s} ${pos.market_value:>12,.2f}')

if __name__ == "__main__":
    asyncio.run(main())
