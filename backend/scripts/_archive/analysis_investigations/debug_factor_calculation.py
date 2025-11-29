"""
Debug the factor exposure calculation to find why it's still multiplying
"""
import asyncio
from datetime import date
from uuid import UUID
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.positions import Position, PositionType
from app.models.market_data import PositionFactorExposure, FactorDefinition
from app.calculations.portfolio import calculate_portfolio_exposures
from decimal import Decimal

async def debug_calculation():
    """
    Step through the calculation manually to find the issue
    """
    portfolio_id = UUID('51134ffd-2f13-49bd-b1f5-0c327e801b69')  # Demo Individual
    
    async with get_async_session() as db:
        print("=" * 80)
        print("DEBUGGING FACTOR EXPOSURE CALCULATION")
        print("=" * 80)
        
        # 1. Get positions
        pos_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.deleted_at.is_(None)
            )
        )
        pos_result = await db.execute(pos_stmt)
        positions = pos_result.scalars().all()
        
        print(f"\n1. POSITIONS: {len(positions)} total")
        
        # 2. Calculate position exposures with correct signs
        position_exposures = {}
        total_gross = 0
        for position in positions:
            pos_id_str = str(position.id)
            market_val = float(position.market_value) if position.market_value else 0
            
            # Apply sign based on position type
            if position.position_type in [PositionType.SHORT, PositionType.SC, PositionType.SP]:
                signed_exposure = -abs(market_val)
            else:
                signed_exposure = abs(market_val)
            
            position_exposures[pos_id_str] = signed_exposure
            total_gross += abs(signed_exposure)
            
            if position.symbol in ['AAPL', 'MSFT']:  # Sample a few
                print(f"   {position.symbol}: ${signed_exposure:,.2f} ({position.position_type.value})")
        
        print(f"\n2. GROSS EXPOSURE: ${total_gross:,.2f}")
        
        # 3. Get position factor betas
        print("\n3. POSITION FACTOR BETAS:")
        
        # Get factor definitions
        factor_stmt = select(FactorDefinition).where(FactorDefinition.is_active == True)
        factor_result = await db.execute(factor_stmt)
        factor_defs = factor_result.scalars().all()
        factor_id_to_name = {fd.id: fd.name for fd in factor_defs}
        factor_name_to_id = {fd.name: fd.id for fd in factor_defs}
        
        # Get position factor exposures for first position as example
        first_pos = positions[0]
        pfe_stmt = select(PositionFactorExposure).where(
            PositionFactorExposure.position_id == first_pos.id
        ).order_by(PositionFactorExposure.calculation_date.desc()).limit(7)
        
        pfe_result = await db.execute(pfe_stmt)
        pfes = pfe_result.scalars().all()
        
        if pfes:
            print(f"   Example: {first_pos.symbol} (ID: {first_pos.id})")
            print(f"   Market value: ${position_exposures[str(first_pos.id)]:,.2f}")
            for pfe in pfes:
                factor_name = factor_id_to_name.get(pfe.factor_id, "Unknown")
                print(f"     {factor_name}: Beta = {pfe.exposure_value}")
        
        # 4. Calculate factor dollar exposures (Option B way)
        print("\n4. CALCULATING FACTOR DOLLAR EXPOSURES (Option B):")
        
        # Get all position betas
        all_position_betas = {}
        for position in positions:
            pos_id_str = str(position.id)
            all_position_betas[pos_id_str] = {}
            
            # Get betas for this position
            pfe_stmt = select(PositionFactorExposure).where(
                PositionFactorExposure.position_id == position.id
            ).order_by(PositionFactorExposure.calculation_date.desc()).limit(7)
            
            pfe_result = await db.execute(pfe_stmt)
            pfes = pfe_result.scalars().all()
            
            for pfe in pfes:
                factor_name = factor_id_to_name.get(pfe.factor_id, "Unknown")
                if factor_name not in all_position_betas[pos_id_str]:
                    all_position_betas[pos_id_str][factor_name] = float(pfe.exposure_value)
        
        # Calculate factor dollar exposures
        factor_dollar_exposures = {}
        
        # Focus on Market Beta as example
        market_beta_total = 0
        market_beta_details = []
        
        for pos_id_str, pos_betas in all_position_betas.items():
            if 'Market Beta' in pos_betas:
                position_beta = pos_betas['Market Beta']
                position_exposure = position_exposures.get(pos_id_str, 0)
                contribution = position_exposure * position_beta
                market_beta_total += contribution
                
                # Find position symbol for debugging
                pos_uuid = UUID(pos_id_str)
                pos = next((p for p in positions if p.id == pos_uuid), None)
                if pos and abs(contribution) > 1000:  # Only show significant contributions
                    market_beta_details.append({
                        'symbol': pos.symbol,
                        'exposure': position_exposure,
                        'beta': position_beta,
                        'contribution': contribution
                    })
        
        print(f"\n   Market Beta Factor:")
        print(f"   Total Dollar Exposure: ${market_beta_total:,.2f}")
        print(f"   As % of Gross: {(market_beta_total/total_gross)*100:.1f}%")
        print(f"\n   Top contributions:")
        for detail in sorted(market_beta_details, key=lambda x: abs(x['contribution']), reverse=True)[:5]:
            print(f"     {detail['symbol']:6} Exp=${detail['exposure']:>10,.0f} × Beta={detail['beta']:>6.3f} = ${detail['contribution']:>10,.0f}")
        
        # Check all factors
        print(f"\n5. ALL FACTOR DOLLAR EXPOSURES:")
        for factor_name in ['Market Beta', 'Value', 'Growth', 'Momentum', 'Quality', 'Size', 'Low Volatility']:
            factor_total = 0
            for pos_id_str, pos_betas in all_position_betas.items():
                if factor_name in pos_betas:
                    position_beta = pos_betas[factor_name]
                    position_exposure = position_exposures.get(pos_id_str, 0)
                    contribution = position_exposure * position_beta
                    factor_total += contribution
            
            factor_dollar_exposures[factor_name] = factor_total
            print(f"   {factor_name:20} ${factor_total:>12,.2f} ({(factor_total/total_gross)*100:>6.1f}% of gross)")
        
        total_factor_exposure = sum(abs(v) for v in factor_dollar_exposures.values())
        print(f"\n   TOTAL (absolute sum): ${total_factor_exposure:,.2f}")
        print(f"   Ratio to Gross: {total_factor_exposure/total_gross:.2f}x")
        
        if total_factor_exposure/total_gross > 2:
            print("\n   ℹ️  NOTE: Factor exposures sum >100% is CORRECT behavior!")
            print("   Factors are independent risk dimensions, not mutually exclusive.")
            print("   A position can have high exposure to multiple factors simultaneously.")
            print("   This follows industry standard (Bloomberg, MSCI Barra) methodology.")

if __name__ == "__main__":
    asyncio.run(debug_calculation())