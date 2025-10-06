import asyncio
from app.database import AsyncSessionLocal
from app.models.market_data import CompanyProfile
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Check specific symbols that should have names
        symbols = ['PG', 'C', 'XOM', 'VTI', 'SPY', 'AAPL', 'MSFT', 'META']
        stmt = select(CompanyProfile.symbol, CompanyProfile.company_name).where(
            CompanyProfile.symbol.in_(symbols)
        )
        result = await db.execute(stmt)
        rows = result.all()

        print('\nCompany Profiles for specific symbols:')
        print('=' * 60)
        for row in rows:
            print(f'{row[0]:10} -> {row[1]}')
        print('=' * 60)
        print(f'\nFound {len(rows)} out of {len(symbols)} symbols')

if __name__ == "__main__":
    asyncio.run(main())
