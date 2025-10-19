"""
Test Interest Rate Beta Calculation on Demo Portfolios (TLT-based)
Verifies:
1. TLT (20+ Year Treasury Bond ETF) price data availability
2. IR beta calculation for all demo portfolios using TLT
3. Database persistence of position IR betas
"""
import asyncio
from datetime import date
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_async_session
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.market_data import MarketDataCache, PositionInterestRateBeta
from app.calculations.interest_rate_beta import calculate_portfolio_ir_beta
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_treasury_data():
    """Verify TLT (Bond ETF) price data availability"""
    logger.info("=" * 60)
    logger.info("Step 1: Checking TLT Bond ETF Data Availability")
    logger.info("=" * 60)

    async with get_async_session() as db:
        # Check TLT data
        stmt = select(
            func.count(MarketDataCache.id),
            func.min(MarketDataCache.date),
            func.max(MarketDataCache.date)
        ).where(MarketDataCache.symbol == 'TLT')

        result = await db.execute(stmt)
        count, min_date, max_date = result.one()

        if count == 0:
            logger.error("No TLT price data found in database!")
            logger.info("Run: uv run python scripts/fetch_tlt_data.py")
            return False

        logger.info(f"Found {count} days of TLT data")
        logger.info(f"Date range: {min_date} to {max_date}")

        # Check if we have recent data (within last 7 days)
        days_since_last = (date.today() - max_date).days if max_date else 999
        if days_since_last > 7:
            logger.warning(f"TLT data is {days_since_last} days old - consider refreshing")

        return True


async def get_demo_portfolios():
    """Get all demo portfolios"""
    async with get_async_session() as db:
        # Get demo users
        demo_emails = [
            "demo_individual@sigmasight.com",
            "demo_hnw@sigmasight.com",
            "demo_hedgefundstyle@sigmasight.com"
        ]

        stmt = select(User).where(User.email.in_(demo_emails))
        result = await db.execute(stmt)
        demo_users = result.scalars().all()

        # Get portfolios for demo users
        user_ids = [u.id for u in demo_users]

        stmt = select(Portfolio).where(
            Portfolio.user_id.in_(user_ids),
            Portfolio.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        return portfolios


async def test_ir_beta_calculation(portfolio: Portfolio):
    """Test IR beta calculation for a single portfolio"""
    logger.info("=" * 60)
    logger.info(f"Testing Portfolio: {portfolio.name}")
    logger.info("=" * 60)

    async with get_async_session() as db:
        # Calculate IR beta using TLT (Bond ETF)
        result = await calculate_portfolio_ir_beta(
            db=db,
            portfolio_id=portfolio.id,
            calculation_date=date.today(),
            window_days=90,
            treasury_symbol='TLT',  # 20+ Year Treasury Bond ETF
            persist=True
        )

        if result['success']:
            logger.info(f"✓ IR Beta Calculation SUCCESS")
            logger.info(f"  Portfolio IR Beta: {result['portfolio_ir_beta']:.4f}")
            logger.info(f"  Sensitivity Level: {result['sensitivity_level']}")
            logger.info(f"  R-Squared: {result['r_squared']:.3f}")
            logger.info(f"  Positions Calculated: {result['positions_count']}")
            logger.info(f"  Min Observations: {result['observations']}")

            # Verify database persistence
            stmt = select(func.count(PositionInterestRateBeta.id)).where(
                PositionInterestRateBeta.position_id.in_(
                    select(Position.id).where(Position.portfolio_id == portfolio.id)
                )
            )

            count_result = await db.execute(stmt)
            persisted_count = count_result.scalar()

            logger.info(f"  Database Records: {persisted_count} position IR betas persisted")

            return True
        else:
            logger.error(f"✗ IR Beta Calculation FAILED")
            logger.error(f"  Error: {result.get('error', 'Unknown error')}")
            return False


async def main():
    """Main test execution"""
    logger.info("=" * 60)
    logger.info("Interest Rate Beta Calculation Test")
    logger.info("=" * 60)

    # Step 1: Check TLT data
    treasury_ok = await check_treasury_data()
    if not treasury_ok:
        logger.error("TLT price data not available - cannot proceed with IR beta test")
        return

    # Step 2: Get demo portfolios
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Loading Demo Portfolios")
    logger.info("=" * 60)

    portfolios = await get_demo_portfolios()
    logger.info(f"Found {len(portfolios)} demo portfolios")

    if not portfolios:
        logger.error("No demo portfolios found!")
        return

    # Step 3: Test IR beta on each portfolio
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: Testing IR Beta Calculation")
    logger.info("=" * 60)

    success_count = 0
    fail_count = 0

    for portfolio in portfolios:
        try:
            success = await test_ir_beta_calculation(portfolio)
            if success:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Exception testing portfolio {portfolio.name}: {e}")
            fail_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Total Portfolios: {len(portfolios)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")

    if fail_count == 0:
        logger.info("\n✓ All IR beta calculations completed successfully!")
    else:
        logger.warning(f"\n⚠ {fail_count} portfolios failed IR beta calculation")


if __name__ == "__main__":
    asyncio.run(main())
