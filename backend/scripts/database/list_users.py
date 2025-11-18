"""
List all user accounts in the database.

Usage:
    # List all users with details
    python list_users.py

    # Show only summary counts
    python list_users.py --summary
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def list_all_users(summary_only: bool = False):
    """List all users in the database with their portfolios."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).options(selectinload(User.portfolios))
        )
        users = result.scalars().all()

        if not users:
            print("No users found in database.")
            return

        demo_users = [u for u in users if u.email.startswith('demo_')]
        test_users = [u for u in users if not u.email.startswith('demo_')]

        print(f"\n{'='*80}")
        print(f"DATABASE USER SUMMARY")
        print(f"{'='*80}")
        print(f"Total Users: {len(users)}")
        print(f"  - Demo Users: {len(demo_users)}")
        print(f"  - Test Users: {len(test_users)}")
        print(f"{'='*80}\n")

        if summary_only:
            return

        if demo_users:
            print(f"{'='*80}")
            print(f"DEMO USERS ({len(demo_users)}):")
            print(f"{'='*80}\n")
            for user in demo_users:
                portfolio_count = len(user.portfolios)
                print(f"📧 {user.email}")
                print(f"   ID: {user.id}")
                print(f"   Name: {user.full_name}")
                print(f"   Portfolios: {portfolio_count}")
                print(f"   Created: {user.created_at}")
                print()

        if test_users:
            print(f"{'='*80}")
            print(f"TEST USERS ({len(test_users)}):")
            print(f"{'='*80}\n")
            for user in test_users:
                portfolio_count = len(user.portfolios)
                print(f"📧 {user.email}")
                print(f"   ID: {user.id}")
                print(f"   Name: {user.full_name}")
                print(f"   Portfolios: {portfolio_count}")
                print(f"   Created: {user.created_at}")
                print()

        print(f"{'='*80}")
        print(f"Total: {len(users)} user(s)")
        print(f"{'='*80}\n")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="List all user accounts in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show only summary counts (no detailed user info)'
    )

    args = parser.parse_args()

    await list_all_users(summary_only=args.summary)


if __name__ == "__main__":
    asyncio.run(main())
