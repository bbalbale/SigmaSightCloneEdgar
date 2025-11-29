"""Verify IR Beta was persisted to database"""
import asyncio
from datetime import date
from uuid import UUID
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.market_data import FactorExposure, FactorDefinition


async def main():
    # HNW Demo Portfolio ID
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    calculation_date = date(2025, 11, 7)

    print("=" * 80)
    print("Checking IR Beta in Database")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Check for IR Beta factor definition
        print("\n[1/2] Checking if IR Beta factor definition exists...")
        factor_stmt = select(FactorDefinition).where(FactorDefinition.name == 'IR Beta')
        factor_result = await db.execute(factor_stmt)
        ir_beta_factor = factor_result.scalar_one_or_none()

        if ir_beta_factor:
            print(f"[OK] IR Beta factor found:")
            print(f"   ID: {ir_beta_factor.id}")
            print(f"   Name: {ir_beta_factor.name}")
            print(f"   Description: {ir_beta_factor.description}")
            print(f"   Type: {ir_beta_factor.factor_type}")

            # Check for IR Beta exposures
            print("\n[2/2] Checking if IR Beta exposures were persisted...")
            exposure_stmt = select(FactorExposure).where(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id == ir_beta_factor.id,
                FactorExposure.calculation_date == calculation_date
            )
            exposure_result = await db.execute(exposure_stmt)
            exposure = exposure_result.scalar_one_or_none()

            if exposure:
                print(f"[OK] IR Beta exposure found for HNW portfolio!")
                print(f"   Portfolio ID: {exposure.portfolio_id}")
                print(f"   Exposure value: {exposure.exposure_value}")
                print(f"   Exposure dollar: ${exposure.exposure_dollar}")
                print(f"   Calculation date: {exposure.calculation_date}")
                print("\n" + "=" * 80)
                print("[SUCCESS] IR Beta is working correctly!")
                print("=" * 80)
                print("\nNext step: Check the frontend to see if IR Beta appears in the hero bar")
            else:
                print(f"[ERROR] IR Beta factor exists but no exposure record found")
                print(f"   Portfolio: {portfolio_id}")
                print(f"   Date: {calculation_date}")
                print("\nCheck batch logs for IR Beta calculation errors")
        else:
            print("[ERROR] IR Beta factor definition not found in database")
            print("\nThe _calculate_ir_beta method may not have created the factor definition")


if __name__ == "__main__":
    asyncio.run(main())
