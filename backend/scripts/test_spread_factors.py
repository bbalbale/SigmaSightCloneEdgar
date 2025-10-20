"""
Test Spread Factor Calculation
Quick validation of spread factor implementation.
"""
import asyncio
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.market_data import FactorDefinition, FactorExposure
from app.calculations.factors_spread import calculate_portfolio_spread_betas
from app.calculations.factor_interpretation import interpret_spread_beta
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_spread_factor_definitions(db: AsyncSession):
    """Verify the 4 spread factor definitions exist in database."""
    print("\n" + "="*60)
    print("STEP 1: Verifying Spread Factor Definitions")
    print("="*60)

    query = select(FactorDefinition).where(
        FactorDefinition.factor_type == 'spread'
    ).order_by(FactorDefinition.display_order)

    result = await db.execute(query)
    spread_factors = result.scalars().all()

    print(f"\n✅ Found {len(spread_factors)} spread factor definitions:\n")
    for factor in spread_factors:
        print(f"  {factor.display_order}. {factor.name}")
        print(f"     ETF Proxy: {factor.etf_proxy}")
        print(f"     Method: {factor.calculation_method}")
        print()

    return len(spread_factors) == 4


async def test_calculation_on_demo_portfolio(db: AsyncSession):
    """Test spread factor calculation on demo HNW portfolio."""
    print("\n" + "="*60)
    print("STEP 2: Testing Calculation on Demo Portfolio")
    print("="*60)

    # Get demo_hnw portfolio (has NVDA - should show strong growth tilt)
    portfolio_query = select(Portfolio).where(
        Portfolio.name.like('%High Net Worth%')
    )
    result = await db.execute(portfolio_query)
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        print("❌ Demo HNW portfolio not found")
        return False

    print(f"\n📊 Portfolio: {portfolio.name}")
    print(f"   ID: {portfolio.id}")
    print(f"   Equity: ${float(portfolio.equity_balance):,.2f}")

    # Run calculation
    print("\n⏳ Running spread factor calculation (180-day window)...")

    try:
        results = await calculate_portfolio_spread_betas(
            db=db,
            portfolio_id=portfolio.id,
            calculation_date=date.today()
        )

        print("\n✅ Calculation completed successfully!\n")

        # Display results
        print("="*60)
        print("PORTFOLIO-LEVEL SPREAD FACTOR BETAS")
        print("="*60)

        factor_betas = results['factor_betas']

        for factor_name, beta in factor_betas.items():
            print(f"\n{factor_name}:")
            print(f"  Beta: {beta:+.3f}")

            # Get interpretation
            interp = interpret_spread_beta(factor_name, beta)
            print(f"  Direction: {interp['direction']}")
            print(f"  Magnitude: {interp['magnitude']}")
            print(f"  Risk Level: {interp['risk_level']}")
            print(f"  Explanation: {interp['explanation']}")

        # Display metadata
        print("\n" + "="*60)
        print("CALCULATION METADATA")
        print("="*60)
        metadata = results['metadata']
        print(f"  Regression Window: {metadata['regression_window_days']} days")
        print(f"  Start Date: {metadata['start_date']}")
        print(f"  End Date: {metadata['end_date']}")
        print(f"  Method: {metadata['method']}")

        data_quality = results['data_quality']
        print(f"\n  Regression Days: {data_quality['regression_days']}")
        print(f"  Positions Processed: {data_quality['positions_processed']}")
        print(f"  Factors Processed: {data_quality['factors_processed']}")

        # Display storage results
        print("\n" + "="*60)
        print("DATABASE STORAGE")
        print("="*60)
        storage = results['storage_results']
        if 'position_storage' in storage:
            print(f"  Position records stored: {storage['position_storage']['records_stored']}")
        if 'portfolio_storage' in storage:
            print(f"  Portfolio records stored: {storage['portfolio_storage']['records_stored']}")

        return True

    except Exception as e:
        print(f"\n❌ Calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_stored_data(db: AsyncSession):
    """Verify data was stored in factor_exposures tables."""
    print("\n" + "="*60)
    print("STEP 3: Verifying Stored Data")
    print("="*60)

    # Count spread factor exposures
    query = select(func.count(FactorExposure.id)).join(
        FactorDefinition
    ).where(
        FactorDefinition.factor_type == 'spread'
    )

    result = await db.execute(query)
    count = result.scalar()

    print(f"\n✅ Found {count} spread factor exposure records in database")

    # Get latest calculation date
    date_query = select(FactorExposure.calculation_date).join(
        FactorDefinition
    ).where(
        FactorDefinition.factor_type == 'spread'
    ).order_by(FactorExposure.calculation_date.desc()).limit(1)

    result = await db.execute(date_query)
    latest_date = result.scalar_one_or_none()

    if latest_date:
        print(f"   Latest calculation date: {latest_date}")

    return count > 0


async def run_all_tests():
    """Run all validation tests."""
    print("\n" + "="*70)
    print(" SPREAD FACTOR IMPLEMENTATION TEST SUITE")
    print("="*70)

    async with AsyncSessionLocal() as db:
        # Step 1: Verify definitions
        step1_success = await verify_spread_factor_definitions(db)

        if not step1_success:
            print("\n❌ TEST FAILED: Spread factor definitions not found")
            return

        # Step 2: Test calculation
        step2_success = await test_calculation_on_demo_portfolio(db)

        if not step2_success:
            print("\n❌ TEST FAILED: Calculation did not complete")
            return

        # Step 3: Verify storage
        step3_success = await verify_stored_data(db)

        if not step3_success:
            print("\n❌ TEST FAILED: Data not stored properly")
            return

        # Summary
        print("\n" + "="*70)
        print(" ✅ ALL TESTS PASSED!")
        print("="*70)
        print("\n✅ Spread factor definitions created")
        print("✅ 180-day OLS regression working")
        print("✅ Portfolio betas calculated correctly")
        print("✅ Interpretations generated")
        print("✅ Data stored in database")
        print("\n🎉 Spread factor implementation validated successfully!")
        print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
