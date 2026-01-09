"""
Test Random UUID Generation

Tests that DETERMINISTIC_UUIDS=False produces truly random UUIDs
for non-demo users (emails not ending in @sigmasight.com).
"""
import asyncio
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy import select, delete

from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.core.auth import get_password_hash
from app.core.uuid_strategy import generate_user_uuid, generate_portfolio_uuid
from app.config import settings


TEST_EMAIL = "test_random_uuid@gmail.com"
TEST_PASSWORD = "testpass123"


async def main():
    print("=" * 60)
    print("RANDOM UUID TEST")
    print("=" * 60)

    # Check current setting
    print(f"\n1. Current DETERMINISTIC_UUIDS setting: {settings.DETERMINISTIC_UUIDS}")

    if settings.DETERMINISTIC_UUIDS:
        print("   ⚠️  WARNING: DETERMINISTIC_UUIDS is True!")
        print("   Set DETERMINISTIC_UUIDS=False in .env and restart backend.")
        return

    print("   ✅ DETERMINISTIC_UUIDS is False - random UUIDs enabled")

    # Generate UUIDs using the strategy
    print(f"\n2. Testing UUID generation for: {TEST_EMAIL}")

    # What deterministic UUID WOULD have been
    deterministic_uuid = uuid5(NAMESPACE_DNS, TEST_EMAIL.lower())
    print(f"   Deterministic UUID would be: {deterministic_uuid}")

    # What we actually get with the current strategy
    random_uuid_1 = generate_user_uuid(TEST_EMAIL)
    random_uuid_2 = generate_user_uuid(TEST_EMAIL)

    print(f"   Generated UUID #1: {random_uuid_1}")
    print(f"   Generated UUID #2: {random_uuid_2}")

    # Check if they're random
    if random_uuid_1 == deterministic_uuid:
        print("   ❌ FAIL: UUID matches deterministic - not random!")
        return

    if random_uuid_1 == random_uuid_2:
        print("   ❌ FAIL: Two calls returned same UUID - not random!")
        return

    print("   ✅ UUIDs are random and different each call")

    # Test actual database creation
    print(f"\n3. Creating test user in database...")

    async with get_async_session() as db:
        # Clean up any existing test user
        await db.execute(delete(Position).where(
            Position.portfolio_id.in_(
                select(Portfolio.id).where(Portfolio.user_id.in_(
                    select(User.id).where(User.email == TEST_EMAIL)
                ))
            )
        ))
        await db.execute(delete(Portfolio).where(
            Portfolio.user_id.in_(
                select(User.id).where(User.email == TEST_EMAIL)
            )
        ))
        await db.execute(delete(User).where(User.email == TEST_EMAIL))
        await db.commit()

        # Create user with random UUID
        user_uuid = generate_user_uuid(TEST_EMAIL)
        user = User(
            id=user_uuid,
            email=TEST_EMAIL,
            full_name="Test Random UUID User",
            hashed_password=get_password_hash(TEST_PASSWORD),
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"   Created user with ID: {user.id}")
        print(f"   Email: {user.email}")

        # Verify it's not deterministic
        if str(user.id) == str(deterministic_uuid):
            print("   ❌ FAIL: Database user ID matches deterministic!")
            return

        print("   ✅ User created with random UUID")

        # Create portfolio
        print(f"\n4. Creating portfolio for test user...")
        portfolio_uuid = generate_portfolio_uuid(user.id, "Test Portfolio")
        portfolio = Portfolio(
            id=portfolio_uuid,
            user_id=user.id,
            name="Test Random UUID Portfolio",
            account_name="Test Portfolio",
            account_type="taxable",
            description="Testing random UUID generation"
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        print(f"   Created portfolio with ID: {portfolio.id}")
        print("   ✅ Portfolio created successfully")

        # Test login via API
        print(f"\n5. Testing login via API...")

    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful!")
            print(f"   Token type: {data.get('token_type')}")
            print(f"   User ID from response: {data.get('user_id')}")

            # Verify the returned user_id matches what we created
            if data.get('user_id') == str(user.id):
                print("   ✅ User ID in response matches database")
            else:
                print(f"   ❌ User ID mismatch: {data.get('user_id')} vs {user.id}")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ DETERMINISTIC_UUIDS=False is working correctly")
    print(f"✅ Non-demo users get random UUIDs")
    print(f"✅ Database operations work with random UUIDs")
    print(f"✅ Authentication works with random UUIDs")
    print(f"\nTest user credentials (for manual testing):")
    print(f"   Email: {TEST_EMAIL}")
    print(f"   Password: {TEST_PASSWORD}")
    print(f"   User ID: {user.id}")
    print(f"\nTo clean up, run this script again or delete manually.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
