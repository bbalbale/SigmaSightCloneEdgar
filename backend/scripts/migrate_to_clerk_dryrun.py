#!/usr/bin/env python3
"""
Clerk Migration Dry-Run Script

Verifies that the database and environment are ready for Clerk migration.
Run this BEFORE the actual migration to catch issues early.

Usage:
    cd backend
    uv run python scripts/migrate_to_clerk_dryrun.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import text, inspect
from app.database import get_async_session
from app.config import settings


DEMO_ACCOUNTS = [
    "demo_individual@sigmasight.com",
    "demo_hnw@sigmasight.com",
    "demo_hedgefundstyle@sigmasight.com",
]

REQUIRED_COLUMNS = [
    "clerk_user_id",
    "tier",
    "invite_validated",
    "ai_messages_used",
    "ai_messages_reset_at",
]


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(text)
    print('=' * 60)


def print_check(name: str, passed: bool, details: str = ""):
    status = "✅" if passed else "❌"
    print(f"   {status} {name}")
    if details:
        print(f"      {details}")


async def check_demo_accounts() -> tuple[bool, list[str]]:
    """Check that demo accounts exist in the database."""
    print("\n1. Checking demo accounts in database...")

    found = []
    missing = []

    async with get_async_session() as db:
        for email in DEMO_ACCOUNTS:
            result = await db.execute(
                text("SELECT id, email FROM users WHERE email = :email"),
                {"email": email}
            )
            user = result.fetchone()
            if user:
                found.append(email)
                print_check(email, True)
            else:
                missing.append(email)
                print_check(email, False, "Not found in database")

    return len(missing) == 0, missing


async def check_required_columns() -> tuple[bool, list[str]]:
    """Check that required Clerk columns exist in users table."""
    print("\n2. Checking required columns in users table...")

    missing = []

    async with get_async_session() as db:
        # Get column names from users table
        result = await db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
        """))
        existing_columns = {row[0] for row in result.fetchall()}

        for col in REQUIRED_COLUMNS:
            if col in existing_columns:
                print_check(f"users.{col}", True)
            else:
                missing.append(col)
                print_check(f"users.{col}", False, "Column missing - run migrations")

    return len(missing) == 0, missing


async def check_clerk_api() -> tuple[bool, str]:
    """Check that Clerk JWKS endpoint is reachable."""
    print("\n3. Checking Clerk API connectivity...")

    # Get Clerk domain from settings or env
    clerk_domain = getattr(settings, 'CLERK_DOMAIN', None) or os.getenv('CLERK_DOMAIN')

    if not clerk_domain:
        print_check("Clerk JWKS endpoint", False, "CLERK_DOMAIN not configured")
        return False, "CLERK_DOMAIN environment variable not set"

    # Try both possible JWKS URL formats
    jwks_urls = [
        f"https://{clerk_domain}/.well-known/jwks.json",
        f"https://{clerk_domain}/v1/.well-known/jwks.json",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in jwks_urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if "keys" in data and len(data["keys"]) > 0:
                        print_check("Clerk JWKS endpoint reachable", True, url)
                        return True, ""
            except Exception as e:
                continue

        print_check("Clerk JWKS endpoint", False, f"Could not reach JWKS at {clerk_domain}")
        return False, f"JWKS endpoint not reachable"


async def check_env_vars() -> tuple[bool, list[str]]:
    """Check that required environment variables are set."""
    print("\n4. Checking environment variables...")

    required_vars = [
        ("CLERK_SECRET_KEY", "Required for Clerk API calls"),
        ("CLERK_WEBHOOK_SECRET", "Required for webhook verification"),
        ("CLERK_DOMAIN", "Required for JWKS fetching"),
    ]

    optional_vars = [
        ("BETA_INVITE_CODE", "Invite code for new users (default: 2026-FOUNDERS-BETA)"),
    ]

    missing = []

    for var, desc in required_vars:
        value = os.getenv(var) or getattr(settings, var, None)
        if value:
            # Mask the value for security
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print_check(var, True, f"Set ({masked})")
        else:
            missing.append(var)
            print_check(var, False, desc)

    print("\n   Optional variables:")
    for var, desc in optional_vars:
        value = os.getenv(var) or getattr(settings, var, None)
        if value:
            print_check(var, True, f"Set ({value})")
        else:
            print_check(var, None, f"Not set - {desc}")

    return len(missing) == 0, missing


async def check_existing_clerk_ids() -> tuple[bool, int]:
    """Check if any users already have clerk_user_id set."""
    print("\n5. Checking for existing Clerk user IDs...")

    async with get_async_session() as db:
        result = await db.execute(text("""
            SELECT COUNT(*) FROM users WHERE clerk_user_id IS NOT NULL
        """))
        count = result.scalar()

        if count > 0:
            print_check(f"Found {count} users with clerk_user_id", True, "Already migrated")
        else:
            print_check("No users have clerk_user_id yet", True, "Ready for migration")

        return True, count


async def main():
    print_header("CLERK MIGRATION DRY-RUN")

    all_passed = True
    issues = []

    # Run all checks
    passed, missing = await check_demo_accounts()
    if not passed:
        all_passed = False
        issues.append(f"Missing demo accounts: {missing}")

    passed, missing = await check_required_columns()
    if not passed:
        all_passed = False
        issues.append(f"Missing columns: {missing}. Run: uv run alembic upgrade head")

    passed, error = await check_clerk_api()
    if not passed:
        all_passed = False
        issues.append(f"Clerk API: {error}")

    passed, missing = await check_env_vars()
    if not passed:
        all_passed = False
        issues.append(f"Missing env vars: {missing}")

    _, existing_count = await check_existing_clerk_ids()

    # Summary
    print_header("DRY-RUN SUMMARY")

    if all_passed:
        print("\n✅ ALL CHECKS PASSED - Ready for migration")
        if existing_count > 0:
            print(f"\n⚠️  Note: {existing_count} users already have clerk_user_id set.")
            print("   Migration script will skip these users.")
        print("\nNext steps:")
        print("   1. Run: uv run python scripts/migrate_to_clerk.py")
        print("   2. Verify in Clerk Dashboard that users were created")
        return 0
    else:
        print("\n❌ DRY-RUN FAILED - Fix issues before migrating")
        print("\nIssues to fix:")
        for issue in issues:
            print(f"   • {issue}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
