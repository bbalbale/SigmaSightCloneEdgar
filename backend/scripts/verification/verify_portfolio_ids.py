#!/usr/bin/env python
"""Quick script to verify portfolio IDs match expected deterministic values."""

import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select, text

async def main():
    print("Checking portfolio IDs in database...")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        # Simple raw SQL query
        result = await db.execute(text("""
            SELECT u.email, p.id::text as portfolio_id 
            FROM users u 
            JOIN portfolios p ON u.id = p.user_id 
            WHERE u.email LIKE 'demo_%'
            ORDER BY u.email
        """))
        
        rows = result.all()
        
        # Expected deterministic IDs
        expected = {
            "demo_hedgefundstyle@sigmasight.com": "fcd71196-e93e-f000-5a74-31a9eead3118",
            "demo_hnw@sigmasight.com": "e23ab931-a033-edfe-ed4f-9d02474780b4",
            "demo_individual@sigmasight.com": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"
        }
        
        print("Portfolio IDs in your database:")
        all_match = True
        for email, portfolio_id in rows:
            expected_id = expected.get(email)
            match = "✅" if portfolio_id == expected_id else "❌"
            print(f"  {match} {email}: {portfolio_id}")
            if expected_id and portfolio_id != expected_id:
                print(f"     Expected: {expected_id}")
                all_match = False
        
        print("-" * 50)
        if all_match:
            print("✅ All portfolio IDs match expected deterministic values!")
            print("   The chat authentication issues are NOT due to portfolio ID mismatches.")
        else:
            print("❌ Portfolio IDs don't match!")
            print("   You need to reset and reseed with deterministic IDs:")
            print("   uv run python scripts/reset_and_seed.py reset --confirm")

if __name__ == "__main__":
    asyncio.run(main())