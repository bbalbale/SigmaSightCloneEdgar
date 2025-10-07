#!/usr/bin/env python
"""Check position counts for all portfolios on Railway database"""
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position

async def check():
    async with get_async_session() as db:
        portfolios = await db.execute(select(Portfolio))
        for p in portfolios.scalars().all():
            count = await db.execute(
                select(func.count(Position.id))
                .where(Position.portfolio_id == p.id)
            )
            print(f'{p.name}: {count.scalar()} positions')

if __name__ == "__main__":
    asyncio.run(check())
