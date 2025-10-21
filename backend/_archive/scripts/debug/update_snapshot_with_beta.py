"""
Update Oct 14 snapshot with manually calculated beta from Oct 17 data
"""

import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select, and_, update
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionMarketBeta
from app.models.positions import Position


async def main():
    async with get_async_session() as db:
        # Get hedge fund portfolio
        result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalars().first()

        print("=" * 80)
        print("UPDATING OCT 14 SNAPSHOT WITH BETA CALCULATION")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Equity Balance: ${portfolio.equity_balance:,.2f}")
        print()

        # Get Oct 17 beta data (latest available)
        beta_date = date(2025, 10, 17)
        result = await db.execute(
            select(PositionMarketBeta)
            .where(PositionMarketBeta.portfolio_id == portfolio.id)
            .where(PositionMarketBeta.calc_date == beta_date)
        )
        beta_records = result.scalars().all()

        print(f"Found {len(beta_records)} beta records for {beta_date}")
        print()

        # Calculate equity-weighted beta
        total_weighted_beta = Decimal('0')
        total_weighted_r_squared = Decimal('0')
        min_observations = None

        print(f"{'Symbol':<8} {'Beta':>8} {'R²':>8} {'Obs':>5} {'MV':>12} {'Weight':>8}")
        print("-" * 60)

        for beta_record in beta_records:
            # Get position
            result = await db.execute(
                select(Position).where(Position.id == beta_record.position_id)
            )
            position = result.scalar_one_or_none()

            if position and position.market_value:
                weight = position.market_value / portfolio.equity_balance
                total_weighted_beta += beta_record.beta * weight
                total_weighted_r_squared += (beta_record.r_squared or Decimal('0')) * weight

                if min_observations is None or beta_record.observations < min_observations:
                    min_observations = beta_record.observations

                print(f"{position.symbol:<8} {float(beta_record.beta):>8.4f} "
                      f"{float(beta_record.r_squared):>8.4f} {beta_record.observations:>5} "
                      f"${float(position.market_value):>11,.2f} {float(weight):>7.2%}")

        print()
        print(f"Portfolio Beta: {float(total_weighted_beta):.6f}")
        print(f"Portfolio R²: {float(total_weighted_r_squared):.4f}")
        print(f"Min Observations: {min_observations}")
        print()

        # Update Oct 14 snapshot
        snapshot_date = date(2025, 10, 14)
        stmt = (
            update(PortfolioSnapshot)
            .where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date == snapshot_date
                )
            )
            .values(
                market_beta_weighted=total_weighted_beta,
                market_beta_r_squared=total_weighted_r_squared,
                market_beta_observations=min_observations
            )
        )

        result = await db.execute(stmt)
        await db.commit()

        print(f"✅ Updated snapshot for {snapshot_date} with beta data")
        print(f"   Rows affected: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(main())
