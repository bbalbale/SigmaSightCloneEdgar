"""
Create Admin Tables and Seed Users Script

Creates the admin tables and seeds initial admin accounts directly using SQLAlchemy.
This bypasses Alembic for direct table creation against Railway.

Usage:
    cd backend
    python scripts/create_admin_tables_and_seed.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Password hashing (same as app/core/auth.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


# Railway Core Database URL
DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

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


async def create_tables_and_seed():
    """Create admin tables and seed users."""
    print("=" * 60)
    print("SigmaSight Admin Tables Creation and Seeding")
    print("=" * 60)
    print(f"\nConnecting to: {DATABASE_URL.split('@')[1]}")  # Hide password

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Check if admin_users table already exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'admin_users'
            );
        """))
        table_exists = result.scalar()

        if table_exists:
            print("\n[INFO] admin_users table already exists")
        else:
            print("\n[CREATING] admin_users table...")
            await conn.execute(text("""
                CREATE TABLE admin_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'admin',
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_login_at TIMESTAMP WITH TIME ZONE
                );
            """))
            await conn.execute(text("""
                CREATE INDEX ix_admin_users_email ON admin_users(email);
            """))
            print("  [OK] admin_users table created")

        # Check if admin_sessions table already exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'admin_sessions'
            );
        """))
        sessions_exists = result.scalar()

        if sessions_exists:
            print("[INFO] admin_sessions table already exists")
        else:
            print("[CREATING] admin_sessions table...")
            await conn.execute(text("""
                CREATE TABLE admin_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_user_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(255) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """))
            await conn.execute(text("""
                CREATE INDEX ix_admin_sessions_admin_user_id ON admin_sessions(admin_user_id);
            """))
            await conn.execute(text("""
                CREATE INDEX ix_admin_sessions_expires_at ON admin_sessions(expires_at);
            """))
            await conn.execute(text("""
                CREATE INDEX ix_admin_sessions_token_hash ON admin_sessions(token_hash);
            """))
            print("  [OK] admin_sessions table created")

    # Now seed admin users
    print("\n" + "=" * 60)
    print("Seeding Admin Users")
    print("=" * 60)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        created_count = 0
        skipped_count = 0

        for account in ADMIN_ACCOUNTS:
            # Check if admin already exists
            result = await session.execute(
                text("SELECT id FROM admin_users WHERE email = :email"),
                {"email": account["email"]}
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  [SKIP] {account['email']} - already exists")
                skipped_count += 1
                continue

            # Create new admin user
            hashed_password = get_password_hash(account["password"])
            await session.execute(
                text("""
                    INSERT INTO admin_users (email, hashed_password, full_name, role, is_active)
                    VALUES (:email, :hashed_password, :full_name, :role, true)
                """),
                {
                    "email": account["email"],
                    "hashed_password": hashed_password,
                    "full_name": account["full_name"],
                    "role": account["role"],
                }
            )
            print(f"  [CREATE] {account['email']} ({account['role']})")
            created_count += 1

        await session.commit()

        print()
        print("=" * 60)
        print(f"Summary: {created_count} created, {skipped_count} skipped")
        print("=" * 60)

        if created_count > 0:
            print("\n[SUCCESS] Admin accounts created successfully!")
            print("Login at: /admin/login")
        else:
            print("\n[INFO] No new accounts created (all already exist).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables_and_seed())
