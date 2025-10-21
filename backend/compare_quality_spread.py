import asyncio
from uuid import UUID
from datetime import date
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.market_data import FactorExposure, FactorDefinition

async def check():
    hnw_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    async with AsyncSessionLocal() as db:
        print('Quality Spread Comparison:')
        print('=' * 70)
        # Compare Oct 20 vs Oct 21
        for calc_date in [date(2025, 10, 20), date(2025, 10, 21)]:
            stmt = select(
                FactorDefinition.name,
                FactorExposure.exposure_value,
                FactorExposure.exposure_dollar
            ).join(
                FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
            ).where(
                and_(
                    FactorExposure.portfolio_id == hnw_id,
                    FactorExposure.calculation_date == calc_date,
                    FactorDefinition.name == 'Quality Spread'
                )
            )

            result = await db.execute(stmt)
            row = result.first()

            if row:
                name, beta, dollar = row
                print(f'{calc_date}: Beta={float(beta):>8.4f}, Dollar=${float(dollar):>15,.0f}')
            else:
                print(f'{calc_date}: NO DATA')

asyncio.run(check())
