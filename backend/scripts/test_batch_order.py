"""
Test Batch Orchestrator Job Execution Order

Verifies that portfolio_snapshot runs before stress_testing.
"""
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Test batch orchestrator execution order for hedge fund portfolio"""

    print("\n" + "="*80)
    print("TESTING BATCH ORCHESTRATOR EXECUTION ORDER")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get hedge fund portfolio
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_hedgefundstyle@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ Hedge fund portfolio not found")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"ID: {portfolio.id}")

        # Run batch sequence for this portfolio only
        print(f"\nRunning batch orchestrator...")
        print(f"Expected order:")
        print(f"  1. market_data_update")
        print(f"  2. position_values_update")
        print(f"  3. portfolio_aggregation")
        print(f"  4. factor_analysis")
        print(f"  5. market_risk_scenarios")
        print(f"  6. portfolio_snapshot      ← Creates gross/net exposure")
        print(f"  7. stress_testing          ← Uses gross/net exposure")
        print(f"  8. position_correlations")

        results = await batch_orchestrator_v2.run_daily_batch_sequence(
            portfolio_id=str(portfolio.id)
        )

        # Display results in order
        print(f"\n{'='*80}")
        print(f"EXECUTION RESULTS")
        print(f"{'='*80}")

        snapshot_order = None
        stress_test_order = None

        for i, result in enumerate(results, 1):
            job_name = result['job_name'].split('_')[0]  # Extract first part
            status = result['status']
            duration = result.get('duration_seconds', 0)

            emoji = "✅" if status == "completed" else "❌"
            print(f"{i}. {emoji} {job_name}: {status} ({duration:.2f}s)")

            # Track snapshot and stress test positions
            if 'snapshot' in result['job_name']:
                snapshot_order = i
            elif 'stress' in result['job_name']:
                stress_test_order = i

        # Verify correct order
        print(f"\n{'='*80}")
        print(f"ORDER VERIFICATION")
        print(f"{'='*80}")

        if snapshot_order and stress_test_order:
            if snapshot_order < stress_test_order:
                print(f"✅ CORRECT ORDER: portfolio_snapshot (#{snapshot_order}) ran before stress_testing (#{stress_test_order})")
            else:
                print(f"❌ WRONG ORDER: stress_testing (#{stress_test_order}) ran before portfolio_snapshot (#{snapshot_order})")
        else:
            print(f"⚠️  Could not verify order (snapshot_order={snapshot_order}, stress_test_order={stress_test_order})")


if __name__ == "__main__":
    asyncio.run(main())
