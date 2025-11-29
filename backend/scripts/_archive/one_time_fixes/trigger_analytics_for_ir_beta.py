"""
Quick script to trigger analytics calculation to populate IR Beta factor exposure.
This will run analytics for the demo_hnw portfolio.
"""
import asyncio
from datetime import date
from uuid import UUID

from app.database import AsyncSessionLocal
from app.batch.analytics_runner import AnalyticsRunner


async def main():
    # HNW Demo Portfolio ID
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    calculation_date = date.today()

    print(f"Running analytics for portfolio {portfolio_id} on {calculation_date}")
    print("This will calculate and persist IR Beta as a FactorExposure...")

    async with AsyncSessionLocal() as db:
        runner = AnalyticsRunner()

        # Run analytics (includes IR Beta calculation)
        result = await runner.run_analytics(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            run_sector_analysis=False  # Skip sector analysis for speed
        )

        if result:
            print("✅ Analytics completed successfully!")
            print("IR Beta should now be available in the factor exposures API")
        else:
            print("⚠️ Analytics completed with some warnings (check logs)")

        # Commit the changes
        await db.commit()
        print("✅ Changes committed to database")


if __name__ == "__main__":
    asyncio.run(main())
