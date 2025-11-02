"""
Pragmatic Batch Processing Tests - Section 1.6 (Fast Smoke Tests)
Based on BATCH_TESTING_PRAGMATIC.md for demo-stage product (20 users max)

Testing Philosophy:
- Verify v3 API compatibility (not external API functionality)
- Fast smoke tests (~1-2 minutes total)
- No repeated API calls
- Focus on integration points

Updated for batch_orchestrator_v3 (November 2, 2025)
"""
import asyncio
from datetime import date
import pytest

from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3


# ============================================================================
# CRITICAL PATH TESTING - Fast Smoke Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_orchestrator_v3_api_compatibility():
    """
    Verify onboarding/batch code uses v3 API correctly.

    This is the CRITICAL test - confirms API signature and return structure match.
    Single portfolio, single run - verifies integration without testing external APIs.
    """
    print("\n" + "="*70)
    print("BATCH ORCHESTRATOR V3 API COMPATIBILITY TEST")
    print("="*70)

    portfolio_id = "550e8400-e29b-41d4-a716-446655440001"  # Growth Investor
    today = date.today()

    print(f"\n▶ Testing v3 API signature...")
    print(f"   Portfolio: {portfolio_id}")
    print(f"   Date: {today}")

    # Test v3 API signature: run_daily_batch_sequence(calculation_date, portfolio_ids)
    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=[portfolio_id]  # v3 expects list, not single ID
    )

    print(f"\n✓ Batch completed")
    print(f"   Success: {result.get('success', False)}")

    if result.get('errors'):
        print(f"   ⚠️  {len(result['errors'])} errors (graceful degradation working)")

    # CRITICAL: Verify v3 return structure (dict with phase keys)
    print("\n▶ Verifying v3 return structure...")
    assert result is not None, "Batch should return result"
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'phase_1' in result, "Missing phase_1 in result"
    assert 'phase_2' in result, "Missing phase_2 in result"
    assert 'phase_3' in result, "Missing phase_3 in result"

    print("   ✓ phase_1 present")
    print("   ✓ phase_2 present")
    print("   ✓ phase_3 present")

    print("\n" + "="*70)
    print("✓ BATCH ORCHESTRATOR V3 COMPATIBILITY VERIFIED")
    print("="*70)


@pytest.mark.asyncio
async def test_multi_portfolio_api_signature():
    """
    Verify v3 handles multiple portfolio IDs correctly.
    Tests the list parameter without making redundant API calls.
    """
    print("\n" + "="*70)
    print("MULTI-PORTFOLIO API SIGNATURE TEST")
    print("="*70)

    portfolio_ids = [
        "550e8400-e29b-41d4-a716-446655440001",  # Growth
        "550e8400-e29b-41d4-a716-446655440002",  # Conservative
    ]
    today = date.today()

    print(f"\n▶ Testing v3 with multiple portfolio IDs...")
    print(f"   Portfolios: {len(portfolio_ids)}")

    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=portfolio_ids  # v3 should accept list
    )

    assert result is not None, "Should handle multiple portfolios"
    assert 'phase_1' in result
    assert 'phase_2' in result
    assert 'phase_3' in result

    print(f"\n✓ Multi-portfolio support verified")
    print("   ✓ Accepts list of portfolio IDs")
    print("   ✓ Returns correct structure")


@pytest.mark.asyncio
async def test_all_portfolios_api_signature():
    """
    Verify v3 handles None portfolio_ids correctly (all portfolios).
    """
    print("\n" + "="*70)
    print("ALL PORTFOLIOS API SIGNATURE TEST")
    print("="*70)

    today = date.today()

    print(f"\n▶ Testing v3 with portfolio_ids=None (all portfolios)...")

    result = await batch_orchestrator_v3.run_daily_batch_sequence(
        calculation_date=today,
        portfolio_ids=None  # v3 should process all portfolios
    )

    assert result is not None, "Should handle None (all portfolios)"
    assert 'phase_1' in result
    assert 'phase_2' in result
    assert 'phase_3' in result

    print(f"\n✓ All-portfolios support verified")
    print("   ✓ Accepts None for all portfolios")
    print("   ✓ Returns correct structure")


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

pytestmark = pytest.mark.asyncio
pytest_plugins = ['pytest_asyncio']


def pytest_configure(config):
    """Configure test environment"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
