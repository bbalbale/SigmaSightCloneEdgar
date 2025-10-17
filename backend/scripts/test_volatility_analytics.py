"""
Test Volatility Analytics Calculations
Tests the Phase 2 volatility calculation module with demo data.

Usage:
    uv run python scripts/test_volatility_analytics.py
"""
import asyncio
from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position
from app.calculations.volatility_analytics import (
    calculate_position_volatility,
    calculate_portfolio_volatility,
    calculate_portfolio_volatility_batch
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_volatility_calculations():
    """Test volatility calculations on demo portfolios"""
    logger.info("=" * 60)
    logger.info("Testing Volatility Analytics (Phase 2)")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        # Get first portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            logger.error("No portfolios found in database!")
            return

        portfolio_id = portfolio.id
        logger.info(f"\nTesting with Portfolio: {portfolio.name}")
        logger.info(f"Portfolio ID: {portfolio_id}")

        # Get first position from portfolio
        result = await db.execute(
            select(Position)
            .where(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
            .limit(1)
        )
        position = result.scalar_one_or_none()

        if not position:
            logger.error("No active positions found in portfolio!")
            return

        calculation_date = date.today()
        logger.info(f"Calculation Date: {calculation_date}")

        # Test 1: Position-level volatility
        logger.info("\n" + "=" * 60)
        logger.info("Test 1: Position-Level Volatility")
        logger.info("=" * 60)
        logger.info(f"Testing position: {position.symbol}")

        try:
            vol_data = await calculate_position_volatility(
                db=db,
                position_id=position.id,
                calculation_date=calculation_date
            )

            if vol_data:
                # Helper to format optional values
                def fmt_pct(val):
                    return f"{val:.2%}" if val is not None else "N/A"

                def fmt_float(val, precision=2):
                    return f"{val:.{precision}f}" if val is not None else "N/A"

                logger.info(f"\nPosition Volatility Results:")
                logger.info(f"  Symbol: {position.symbol}")
                logger.info(f"  Realized Vol 21d: {fmt_pct(vol_data.get('realized_vol_21d'))}")
                logger.info(f"  Realized Vol 63d: {fmt_pct(vol_data.get('realized_vol_63d'))}")
                logger.info(f"  Expected Vol 21d: {fmt_pct(vol_data.get('expected_vol_21d'))}")
                logger.info(f"  Trend: {vol_data.get('vol_trend', 'N/A')}")
                logger.info(f"  Trend Strength: {fmt_float(vol_data.get('vol_trend_strength'))}")
                logger.info(f"  Percentile: {fmt_pct(vol_data.get('vol_percentile'))}")
                logger.info(f"  Observations: {vol_data.get('observations', 0)}")
                logger.info(f"  Model R²: {fmt_float(vol_data.get('model_r_squared'), 4)}")
                logger.info("\nTest 1: SUCCESS")
            else:
                logger.warning("Position volatility calculation returned None")
                logger.info("\nTest 1: SKIPPED (insufficient data)")

        except Exception as e:
            logger.error(f"Test 1 FAILED: {e}", exc_info=True)

        # Test 2: Portfolio-level volatility
        logger.info("\n" + "=" * 60)
        logger.info("Test 2: Portfolio-Level Volatility")
        logger.info("=" * 60)

        try:
            port_vol = await calculate_portfolio_volatility(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if port_vol:
                logger.info(f"\nPortfolio Volatility Results:")

                # Helper to format optional values
                def fmt_pct(val):
                    return f"{val:.2%}" if val is not None else "N/A"

                logger.info(f"  Realized Vol 21d: {fmt_pct(port_vol.get('realized_vol_21d'))}")
                logger.info(f"  Realized Vol 63d: {fmt_pct(port_vol.get('realized_vol_63d'))}")
                logger.info(f"  Expected Vol 21d: {fmt_pct(port_vol.get('expected_vol_21d'))}")
                logger.info(f"  Trend: {port_vol.get('vol_trend', 'N/A')}")
                logger.info(f"  Percentile: {fmt_pct(port_vol.get('vol_percentile'))}")
                logger.info(f"  Observations: {port_vol.get('observations', 0)}")
                logger.info(f"  Positions Included: {port_vol.get('positions_included', 0)}")
                logger.info("\nTest 2: SUCCESS")
            else:
                logger.warning("Portfolio volatility calculation returned None")
                logger.info("\nTest 2: SKIPPED (insufficient data)")

        except Exception as e:
            logger.error(f"Test 2 FAILED: {e}", exc_info=True)

        # Test 3: Batch processing
        logger.info("\n" + "=" * 60)
        logger.info("Test 3: Batch Processing")
        logger.info("=" * 60)

        try:
            batch_result = await calculate_portfolio_volatility_batch(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            logger.info(f"\nBatch Processing Results:")
            logger.info(f"  Success: {batch_result['success']}")
            logger.info(f"  Positions Processed: {batch_result['positions_processed']}")
            logger.info(f"  Positions Failed: {batch_result['positions_failed']}")

            if batch_result['success']:
                # Helper to format optional values
                def fmt_pct(val):
                    return f"{val:.2%}" if val is not None else "N/A"

                if batch_result['portfolio_volatility']:
                    pv = batch_result['portfolio_volatility']
                    logger.info(f"\n  Portfolio Metrics:")
                    logger.info(f"    Realized Vol 21d: {fmt_pct(pv.get('realized_vol_21d'))}")
                    logger.info(f"    Expected Vol 21d: {fmt_pct(pv.get('expected_vol_21d'))}")
                    logger.info(f"    Trend: {pv.get('vol_trend', 'N/A')}")

                logger.info(f"\n  Sample Position Results:")
                for i, pos_vol in enumerate(batch_result['position_volatilities'][:3]):
                    logger.info(f"    Position {i+1}:")
                    logger.info(f"      Realized Vol: {fmt_pct(pos_vol.get('realized_vol_21d'))}")
                    logger.info(f"      Expected Vol: {fmt_pct(pos_vol.get('expected_vol_21d'))}")

                logger.info("\nTest 3: SUCCESS")
            else:
                logger.error(f"Batch processing failed: {batch_result.get('error')}")
                logger.info("\nTest 3: FAILED")

        except Exception as e:
            logger.error(f"Test 3 FAILED: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("Volatility Analytics Testing Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_volatility_calculations())
