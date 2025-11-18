"""
Delete a user account from the database.

⚠️  WARNING: This script permanently deletes users and all their data!
⚠️  Run list_users.py first to see what users exist before deleting.

Usage:
    # Delete specific user by email
    python delete_users.py --email test@example.com

    # Skip confirmation prompt (use with caution!)
    python delete_users.py --email test@example.com --confirm
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# CRITICAL: Ensure DATABASE_URL uses asyncpg driver
# Railway sets DATABASE_URL with postgresql:// which loads psycopg2
# We need postgresql+asyncpg:// for async operations
if "DATABASE_URL" in os.environ:
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("postgresql://"):
        os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        print(f"✓ Modified DATABASE_URL to use asyncpg driver")

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.users import User
from app.core.logging import get_logger

logger = get_logger(__name__)


async def delete_user_by_email(email: str, confirm: bool = False):
    """Delete a specific user by email."""
    async with AsyncSessionLocal() as db:
        # Find user
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.portfolios))
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User with email '{email}' not found.")
            return False

        portfolio_count = len(user.portfolios)

        print(f"\n{'='*80}")
        print(f"USER TO DELETE:")
        print(f"{'='*80}")
        print(f"Email: {user.email}")
        print(f"ID: {user.id}")
        print(f"Name: {user.full_name}")
        print(f"Portfolios: {portfolio_count}")
        print(f"Created: {user.created_at}")
        print(f"{'='*80}\n")

        if not confirm:
            print("⚠️  This will permanently delete:")
            print(f"   - The user account")
            print(f"   - {portfolio_count} portfolio(s)")
            print(f"   - All positions, calculations, and related data")
            print()
            response = input("Type 'DELETE' to confirm deletion: ")
            if response != 'DELETE':
                print("Deletion cancelled.")
                return False

        try:
            # Delete user (cascades to portfolios and positions via database constraints)
            await db.delete(user)
            await db.commit()

            print(f"\n✅ Successfully deleted user: {email}")
            print(f"   - Deleted {portfolio_count} portfolio(s) and all associated data\n")
            return True

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error deleting user: {e}\n")
            logger.error(f"Error deleting user {email}: {e}")
            return False




async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Delete a user account from the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--email',
        type=str,
        required=True,
        help='Email address of user to delete'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt (use with caution!)'
    )

    args = parser.parse_args()

    await delete_user_by_email(args.email, confirm=args.confirm)


if __name__ == "__main__":
    asyncio.run(main())
