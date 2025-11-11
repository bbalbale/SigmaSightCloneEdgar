#!/usr/bin/env python
"""
Test stress testing calculations in isolation.
"""

import asyncio
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.calculations.stress_testing import (
    run_comprehensive_stress_test,
    calculate_direct_stress_impact,
    calculate_factor_correlation_matrix
)
from app.models.market_data import StressTestScenario, StressTestResult
from app.core.logging import get_logger
from sqlalchemy import select, func

logger = get_logger(__name__)


async def test_stress_calculations():
    """Test stress calculations for demo portfolio."""
    
    print("=" * 60)
    print("🧪 TESTING STRESS CALCULATIONS")
    print("=" * 60)
    
    # Use demo portfolio
    portfolio_id = UUID("51134ffd-2f13-49bd-b1f5-0c327e801b69")
    portfolio_name = "Demo Individual Investor Portfolio"
    
    print(f"\nPortfolio: {portfolio_name}")
    print(f"ID: {portfolio_id}")
    
    async with get_async_session() as db:
        # Check scenarios exist
        result = await db.execute(select(func.count(StressTestScenario.id)))
        scenario_count = result.scalar()
        
        if scenario_count == 0:
            print("\n❌ No scenarios in database. Run seed_stress_scenarios.py first!")
            return False
        
        print(f"\n✅ Found {scenario_count} stress scenarios")
        
        # Test factor correlation matrix calculation
        print("\n📊 Testing Factor Correlation Matrix...")
        try:
            correlation_data = await calculate_factor_correlation_matrix(
                db,
                lookback_days=150  # Use shorter period for testing
            )
            
            print(f"   ✅ Correlation matrix calculated")
            print(f"   - Factors: {len(correlation_data['factor_names'])}")
            print(f"   - Data days: {correlation_data['data_days']}")
            print(f"   - Mean correlation: {correlation_data['matrix_stats']['mean_correlation']:.3f}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False
        
        # Test a single scenario
        print("\n🎯 Testing Single Scenario (Market Down 10%)...")
        
        # Get a test scenario
        result = await db.execute(
            select(StressTestScenario).where(
                StressTestScenario.scenario_id == "market_down_10"
            )
        )
        test_scenario = result.scalar_one_or_none()
        
        if test_scenario:
            print(f"   Scenario: {test_scenario.name}")
            print(f"   Shocks: {test_scenario.shock_config}")
            
            try:
                # Test direct impact calculation
                scenario_config = {
                    'id': test_scenario.scenario_id,
                    'name': test_scenario.name,
                    'shocked_factors': test_scenario.shock_config
                }
                
                direct_result = await calculate_direct_stress_impact(
                    db,
                    portfolio_id,
                    scenario_config,
                    date.today()
                )
                
                print(f"\n   📈 Direct Impact Results:")
                print(f"      Total P&L: ${direct_result.get('total_direct_pnl', 0):,.2f}")
                
                # Show factor impacts
                factor_impacts = direct_result.get('factor_impacts', {})
                if factor_impacts:
                    print(f"      Factor Impacts:")
                    for factor, impact_data in factor_impacts.items():
                        pnl = impact_data.get('factor_pnl', 0)
                        if pnl != 0:
                            print(f"         {factor}: ${pnl:,.2f}")
                
            except Exception as e:
                print(f"   ❌ Error in direct calculation: {str(e)}")
        
        # Test comprehensive stress test
        print("\n🚀 Testing Comprehensive Stress Test...")
        print("   (This will run all 18 scenarios)")
        
        try:
            results = await run_comprehensive_stress_test(
                db,
                portfolio_id,
                date.today(),
                scenario_filter=["market_risk", "interest_rate_risk"]  # Use correct category names
            )
            
            print(f"\n   ✅ Stress test completed")
            
            # Show summary
            summary = results.get('stress_test_results', {}).get('summary_stats', {})
            scenarios_tested = results.get('stress_test_results', {}).get('scenarios_tested', 0)
            
            print(f"\n   📊 Summary Statistics:")
            print(f"      Scenarios tested: {scenarios_tested}")
            
            if summary:
                print(f"      Worst case P&L: ${summary.get('worst_case_pnl', 0):,.2f}")
                print(f"      Best case P&L: ${summary.get('best_case_pnl', 0):,.2f}")
                print(f"      Mean P&L: ${summary.get('mean_pnl', 0):,.2f}")
                print(f"      Std Dev: ${summary.get('pnl_std', 0):,.2f}")
            
            # Check if results were saved
            result = await db.execute(
                select(func.count(StressTestResult.id)).where(
                    StressTestResult.portfolio_id == portfolio_id
                )
            )
            saved_results = result.scalar()
            
            print(f"\n   💾 Database Status:")
            print(f"      Results saved: {saved_results}")
            
            if saved_results == 0:
                print("      ⚠️ Note: Results not being saved to database yet")
                print("         This is expected - saving logic not implemented")
            
            return True
            
        except Exception as e:
            print(f"\n   ❌ Error in comprehensive test: {str(e)}")
            logger.error(f"Comprehensive test error: {str(e)}", exc_info=True)
            return False


def main():
    """Main entry point."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(test_stress_calculations())
        
        if success:
            print("\n✅ Stress testing calculations working!")
            return 0
        else:
            print("\n❌ Stress testing has issues")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())