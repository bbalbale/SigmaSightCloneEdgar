"""
Check Hedge Fund Portfolio Factor Exposures

Investigates why hedge fund portfolio is being skipped in stress testing.
"""
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.market_data import FactorExposure, FactorDefinition

async def main():
    print("\n" + "="*80)
    print("HEDGE FUND PORTFOLIO FACTOR EXPOSURE INVESTIGATION")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get hedge fund portfolio
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_hedgefundstyle@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ Hedge fund portfolio not found")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"ID: {portfolio.id}")

        # Check positions
        positions_stmt = select(
            Position.investment_class,
            func.count(Position.id).label('count')
        ).where(
            Position.portfolio_id == portfolio.id,
            Position.deleted_at.is_(None)
        ).group_by(Position.investment_class)

        positions_result = await db.execute(positions_stmt)
        positions_by_class = positions_result.all()

        print(f"\n--- Positions by Investment Class ---")
        total_positions = 0
        for inv_class, count in positions_by_class:
            print(f"  {inv_class}: {count} positions")
            total_positions += count
        print(f"  TOTAL: {total_positions} positions")

        # Check ALL factor exposures for this portfolio
        all_exposures_stmt = select(
            FactorExposure,
            FactorDefinition
        ).join(
            FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
        ).where(
            FactorExposure.portfolio_id == portfolio.id
        ).order_by(FactorExposure.calculation_date.desc())

        all_exposures_result = await db.execute(all_exposures_stmt)
        all_exposures = all_exposures_result.all()

        print(f"\n--- All Factor Exposures ---")
        print(f"Total factor exposure records: {len(all_exposures)}")

        if all_exposures:
            print(f"\nFactor exposures by factor:")
            factor_counts = {}
            for exposure, factor_def in all_exposures:
                factor_name = factor_def.name
                if factor_name not in factor_counts:
                    factor_counts[factor_name] = {
                        'count': 0,
                        'latest_date': exposure.calculation_date,
                        'exposure_value': exposure.exposure_value,
                        'exposure_dollar': exposure.exposure_dollar
                    }
                factor_counts[factor_name]['count'] += 1
                if exposure.calculation_date > factor_counts[factor_name]['latest_date']:
                    factor_counts[factor_name]['latest_date'] = exposure.calculation_date
                    factor_counts[factor_name]['exposure_value'] = exposure.exposure_value
                    factor_counts[factor_name]['exposure_dollar'] = exposure.exposure_dollar

            for factor_name, data in factor_counts.items():
                print(f"\n  {factor_name}:")
                print(f"    Records: {data['count']}")
                print(f"    Latest date: {data['latest_date']}")
                print(f"    Latest exposure_value (beta): {data['exposure_value']}")
                print(f"    Latest exposure_dollar: ${data['exposure_dollar']:,.2f}" if data['exposure_dollar'] else f"    Latest exposure_dollar: None")
        else:
            print("❌ NO FACTOR EXPOSURES FOUND!")

        # Check what the stress testing query is actually finding
        from datetime import date
        calculation_date = date.today()

        print(f"\n--- Stress Testing Query (date <= {calculation_date}) ---")
        stress_test_stmt = select(FactorExposure).where(
            FactorExposure.portfolio_id == portfolio.id,
            FactorExposure.calculation_date <= calculation_date
        ).limit(1)

        stress_test_result = await db.execute(stress_test_stmt)
        stress_test_exposure = stress_test_result.scalar_one_or_none()

        if stress_test_exposure:
            print(f"✅ Stress testing query FOUND exposure")
            print(f"   Date: {stress_test_exposure.calculation_date}")
            print(f"   Factor ID: {stress_test_exposure.factor_id}")
        else:
            print(f"❌ Stress testing query found NO exposures")

        # Check if there are any exposures with future dates
        future_exposures_stmt = select(
            func.count(FactorExposure.id)
        ).where(
            FactorExposure.portfolio_id == portfolio.id,
            FactorExposure.calculation_date > calculation_date
        )

        future_result = await db.execute(future_exposures_stmt)
        future_count = future_result.scalar()

        if future_count > 0:
            print(f"\n⚠️  Found {future_count} factor exposures with FUTURE dates (> {calculation_date})")
            print(f"   This could be why stress testing is not finding them!")

            # Show the future dates
            future_dates_stmt = select(
                FactorExposure.calculation_date,
                func.count(FactorExposure.id)
            ).where(
                FactorExposure.portfolio_id == portfolio.id,
                FactorExposure.calculation_date > calculation_date
            ).group_by(FactorExposure.calculation_date).order_by(FactorExposure.calculation_date)

            future_dates_result = await db.execute(future_dates_stmt)
            future_dates = future_dates_result.all()

            print(f"\n   Future dates:")
            for exp_date, count in future_dates:
                print(f"     {exp_date}: {count} exposures")


if __name__ == "__main__":
    asyncio.run(main())
