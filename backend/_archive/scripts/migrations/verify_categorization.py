import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT id, name, direction, primary_investment_class FROM strategies LIMIT 10'))
        rows = result.fetchall()
        print('ID | Name | Direction | Investment Class')
        print('-' * 100)
        for row in rows:
            print(f'{row[0]} | {row[1][:30]:30} | {str(row[2]):10} | {row[3]}')

asyncio.run(check())
