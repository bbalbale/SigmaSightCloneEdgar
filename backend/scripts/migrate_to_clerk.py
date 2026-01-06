#!/usr/bin/env python3
"""
Clerk Migration Script

Migrates existing demo accounts to Clerk authentication.
This script:
1. Creates Clerk users for each demo account
2. Updates database with clerk_user_id
3. Sets invite_validated=true for demo accounts
4. Sets tier='free' for demo accounts

Prerequisites:
- Run migrate_to_clerk_dryrun.py first to verify readiness
- CLERK_SECRET_KEY must be set in environment

Usage:
    cd backend
    uv run python scripts/migrate_to_clerk.py

Options:
    --dry-run    Show what would be done without making changes
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import text
from app.database import get_async_session
from app.config import settings


DEMO_ACCOUNTS = [
    {
        "email": "demo_individual@sigmasight.com",
        "password": "demo12345",
        "full_name": "Demo Individual Investor",
        "username": "demo_individual",
    },
    {
        "email": "demo_hnw@sigmasight.com",
        "password": "demo12345",
        "full_name": "Demo High Net Worth",
        "username": "demo_hnw",
    },
    {
        "email": "demo_hedgefundstyle@sigmasight.com",
        "password": "demo12345",
        "full_name": "Demo Hedge Fund",
        "username": "demo_hedgefund",
    },
]


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(text)
    print('=' * 60)


def print_step(step: int, text: str):
    print(f"\n[Step {step}] {text}")


class ClerkMigrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.clerk_secret = os.getenv('CLERK_SECRET_KEY') or getattr(settings, 'CLERK_SECRET_KEY', None)
        self.clerk_api_url = "https://api.clerk.com/v1"
        self.migrated = []
        self.skipped = []
        self.failed = []

    async def get_db_users(self) -> list[dict]:
        """Get demo users from database."""
        users = []
        async with get_async_session() as db:
            for account in DEMO_ACCOUNTS:
                result = await db.execute(
                    text("SELECT id, email, full_name, clerk_user_id FROM users WHERE email = :email"),
                    {"email": account["email"]}
                )
                row = result.fetchone()
                if row:
                    users.append({
                        "id": str(row[0]),
                        "email": row[1],
                        "full_name": row[2] or account["full_name"],
                        "clerk_user_id": row[3],
                        "password": account["password"],
                        "username": account["username"],
                    })
        return users

    async def create_clerk_user(self, email: str, password: str, full_name: str, username: str) -> str | None:
        """Create a user in Clerk and return the clerk_user_id."""
        if self.dry_run:
            print(f"      [DRY-RUN] Would create Clerk user for {email}")
            return "user_dry_run_placeholder"

        if not self.clerk_secret:
            print(f"      ❌ CLERK_SECRET_KEY not set")
            return None

        # Split name into first/last
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.clerk_api_url}/users",
                    headers={
                        "Authorization": f"Bearer {self.clerk_secret}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "email_address": [email],
                        "password": password,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "skip_password_checks": True,  # Allow demo password
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    clerk_user_id = data.get("id")
                    print(f"      ✅ Created Clerk user: {clerk_user_id}")
                    return clerk_user_id
                elif response.status_code == 422:
                    # User might already exist
                    error = response.json()
                    if "already exists" in str(error).lower():
                        print(f"      ⚠️  User already exists in Clerk, looking up...")
                        return await self.find_clerk_user(email)
                    else:
                        print(f"      ❌ Clerk API error: {error}")
                        return None
                else:
                    print(f"      ❌ Clerk API error ({response.status_code}): {response.text}")
                    return None

            except Exception as e:
                print(f"      ❌ Error creating Clerk user: {e}")
                return None

    async def find_clerk_user(self, email: str) -> str | None:
        """Find an existing Clerk user by email."""
        if not self.clerk_secret:
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.clerk_api_url}/users",
                    headers={
                        "Authorization": f"Bearer {self.clerk_secret}",
                    },
                    params={"email_address": email}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        clerk_user_id = data[0].get("id")
                        print(f"      ✅ Found existing Clerk user: {clerk_user_id}")
                        return clerk_user_id

                return None

            except Exception as e:
                print(f"      ❌ Error finding Clerk user: {e}")
                return None

    async def update_db_user(self, user_id: str, clerk_user_id: str) -> bool:
        """Update database user with Clerk info."""
        if self.dry_run:
            print(f"      [DRY-RUN] Would update DB user {user_id} with clerk_user_id")
            return True

        async with get_async_session() as db:
            try:
                await db.execute(
                    text("""
                        UPDATE users
                        SET clerk_user_id = :clerk_user_id,
                            tier = 'free',
                            invite_validated = true
                        WHERE id = :user_id
                    """),
                    {"clerk_user_id": clerk_user_id, "user_id": user_id}
                )
                await db.commit()
                print(f"      ✅ Updated database: clerk_user_id, tier=free, invite_validated=true")
                return True
            except Exception as e:
                print(f"      ❌ Error updating database: {e}")
                return False

    async def migrate_user(self, user: dict) -> bool:
        """Migrate a single user to Clerk."""
        email = user["email"]
        print(f"\n   Processing: {email}")

        # Check if already migrated
        if user.get("clerk_user_id"):
            print(f"      ⏭️  Already has clerk_user_id: {user['clerk_user_id']}")
            self.skipped.append(email)
            return True

        # Create Clerk user
        clerk_user_id = await self.create_clerk_user(
            email=email,
            password=user["password"],
            full_name=user["full_name"],
            username=user["username"],
        )

        if not clerk_user_id:
            self.failed.append(email)
            return False

        # Update database
        success = await self.update_db_user(user["id"], clerk_user_id)
        if success:
            self.migrated.append(email)
            return True
        else:
            self.failed.append(email)
            return False

    async def run(self):
        """Run the full migration."""
        print_header("CLERK MIGRATION" + (" (DRY-RUN)" if self.dry_run else ""))

        # Step 1: Get users from database
        print_step(1, "Loading demo accounts from database...")
        users = await self.get_db_users()
        print(f"   Found {len(users)} demo accounts")

        if not users:
            print("\n❌ No demo accounts found. Run database seeding first.")
            return False

        # Step 2: Migrate each user
        print_step(2, "Migrating users to Clerk...")
        for user in users:
            await self.migrate_user(user)

        # Step 3: Summary
        print_header("MIGRATION SUMMARY")
        print(f"\n   ✅ Migrated: {len(self.migrated)}")
        for email in self.migrated:
            print(f"      • {email}")

        print(f"\n   ⏭️  Skipped (already migrated): {len(self.skipped)}")
        for email in self.skipped:
            print(f"      • {email}")

        print(f"\n   ❌ Failed: {len(self.failed)}")
        for email in self.failed:
            print(f"      • {email}")

        if self.dry_run:
            print("\n[DRY-RUN] No changes were made.")
            print("Run without --dry-run to perform actual migration.")

        if len(self.failed) > 0:
            print("\n⚠️  Some migrations failed. Check errors above.")
            return False

        print("\n✅ Migration complete!")
        print("\nNext steps:")
        print("   1. Verify users in Clerk Dashboard")
        print("   2. Test login with demo accounts")
        print("   3. Deploy to production")

        return True


async def main():
    parser = argparse.ArgumentParser(description="Migrate demo accounts to Clerk")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    migrator = ClerkMigrator(dry_run=args.dry_run)
    success = await migrator.run()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
