"""Test IR Beta calculation for a single portfolio on a single date"""
import asyncio
from datetime import date
from uuid import UUID

from app.database import AsyncSessionLocal
from app.batch.analytics_runner import AnalyticsRunner
from sqlalchemy import select
from app.models.market_data import FactorExposure, FactorDefinition


async def main():
    # HNW Demo Portfolio ID
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    calculation_date = date(2025, 11, 7)  # Use a recent date

    print("=" * 80)
    print(f"Testing IR Beta calculation for portfolio {portfolio_id}")
    print(f"Calculation date: {calculation_date}")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        runner = AnalyticsRunner()

        # Run analytics (includes IR Beta calculation)
        print("\n[1/3] Running analytics calculation...")
        result = await runner.run_analytics(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            run_sector_analysis=False  # Skip sector for speed
        )

        if result:
            print("[OK] Analytics completed successfully!")
        else:
            print("[WARN] Analytics completed with warnings (check logs above)")

        # Commit the changes
        await db.commit()
        print("[OK] Changes committed to database")

        # Verify IR Beta was persisted
        print("\n[2/3] Checking if IR Beta factor definition exists...")
        factor_stmt = select(FactorDefinition).where(FactorDefinition.name == 'IR Beta')
        factor_result = await db.execute(factor_stmt)
        ir_beta_factor = factor_result.scalar_one_or_none()

        if ir_beta_factor:
            print(f"[OK] IR Beta factor found: {ir_beta_factor.name} (ID: {ir_beta_factor.id})")

            # Check for IR Beta exposure
            print("\n[3/3] Checking if IR Beta exposure was persisted...")
            exposure_stmt = select(FactorExposure).where(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id == ir_beta_factor.id,
                FactorExposure.calculation_date == calculation_date
            )
            exposure_result = await db.execute(exposure_stmt)
            exposure = exposure_result.scalar_one_or_none()

            if exposure:
                print(f"[OK] IR Beta exposure found!")
                print(f"   Exposure value: {exposure.exposure_value}")
                print(f"   Exposure dollar: ${exposure.exposure_dollar}")
                print(f"   Calculation date: {exposure.calculation_date}")
                print("\n" + "=" * 80)
                print("[SUCCESS] IR Beta is being calculated and persisted correctly!")
                print("=" * 80)
            else:
                print("[ERROR] IR Beta factor exists but no exposure record found")
                print(f"Portfolio: {portfolio_id}, Date: {calculation_date}")
        else:
            print("[ERROR] IR Beta factor definition not found in database")


if __name__ == "__main__":
    asyncio.run(main())
