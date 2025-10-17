"""
Test Sector Exposure and Concentration Metrics API Endpoints
Tests the two new Phase 1 Risk Metrics endpoints.

Usage:
    uv run python scripts/test_sector_endpoints.py
"""
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.api.v1.analytics.portfolio import get_sector_exposure, get_concentration_metrics
from app.schemas.auth import CurrentUser
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_endpoints():
    """Test sector exposure and concentration metrics endpoints"""
    logger.info("=" * 60)
    logger.info("Testing Sector Exposure & Concentration Metrics Endpoints")
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

        # Create mock user for testing
        from datetime import datetime, timezone
        mock_user = CurrentUser(
            id=portfolio.user_id,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc)
        )

        # Test sector exposure endpoint
        logger.info("\n" + "=" * 60)
        logger.info("Testing Sector Exposure Endpoint")
        logger.info("=" * 60)
        try:
            sector_response = await get_sector_exposure(
                portfolio_id=portfolio_id,
                current_user=mock_user,
                db=db
            )

            logger.info(f"\nSector Exposure Response:")
            logger.info(f"  Available: {sector_response.available}")
            logger.info(f"  Portfolio ID: {sector_response.portfolio_id}")
            logger.info(f"  Calculation Date: {sector_response.calculation_date}")

            if sector_response.available and sector_response.data:
                data = sector_response.data
                logger.info(f"\n  Portfolio Weights:")
                for sector, weight in sorted(data.portfolio_weights.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"    {sector}: {weight*100:.2f}%")

                logger.info(f"\n  Over/Underweight vs S&P 500:")
                for sector, diff in sorted(data.over_underweight.items(), key=lambda x: x[1], reverse=True)[:5]:
                    logger.info(f"    {sector}: {diff*100:+.2f}%")

                logger.info(f"\n  Total Portfolio Value: ${data.total_portfolio_value:,.2f}")
                logger.info(f"  Largest Overweight: {data.largest_overweight}")
                logger.info(f"  Largest Underweight: {data.largest_underweight}")
                logger.info(f"  Unclassified Positions: {data.unclassified_count}")

            logger.info("\nSector Exposure Endpoint: SUCCESS")

        except Exception as e:
            logger.error(f"Sector Exposure Endpoint FAILED: {e}", exc_info=True)

        # Test concentration metrics endpoint
        logger.info("\n" + "=" * 60)
        logger.info("Testing Concentration Metrics Endpoint")
        logger.info("=" * 60)
        try:
            concentration_response = await get_concentration_metrics(
                portfolio_id=portfolio_id,
                current_user=mock_user,
                db=db
            )

            logger.info(f"\nConcentration Metrics Response:")
            logger.info(f"  Available: {concentration_response.available}")
            logger.info(f"  Portfolio ID: {concentration_response.portfolio_id}")
            logger.info(f"  Calculation Date: {concentration_response.calculation_date}")

            if concentration_response.available and concentration_response.data:
                data = concentration_response.data
                logger.info(f"\n  HHI: {data.hhi:.2f}")
                logger.info(f"  Effective # of Positions: {data.effective_num_positions:.2f}")
                logger.info(f"  Top 3 Concentration: {data.top_3_concentration*100:.2f}%")
                logger.info(f"  Top 10 Concentration: {data.top_10_concentration*100:.2f}%")
                logger.info(f"  Total Positions: {data.total_positions}")

                # Interpretation
                hhi = data.hhi
                if hhi > 2500:
                    logger.info(f"\n  Interpretation: HIGHLY CONCENTRATED (HHI > 2500)")
                elif hhi > 1500:
                    logger.info(f"\n  Interpretation: MODERATELY CONCENTRATED (HHI 1500-2500)")
                else:
                    logger.info(f"\n  Interpretation: WELL DIVERSIFIED (HHI < 1500)")

            logger.info("\nConcentration Metrics Endpoint: SUCCESS")

        except Exception as e:
            logger.error(f"Concentration Metrics Endpoint FAILED: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("Endpoint Testing Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_endpoints())
