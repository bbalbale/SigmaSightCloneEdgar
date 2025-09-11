#!/usr/bin/env python3
"""
Test script for Comprehensive Stress Testing Framework - Section 1.4.7
"""
import asyncio
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position
from app.calculations.stress_testing import (
    calculate_factor_correlation_matrix,
    load_stress_scenarios,
    calculate_direct_stress_impact,
    calculate_correlated_stress_impact,
    run_comprehensive_stress_test,
    save_stress_test_results
)
from sqlalchemy import select


async def test_factor_correlation_matrix():
    """Test factor correlation matrix calculation"""
    print("\n" + "="*60)
    print("Testing Factor Correlation Matrix Calculation")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        try:
            # Test correlation matrix calculation
            correlation_data = await calculate_factor_correlation_matrix(
                db=db,
                lookback_days=252,
                decay_factor=0.94
            )
            
            print(f"✅ Correlation matrix calculated successfully")
            print(f"   📊 Data days: {correlation_data['data_days']}")
            print(f"   📊 Factors: {len(correlation_data['factor_names'])}")
            print(f"   📊 Mean correlation: {correlation_data['matrix_stats']['mean_correlation']:.3f}")
            print(f"   📊 Max correlation: {correlation_data['matrix_stats']['max_correlation']:.3f}")
            print(f"   📊 Min correlation: {correlation_data['matrix_stats']['min_correlation']:.3f}")
            
            # Show sample correlations
            print(f"\n   Sample correlations:")
            factor_names = correlation_data['factor_names'][:4]  # First 4 factors
            for i, factor1 in enumerate(factor_names):
                for j, factor2 in enumerate(factor_names):
                    if i < j:  # Only show upper triangle
                        corr = correlation_data['correlation_matrix'][factor1][factor2]
                        print(f"   {factor1} vs {factor2}: {corr:+.3f}")
            
            return correlation_data
            
        except Exception as e:
            print(f"❌ Error testing correlation matrix: {str(e)}")
            return None


def test_stress_scenarios_config():
    """Test stress scenarios configuration loading"""
    print("\n" + "="*60)
    print("Testing Stress Scenarios Configuration")
    print("="*60)
    
    try:
        # Test loading stress scenarios
        config = load_stress_scenarios()
        
        print(f"✅ Stress scenarios loaded successfully")
        
        # Count scenarios by category
        total_scenarios = 0
        active_scenarios = 0
        categories = {}
        
        for category, scenarios in config['stress_scenarios'].items():
            category_count = len(scenarios)
            active_count = len([s for s in scenarios.values() if s.get('active', True)])
            categories[category] = {'total': category_count, 'active': active_count}
            total_scenarios += category_count
            active_scenarios += active_count
        
        print(f"   📊 Total scenarios: {total_scenarios}")
        print(f"   📊 Active scenarios: {active_scenarios}")
        print(f"   📊 Categories: {len(categories)}")
        
        for category, counts in categories.items():
            print(f"   📋 {category}: {counts['active']}/{counts['total']} active")
        
        # Show sample scenarios
        print(f"\n   Sample scenarios:")
        for category, scenarios in list(config['stress_scenarios'].items())[:2]:
            for scenario_id, scenario in list(scenarios.items())[:2]:
                name = scenario['name']
                severity = scenario['severity']
                factors = list(scenario['shocked_factors'].keys())
                print(f"   {scenario_id}: {name} ({severity}) - Factors: {factors}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error testing stress scenarios config: {str(e)}")
        return None


async def test_direct_stress_impact():
    """Test direct stress impact calculation"""
    print("\n" + "="*60)
    print("Testing Direct Stress Impact Calculation")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio for testing
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return None
        
        print(f"Testing with Portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        try:
            # Test with a sample market crash scenario
            sample_scenario = {
                'name': 'Market Crash 35%',
                'description': 'Severe market crash similar to COVID-19 March 2020',
                'shocked_factors': {
                    'Market': -0.35
                },
                'category': 'market',
                'severity': 'severe'
            }
            
            calculation_date = date.today()
            
            direct_result = await calculate_direct_stress_impact(
                db=db,
                portfolio_id=portfolio.id,
                scenario_config=sample_scenario,
                calculation_date=calculation_date
            )
            
            print(f"✅ Direct stress impact calculated successfully")
            print(f"   📊 Scenario: {direct_result['scenario_name']}")
            print(f"   📊 Total direct P&L: ${direct_result['total_direct_pnl']:,.0f}")
            print(f"   📊 Shocked factors: {len(direct_result['shocked_factors'])}")
            
            # Show factor impacts
            print(f"\n   Factor impacts:")
            for factor_name, impact in direct_result['factor_impacts'].items():
                exposure = impact['exposure_dollar']
                shock = impact['shock_amount']
                pnl = impact['factor_pnl']
                print(f"   {factor_name}: ${exposure:,.0f} × {shock:+.1%} = ${pnl:,.0f}")
            
            return direct_result
            
        except Exception as e:
            print(f"❌ Error testing direct stress impact: {str(e)}")
            return None


async def test_correlated_stress_impact():
    """Test correlated stress impact calculation"""
    print("\n" + "="*60)
    print("Testing Correlated Stress Impact Calculation")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio for testing
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return None
        
        try:
            # Get correlation matrix
            correlation_data = await calculate_factor_correlation_matrix(db)
            correlation_matrix = correlation_data['correlation_matrix']
            
            # Test with a multi-factor scenario
            sample_scenario = {
                'name': 'Value Rotation 20%',
                'description': 'Strong rotation from growth to value stocks',
                'shocked_factors': {
                    'Value': 0.20,
                    'Growth': -0.10
                },
                'category': 'rotation',
                'severity': 'moderate'
            }
            
            calculation_date = date.today()
            
            correlated_result = await calculate_correlated_stress_impact(
                db=db,
                portfolio_id=portfolio.id,
                scenario_config=sample_scenario,
                correlation_matrix=correlation_matrix,
                calculation_date=calculation_date
            )
            
            print(f"✅ Correlated stress impact calculated successfully")
            print(f"   📊 Scenario: {correlated_result['scenario_name']}")
            print(f"   📊 Direct P&L: ${correlated_result['direct_pnl']:,.0f}")
            print(f"   📊 Correlated P&L: ${correlated_result['correlated_pnl']:,.0f}")
            print(f"   📊 Correlation effect: ${correlated_result['correlation_effect']:,.0f}")
            
            # Show top factor impacts
            print(f"\n   Top factor impacts:")
            factor_impacts = [(name, data['total_factor_impact']) 
                            for name, data in correlated_result['factor_impacts'].items()]
            factor_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
            
            for factor_name, impact in factor_impacts[:5]:
                print(f"   {factor_name}: ${impact:,.0f}")
            
            return correlated_result
            
        except Exception as e:
            print(f"❌ Error testing correlated stress impact: {str(e)}")
            return None


async def test_comprehensive_stress_test():
    """Test comprehensive stress test execution"""
    print("\n" + "="*60)
    print("Testing Comprehensive Stress Test")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio for testing
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return None
        
        print(f"Running comprehensive stress test for: {portfolio.name}")
        
        try:
            calculation_date = date.today()
            
            # Run comprehensive stress test (limit to market_risk scenarios for faster testing)
            comprehensive_results = await run_comprehensive_stress_test(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date,
                scenario_filter=['market_risk', 'factor_rotations']  # Limit for testing
            )
            
            print(f"✅ Comprehensive stress test completed successfully")
            
            # Show summary statistics
            config_meta = comprehensive_results['config_metadata']
            print(f"   📊 Scenarios tested: {config_meta['scenarios_tested']}/{config_meta['scenarios_available']}")
            print(f"   📊 Categories tested: {config_meta['categories_tested']}")
            
            stress_stats = comprehensive_results['stress_test_results']['summary_stats']
            if stress_stats:
                print(f"   📊 Worst case P&L: ${stress_stats['worst_case_pnl']:,.0f}")
                print(f"   📊 Best case P&L: ${stress_stats['best_case_pnl']:,.0f}")
                print(f"   📊 Mean P&L: ${stress_stats['mean_pnl']:,.0f}")
                print(f"   📊 Negative scenarios: {stress_stats['scenarios_negative']}")
                print(f"   📊 Positive scenarios: {stress_stats['scenarios_positive']}")
                print(f"   📊 Mean correlation effect: ${stress_stats['mean_correlation_effect']:,.0f}")
            
            # Show sample results
            print(f"\n   Sample scenario results:")
            stress_results = comprehensive_results['stress_test_results']['correlated_impacts']
            sample_count = 0
            
            for category, scenarios in stress_results.items():
                if sample_count >= 5:
                    break
                for scenario_id, result in scenarios.items():
                    if sample_count >= 5:
                        break
                    name = result['scenario_name']
                    pnl = result['correlated_pnl']
                    correlation_effect = result['correlation_effect']
                    print(f"   {scenario_id}: {name} → ${pnl:,.0f} (corr: ${correlation_effect:+,.0f})")
                    sample_count += 1
            
            return comprehensive_results
            
        except Exception as e:
            print(f"❌ Error testing comprehensive stress test: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """Main test function"""
    print("Comprehensive Stress Testing Framework - Section 1.4.7")
    print("=" * 80)
    
    # Test 1: Factor correlation matrix
    correlation_data = await test_factor_correlation_matrix()
    
    # Test 2: Stress scenarios configuration
    config_data = test_stress_scenarios_config()
    
    # Test 3: Direct stress impact
    direct_result = await test_direct_stress_impact()
    
    # Test 4: Correlated stress impact
    correlated_result = await test_correlated_stress_impact()
    
    # Test 5: Comprehensive stress test
    comprehensive_result = await test_comprehensive_stress_test()
    
    # Summary
    print("\n" + "="*80)
    tests_passed = sum([
        1 if correlation_data else 0,
        1 if config_data else 0, 
        1 if direct_result else 0,
        1 if correlated_result else 0,
        1 if comprehensive_result else 0
    ])
    
    if tests_passed == 5:
        print("✅ All Comprehensive Stress Testing tests passed!")
        print(f"🎯 Framework ready for production use")
        if comprehensive_result:
            stats = comprehensive_result['stress_test_results']['summary_stats']
            if stats:
                print(f"📊 Portfolio risk range: ${stats['worst_case_pnl']:,.0f} to ${stats['best_case_pnl']:,.0f}")
        return True
    else:
        print(f"❌ {5-tests_passed}/5 tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)