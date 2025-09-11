"""
Validate Option B implementation for factor exposures
"""
import asyncio
from datetime import date
from uuid import UUID
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import FactorExposure, FactorDefinition, PositionFactorExposure
from app.calculations.portfolio import calculate_portfolio_exposures
from app.calculations.factors import calculate_factor_betas_hybrid
from app.core.logging import get_logger

logger = get_logger(__name__)

# Demo portfolio IDs (actual IDs from database)
DEMO_PORTFOLIOS = {
    "Demo Individual": UUID("51134ffd-2f13-49bd-b1f5-0c327e801b69"),
    "Demo HNW": UUID("c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e"),
    "Demo Hedge Fund": UUID("2ee7435f-379f-4606-bdb7-dadce587a182")
}

async def validate_implementation():
    """
    Validate the Option B implementation by running calculations and checking results
    """
    print("=" * 80)
    print("VALIDATING OPTION B IMPLEMENTATION")
    print("=" * 80)
    
    async with get_async_session() as db:
        # Get factor definitions
        factor_stmt = select(FactorDefinition).where(FactorDefinition.is_active == True)
        factor_result = await db.execute(factor_stmt)
        factor_defs = factor_result.scalars().all()
        factor_id_to_name = {fd.id: fd.name for fd in factor_defs}
        
        for portfolio_name, portfolio_id in DEMO_PORTFOLIOS.items():
            print(f"\n{'=' * 40}")
            print(f"Portfolio: {portfolio_name}")
            print(f"ID: {portfolio_id}")
            print(f"{'=' * 40}")
            
            # 1. Get positions
            pos_stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.deleted_at.is_(None)
                )
            )
            pos_result = await db.execute(pos_stmt)
            positions = pos_result.scalars().all()
            
            if not positions:
                print("❌ No positions found")
                continue
            
            print(f"\n1. POSITION ANALYSIS:")
            print(f"   Total positions: {len(positions)}")
            
            # Count position types
            long_count = sum(1 for p in positions if p.position_type.value in ['LONG', 'LC', 'LP'])
            short_count = sum(1 for p in positions if p.position_type.value in ['SHORT', 'SC', 'SP'])
            
            print(f"   Long positions: {long_count}")
            print(f"   Short positions: {short_count}")
            
            # 2. Calculate portfolio exposures
            position_dicts = []
            for pos in positions:
                market_value = float(pos.market_value) if pos.market_value else 0
                position_dicts.append({
                    'symbol': pos.symbol,
                    'quantity': float(pos.quantity),
                    'market_value': market_value,
                    'exposure': market_value,
                    'position_type': pos.position_type.value if pos.position_type else 'LONG',
                    'last_price': float(pos.last_price) if pos.last_price else 0
                })
            
            portfolio_exposures = calculate_portfolio_exposures(position_dicts)
            
            print(f"\n2. PORTFOLIO EXPOSURES:")
            print(f"   Gross exposure: ${portfolio_exposures.get('gross_exposure', 0):,.2f}")
            print(f"   Long exposure: ${portfolio_exposures.get('long_exposure', 0):,.2f}")
            print(f"   Short exposure: ${portfolio_exposures.get('short_exposure', 0):,.2f}")
            print(f"   Net exposure: ${portfolio_exposures.get('net_exposure', 0):,.2f}")
            
            # Validate short exposure
            if short_count > 0 and portfolio_exposures.get('short_exposure', 0) == 0:
                print("   ❌ ERROR: Has short positions but short_exposure is $0!")
            elif short_count > 0:
                print("   ✅ Short exposure correctly calculated")
            
            # 3. Check position factor betas
            print(f"\n3. POSITION FACTOR BETAS:")
            pos_factor_stmt = select(PositionFactorExposure).join(
                Position, Position.id == PositionFactorExposure.position_id
            ).where(Position.portfolio_id == portfolio_id)
            
            pos_factor_result = await db.execute(pos_factor_stmt)
            pos_factor_exposures = pos_factor_result.scalars().all()
            
            if pos_factor_exposures:
                print(f"   Position factor records: {len(pos_factor_exposures)}")
                
                # Group by factor
                factor_coverage = {}
                for pfe in pos_factor_exposures:
                    factor_name = factor_id_to_name.get(pfe.factor_id, "Unknown")
                    if factor_name not in factor_coverage:
                        factor_coverage[factor_name] = 0
                    factor_coverage[factor_name] += 1
                
                print("   Factor coverage:")
                for factor_name, count in factor_coverage.items():
                    coverage_pct = (count / len(positions)) * 100
                    print(f"     {factor_name}: {count}/{len(positions)} positions ({coverage_pct:.1f}%)")
            else:
                print("   ❌ No position factor betas found - need to run batch calculations")
            
            # 4. Check portfolio factor exposures
            print(f"\n4. PORTFOLIO FACTOR EXPOSURES:")
            portfolio_factor_stmt = select(FactorExposure).where(
                FactorExposure.portfolio_id == portfolio_id
            ).order_by(FactorExposure.calculation_date.desc()).limit(10)
            
            portfolio_factor_result = await db.execute(portfolio_factor_stmt)
            portfolio_factors = portfolio_factor_result.scalars().all()
            
            if portfolio_factors:
                # Group by date
                latest_date = portfolio_factors[0].calculation_date
                latest_factors = [pf for pf in portfolio_factors if pf.calculation_date == latest_date]
                
                print(f"   Latest calculation date: {latest_date}")
                print(f"   Factor exposures:")
                
                total_dollar_exposure = 0
                gross_exposure = float(portfolio_exposures.get('gross_exposure', 0))
                
                for pf in latest_factors:
                    factor_name = factor_id_to_name.get(pf.factor_id, "Unknown")
                    beta = float(pf.exposure_value) if pf.exposure_value else 0
                    dollar_exp = float(pf.exposure_dollar) if pf.exposure_dollar else 0
                    total_dollar_exposure += abs(dollar_exp)
                    
                    print(f"     {factor_name:20} Beta: {beta:>7.4f}  Dollar: ${dollar_exp:>15,.2f}")
                
                print(f"\n   VALIDATION:")
                print(f"   Total factor $ exposure: ${total_dollar_exposure:,.2f}")
                print(f"   Gross portfolio exposure: ${gross_exposure:,.2f}")
                
                if gross_exposure > 0:
                    ratio = total_dollar_exposure / gross_exposure
                    print(f"   Ratio: {ratio:.2f}x")
                    
                    if ratio > 1.5:
                        print("   ❌ ERROR: Factor exposures exceed gross exposure!")
                        print("   This suggests the old flawed calculation is still running")
                    elif ratio < 0.5:
                        print("   ⚠️ WARNING: Factor exposures seem too low")
                    else:
                        print("   ✅ Factor exposures appear reasonable")
            else:
                print("   ❌ No portfolio factor exposures found - need to run batch calculations")
            
            # 5. Run new calculation (if needed)
            if not portfolio_factors or not pos_factor_exposures:
                print(f"\n5. RUNNING NEW CALCULATIONS:")
                try:
                    # Run factor beta calculation
                    print("   Running factor beta calculations...")
                    factor_results = await calculate_factor_betas_hybrid(
                        db=db,
                        portfolio_id=portfolio_id,
                        calculation_date=date.today(),
                        use_delta_adjusted=False
                    )
                    
                    if factor_results:
                        print(f"   ✅ Factor betas calculated for {len(factor_results.get('position_betas', {}))} positions")
                        print(f"   ✅ Portfolio betas: {list(factor_results.get('factor_betas', {}).keys())}")
                    else:
                        print("   ❌ Factor calculation failed")
                        
                except Exception as e:
                    print(f"   ❌ Error calculating factors: {str(e)}")
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print("\nNEXT STEPS:")
    print("1. If no calculations exist, run batch processing")
    print("2. Generate reports to see the final output")
    print("3. Compare factor exposures to gross exposure")
    print("4. Verify short positions show negative exposure")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(validate_implementation())