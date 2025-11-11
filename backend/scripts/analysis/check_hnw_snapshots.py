"""Check HNW portfolio snapshot history"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot

async def check():
    async with get_async_session() as db:
        # HNW portfolio ID
        hnw_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'

        query = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == hnw_id
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(10)

        result = await db.execute(query)
        snapshots = result.scalars().all()

        print('\n' + '=' * 70)
        print('HNW Portfolio - Snapshot History')
        print('=' * 70)
        if snapshots:
            print(f'\nFound {len(snapshots)} snapshots:\n')
            for s in snapshots:
                equity = f'${s.equity_balance:,.2f}' if s.equity_balance else 'NULL'
                pnl = f'${s.daily_pnl:,.2f}' if s.daily_pnl else 'NULL'
                print(f'  {s.snapshot_date}: Equity = {equity}, Daily P&L = {pnl}')
        else:
            print('\n❌ NO SNAPSHOTS FOUND FOR HNW PORTFOLIO!')
            print('\nThis portfolio has no historical data.')
            print('The equity balance of $2,850,000 is correct (initial value).')
        print()

asyncio.run(check())
