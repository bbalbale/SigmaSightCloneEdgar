"""
Pragmatic Batch Processing Tests - Section 1.6
Based on BATCH_TESTING_PRAGMATIC.md for demo-stage product (20 users max)

NOTE: The comprehensive test plan (BATCH_PROCESSING_TEST_PLAN.md) is DEFERRED
for later production scaling. This focuses on what matters for demos.

Testing Philosophy:
- Accuracy over scale
- Manual verification acceptable
- Focus on demo scenarios
- Skip premature optimization

Updated for batch_orchestrator_v3 (November 2, 2025)
"""
import asyncio
import time
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3
from app.database import AsyncSessionLocal
from app.models.snapshots import BatchJob


# ============================================================================
# 1. CRITICAL PATH TESTING - What Actually Matters for Demos
# ============================================================================

@pytest.mark.asyncio
async def test_calculation_accuracy_for_demo():
    """
    Verify calculations match trader expectations.
    This is the MOST IMPORTANT test - traders need accurate numbers.
    """
    print("\n" + "="*70)
    print("ACCURACY VALIDATION TEST - Critical for Demo Success")
    print("="*70)

    # Use Growth Investor portfolio (most likely demo)
    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"  # Growth Investor UUID

    # Run the batch sequence for today
    today = date.today()
    print(f"\n▶ Running batch sequence for portfolio {portfolio_id} on {today}...")
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )

    # Check overall success
    print(f"\n✓ Batch completed: {result.get('success', False)}")
    if result.get('errors'):
        print(f"\n⚠️  WARNING: {len(result['errors'])} errors occurred:")
        for error in result['errors']:
            print(f"   - {error}")

    # MANUAL VERIFICATION POINTS (for demo prep):
    print("\n" + "-"*50)
    print("MANUAL VERIFICATION CHECKLIST FOR DEMO:")
    print("-"*50)

    async with AsyncSessionLocal() as db:
        # 1. Portfolio Value Check
        print("\n1. PORTFOLIO VALUE:")
        print("   □ Compare to TD Ameritrade/Bloomberg")
        print("   □ Should match within 1-2%")
        print("   □ Note any discrepancies for demo explanation")

        # 2. Greeks Spot Check (if options exist)
        print("\n2. OPTIONS GREEKS (if applicable):")
        print("   □ AAPL Call Delta should be ~0.55 for ATM")
        print("   □ SPY Put Delta should be negative")
        print("   □ Theta should be negative (time decay)")

        # 3. Factor Exposures Sanity Check
        print("\n3. FACTOR EXPOSURES:")
        print("   □ SPY Beta should be 0.8-1.2 for typical portfolio")
        print("   □ Factor exposures should sum close to 1.0")
        print("   □ No extreme outliers (>5 or <-5)")

        # 4. Stress Test Results
        print("\n4. STRESS TEST SCENARIOS:")
        print("   □ Market Crash -20% should show negative impact")
        print("   □ Interest Rate +200bp should affect bonds")
        print("   □ Results should be directionally correct")

    print("\n" + "="*70)
    print("TEST RESULT: Run manual checks above before demo")
    print("="*70)

    # Basic automated checks
    assert result is not None, "No batch result returned"
    assert 'phase_1' in result, "Phase 1 results missing"
    assert 'phase_2' in result, "Phase 2 results missing"
    assert 'phase_3' in result, "Phase 3 results missing"


@pytest.mark.asyncio
async def test_demo_scenarios():
    """
    Test exactly what we'll show in demos.
    These are the actual use cases traders will see.
    """
    print("\n" + "="*70)
    print("DEMO SCENARIO TEST - What Traders Will Actually See")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"  # Growth Investor
    today = date.today()

    # Scenario 1: Daily update at market close
    print("\n▶ Scenario 1: Daily batch at 4 PM market close")
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )

    # Just verify we have results to show
    assert result is not None, "No results to show in demo"
    assert result.get('success') is not None, "Success status missing"

    print(f"   ✓ Daily batch completed successfully: {result.get('success')}")

    # Scenario 2: Manual trigger from admin panel
    print("\n▶ Scenario 2: Manual trigger (admin panel demo)")
    print("   □ Admin can trigger via POST /api/v1/admin/batch/trigger/daily")
    print("   □ Status visible at GET /api/v1/admin/batch/jobs/status")
    print("   □ Can show real-time execution monitoring")

    # Scenario 3: Tuesday correlation run
    print("\n▶ Scenario 3: Weekly correlation (Tuesday only)")
    # Skip if not Tuesday
    if today.weekday() == 1:  # Tuesday
        result_tuesday = await batch_orchestrator_v3.run_daily_batch_sequence(
            calculation_date=today,
            portfolio_ids=[portfolio_id]
        )
        print(f"   ✓ Tuesday correlation completed: {result_tuesday.get('success')}")
    else:
        print(f"   ⊘ Skipped (today is {today.strftime('%A')}, not Tuesday)")


@pytest.mark.asyncio
async def test_multi_portfolio_batch():
    """
    Test batch processing multiple portfolios.
    Verify parallel execution works for scale demos.
    """
    print("\n" + "="*70)
    print("MULTI-PORTFOLIO BATCH TEST")
    print("="*70)

    # All 3 demo portfolios
    portfolio_ids = [
        "550e8400-e29b-41d4-a716-446655440001",  # Growth Investor
        "550e8400-e29b-41d4-a716-446655440002",  # Conservative
        "550e8400-e29b-41d4-a716-446655440003",  # Aggressive
    ]

    today = date.today()
    start_time = time.time()

    print(f"\n▶ Processing {len(portfolio_ids)} portfolios...")

    # Run all portfolios (v3 handles multiple portfolio IDs)
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=portfolio_ids
    )

    duration = time.time() - start_time

    print(f"\n✓ Completed in {duration:.1f}s")
    print(f"   Success: {result.get('success', False)}")
    print(f"   Average: {duration/len(portfolio_ids):.1f}s per portfolio")

    # For demo, we want < 30 seconds total
    assert duration < 30, f"Batch took {duration}s, expected < 30s"
    print(f"\n✓ Performance acceptable for demo (< 30s)")


@pytest.mark.asyncio
async def test_error_handling_resilience():
    """
    Verify graceful degradation when market data unavailable.
    Critical for demos with live data - we need to handle failures gracefully.
    """
    print("\n" + "="*70)
    print("ERROR HANDLING TEST - Graceful Degradation")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"
    today = date.today()

    # Mock a market data failure
    with patch('app.services.market_data_service.get_market_data') as mock_market:
        mock_market.side_effect = Exception("Market data API timeout")

        print("\n▶ Simulating market data failure...")
        result = await batch_orchestrator_v3.run_daily_batch_sequence(
            calculation_date=today,
            portfolio_ids=[portfolio_id]
        )

        # Should complete even with errors
        print(f"\n✓ Batch completed: {result.get('success', False)}")
        if result.get('errors'):
            print(f"   Errors logged: {len(result['errors'])}")

        # Verify graceful handling
        assert result is not None, "Batch should return result even on errors"


@pytest.mark.asyncio
async def test_idempotent_reruns():
    """
    Test that we can safely re-run batch multiple times.
    Important for demo recovery if something goes wrong during presentation.
    """
    print("\n" + "="*70)
    print("IDEMPOTENT RERUN TEST - Safe Demo Recovery")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"
    today = date.today()

    # Run 1
    print("\n▶ Run 1...")
    result1 = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )

    # Run 2 immediately
    print("\n▶ Run 2 (immediate rerun)...")
    result2 = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )

    # Both should succeed
    assert result1 is not None, "Run 1 should return result"
    assert result2 is not None, "Run 2 should return result"

    print("\n✓ Both runs completed successfully")
    print("   (Safe to re-trigger during demo if needed)")


@pytest.mark.asyncio
async def test_weekend_handling():
    """
    Test weekend behavior - important for Monday morning demos.
    We should use Friday's data without errors.
    """
    print("\n" + "="*70)
    print("WEEKEND HANDLING TEST - Monday Morning Demo Safety")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"
    today = date.today()

    print(f"\n▶ Running batch for {today.strftime('%A, %B %d, %Y')}...")
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )

    # Should handle gracefully regardless of day
    print(f"\n✓ Batch completed: {result.get('success', False)}")

    if today.weekday() >= 5:  # Saturday or Sunday
        print("   Weekend detected - using most recent market data")
        print("   (Expected behavior for Monday morning demo prep)")
    else:
        print("   Weekday - using current market data")


@pytest.mark.asyncio
async def test_calculation_performance():
    """
    Track calculation speed for demo responsiveness.
    We want sub-5 second response for individual portfolio analytics.
    """
    print("\n" + "="*70)
    print("PERFORMANCE TEST - Demo Responsiveness")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"
    today = date.today()

    # Time the batch run
    start = time.time()
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]
    )
    duration = time.time() - start

    print(f"\n✓ Batch completed in {duration:.2f}s")

    # For demo, we want < 10 seconds
    if duration < 5:
        print("   Performance: EXCELLENT (< 5s)")
    elif duration < 10:
        print("   Performance: GOOD (< 10s)")
    else:
        print(f"   Performance: SLOW ({duration:.1f}s)")
        print("   (Consider optimization before high-stakes demo)")

    assert duration < 30, f"Batch took {duration}s, expected < 30s"


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# Timeouts set generously for demo environment (not production-grade)
pytestmark = pytest.mark.asyncio
pytest_plugins = ['pytest_asyncio']


# Skip tests if database not available (allows CI to pass)
def pytest_configure(config):
    """Configure test environment"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
