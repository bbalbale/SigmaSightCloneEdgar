"""Check current state of exposure data storage in database"""
import asyncio
from sqlalchemy import select, func, and_
from app.database import get_async_session
from app.models.market_data import PositionFactorExposure, FactorExposure, FactorDefinition
from app.models.positions import Position
from datetime import date

async def check_exposure_storage():
    async with get_async_session() as db:
        # Get a sample position with factor exposures
        position = await db.execute(
            select(Position)
            .where(Position.deleted_at.is_(None))
            .limit(1)
        )
        pos = position.scalar_one_or_none()
        
        if pos:
            # Check position factor exposures
            pfe_for_position = await db.execute(
                select(PositionFactorExposure, FactorDefinition)
                .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
                .where(PositionFactorExposure.position_id == pos.id)
                .order_by(FactorDefinition.name)
            )
            pfe_records = pfe_for_position.all()
            
            # Check portfolio-level exposures
            fe_for_portfolio = await db.execute(
                select(FactorExposure, FactorDefinition)
                .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
                .where(FactorExposure.portfolio_id == pos.portfolio_id)
                .order_by(FactorExposure.calculation_date.desc())
                .limit(7)
            )
            fe_records = fe_for_portfolio.all()
        
        print('=== COMPREHENSIVE EXPOSURE DATA ANALYSIS ===')
        
        print(f'\n1. POSITION-LEVEL FACTOR BETAS (PositionFactorExposure):')
        print(f'   ✅ STORED: Beta for each position-factor pair')
        print(f'   - Field: exposure_value (the beta coefficient)')
        print(f'   - NO dollar exposure at position level')
        
        if pfe_records:
            print(f'\n   Example Position ({pos.symbol}):')
            for pfe, fd in pfe_records:
                print(f'   - {fd.name:<20}: Beta = {pfe.exposure_value:>8.4f}')
        
        print(f'\n2. PORTFOLIO-LEVEL FACTOR EXPOSURES (FactorExposure):')
        print(f'   ✅ STORED: Portfolio beta and dollar exposure')
        print(f'   - exposure_value: Portfolio beta (weighted avg of position betas)')
        print(f'   - exposure_dollar: Beta × Gross_Exposure (FLAWED!)')
        
        if fe_records:
            print(f'\n   Example Portfolio Exposures:')
            for fe, fd in fe_records[:3]:
                print(f'   - {fd.name:<20}: Beta = {fe.exposure_value:>8.4f}, Dollar = ${fe.exposure_dollar:>12,.2f}')
        
        print(f'\n3. POSITION EXPOSURES:')
        print(f'   Position Table Fields:')
        print(f'   - quantity: ✅ STORED')
        print(f'   - market_value: ✅ STORED (quantity × price × multiplier)')
        print(f'   - notional_exposure: ❌ NOT STORED (calculated from market_value)')
        print(f'   - delta_adjusted_exposure: ❌ NOT STORED (would need Greeks)')
        
        print(f'\n4. WHAT WE NEED FOR OPTION B (Position-Level Attribution):')
        print(f'   ✅ HAVE: Position-level betas (PositionFactorExposure.exposure_value)')
        print(f'   ✅ HAVE: Position market values (Position.market_value)')
        print(f'   ❌ NEED: Position exposure with correct sign (market_value × sign)')
        print(f'   ❌ NEED: Position factor dollar contribution (position_exposure × beta)')
        
        print(f'\n=== IMPLEMENTATION NOTES ===')
        print(f'Option B can be implemented WITHOUT schema changes:')
        print(f'1. Calculate position exposure = market_value × (1 if LONG else -1)')
        print(f'2. Calculate factor contribution = position_exposure × position_beta')
        print(f'3. Sum contributions by factor for portfolio-level dollar exposure')
        print(f'4. Fix FactorExposure.exposure_dollar to store sum of contributions')
        print(f'\nOptional schema enhancement (not required):')
        print(f'- Add PositionFactorExposure.dollar_contribution field')
        print(f'- Add Position.signed_exposure field for clarity')

if __name__ == "__main__":
    asyncio.run(check_exposure_storage())