"""Check demo users in database"""
import asyncio
from app.database import get_async_session
from sqlalchemy import select
from app.models import User

async def list_users():
    async with get_async_session() as db:
        result = await db.execute(select(User.email))
        users = result.scalars().all()

        if users:
            print("Demo users in database:")
            for email in users:
                print(f"  - {email}")
        else:
            print("No users found in database")

if __name__ == "__main__":
    asyncio.run(list_users())