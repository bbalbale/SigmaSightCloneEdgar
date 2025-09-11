"""
Analyze the impact of the interest rate units issue (10x multiplier problem)
"""
import asyncio
from app.database import get_async_session
from sqlalchemy import select, text
from app.models.market_data import StressTestResult
from app.models.users import Portfolio
from decimal import Decimal

async def analyze_interest_rate_impact():
    """
    Check the magnitude of interest rate stress test results to understand
    if the 10x multiplier issue is causing unrealistic scenarios.
    """
    
    async with get_async_session() as db:
        print("=" * 80)
        print("INTEREST RATE UNITS IMPACT ANALYSIS")
        print("=" * 80)
        
        # 1. Check if stress_test_results table exists
        try:
            check_table = await db.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'stress_test_results')"
            ))
            table_exists = check_table.scalar()
            
            if not table_exists:
                print("\n❌ stress_test_results table does not exist")
                print("This is a known issue - table was never created in migrations")
                print("\nIMPACT: Stress test results are calculated but not persisted")
                print("SEVERITY: Low - calculations still work, just not saved to DB")
                
                # Let's check the actual calculation logic instead
                print("\n" + "=" * 80)
                print("CHECKING CALCULATION LOGIC")
                print("=" * 80)
                
                from app.calculations.stress_tests import STRESS_SCENARIOS
                
                print("\nDefined stress scenarios:")
                for scenario in STRESS_SCENARIOS:
                    print(f"\n{scenario['name']}:")
                    for shock in scenario.get('shocks', []):
                        factor = shock.get('factor', 'Unknown')
                        magnitude = shock.get('magnitude', 0)
                        print(f"  - {factor}: {magnitude:.1%} shock")
                
                # Check Interest Rate scenario specifically
                interest_scenarios = [s for s in STRESS_SCENARIOS 
                                    if 'Interest' in s['name'] or 'Rate' in s['name']]
                
                print("\n" + "=" * 80)
                print("INTEREST RATE SCENARIOS:")
                print("=" * 80)
                
                for scenario in interest_scenarios:
                    print(f"\n{scenario['name']}:")
                    print(f"  Description: {scenario.get('description', 'N/A')}")
                    shocks = scenario.get('shocks', [])
                    for shock in shocks:
                        if 'Interest' in shock.get('factor', ''):
                            magnitude = shock.get('magnitude', 0)
                            print(f"  Shock magnitude: {magnitude:.1%}")
                            
                            # Check if this is reasonable
                            if abs(magnitude) > 0.5:  # More than 50%
                                print(f"  ⚠️ WARNING: {abs(magnitude):.0%} shock seems excessive")
                                print(f"     Typical rate shocks are 1-3% (0.01-0.03)")
                                print(f"     This might be the 10x issue!")
                            else:
                                print(f"  ✅ Magnitude seems reasonable")
                
                # Let's also check how interest rate factor is mapped
                print("\n" + "=" * 80)
                print("FACTOR MAPPING CHECK:")
                print("=" * 80)
                
                from app.calculations.stress_tests import FACTOR_MAPPING
                
                interest_mappings = {k: v for k, v in FACTOR_MAPPING.items() 
                                   if 'Interest' in k or 'Interest' in v}
                
                if interest_mappings:
                    print("\nInterest rate factor mappings:")
                    for key, value in interest_mappings.items():
                        print(f"  {key} -> {value}")
                else:
                    print("\n⚠️ No interest rate factor mapping found")
                    print("This might be why stress tests show 'No exposure found for Interest_Rate'")
                
                return
                
        except Exception as e:
            print(f"\n❌ Error checking table: {e}")
            print("Proceeding with calculation logic check...")
        
        # If table exists, check actual results (unlikely given known issue)
        print("\n✅ stress_test_results table exists (unexpected!)")
        
        # Get portfolios
        portfolios = await db.execute(select(Portfolio))
        portfolios = portfolios.scalars().all()
        
        print(f"\nAnalyzing stress test results for {len(portfolios)} portfolios...")
        
        for portfolio in portfolios:
            print(f"\n{portfolio.name}:")
            
            # Get stress test results
            stmt = select(StressTestResult).where(
                StressTestResult.portfolio_id == portfolio.id
            ).order_by(StressTestResult.calculation_date.desc()).limit(10)
            
            results = await db.execute(stmt)
            stress_results = results.scalars().all()
            
            if not stress_results:
                print("  No stress test results found")
                continue
            
            # Check for interest rate scenarios
            # Note: StressTestResult has scenario_id, not scenario_name
            interest_results = []
            for r in stress_results:
                # For now, just show all results since we don't have scenario names
                interest_results.append(r)
            
            if interest_results:
                print(f"  Found {len(interest_results)} stress test results:")
                for result in interest_results[:3]:  # Show first 3
                    # Get portfolio value for percentage calculation
                    portfolio_value = 1000000  # Default assumption
                    loss_pct = (float(result.portfolio_impact) / portfolio_value * 100) if portfolio_value else 0
                    print(f"    - Scenario {result.scenario_id}: ${float(result.portfolio_impact):,.2f} ({loss_pct:.1f}% of portfolio)")
                    
                    # Check if impact seems unreasonable
                    if abs(loss_pct) > 50:
                        print(f"      ⚠️ WARNING: {abs(loss_pct):.0f}% loss seems excessive for interest rate shock")
            else:
                print("  No interest rate stress test results")

async def check_actual_calculations():
    """
    Run a sample interest rate calculation to see the actual impact
    """
    print("\n" + "=" * 80)
    print("SAMPLE CALCULATION CHECK")
    print("=" * 80)
    
    # Simulate what happens with different units
    portfolio_value = 1000000  # $1M portfolio
    interest_rate_beta = 0.5  # Moderate interest rate sensitivity
    
    print(f"\nPortfolio: ${portfolio_value:,.0f}")
    print(f"Interest Rate Beta: {interest_rate_beta}")
    
    # Scenario 1: Correct units (basis points)
    rate_shock_bps = 100  # 100 basis points = 1%
    rate_shock_decimal = rate_shock_bps / 10000  # Convert to decimal
    impact_correct = portfolio_value * interest_rate_beta * rate_shock_decimal
    
    print(f"\n✅ CORRECT: 100bp (1%) rate increase")
    print(f"  Calculation: ${portfolio_value:,.0f} × {interest_rate_beta} × {rate_shock_decimal:.4f}")
    print(f"  Impact: ${impact_correct:,.2f} ({impact_correct/portfolio_value*100:.2f}%)")
    
    # Scenario 2: Wrong units (treating 1% as 1.0 instead of 0.01)
    rate_shock_wrong = 1.0  # Wrong: treating 1% as 1.0
    impact_wrong = portfolio_value * interest_rate_beta * rate_shock_wrong
    
    print(f"\n❌ WRONG: 1% rate increase (incorrect units)")
    print(f"  Calculation: ${portfolio_value:,.0f} × {interest_rate_beta} × {rate_shock_wrong:.1f}")
    print(f"  Impact: ${impact_wrong:,.2f} ({impact_wrong/portfolio_value*100:.0f}%)")
    
    print(f"\n🔍 MULTIPLIER ERROR: {impact_wrong/impact_correct:.0f}x too large")
    
    # Scenario 3: What we might be seeing (10% instead of 1%)
    rate_shock_10x = 0.10  # 10% shock when we meant 1%
    impact_10x = portfolio_value * interest_rate_beta * rate_shock_10x
    
    print(f"\n⚠️ POSSIBLE ISSUE: 10% shock instead of 1%")
    print(f"  Calculation: ${portfolio_value:,.0f} × {interest_rate_beta} × {rate_shock_10x:.2f}")
    print(f"  Impact: ${impact_10x:,.2f} ({impact_10x/portfolio_value*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(analyze_interest_rate_impact())
    asyncio.run(check_actual_calculations())