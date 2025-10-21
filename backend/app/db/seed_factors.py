"""
Seed factor definitions into the database

This script seeds the 8 confirmed factors as per the design decisions.
"""
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.market_data import FactorDefinition


# Factor definitions based on confirmed design
FACTOR_DEFINITIONS = [
    {
        "name": "Market Beta",
        "description": "Sensitivity to overall market movements (S&P 500)",
        "factor_type": "style",
        "calculation_method": "rolling_regression",
        "etf_proxy": "SPY",
        "display_order": 0
    },
    {
        "name": "Momentum",
        "description": "12-month price momentum excluding most recent month",
        "factor_type": "style",
        "calculation_method": "price_momentum",
        "etf_proxy": "MTUM",
        "display_order": 1
    },
    {
        "name": "Value",
        "description": "Exposure to value stocks (low P/B, P/E ratios)",
        "factor_type": "style",
        "calculation_method": "fundamental_ratios",
        "etf_proxy": "VTV",
        "display_order": 2
    },
    {
        "name": "Growth",
        "description": "Exposure to growth stocks (high earnings growth)",
        "factor_type": "style",
        "calculation_method": "earnings_growth",
        "etf_proxy": "VUG",
        "display_order": 3
    },
    {
        "name": "Quality",
        "description": "Exposure to high-quality companies (high ROE, low debt)",
        "factor_type": "style",
        "calculation_method": "quality_metrics",
        "etf_proxy": "QUAL",
        "display_order": 4
    },
    {
        "name": "Size",
        "description": "Exposure to small-cap vs large-cap stocks",
        "factor_type": "style",
        "calculation_method": "market_cap",
        "etf_proxy": "IWM",
        "display_order": 5
    },
    {
        "name": "Low Volatility",
        "description": "Exposure to low volatility stocks",
        "factor_type": "style",
        "calculation_method": "realized_volatility",
        "etf_proxy": "USMV",
        "display_order": 6
    },
    {
        "name": "Short Interest",
        "description": "Exposure to heavily shorted stocks",
        "factor_type": "style",
        "calculation_method": "short_interest_ratio",
        "etf_proxy": None,  # No ETF proxy for short interest
        "display_order": 7
    }
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
