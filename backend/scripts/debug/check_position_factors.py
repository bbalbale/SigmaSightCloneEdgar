"""
Debug script to check position-level vs portfolio-level factor exposures
for the Hedge Fund Style portfolio.

Run on Railway:
    railway run python scripts/debug/check_position_factors.py

Or locally with DATABASE_URL set:
    uv run python scripts/debug/check_position_factors.py
"""
import asyncio
import os
from datetime import date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Get DATABASE_URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Convert postgres:// to postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def check_factors():
    # Import models after engine is set up
    from app.models.users import User, Portfolio
    from app.models.positions import Position
    from app.models.market_data import PositionFactorExposure, FactorDefinition, FactorExposure

    async with AsyncSessionLocal() as db:
        # 1. Find the Hedge Fund Style portfolio
        print("=" * 80)
        print("CHECKING FACTOR DATA FOR HEDGE FUND STYLE PORTFOLIO")
        print("=" * 80)

        user_result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = user_result.scalar_one_or_none()

        if not user:
            print("ERROR: Hedge Fund Style user not found")
            return

        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print("ERROR: Portfolio not found")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")

        # 2. Get all positions
        positions_result = await db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.exit_date.is_(None),
                    Position.deleted_at.is_(None)
                )
            )
        )
        positions = positions_result.scalars().all()
        print(f"Active positions: {len(positions)}")

        # 3. Get all factor definitions
        print("\n" + "-" * 80)
        print("FACTOR DEFINITIONS IN DATABASE")
        print("-" * 80)

        factor_result = await db.execute(
            select(FactorDefinition).where(FactorDefinition.is_active == True)
            .order_by(FactorDefinition.display_order)
        )
        factors = factor_result.scalars().all()

        print(f"{'Name':<25} {'Type':<10} {'Method':<20} {'ETF':<6}")
        print("-" * 65)
        for f in factors:
            print(f"{f.name:<25} {f.factor_type:<10} {f.calculation_method:<20} {f.etf_proxy or 'N/A':<6}")

        factor_ids = {f.id: f.name for f in factors}
        style_factor_ids = {f.id for f in factors if f.factor_type == 'style'}

        # 4. Check PORTFOLIO-LEVEL factor exposures (FactorExposure table)
        print("\n" + "-" * 80)
        print("PORTFOLIO-LEVEL FACTOR EXPOSURES (FactorExposure table)")
        print("-" * 80)

        portfolio_exp_result = await db.execute(
            select(FactorExposure)
            .where(FactorExposure.portfolio_id == portfolio.id)
            .order_by(FactorExposure.calculation_date.desc())
            .limit(20)
        )
        portfolio_exposures = portfolio_exp_result.scalars().all()

        if portfolio_exposures:
            print(f"Found {len(portfolio_exposures)} portfolio-level factor exposure records")
            print(f"\n{'Date':<12} {'Factor':<25} {'Beta':<10} {'Dollar Exp':<15}")
            print("-" * 65)
            for exp in portfolio_exposures[:10]:
                factor_name = factor_ids.get(exp.factor_id, "Unknown")
                print(f"{str(exp.calculation_date):<12} {factor_name:<25} {float(exp.exposure_value):>9.4f} ${float(exp.exposure_dollar or 0):>12,.0f}")
        else:
            print("NO portfolio-level factor exposures found!")

        # 5. Check POSITION-LEVEL factor exposures (PositionFactorExposure table)
        print("\n" + "-" * 80)
        print("POSITION-LEVEL FACTOR EXPOSURES (PositionFactorExposure table)")
        print("-" * 80)

        position_ids = [p.id for p in positions]

        # Count total records
        count_result = await db.execute(
            select(func.count(PositionFactorExposure.id))
            .where(PositionFactorExposure.position_id.in_(position_ids))
        )
        total_count = count_result.scalar()
        print(f"Total position-level factor exposure records: {total_count}")

        # Get recent records
        position_exp_result = await db.execute(
            select(PositionFactorExposure)
            .where(PositionFactorExposure.position_id.in_(position_ids))
            .order_by(PositionFactorExposure.calculation_date.desc())
            .limit(50)
        )
        position_exposures = position_exp_result.scalars().all()

        if position_exposures:
            # Group by date
            dates = set(exp.calculation_date for exp in position_exposures)
            print(f"Dates with data: {sorted(dates, reverse=True)[:5]}")

            # Get the most recent date
            latest_date = max(dates)
            print(f"\nMost recent calculation date: {latest_date}")

            # Count by factor for latest date
            latest_exp_result = await db.execute(
                select(
                    PositionFactorExposure.factor_id,
                    func.count(PositionFactorExposure.id).label('count')
                )
                .where(
                    and_(
                        PositionFactorExposure.position_id.in_(position_ids),
                        PositionFactorExposure.calculation_date == latest_date
                    )
                )
                .group_by(PositionFactorExposure.factor_id)
            )
            factor_counts = latest_exp_result.all()

            print(f"\nRecords per factor on {latest_date}:")
            print(f"{'Factor':<25} {'Count':<10} {'Type':<10}")
            print("-" * 50)
            for factor_id, count in factor_counts:
                factor_name = factor_ids.get(factor_id, f"Unknown ({factor_id})")
                factor_type = next((f.factor_type for f in factors if f.id == factor_id), "?")
                print(f"{factor_name:<25} {count:<10} {factor_type:<10}")

            # Show sample position exposures
            print(f"\nSample position exposures (first 5 positions on {latest_date}):")
            print("-" * 80)

            sample_positions = positions[:5]
            for pos in sample_positions:
                pos_exp_result = await db.execute(
                    select(PositionFactorExposure)
                    .where(
                        and_(
                            PositionFactorExposure.position_id == pos.id,
                            PositionFactorExposure.calculation_date == latest_date
                        )
                    )
                )
                pos_exposures = pos_exp_result.scalars().all()

                print(f"\n{pos.symbol} ({pos.position_type}):")
                if pos_exposures:
                    for exp in pos_exposures:
                        factor_name = factor_ids.get(exp.factor_id, "Unknown")
                        print(f"  {factor_name:<20}: {float(exp.exposure_value):>8.4f}")
                else:
                    print("  NO factor exposures!")
        else:
            print("NO position-level factor exposures found!")

        # 6. Check which positions have NO factor exposures at all
        print("\n" + "-" * 80)
        print("POSITIONS WITHOUT ANY FACTOR EXPOSURES")
        print("-" * 80)

        positions_with_exp = set()
        if position_exposures:
            positions_with_exp = set(exp.position_id for exp in position_exposures)

        positions_without = [p for p in positions if p.id not in positions_with_exp]
        print(f"Positions with factor exposures: {len(positions_with_exp)}")
        print(f"Positions WITHOUT factor exposures: {len(positions_without)}")

        if positions_without:
            print("\nPositions missing factor exposures:")
            for p in positions_without[:10]:
                print(f"  {p.symbol} ({p.investment_class}, {p.position_type})")

        # 7. Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Portfolio-level factor records: {len(portfolio_exposures)}")
        print(f"Position-level factor records: {total_count}")
        print(f"Positions with exposures: {len(positions_with_exp)} / {len(positions)}")

        if total_count == 0:
            print("\n⚠️  NO POSITION-LEVEL FACTORS STORED!")
            print("   This is the bug - Ridge regression is not storing position factors.")
        elif len(positions_with_exp) < len(positions):
            print(f"\n⚠️  PARTIAL DATA - {len(positions) - len(positions_with_exp)} positions missing factors")
        else:
            print("\n✅ All positions have factor exposures")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_factors())
