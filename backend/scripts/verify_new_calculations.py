"""
Verify New Calculations (IR Beta and Ridge) in Database
"""
import asyncio
from sqlalchemy import select, func
from datetime import date

from app.database import get_async_session
from app.models.market_data import PositionInterestRateBeta, PositionFactorExposure
from app.models.users import Portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_calculations():
    """Verify IR beta and Ridge factor calculations completed"""

    async with get_async_session() as db:
        # Get portfolio count
        portfolio_count = await db.execute(
            select(func.count(Portfolio.id)).where(Portfolio.deleted_at.is_(None))
        )
        total_portfolios = portfolio_count.scalar()

        # Check IR beta records
        ir_beta_count = await db.execute(
            select(func.count(PositionInterestRateBeta.id)).where(
                PositionInterestRateBeta.calculation_date == date.today()
            )
        )
        total_ir_betas = ir_beta_count.scalar()

        # Check Ridge factor exposure records (today's date)
        ridge_count = await db.execute(
            select(func.count(PositionFactorExposure.id)).where(
                PositionFactorExposure.calculation_date == date.today()
            )
        )
        total_ridge = ridge_count.scalar()

        print("=" * 60)
        print("Batch Processing Verification Results")
        print("=" * 60)
        print(f"Date: {date.today()}")
        print(f"Total Portfolios: {total_portfolios}")
        print()
        print(f"IR Beta Records (today): {total_ir_betas}")
        print(f"Ridge Factor Exposures (today): {total_ridge}")
        print()

        if total_ir_betas > 0 and total_ridge > 0:
            print("SUCCESS: New calculations completed!")
            print()
            print("IR Beta Calculation: WORKING")
            print("Ridge Regression: WORKING")
        else:
            print("WARNING: Some calculations may not have completed")
            if total_ir_betas == 0:
                print("  - No IR beta records found for today")
            if total_ridge == 0:
                print("  - No Ridge factor exposures found for today")

        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_calculations())
