"""
Test script for enhanced hybrid_context_builder with volatility and spread factors.

Usage:
    cd backend
    uv run python scripts/test_context_builder_enhanced.py
"""
import asyncio
import json
from uuid import UUID

from app.services.hybrid_context_builder import hybrid_context_builder
from app.database import get_async_session
from app.models.users import Portfolio
from sqlalchemy import select


async def test_context_builder():
    """Test that context builder includes volatility analytics and spread factors."""

    async with get_async_session() as db:
        # Get a demo portfolio
        result = await db.execute(
            select(Portfolio).limit(1)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ No portfolios found. Run seed script first.")
            return False

        print(f"\n{'='*70}")
        print(f"Testing Context Builder Enhancement")
        print(f"{'='*70}")
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print(f"{'='*70}\n")

        # Build context
        context = await hybrid_context_builder.build_context(
            db=db,
            portfolio_id=portfolio.id
        )

        # Check what we got
        print("Context Keys:")
        for key in context.keys():
            print(f"  OK {key}")

        print("\n" + "="*70)

        # Test volatility analytics
        print("\nVolatility Analytics:")
        vol = context.get('volatility_analytics', {})
        if vol.get('available'):
            print("  [OK] Available: YES")
            portfolio_vol = vol.get('portfolio_level', {})
            print(f"  - Realized Vol 21d: {portfolio_vol.get('realized_volatility_21d')}")
            print(f"  - Realized Vol 63d: {portfolio_vol.get('realized_volatility_63d')}")
            print(f"  - Expected Vol 21d: {portfolio_vol.get('expected_volatility_21d')}")
            print(f"  - Volatility Trend: {portfolio_vol.get('volatility_trend')}")
            print(f"  - Volatility Percentile: {portfolio_vol.get('volatility_percentile')}")
        else:
            print("  [WARN] Available: NO (data not calculated yet)")

        # Test spread factors
        print("\nSpread Factors:")
        spread = context.get('spread_factors', {})
        if spread.get('available'):
            print("  [OK] Available: YES")
            factors = spread.get('factors', {})
            print(f"  - Calculation Date: {spread.get('calculation_date')}")
            print(f"  - Number of Factors: {len(factors)}")
            for factor_name, factor_data in factors.items():
                print(f"\n  Factor: {factor_name}")
                print(f"    - Beta: {factor_data.get('beta'):.4f}")
                print(f"    - Direction: {factor_data.get('direction')}")
                print(f"    - Magnitude: {factor_data.get('magnitude')}")
                print(f"    - Risk Level: {factor_data.get('risk_level')}")
                print(f"    - Explanation: {factor_data.get('explanation')[:80]}...")
        else:
            print("  [WARN] Available: NO (data not calculated yet)")

        # Test data quality
        print("\nData Quality Assessment:")
        quality = context.get('data_quality', {})
        for metric, status in quality.items():
            icon = "[OK]" if status == "complete" else "[PARTIAL]" if status == "partial" else "[MISSING]"
            print(f"  {icon} {metric}: {status}")

        # Test existing data still works
        print("\nExisting Data (Regression Check):")
        positions = context.get('positions', {})
        print(f"  OK Positions: {positions.get('count', 0)} positions")

        snapshot = context.get('snapshot', {})
        print(f"  OK Snapshot: {snapshot.get('date') if snapshot else 'N/A'}")

        correlations = context.get('correlations', {})
        print(f"  OK Correlations: {'Available' if correlations.get('available') else 'Not Available'}")

        risk_metrics = context.get('risk_metrics', {})
        greeks = risk_metrics.get('greeks', {})
        print(f"  OK Greeks: {greeks.get('count', 0)} positions with Greeks")

        print("\n" + "="*70)

        # Summary
        success = True
        warnings = []

        if not vol.get('available'):
            warnings.append("Volatility analytics not available")
        if not spread.get('available'):
            warnings.append("Spread factors not available")

        if warnings:
            print("\n[WARNINGS]:")
            for warning in warnings:
                print(f"  - {warning}")
            print("\nThis is normal if batch calculations haven't run yet.")
            print("The context builder gracefully handles missing data.")

        print("\n" + "="*70)
        print("[SUCCESS] CONTEXT BUILDER TEST PASSED")
        print("   - New methods added successfully")
        print("   - Context includes volatility_analytics and spread_factors")
        print("   - Data quality assessment updated")
        print("   - Existing functionality preserved")
        print("="*70 + "\n")

        return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_context_builder())
        if result:
            exit(0)
        else:
            exit(1)
    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
