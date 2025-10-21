#!/usr/bin/env python3
"""
Test script for Market Risk Scenarios - Section 1.4.5
"""
import asyncio
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.calculations.market_risk import (
    calculate_portfolio_market_beta,
    calculate_market_scenarios,
    calculate_position_interest_rate_betas,
    calculate_interest_rate_scenarios
)
from sqlalchemy import select


async def test_market_risk_scenarios():
    """Test market risk scenario calculations"""
    print("Testing Market Risk Scenarios - Section 1.4.5")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio for testing
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return False
        
        print(f"Testing with Portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        # Check if portfolio has active positions
        stmt = select(Position).where(Position.portfolio_id == portfolio.id, Position.exit_date.is_(None))
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            print("❌ No active positions found for portfolio")
            return False
        
        print(f"Found {len(positions)} active positions")
        
        calculation_date = date.today()
        
        try:
            # Test 1: Calculate portfolio market beta
            print("\n1. Testing Portfolio Market Beta Calculation...")
            market_beta_result = await calculate_portfolio_market_beta(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            
            print(f"   ✅ Market Beta: {market_beta_result['market_beta']:.4f}")
            print(f"   ✅ Portfolio Value: ${market_beta_result['portfolio_value']:,.2f}")
            print(f"   ✅ Data Quality: {market_beta_result['data_quality']['quality_flag']}")
            
            # Test 2: Calculate market scenarios
            print("\n2. Testing Market Scenarios Calculation...")
            market_scenarios_result = await calculate_market_scenarios(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            
            print(f"   ✅ Scenarios calculated: {len(market_scenarios_result['scenarios'])}")
            print(f"   ✅ Records stored: {market_scenarios_result['records_stored']}")
            
            # Show some scenario results
            for scenario_name, scenario_data in list(market_scenarios_result['scenarios'].items())[:3]:
                pnl = scenario_data['predicted_pnl']
                change = scenario_data['scenario_value'] * 100
                print(f"   📊 {scenario_name}: {change:+.1f}% → ${pnl:,.2f} P&L")
            
            # Test 3: Calculate position interest rate betas
            print("\n3. Testing Position Interest Rate Betas...")
            ir_beta_result = await calculate_position_interest_rate_betas(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            
            print(f"   ✅ IR Betas calculated: {len(ir_beta_result['position_ir_betas'])}")
            print(f"   ✅ Records stored: {ir_beta_result['records_stored']}")
            print(f"   ✅ Treasury series: {ir_beta_result['treasury_series']}")
            
            # Show some IR beta results
            for i, (pos_id, beta_data) in enumerate(list(ir_beta_result['position_ir_betas'].items())[:3]):
                ir_beta = beta_data['ir_beta']
                r_squared = beta_data['r_squared']
                print(f"   📊 Position {i+1}: IR Beta = {ir_beta:.4f}, R² = {r_squared:.3f}")
            
            # Test 4: Calculate interest rate scenarios
            print("\n4. Testing Interest Rate Scenarios...")
            ir_scenarios_result = await calculate_interest_rate_scenarios(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date
            )
            
            print(f"   ✅ IR Scenarios calculated: {len(ir_scenarios_result['scenarios'])}")
            print(f"   ✅ Records stored: {ir_scenarios_result['records_stored']}")
            print(f"   ✅ Portfolio IR Beta: {ir_scenarios_result['portfolio_ir_beta']:.4f}")
            
            # Show some IR scenario results
            for scenario_name, scenario_data in list(ir_scenarios_result['scenarios'].items())[:2]:
                pnl = scenario_data['predicted_pnl'] 
                rate_change_bp = scenario_data['rate_change_bp']
                print(f"   📊 {scenario_name}: {rate_change_bp:+.0f}bp → ${pnl:,.2f} P&L")
            
            print("\n" + "=" * 50)
            print("✅ All Market Risk Scenario tests passed!")
            print(f"📊 Total scenarios stored: {market_scenarios_result['records_stored'] + ir_scenarios_result['records_stored']}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Main test function"""
    success = await test_market_risk_scenarios()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)