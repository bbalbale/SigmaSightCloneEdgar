#!/usr/bin/env python3
"""
Check stress test data in the database for a specific portfolio.
"""

import asyncio
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.market_data import StressTestScenario, StressTestResult
from app.models.users import Portfolio
import json
from datetime import datetime

PORTFOLIO_ID = "e23ab931-a033-edfe-ed4f-9d02474780b4"

async def check_stress_test():
    """Check what stress test data exists for the portfolio."""
    
    async with AsyncSessionLocal() as session:
        portfolio_uuid = UUID(PORTFOLIO_ID)
        
        print(f"\n{'='*80}")
        print(f"Stress Test Analysis for Portfolio: {PORTFOLIO_ID}")
        print(f"{'='*80}\n")
        
        # 1. Check if portfolio exists
        portfolio = await session.get(Portfolio, portfolio_uuid)
        if not portfolio:
            print(f"❌ Portfolio not found!")
            return
        
        print(f"✅ Portfolio found: {portfolio.name}")
        print(f"   User ID: {portfolio.user_id}")
        print(f"   Created: {portfolio.created_at}")
        
        # 2. Check stress test scenarios (definitions)
        print(f"\n📊 STRESS TEST SCENARIOS (DEFINITIONS):")
        print("-" * 40)
        
        scenarios_query = select(StressTestScenario).where(
            StressTestScenario.active == True
        ).order_by(StressTestScenario.category, StressTestScenario.severity)
        
        scenarios_result = await session.execute(scenarios_query)
        scenarios = scenarios_result.scalars().all()
        
        if not scenarios:
            print("❌ No active stress test scenarios found")
        else:
            print(f"✅ Found {len(scenarios)} active stress test scenarios")
            
            # Group by category
            categories = {}
            for scenario in scenarios:
                if scenario.category not in categories:
                    categories[scenario.category] = []
                categories[scenario.category].append(scenario)
            
            for category, cat_scenarios in categories.items():
                print(f"\n   📋 Category: {category}")
                for scenario in cat_scenarios:
                    print(f"      • {scenario.scenario_id}: {scenario.name} ({scenario.severity})")
                    if scenario.description:
                        print(f"        Description: {scenario.description[:80]}...")
                    print(f"        Config: {json.dumps(scenario.shock_config, indent=8)}")
        
        # 3. Check stress test results for this portfolio
        print(f"\n📊 STRESS TEST RESULTS:")
        print("-" * 40)
        
        results_query = select(StressTestResult).options(
            selectinload(StressTestResult.scenario)
        ).where(
            StressTestResult.portfolio_id == portfolio_uuid
        ).order_by(StressTestResult.calculation_date.desc())
        
        results_result = await session.execute(results_query)
        stress_results = results_result.scalars().all()
        
        if not stress_results:
            print("❌ No stress test results found for this portfolio")
        else:
            print(f"✅ Found {len(stress_results)} stress test results")
            
            # Group by calculation date
            dates = {}
            for result in stress_results:
                date_str = result.calculation_date.strftime("%Y-%m-%d") if result.calculation_date else "None"
                if date_str not in dates:
                    dates[date_str] = []
                dates[date_str].append(result)
            
            for date_str, results in sorted(dates.items(), reverse=True)[:3]:  # Show last 3 dates
                print(f"\n   📅 Date: {date_str}")
                print(f"   Results ({len(results)}):")
                for result in results[:10]:  # Show first 10 results
                    scenario_name = result.scenario.name if result.scenario else "Unknown"
                    print(f"      • {scenario_name}:")
                    print(f"        Direct P&L: ${result.direct_pnl:,.2f}")
                    print(f"        Correlated P&L: ${result.correlated_pnl:,.2f}")
                    print(f"        Correlation Effect: ${result.correlation_effect:,.2f}")
                if len(results) > 10:
                    print(f"      ... and {len(results) - 10} more results")
        
        # 4. Check for calculation date consistency
        print(f"\n📅 CALCULATION DATE ANALYSIS:")
        print("-" * 40)
        
        # Get unique calculation dates for stress test results
        dates_query = select(
            func.distinct(StressTestResult.calculation_date)
        ).where(
            StressTestResult.portfolio_id == portfolio_uuid
        ).order_by(StressTestResult.calculation_date.desc())
        
        dates_result = await session.execute(dates_query)
        result_dates = [d[0] for d in dates_result.all() if d[0]]
        
        print(f"Stress test calculation dates: {len(result_dates)}")
        for date in result_dates[:5]:
            print(f"   • {date.strftime('%Y-%m-%d')}")
        
        # 5. Check scenario coverage
        print(f"\n✅ SCENARIO COVERAGE CHECK:")
        print("-" * 40)
        
        if result_dates:
            latest_date = result_dates[0]
            date_str = latest_date.strftime("%Y-%m-%d")
            
            # Count scenarios for latest date
            scenario_count_query = select(
                func.count(func.distinct(StressTestResult.scenario_id))
            ).where(
                StressTestResult.portfolio_id == portfolio_uuid,
                StressTestResult.calculation_date == latest_date
            )
            
            scenario_count_result = await session.execute(scenario_count_query)
            scenario_count = scenario_count_result.scalar()
            
            # Get actual scenario names for latest date
            scenario_names_query = select(StressTestScenario.name).join(
                StressTestResult, StressTestScenario.id == StressTestResult.scenario_id
            ).where(
                StressTestResult.portfolio_id == portfolio_uuid,
                StressTestResult.calculation_date == latest_date
            ).distinct()
            
            scenario_names_result = await session.execute(scenario_names_query)
            scenario_names = [s[0] for s in scenario_names_result.all()]
            
            print(f"\n   Latest date: {date_str}")
            print(f"   Scenarios with results: {scenario_count}/{len(scenarios)}")
            print(f"   Scenarios: {', '.join(scenario_names)}")
            
            missing_scenarios = set(s.name for s in scenarios) - set(scenario_names)
            if missing_scenarios:
                print(f"   ❌ Missing scenarios: {', '.join(missing_scenarios)}")
            else:
                print(f"   ✅ All active scenarios have results!")
        
        # 6. Check for table existence and structure
        print(f"\n🗃️ TABLE STRUCTURE CHECK:")
        print("-" * 40)
        
        # Test basic queries to check table structure
        try:
            test_query = select(func.count()).select_from(StressTestScenario)
            test_result = await session.execute(test_query)
            scenario_table_count = test_result.scalar()
            print(f"✅ stress_test_scenarios table exists ({scenario_table_count} total records)")
        except Exception as e:
            print(f"❌ stress_test_scenarios table issue: {e}")
            
        try:
            test_query2 = select(func.count()).select_from(StressTestResult)
            test_result2 = await session.execute(test_query2)
            results_table_count = test_result2.scalar()
            print(f"✅ stress_test_results table exists ({results_table_count} total records)")
        except Exception as e:
            print(f"❌ stress_test_results table issue: {e}")
        
        print(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(check_stress_test())