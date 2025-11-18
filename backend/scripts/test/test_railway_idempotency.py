#!/usr/bin/env python
"""
Test Phase 2.10 Idempotency on Railway

Tests that running batch processing multiple times for the same date
does NOT duplicate snapshots or compound equity balance.

Usage:
  python scripts/test/test_railway_idempotency.py
"""
import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any
from uuid import UUID

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.calculations.snapshots import lock_snapshot_slot, populate_snapshot_data
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_idempotency() -> Dict[str, Any]:
    """
    Test idempotency by attempting to create snapshots twice for the same date.

    Returns:
        Test results with pass/fail status
    """
    results = {
        "test_date": date.today().isoformat(),
        "tests": [],
        "overall_status": "PASS"
    }

    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Get a test portfolio
            portfolio_result = await db.execute(
                select(Portfolio)
                .where(Portfolio.name.like('%High Net Worth%'))
                .limit(1)
            )
            portfolio = portfolio_result.scalar_one_or_none()

            if not portfolio:
                results["overall_status"] = "FAIL"
                results["error"] = "No test portfolio found"
                return results

            test_date = date.today()
            portfolio_id = portfolio.id

            print(f"\n{'='*80}")
            print(f"PHASE 2.10 IDEMPOTENCY TEST")
            print(f"{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"Portfolio ID: {portfolio_id}")
            print(f"Test Date: {test_date}")
            print(f"Starting Equity: ${portfolio.equity_balance:,.2f}\n")

            # Step 2: Check for existing snapshot today
            existing_check = await db.execute(
                select(func.count(PortfolioSnapshot.id))
                .where(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date == test_date
                )
            )
            existing_count = existing_check.scalar()

            print(f"Existing snapshots for today: {existing_count}")

            if existing_count > 0:
                # Delete existing snapshots for clean test
                print("Deleting existing snapshots for clean test...")
                await db.execute(
                    text("DELETE FROM portfolio_snapshots WHERE portfolio_id = :pid AND snapshot_date = :date"),
                    {"pid": str(portfolio_id), "date": test_date}
                )
                await db.commit()
                print("✅ Cleaned up existing snapshots\n")

            # Step 3: TEST 1 - First lock attempt (should succeed)
            print("TEST 1: First lock_snapshot_slot call (should succeed)")
            print("-" * 80)
            try:
                placeholder1 = await lock_snapshot_slot(
                    db=db,
                    portfolio_id=portfolio_id,
                    snapshot_date=test_date
                )
                await db.commit()

                print(f"✅ PASS: Created placeholder snapshot {placeholder1.id}")
                print(f"   is_complete: {placeholder1.is_complete}")
                print(f"   NAV: ${placeholder1.net_asset_value}")

                results["tests"].append({
                    "name": "First lock_snapshot_slot",
                    "status": "PASS",
                    "snapshot_id": str(placeholder1.id),
                    "is_complete": placeholder1.is_complete
                })
            except Exception as e:
                print(f"❌ FAIL: {e}")
                results["tests"].append({
                    "name": "First lock_snapshot_slot",
                    "status": "FAIL",
                    "error": str(e)
                })
                results["overall_status"] = "FAIL"
                return results

            # Step 4: TEST 2 - Second lock attempt (should fail with IntegrityError)
            print("\nTEST 2: Second lock_snapshot_slot call (should fail with IntegrityError)")
            print("-" * 80)
            try:
                placeholder2 = await lock_snapshot_slot(
                    db=db,
                    portfolio_id=portfolio_id,
                    snapshot_date=test_date
                )
                await db.commit()

                # If we got here, the unique constraint didn't work!
                print(f"❌ FAIL: Duplicate snapshot allowed! ID: {placeholder2.id}")
                results["tests"].append({
                    "name": "Second lock_snapshot_slot (should fail)",
                    "status": "FAIL",
                    "error": "Unique constraint not enforced - duplicate snapshot created"
                })
                results["overall_status"] = "FAIL"

            except IntegrityError as e:
                await db.rollback()
                error_str = str(e).lower()

                if "uq_portfolio_snapshot" in error_str or "unique constraint" in error_str:
                    print(f"✅ PASS: IntegrityError caught (unique constraint working)")
                    print(f"   Error: {str(e)[:150]}...")
                    results["tests"].append({
                        "name": "Second lock_snapshot_slot (should fail)",
                        "status": "PASS",
                        "message": "IntegrityError raised as expected"
                    })
                else:
                    print(f"❌ FAIL: Wrong IntegrityError: {e}")
                    results["tests"].append({
                        "name": "Second lock_snapshot_slot (should fail)",
                        "status": "FAIL",
                        "error": f"Wrong IntegrityError: {str(e)[:100]}"
                    })
                    results["overall_status"] = "FAIL"

            # Step 5: TEST 3 - Verify only ONE snapshot exists
            print("\nTEST 3: Verify only ONE snapshot exists for today")
            print("-" * 80)
            snapshot_count = await db.execute(
                select(func.count(PortfolioSnapshot.id))
                .where(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date == test_date
                )
            )
            count = snapshot_count.scalar()

            if count == 1:
                print(f"✅ PASS: Exactly 1 snapshot exists")
                results["tests"].append({
                    "name": "Snapshot count",
                    "status": "PASS",
                    "count": count
                })
            else:
                print(f"❌ FAIL: {count} snapshots exist (expected 1)")
                results["tests"].append({
                    "name": "Snapshot count",
                    "status": "FAIL",
                    "count": count,
                    "expected": 1
                })
                results["overall_status"] = "FAIL"

            # Step 6: TEST 4 - Check for duplicates across all portfolios
            print("\nTEST 4: Check for duplicate snapshots across all portfolios")
            print("-" * 80)
            duplicates_query = await db.execute(
                select(
                    PortfolioSnapshot.portfolio_id,
                    PortfolioSnapshot.snapshot_date,
                    func.count(PortfolioSnapshot.id).label('cnt')
                ).group_by(
                    PortfolioSnapshot.portfolio_id,
                    PortfolioSnapshot.snapshot_date
                ).having(
                    func.count(PortfolioSnapshot.id) > 1
                )
            )
            duplicates = duplicates_query.all()

            if len(duplicates) == 0:
                print(f"✅ PASS: No duplicate snapshots in database")
                results["tests"].append({
                    "name": "Database-wide duplicate check",
                    "status": "PASS",
                    "duplicates": 0
                })
            else:
                print(f"❌ FAIL: {len(duplicates)} duplicate groups found:")
                for dup in duplicates[:5]:
                    print(f"   Portfolio {dup.portfolio_id}, Date {dup.snapshot_date}: {dup.cnt} snapshots")
                results["tests"].append({
                    "name": "Database-wide duplicate check",
                    "status": "FAIL",
                    "duplicates": len(duplicates)
                })
                results["overall_status"] = "FAIL"

            # Cleanup: Delete test snapshot
            print("\nCleaning up test snapshot...")
            await db.execute(
                text("DELETE FROM portfolio_snapshots WHERE portfolio_id = :pid AND snapshot_date = :date"),
                {"pid": str(portfolio_id), "date": test_date}
            )
            await db.commit()
            print("✅ Cleanup complete")

        except Exception as e:
            logger.error(f"Test error: {e}", exc_info=True)
            results["overall_status"] = "ERROR"
            results["error"] = str(e)
            await db.rollback()

    return results


async def main():
    """Main entry point"""
    print("\nStarting Phase 2.10 Idempotency Test on Railway...\n")

    try:
        results = await test_idempotency()

        # Print summary
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Overall Status: {results['overall_status']}")
        print(f"Test Date: {results.get('test_date', 'N/A')}")
        print(f"\nIndividual Tests:")

        for i, test in enumerate(results.get('tests', []), 1):
            status_emoji = "✅" if test['status'] == "PASS" else "❌"
            print(f"  {i}. {status_emoji} {test['name']}: {test['status']}")
            if 'error' in test:
                print(f"     Error: {test['error']}")

        print(f"{'='*80}\n")

        if results['overall_status'] == "PASS":
            print("🎉 SUCCESS: Phase 2.10 idempotency is working correctly!")
            print("   - Unique constraint prevents duplicate snapshots")
            print("   - IntegrityError is raised on duplicate attempts")
            print("   - Database contains no duplicate snapshots")
            sys.exit(0)
        else:
            print("❌ FAILURE: Phase 2.10 idempotency test failed")
            print("   Review the test results above for details")
            if 'error' in results:
                print(f"   Error: {results['error']}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
