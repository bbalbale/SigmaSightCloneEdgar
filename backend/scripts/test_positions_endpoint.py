"""Test the positions endpoint to see if it's slow."""
import asyncio
import time
from uuid import UUID
from app.database import get_async_session
from sqlalchemy import select
from app.models.users import Portfolio
from app.models.positions import Position

async def test_positions():
    portfolio_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    print(f"Testing positions query for {portfolio_id}")
    start = time.time()

    async with get_async_session() as db:
        # This is what the endpoint does
        result = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = result.scalars().all()

    elapsed = time.time() - start
    print(f"✅ Found {len(positions)} positions in {elapsed:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_positions())
