#!/usr/bin/env python
"""
Test backwards compatibility after adding investment classification.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.models.users import Portfolio
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_position_queries():
    """Test that position queries work normally."""
    async with AsyncSessionLocal() as db:
        # Test 1: Basic position query
        result = await db.execute(select(Position).limit(5))
        positions = result.scalars().all()

        logger.info("Test 1: Basic Position Query")
        logger.info(f"  Found {len(positions)} positions")
        for pos in positions[:2]:
            logger.info(f"  - {pos.symbol}: {pos.position_type.value}, "
                       f"investment_class={pos.investment_class}")

        # Test 2: Query with WHERE clause on existing fields
        result = await db.execute(
            select(Position).where(Position.position_type == PositionType.LONG)
        )
        long_positions = result.scalars().all()
        logger.info(f"\nTest 2: Query LONG positions")
        logger.info(f"  Found {len(long_positions)} LONG positions")

        # Test 3: Query with NULL investment_class (backwards compat)
        result = await db.execute(
            select(Position).where(Position.investment_class.is_(None))
        )
        unclassified = result.scalars().all()
        logger.info(f"\nTest 3: Query NULL investment_class")
        logger.info(f"  Found {len(unclassified)} unclassified positions (expected 0)")

        return len(positions) > 0


async def test_greeks_calculation():
    """Test that Greeks calculation still works."""
    try:
        from app.calculations.greeks import calculate_position_greeks
        from app.models.positions import Position

        async with AsyncSessionLocal() as db:
            # Get an options position
            result = await db.execute(
                select(Position).where(
                    Position.position_type.in_([PositionType.LC, PositionType.LP])
                ).limit(1)
            )
            option_position = result.scalar_one_or_none()

            if option_position:
                # Mock market data for testing
                position_data = {
                    'position_type': option_position.position_type.value,
                    'quantity': float(option_position.quantity),
                    'strike_price': float(option_position.strike_price) if option_position.strike_price else 100,
                    'expiration_date': option_position.expiration_date,
                    'underlying_price': 100,
                    'days_to_expiry': 30,
                    'implied_volatility': 0.25
                }

                greeks = await calculate_position_greeks(position_data)
                logger.info("\nGreeks Calculation Test")
                logger.info(f"  Position: {option_position.symbol}")
                logger.info(f"  Greeks calculated: {greeks}")
                return True
            else:
                logger.warning("\nNo options positions found for Greeks test")
                return True

    except Exception as e:
        logger.error(f"Greeks calculation failed: {e}")
        return False


async def test_portfolio_queries():
    """Test portfolio-related queries."""
    async with AsyncSessionLocal() as db:
        # Get portfolios with positions
        result = await db.execute(select(Portfolio).limit(3))
        portfolios = result.scalars().all()

        logger.info("\nPortfolio Query Test")
        for portfolio in portfolios:
            # Count positions for this portfolio
            result = await db.execute(
                select(Position).where(Position.portfolio_id == portfolio.id)
            )
            positions = result.scalars().all()

            # Count by investment_class
            class_counts = {}
            for pos in positions:
                cls = pos.investment_class or 'UNCLASSIFIED'
                class_counts[cls] = class_counts.get(cls, 0) + 1

            logger.info(f"  Portfolio {portfolio.name}:")
            logger.info(f"    Total positions: {len(positions)}")
            for cls, count in class_counts.items():
                logger.info(f"    {cls}: {count}")

        return True


async def main():
    """Run all backwards compatibility tests."""
    logger.info("="*60)
    logger.info("BACKWARDS COMPATIBILITY TESTS")
    logger.info("="*60)

    all_passed = True

    # Test 1: Position queries
    if await test_position_queries():
        logger.info("\n✅ Position queries: PASSED")
    else:
        logger.error("\n❌ Position queries: FAILED")
        all_passed = False

    # Test 2: Greeks calculation
    if await test_greeks_calculation():
        logger.info("\n✅ Greeks calculation: PASSED")
    else:
        logger.error("\n❌ Greeks calculation: FAILED")
        all_passed = False

    # Test 3: Portfolio queries
    if await test_portfolio_queries():
        logger.info("\n✅ Portfolio queries: PASSED")
    else:
        logger.error("\n❌ Portfolio queries: FAILED")
        all_passed = False

    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("🎉 ALL BACKWARDS COMPATIBILITY TESTS PASSED!")
    else:
        logger.error("⚠️  SOME TESTS FAILED")
    logger.info("="*60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)