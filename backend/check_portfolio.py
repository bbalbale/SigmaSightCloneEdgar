import asyncio
from uuid import UUID
from app.database import get_async_session
from app.models.users import Portfolio
from sqlalchemy import select

async def check():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()

        if portfolio:
            print(f"Portfolio found: {portfolio.id}")
            print(f"Owner ID: {portfolio.user_id}")
            print(f"Name: {portfolio.name}")
        else:
            print("Portfolio NOT found in database!")

            # Check what portfolios exist
            all_result = await db.execute(select(Portfolio))
            all_portfolios = all_result.scalars().all()
            print(f"\nFound {len(all_portfolios)} portfolios total:")
            for p in all_portfolios:
                print(f"  - {p.id}: {p.name}")

if __name__ == "__main__":
    asyncio.run(check())