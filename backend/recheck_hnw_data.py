"""
Recheck HNW Portfolio Factor Exposure Data
Comprehensive verification after potential recalculation
"""
import asyncio
from uuid import UUID
from datetime import date
from sqlalchemy import select, func, and_
from app.database import AsyncSessionLocal
from app.models.market_data import PositionFactorExposure, FactorExposure, FactorDefinition
from app.models.positions import Position

async def check():
    hnw_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    async with AsyncSessionLocal() as db:
        print('=' * 80)
        print('DATA VERIFICATION - HNW PORTFOLIO')
        print('=' * 80)
        print()

        # 1. Check position-level exposures for ALL factors
        print('1. POSITION-LEVEL EXPOSURES BY FACTOR:')
        print('-' * 80)
        stmt = select(
            FactorDefinition.name,
            FactorDefinition.factor_type,
            func.count(PositionFactorExposure.id).label('count')
        ).join(
            FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id
        ).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).where(
            and_(
                Position.portfolio_id == hnw_id,
                PositionFactorExposure.calculation_date == date(2025, 10, 20)
            )
        ).group_by(FactorDefinition.name, FactorDefinition.factor_type).order_by(FactorDefinition.factor_type, FactorDefinition.name)

        result = await db.execute(stmt)
        rows = result.all()

        if rows:
            current_type = None
            for name, factor_type, count in rows:
                if factor_type != current_type:
                    print(f'\n{factor_type.upper()}:')
                    current_type = factor_type
                print(f'  {name:30s}: {count:3d} positions')
        else:
            print('  NO POSITION-LEVEL EXPOSURES FOUND!')

        # 2. Check portfolio-level exposures
        print('\n\n2. PORTFOLIO-LEVEL EXPOSURES:')
        print('-' * 80)
        stmt = select(
            FactorDefinition.name,
            FactorDefinition.factor_type,
            FactorExposure.exposure_value,
            FactorExposure.exposure_dollar
        ).join(
            FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
        ).where(
            and_(
                FactorExposure.portfolio_id == hnw_id,
                FactorExposure.calculation_date == date(2025, 10, 20)
            )
        ).order_by(FactorDefinition.factor_type, FactorDefinition.name)

        result = await db.execute(stmt)
        rows = result.all()

        current_type = None
        for name, factor_type, beta, dollar in rows:
            if factor_type != current_type:
                print(f'\n{factor_type.upper()}:')
                current_type = factor_type
            print(f'  {name:30s}: Beta={float(beta):>8.4f}, Dollar=${float(dollar):>14,.0f}')

        # 3. Summary stats
        print('\n\n3. SUMMARY:')
        print('-' * 80)

        # Count by factor type at position level
        stmt = select(
            FactorDefinition.factor_type,
            func.count(PositionFactorExposure.id).label('count')
        ).join(
            FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id
        ).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).where(
            and_(
                Position.portfolio_id == hnw_id,
                PositionFactorExposure.calculation_date == date(2025, 10, 20)
            )
        ).group_by(FactorDefinition.factor_type)

        result = await db.execute(stmt)
        pos_counts = {row[0]: row[1] for row in result.all()}

        # Count by factor type at portfolio level
        stmt = select(
            FactorDefinition.factor_type,
            func.count(FactorExposure.id).label('count')
        ).join(
            FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
        ).where(
            and_(
                FactorExposure.portfolio_id == hnw_id,
                FactorExposure.calculation_date == date(2025, 10, 20)
            )
        ).group_by(FactorDefinition.factor_type)

        result = await db.execute(stmt)
        port_counts = {row[0]: row[1] for row in result.all()}

        print(f'Position-level exposures:')
        for ftype in ['core', 'spread', 'beta']:
            count = pos_counts.get(ftype, 0)
            print(f'  {ftype:10s}: {count:3d} records')

        print(f'\nPortfolio-level exposures:')
        for ftype in ['core', 'spread', 'beta']:
            count = port_counts.get(ftype, 0)
            print(f'  {ftype:10s}: {count:3d} records')

asyncio.run(check())
