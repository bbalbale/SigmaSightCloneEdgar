"""
Test IR Stress Testing Integration
Debug why IR stress test scenarios show 0 values
"""
import asyncio
from datetime import date
from uuid import UUID

from app.database import get_async_session
from app.models.users import Portfolio
from app.calculations.stress_testing_ir_integration import (
    get_portfolio_ir_beta,
    calculate_ir_shock_impact,
    add_ir_shocks_to_stress_results
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_ir_stress_integration():
    """Test IR stress integration step by step"""

    async with get_async_session() as db:
        # Get first portfolio
        from sqlalchemy import select
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one()

        portfolio_id = portfolio.id
        calculation_date = date.today()

        print("=" * 80)
        print("IR Stress Testing Integration Diagnostic")
        print("=" * 80)
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio_id}")
        print(f"Calculation Date: {calculation_date}")
        print()

        # Step 1: Test get_portfolio_ir_beta
        print("=" * 80)
        print("Step 1: Testing get_portfolio_ir_beta()")
        print("=" * 80)

        ir_beta_result = await get_portfolio_ir_beta(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            max_staleness_days=7
        )

        print(f"Success: {ir_beta_result.get('success')}")
        if ir_beta_result['success']:
            print(f"Portfolio IR Beta: {ir_beta_result['portfolio_ir_beta']:.4f}")
            print(f"Portfolio Equity: ${ir_beta_result['portfolio_equity']:,.0f}")
            print(f"Positions with Beta: {ir_beta_result['positions_with_beta']}/{ir_beta_result['total_positions']}")
            print(f"IR Beta Date: {ir_beta_result['ir_beta_date']}")
        else:
            print(f"ERROR: {ir_beta_result.get('error')}")
            return

        print()

        # Step 2: Test calculate_ir_shock_impact
        print("=" * 80)
        print("Step 2: Testing calculate_ir_shock_impact() for +50bp shock")
        print("=" * 80)

        ir_shock_impact = await calculate_ir_shock_impact(
            db=db,
            portfolio_id=portfolio_id,
            ir_shock_bps=50.0,  # +50bp rate increase
            calculation_date=calculation_date
        )

        print(f"Success: {ir_shock_impact.get('success')}")
        if ir_shock_impact['success']:
            print(f"IR Shock: {ir_shock_impact['ir_shock_bps']:+.0f}bp ({ir_shock_impact['ir_shock_pct']:.4f} decimal)")
            print(f"Portfolio IR Beta: {ir_shock_impact['portfolio_ir_beta']:.4f}")
            print(f"Portfolio Value: ${ir_shock_impact['portfolio_value']:,.0f}")
            print(f"Predicted P&L: ${ir_shock_impact['predicted_pnl']:,.0f}")

            # Manual calculation verification
            manual_pnl = ir_shock_impact['portfolio_value'] * ir_shock_impact['portfolio_ir_beta'] * ir_shock_impact['ir_shock_pct']
            print(f"Manual Verification: {ir_shock_impact['portfolio_value']:,.0f} × {ir_shock_impact['portfolio_ir_beta']:.4f} × {ir_shock_impact['ir_shock_pct']:.4f} = ${manual_pnl:,.0f}")
        else:
            print(f"ERROR: {ir_shock_impact.get('error')}")
            return

        print()

        # Step 3: Test add_ir_shocks_to_stress_results (as called by stress_testing.py)
        print("=" * 80)
        print("Step 3: Testing add_ir_shocks_to_stress_results() (integration function)")
        print("=" * 80)

        # Simulate a scenario with Interest_Rate shock
        shocked_factors = {
            'Interest_Rate': 0.005  # 50bp = 0.005 in decimal
        }

        integration_result = await add_ir_shocks_to_stress_results(
            db=db,
            portfolio_id=portfolio_id,
            shocked_factors=shocked_factors,
            calculation_date=calculation_date
        )

        print(f"Has IR Shock: {integration_result['has_ir_shock']}")
        if integration_result['has_ir_shock']:
            ir_impact = integration_result.get('ir_impact')
            if ir_impact:
                print(f"IR Impact Success: {ir_impact.get('success')}")
                print(f"Predicted P&L: ${ir_impact['predicted_pnl']:,.0f}")
                print(f"IR Exposure Dollar: ${integration_result['ir_exposure_dollar']:,.0f}")
                print(f"Portfolio IR Beta: {ir_impact['portfolio_ir_beta']:.4f}")
            else:
                print(f"WARNING: IR shock detected but ir_impact is None")
                print(f"Integration result: {integration_result}")

        print()

        # Step 4: Check database for existing stress test results
        print("=" * 80)
        print("Step 4: Checking database for existing stress test results")
        print("=" * 80)

        from app.models.market_data import StressTestResult, StressTestScenario
        from sqlalchemy import select, and_

        # Get IR scenarios
        scenarios_stmt = select(StressTestScenario).where(
            StressTestScenario.scenario_id.like('rates_%')
        )
        scenarios_result = await db.execute(scenarios_stmt)
        ir_scenarios = scenarios_result.scalars().all()

        print(f"Found {len(ir_scenarios)} IR scenarios in database:")
        for scenario in ir_scenarios:
            print(f"  - {scenario.scenario_id}: {scenario.name}")

            # Check results for this scenario
            results_stmt = select(StressTestResult).where(
                and_(
                    StressTestResult.portfolio_id == portfolio_id,
                    StressTestResult.scenario_id == scenario.id
                )
            ).order_by(StressTestResult.calculation_date.desc()).limit(1)

            results_query = await db.execute(results_stmt)
            result_record = results_query.scalar_one_or_none()

            if result_record:
                print(f"    Latest result ({result_record.calculation_date}): Direct=${float(result_record.direct_pnl):,.2f}, Correlated=${float(result_record.correlated_pnl):,.2f}")
            else:
                print(f"    No results found for this scenario")

        print()
        print("=" * 80)
        print("Diagnostic Summary")
        print("=" * 80)

        if ir_beta_result['success'] and ir_shock_impact['success']:
            print("[OK] IR beta calculation: WORKING")
            print("[OK] IR shock impact calculation: WORKING")

            if integration_result['has_ir_shock'] and integration_result['ir_impact']:
                print("[OK] IR integration function: WORKING")
                print()
                print("DIAGNOSIS: IR calculations are working correctly.")
                print("Issue is likely in:")
                print("  1. Stress test batch process not running")
                print("  2. Results not being saved to database")
                print("  3. Frontend reading old/stale data")
            else:
                print("[FAIL] IR integration function: NOT WORKING")
                print()
                print("DIAGNOSIS: Integration function not returning IR impact correctly")
        else:
            print("[FAIL] IR calculations: NOT WORKING")
            print()
            print("DIAGNOSIS: IR beta or shock calculation failing")


if __name__ == "__main__":
    asyncio.run(test_ir_stress_integration())
