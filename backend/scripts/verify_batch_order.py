"""
Simple Batch Order Verification

Checks if portfolio_snapshot runs before stress_testing in batch orchestrator.
"""
import sys
import logging

# Disable SQLAlchemy logging for cleaner output
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

async def main():
    """Verify batch orchestrator execution order"""

    print("\n" + "="*80)
    print("BATCH ORCHESTRATOR EXECUTION ORDER VERIFICATION")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get hedge fund portfolio
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_hedgefundstyle@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("\n❌ Hedge fund portfolio not found")
            return

        print(f"\n✅ Found portfolio: {portfolio.name}")
        print(f"   Portfolio ID: {portfolio.id}")

    # Run batch sequence
    print(f"\n{'='*80}")
    print("RUNNING BATCH SEQUENCE...")
    print(f"{'='*80}\n")

    results = await batch_orchestrator_v2.run_daily_batch_sequence(
        portfolio_id=str(portfolio.id)
    )

    # Extract and display job order
    print(f"\n{'='*80}")
    print("EXECUTION ORDER")
    print(f"{'='*80}\n")

    snapshot_position = None
    stress_test_position = None

    for i, result in enumerate(results, 1):
        job_name = result['job_name']
        status = result['status']
        duration = result.get('duration_seconds', 0)

        # Extract clean job name
        clean_name = job_name.split('_fcd71196')[0]  # Remove portfolio ID suffix

        emoji = "✅" if status == "completed" else "❌"
        print(f"{i:2}. {emoji} {clean_name:30} ({status:10}) {duration:.2f}s")

        # Track positions
        if 'snapshot' in job_name:
            snapshot_position = i
        elif 'stress' in job_name:
            stress_test_position = i

    # Verify order
    print(f"\n{'='*80}")
    print("ORDER VERIFICATION")
    print(f"{'='*80}\n")

    if snapshot_position and stress_test_position:
        if snapshot_position < stress_test_position:
            print(f"✅ CORRECT ORDER:")
            print(f"   portfolio_snapshot at position #{snapshot_position}")
            print(f"   stress_testing at position #{stress_test_position}")
            print(f"\n   ✓ Snapshots (with gross/net exposure) created BEFORE stress testing")
            print(f"   ✓ Stress testing can use snapshot values via get_portfolio_exposures()")
        else:
            print(f"❌ WRONG ORDER:")
            print(f"   stress_testing at position #{stress_test_position}")
            print(f"   portfolio_snapshot at position #{snapshot_position}")
            print(f"\n   ✗ Stress testing runs before snapshots exist!")
    else:
        print(f"⚠️  Could not verify order:")
        print(f"   snapshot_position = {snapshot_position}")
        print(f"   stress_test_position = {stress_test_position}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
