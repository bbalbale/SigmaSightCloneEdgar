"""
Seed factor definitions into the database

CRITICAL (2025-11-15): These factor definitions must match what analytics_runner.py actually calculates.
Only include factors that are actively being computed.
"""
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.market_data import FactorDefinition


# Factor definitions - ACTIVELY CALCULATED FACTORS ONLY
# These match what analytics_runner.py actually calculates
FACTOR_DEFINITIONS = [
    # Market Beta Factors (2 approaches)
    {
        "name": "Market Beta",
        "description": "90-day OLS regression beta vs S&P 500 (portfolio-level)",
        "factor_type": "market",
        "calculation_method": "rolling_regression",
        "etf_proxy": "SPY",
        "display_order": 0
    },
    {
        "name": "Provider Beta (1Y)",
        "description": "1-year market beta from 3rd party providers (position-level weighted)",
        "factor_type": "market",
        "calculation_method": "provider_data",
        "etf_proxy": "SPY",
        "display_order": 1
    },
    # Interest Rate Beta
    {
        "name": "Interest Rate Beta",
        "description": "90-day regression vs TLT (treasury bonds)",
        "factor_type": "macro",
        "calculation_method": "rolling_regression",
        "etf_proxy": "TLT",
        "display_order": 2
    },
    # 5-Factor Ridge Regression (removed Short Interest per user request)
    {
        "name": "Momentum",
        "description": "12-month price momentum (ridge regression factor)",
        "factor_type": "style",
        "calculation_method": "ridge_regression",
        "etf_proxy": "MTUM",
        "display_order": 3
    },
    {
        "name": "Value",
        "description": "Value factor from ridge regression",
        "factor_type": "style",
        "calculation_method": "ridge_regression",
        "etf_proxy": "VTV",
        "display_order": 4
    },
    {
        "name": "Growth",
        "description": "Growth factor from ridge regression",
        "factor_type": "style",
        "calculation_method": "ridge_regression",
        "etf_proxy": "VUG",
        "display_order": 5
    },
    {
        "name": "Size",
        "description": "Size factor from ridge regression",
        "factor_type": "style",
        "calculation_method": "ridge_regression",
        "etf_proxy": "IWM",
        "display_order": 6
    },
    {
        "name": "Quality",
        "description": "Quality factor from ridge regression",
        "factor_type": "style",
        "calculation_method": "ridge_regression",
        "etf_proxy": "QUAL",
        "display_order": 7
    }
    # NOTE: Short Interest removed - no longer calculated (2025-11-15)
    # NOTE: Low Volatility not currently calculated
]


async def seed_factors(db: AsyncSession) -> None:
    """Seed factor definitions into the database"""
    print("Seeding factor definitions...")

    for factor_data in FACTOR_DEFINITIONS:
        # Check if factor already exists
        result = await db.execute(
            select(FactorDefinition).where(FactorDefinition.name == factor_data["name"])
        )
        existing_factor = result.scalar_one_or_none()

        if existing_factor:
            print(f"Factor '{factor_data['name']}' already exists, skipping...")
            continue

        # Create new factor
        factor = FactorDefinition(
            id=uuid4(),
            **factor_data,
            is_active=True
        )
        db.add(factor)
        print(f"Created factor: {factor_data['name']}")

    await db.commit()
    print("Factor seeding completed!")


async def main():
    """Main function to run the seeding script"""
    async for db in get_db():
        try:
            await seed_factors(db)
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
