"""Check if demo users exist and test login"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User
from app.core.auth import verify_password

async def main():
    async with AsyncSessionLocal() as db:
        # Check if users exist
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print('ERROR: No users found in database')
            print('Solution: Run python scripts/database/reset_and_seed.py seed')
            return

        print(f'Found {len(users)} users in database:')
        for user in users:
            print(f'  - {user.email}')

        # Test demo user login
        demo_email = 'demo_hnw@sigmasight.com'
        demo_password = 'demo12345'

        print(f'\nTesting login for: {demo_email}')

        result = await db.execute(
            select(User).where(User.email == demo_email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f'ERROR: User {demo_email} not found')
            print('Solution: Run python scripts/database/reset_and_seed.py seed')
            return

        # Test password
        password_valid = verify_password(demo_password, user.hashed_password)

        if password_valid:
            print(f'SUCCESS: Password is correct for {demo_email}')
            print(f'User active: {user.is_active}')
        else:
            print(f'ERROR: Password is INCORRECT for {demo_email}')
            print('The password hash might be corrupted')
            print('Solution: Run python scripts/database/reset_and_seed.py reset')

if __name__ == '__main__':
    asyncio.run(main())
