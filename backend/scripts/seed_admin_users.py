"""
Seed Admin Users Script

Creates the initial admin accounts for SigmaSight Admin Dashboard.
Run this after applying the admin tables migration.

Usage:
    cd backend
    uv run python scripts/seed_admin_users.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import get_async_session
from app.models.admin import AdminUser
from app.core.auth import get_password_hash


# Admin accounts to create
ADMIN_ACCOUNTS = [
    {
        "email": "bbalbale@gmail.com",
        "password": "SigmaSight2026",
        "full_name": "Ben Balbale",
        "role": "super_admin",
    },
    {
        "email": "elliott.ng@gmail.com",
        "password": "SigmaSight2026",
        "full_name": "Elliott Ng",
        "role": "super_admin",
    },
]


async def seed_admin_users():
    """Create admin user accounts if they don't exist."""
    print("=" * 60)
    print("SigmaSight Admin User Seeding")
    print("=" * 60)

    async with get_async_session() as db:
        created_count = 0
        skipped_count = 0

        for account in ADMIN_ACCOUNTS:
            # Check if admin already exists
            result = await db.execute(
                select(AdminUser).where(AdminUser.email == account["email"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  [SKIP] {account['email']} - already exists")
                skipped_count += 1
                continue

            # Create new admin user
            admin_user = AdminUser(
                email=account["email"],
                hashed_password=get_password_hash(account["password"]),
                full_name=account["full_name"],
                role=account["role"],
                is_active=True,
            )
            db.add(admin_user)
            print(f"  [CREATE] {account['email']} ({account['role']})")
            created_count += 1

        await db.commit()

        print()
        print("=" * 60)
        print(f"Summary: {created_count} created, {skipped_count} skipped")
        print("=" * 60)

        if created_count > 0:
            print("\nAdmin accounts created successfully!")
            print("Login at: /admin/login")
        else:
            print("\nNo new accounts created (all already exist).")


if __name__ == "__main__":
    asyncio.run(seed_admin_users())
