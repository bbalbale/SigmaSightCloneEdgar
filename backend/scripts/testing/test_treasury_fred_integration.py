#!/usr/bin/env python3
"""
Test Treasury/FRED Integration - Debug Interest Rate Beta Calculations
Investigates why showing "No exposure found" for all portfolios
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
from fredapi import Fred

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.calculations.market_risk import (
    calculate_position_interest_rate_betas,
    calculate_interest_rate_scenarios
)
from app.config import settings
from app.core.logging import get_logger
from sqlalchemy import select
from app.models.users import Portfolio

logger = get_logger(__name__)


async def test_fred_api_connection():
    """Test FRED API connection and data retrieval"""
    print("\n" + "="*80)
    print("Treasury/FRED Integration Test - Debugging Interest Rate Beta")
    print("="*80)
    
    # Test 1: FRED API Configuration
    print("\n📊 Test 1: FRED API Configuration")
    print("-" * 40)
    
    if not hasattr(settings, 'FRED_API_KEY'):
        print("❌ FRED_API_KEY not in settings")
        return False
    
    if not settings.FRED_API_KEY:
        print("❌ FRED_API_KEY is empty")
        return False
    
    print(f"✅ FRED_API_KEY configured: {settings.FRED_API_KEY[:8]}...")
    
    # Test 2: FRED API Connection
    print("\n🔌 Test 2: FRED API Connection")
    print("-" * 40)
    
    try:
        fred = Fred(api_key=settings.FRED_API_KEY)
        
        # Try to fetch 10-Year Treasury data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        treasury_data = fred.get_series(
            'DGS10',  # 10-Year Treasury
            observation_start=start_date,
            observation_end=end_date
        )
        
        print(f"✅ Successfully fetched Treasury data")
        print(f"   Data points: {len(treasury_data)}")
        print(f"   Latest rate: {treasury_data.iloc[-1]:.2f}%")
        print(f"   Date range: {treasury_data.index[0].date()} to {treasury_data.index[-1].date()}")
        
        # Show sample data
        print("\n   Sample data (last 5 days):")
        for idx in range(max(0, len(treasury_data)-5), len(treasury_data)):
            print(f"   {treasury_data.index[idx].date()}: {treasury_data.iloc[idx]:.2f}%")
        
    except Exception as e:
        print(f"❌ Failed to fetch Treasury data: {str(e)}")
        return False
    
    # Test 3: Calculate Interest Rate Betas for Demo Portfolios
    print("\n💰 Test 3: Interest Rate Beta Calculation")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        # Get demo portfolios
        stmt = select(Portfolio).where(
            Portfolio.name.like('Demo%')
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        
        if not portfolios:
            print("❌ No demo portfolios found")
            return False
        
        print(f"Found {len(portfolios)} demo portfolios")
        
        for portfolio in portfolios:
            print(f"\n📁 Portfolio: {portfolio.name}")
            
            try:
                # Calculate IR betas
                ir_results = await calculate_position_interest_rate_betas(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=date.today()
                )
                
                if 'position_ir_betas' in ir_results:
                    ir_betas = ir_results['position_ir_betas']
                    print(f"   ✅ Calculated IR betas for {len(ir_betas)} positions")
                    
                    # Show sample betas
                    if ir_betas:
                        sample_items = list(ir_betas.items())[:3]
                        for pos_id, beta_data in sample_items:
                            print(f"      Position {pos_id[:8]}...: Beta={beta_data['ir_beta']:.4f}, R²={beta_data['r_squared']:.4f}")
                    
                    # Check if all betas are zero
                    all_zero = all(b['ir_beta'] == 0.0 for b in ir_betas.values())
                    if all_zero:
                        print("   ⚠️ WARNING: All IR betas are zero!")
                    
                    print(f"   Treasury data points: {ir_results.get('treasury_data_points', 0)}")
                    print(f"   Regression days: {ir_results.get('regression_days', 0)}")
                    
                else:
                    print("   ❌ No IR betas calculated")
                    
            except Exception as e:
                print(f"   ❌ Error calculating IR betas: {str(e)}")
    
    # Test 4: Interest Rate Scenarios
    print("\n📈 Test 4: Interest Rate Scenarios")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        for portfolio in portfolios[:1]:  # Test first portfolio only
            print(f"\n📁 Portfolio: {portfolio.name}")
            
            try:
                # Calculate IR scenarios
                scenario_results = await calculate_interest_rate_scenarios(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=date.today()
                )
                
                if 'scenarios' in scenario_results:
                    print(f"   ✅ Calculated {len(scenario_results['scenarios'])} scenarios")
                    print(f"   Portfolio IR Beta: {scenario_results.get('portfolio_ir_beta', 0):.4f}")
                    print(f"   Portfolio Value: ${scenario_results.get('portfolio_value', 0):,.2f}")
                    
                    # Show scenario impacts
                    for scenario_name, scenario_data in scenario_results['scenarios'].items():
                        print(f"   {scenario_name}: P&L = ${scenario_data['predicted_pnl']:,.2f}")
                    
                    # Check if all impacts are zero
                    all_zero = all(s['predicted_pnl'] == 0 for s in scenario_results['scenarios'].values())
                    if all_zero:
                        print("   ⚠️ WARNING: All scenario impacts are zero!")
                        print("      This explains 'No exposure found' message")
                        
                else:
                    print("   ❌ No scenarios calculated")
                    
            except Exception as e:
                print(f"   ❌ Error calculating scenarios: {str(e)}")
    
    # Test 5: Debug Position Returns
    print("\n🔍 Test 5: Debug Position Returns Availability")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        from app.calculations.factors import calculate_position_returns
        
        portfolio = portfolios[0] if portfolios else None
        if portfolio:
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=90)
                
                position_returns = await calculate_position_returns(
                    db=db,
                    portfolio_id=portfolio.id,
                    start_date=start_date,
                    end_date=end_date,
                    use_delta_adjusted=False
                )
                
                if position_returns.empty:
                    print("   ❌ No position returns data available")
                    print("      This would cause IR beta calculation to fail")
                else:
                    print(f"   ✅ Position returns available")
                    print(f"      Shape: {position_returns.shape}")
                    print(f"      Date range: {position_returns.index[0]} to {position_returns.index[-1]}")
                    print(f"      Positions: {list(position_returns.columns)[:3]}...")
                    
                    # Check for data overlap with Treasury dates
                    common_dates = treasury_data.index.intersection(position_returns.index)
                    print(f"      Common dates with Treasury: {len(common_dates)}")
                    
                    if len(common_dates) < 60:
                        print("      ⚠️ WARNING: Insufficient overlapping data for regression")
                        
            except Exception as e:
                print(f"   ❌ Error fetching position returns: {str(e)}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 Treasury/FRED Integration Test Summary")
    print("="*80)
    
    print("\nPotential Issues Identified:")
    print("1. Check if position returns have sufficient historical data")
    print("2. Verify date alignment between Treasury and position data")
    print("3. Ensure positions have price history in market_data_cache")
    print("4. Check if regression calculation is failing silently")
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_fred_api_connection())
    sys.exit(0 if result else 1)