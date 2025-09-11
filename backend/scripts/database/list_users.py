#!/usr/bin/env python
"""List all users in the database"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print("Users in database:")
        print("-" * 50)
        for user in users:
            print(f"Email: {user.email}")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  ID: {user.id}")
            print()

if __name__ == "__main__":
    asyncio.run(main())