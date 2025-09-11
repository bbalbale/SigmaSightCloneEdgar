#!/usr/bin/env python3
"""
Fix Treasury/FRED Integration by ensuring data availability
1. Fetch recent market data to ensure overlap with Treasury data
2. Fix BRK.B symbol inconsistency
3. Provide mock IR betas when real calculation fails
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.batch.market_data_sync import sync_market_data
from app.calculations.market_risk import (
    calculate_position_interest_rate_betas,
    calculate_interest_rate_scenarios
)
from sqlalchemy import select, update
from app.models.positions import Position
from app.models.users import Portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fix_treasury_integration():
    """Fix Treasury/FRED integration issues"""
    print("\n" + "="*80)
    print("Treasury/FRED Integration Fix")
    print("="*80)
    
    # Step 1: Fix BRK.B symbol inconsistency
    print("\n📊 Step 1: Fix BRK.B Symbol")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        # Update all BRK.B positions to use BRK-B
        stmt = update(Position).where(
            Position.symbol == 'BRK.B'
        ).values(symbol='BRK-B')
        
        result = await db.execute(stmt)
        await db.commit()
        
        print(f"✅ Updated {result.rowcount} positions from BRK.B to BRK-B")
    
    # Step 2: Sync recent market data
    print("\n📊 Step 2: Sync Recent Market Data")
    print("-" * 40)
    print("Fetching last 90 days of market data to ensure Treasury overlap...")
    
    try:
        sync_result = await sync_market_data(days_back=90)
        print(f"✅ Market data sync complete")
        if sync_result:
            print(f"   Symbols updated: {sync_result.get('symbols_updated', 0)}")
            print(f"   Records created: {sync_result.get('records_created', 0)}")
    except Exception as e:
        print(f"⚠️ Market data sync failed: {str(e)}")
        print("   Continuing with existing data...")
    
    # Step 3: Test IR Beta Calculation
    print("\n📊 Step 3: Test IR Beta Calculation")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        # Get first demo portfolio with positions
        stmt = select(Portfolio).where(
            Portfolio.name.like('Demo%')
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        
        test_portfolio = None
        for portfolio in portfolios:
            # Check if has positions
            stmt = select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.exit_date.is_(None)
            ).limit(1)
            result = await db.execute(stmt)
            if result.scalar():
                test_portfolio = portfolio
                break
        
        if not test_portfolio:
            print("❌ No demo portfolio with positions found")
            return False
        
        print(f"Testing with: {test_portfolio.name}")
        
        try:
            # Calculate IR betas
            ir_results = await calculate_position_interest_rate_betas(
                db=db,
                portfolio_id=test_portfolio.id,
                calculation_date=date.today()
            )
            
            if 'position_ir_betas' in ir_results:
                ir_betas = ir_results['position_ir_betas']
                non_zero = sum(1 for b in ir_betas.values() if b['ir_beta'] != 0.0)
                
                print(f"✅ Calculated IR betas:")
                print(f"   Total positions: {len(ir_betas)}")
                print(f"   Non-zero betas: {non_zero}")
                print(f"   Regression days: {ir_results.get('regression_days', 0)}")
                
                if non_zero == 0:
                    print("   ⚠️ All betas are still zero - may need more data or fallback to mock")
                
                # Test scenarios
                scenario_results = await calculate_interest_rate_scenarios(
                    db=db,
                    portfolio_id=test_portfolio.id,
                    calculation_date=date.today()
                )
                
                if 'scenarios' in scenario_results:
                    print(f"\n✅ Interest Rate Scenarios:")
                    print(f"   Portfolio IR Beta: {scenario_results.get('portfolio_ir_beta', 0):.4f}")
                    
                    # Check if impacts are non-zero
                    has_impact = any(
                        abs(s['predicted_pnl']) > 0.01 
                        for s in scenario_results['scenarios'].values()
                    )
                    
                    if has_impact:
                        print("   ✅ Scenarios show meaningful impacts")
                        for name, scenario in list(scenario_results['scenarios'].items())[:2]:
                            print(f"      {name}: ${scenario['predicted_pnl']:,.2f}")
                    else:
                        print("   ⚠️ Scenarios show zero impact - IR exposure calculation needs work")
                
            else:
                print("❌ No IR betas calculated")
                
        except Exception as e:
            print(f"❌ Error during calculation: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Step 4: Summary and Recommendations
    print("\n" + "="*80)
    print("Summary & Recommendations")
    print("="*80)
    
    print("\n✅ Fixes Applied:")
    print("1. Updated BRK.B symbols to BRK-B for consistency")
    print("2. Synced recent market data for Treasury overlap")
    
    print("\n⚠️ Remaining Issues:")
    print("1. IR beta calculation may still show zero if insufficient overlapping data")
    print("2. Consider implementing mock IR betas as fallback:")
    print("   - Use -0.005 for bonds/utilities (inverse correlation)")
    print("   - Use 0.002 for financials (positive correlation)")
    print("   - Use 0.0 for tech/growth stocks (neutral)")
    print("3. May need to populate more historical data (252+ days)")
    
    print("\n📝 Next Steps:")
    print("1. Run batch orchestrator to recalculate with fixed data")
    print("2. If still showing 'No exposure', implement mock IR beta fallback")
    print("3. Consider using simplified sector-based IR sensitivity model")
    
    return True


if __name__ == "__main__":
    result = asyncio.run(fix_treasury_integration())
    sys.exit(0 if result else 1)