import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position

async def check():
    async with AsyncSessionLocal() as db:
        port_result = await db.execute(select(Portfolio))
        ports = port_result.scalars().all()

        pos_result = await db.execute(select(Position))
        positions = pos_result.scalars().all()

        snap_result = await db.execute(select(PortfolioSnapshot))
        snaps = snap_result.scalars().all()

        print(f'Portfolios: {len(ports)}')
        print(f'Positions: {len(positions)}')
        print(f'Snapshots: {len(snaps)}')

        if snaps:
            dates = sorted(set(s.snapshot_date for s in snaps))
            print(f'Snapshot date range: {dates[0]} to {dates[-1]}')
            print(f'Unique snapshot dates: {len(dates)}')

asyncio.run(check())
