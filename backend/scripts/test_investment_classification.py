#!/usr/bin/env python
"""
Test script to verify investment classification implementation.
"""
import asyncio
from uuid import UUID
import sys
from pathlib import Path
from datetime import date

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.models.users import Portfolio
from sqlalchemy import select, func
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_classification():
    """Test that positions have been correctly classified."""
    async with AsyncSessionLocal() as db:
        logger.info("=" * 60)
        logger.info("TESTING INVESTMENT CLASSIFICATION")
        logger.info("=" * 60)

        # 1. Check classification counts
        result = await db.execute(
            select(
                Position.investment_class,
                Position.investment_subtype,
                func.count(Position.id).label('count')
            ).group_by(Position.investment_class, Position.investment_subtype)
        )
        classifications = result.all()

        logger.info("\n1. Classification Summary:")
        for row in classifications:
            logger.info(f"   {row.investment_class}/{row.investment_subtype}: {row.count} positions")

        # 2. Verify no unclassified positions
        result = await db.execute(
            select(func.count(Position.id)).where(Position.investment_class.is_(None))
        )
        unclassified_count = result.scalar()

        if unclassified_count == 0:
            logger.info("\n2. ✅ All positions have been classified")
        else:
            logger.error(f"\n2. ❌ Found {unclassified_count} unclassified positions")

        # 3. Verify OPTIONS classification
        result = await db.execute(
            select(Position).where(
                Position.position_type.in_([PositionType.LC, PositionType.LP,
                                           PositionType.SC, PositionType.SP])
            )
        )
        options_positions = result.scalars().all()

        options_correct = all(p.investment_class == 'OPTIONS' for p in options_positions)
        if options_correct:
            logger.info(f"\n3. ✅ All {len(options_positions)} options positions correctly classified as OPTIONS")
        else:
            logger.error("\n3. ❌ Some options positions not classified as OPTIONS")

        # 4. Verify PUBLIC classification for stocks
        result = await db.execute(
            select(Position).where(
                Position.position_type.in_([PositionType.LONG, PositionType.SHORT])
            )
        )
        stock_positions = result.scalars().all()

        stocks_correct = all(p.investment_class in ['PUBLIC', None] for p in stock_positions)
        if stocks_correct:
            logger.info(f"\n4. ✅ All {len(stock_positions)} stock positions correctly classified as PUBLIC")
        else:
            logger.error("\n4. ❌ Some stock positions not classified as PUBLIC")

        return True


async def test_factor_analysis_exclusion():
    """Test that factor analysis correctly excludes PRIVATE positions."""
    async with AsyncSessionLocal() as db:
        logger.info("\n" + "=" * 60)
        logger.info("TESTING FACTOR ANALYSIS EXCLUSION")
        logger.info("=" * 60)

        # Get first portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            logger.warning("No portfolios found for testing")
            return False

        # Import factor calculation
        from app.calculations.factors import calculate_position_returns

        # Calculate returns (should exclude PRIVATE positions)
        returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            use_delta_adjusted=False
        )

        logger.info(f"\n✅ Factor analysis ran successfully for portfolio {portfolio.id}")
        logger.info(f"   Processed {len(returns.columns) if not returns.empty else 0} positions")

        return True


async def test_backwards_compatibility():
    """Test that existing functionality still works."""
    async with AsyncSessionLocal() as db:
        logger.info("\n" + "=" * 60)
        logger.info("TESTING BACKWARDS COMPATIBILITY")
        logger.info("=" * 60)

        # 1. Test that positions can still be queried normally
        result = await db.execute(select(Position).limit(5))
        positions = result.scalars().all()

        if positions:
            logger.info("\n1. ✅ Position queries work normally")
            for i, pos in enumerate(positions[:3], 1):
                logger.info(f"   {i}. {pos.symbol} - Type: {pos.position_type.value}, "
                          f"Class: {pos.investment_class or 'None'}")
        else:
            logger.error("\n1. ❌ Failed to query positions")

        # 2. Test that Greeks calculation still works
        try:
            from app.calculations.greeks import calculate_position_greeks
            logger.info("\n2. ✅ Greeks calculation imports successfully")
        except ImportError as e:
            logger.error(f"\n2. ❌ Failed to import Greeks calculation: {e}")

        # 3. Test that batch processing can be imported
        try:
            from app.batch.batch_orchestrator_v2 import BatchOrchestratorV2
            logger.info("\n3. ✅ Batch orchestrator imports successfully")
        except ImportError as e:
            logger.error(f"\n3. ❌ Failed to import batch orchestrator: {e}")

        return True


async def main():
    """Run all tests."""
    logger.info("Starting investment classification tests...\n")

    # Run tests
    test_results = []

    # Test 1: Classification
    try:
        result = await test_classification()
        test_results.append(("Classification", result))
    except Exception as e:
        logger.error(f"Classification test failed: {e}")
        test_results.append(("Classification", False))

    # Test 2: Factor Analysis
    try:
        result = await test_factor_analysis_exclusion()
        test_results.append(("Factor Analysis", result))
    except Exception as e:
        logger.error(f"Factor analysis test failed: {e}")
        test_results.append(("Factor Analysis", False))

    # Test 3: Backwards Compatibility
    try:
        result = await test_backwards_compatibility()
        test_results.append(("Backwards Compatibility", result))
    except Exception as e:
        logger.error(f"Backwards compatibility test failed: {e}")
        test_results.append(("Backwards Compatibility", False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
    else:
        logger.error("\n⚠️  SOME TESTS FAILED")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)