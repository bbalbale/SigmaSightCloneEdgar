import asyncio
from app.database import AsyncSessionLocal
from app.models.market_data import CompanyProfile
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        stmt = select(CompanyProfile.symbol, CompanyProfile.company_name).limit(10)
        result = await db.execute(stmt)
        rows = result.all()
        print('\nCompany Profiles in DB:')
        print('=' * 50)
        for row in rows:
            print(f'{row[0]:10} -> {row[1]}')
        print('=' * 50)

if __name__ == "__main__":
    asyncio.run(main())
