"""
Verify Portfolio Beta Weighting Method

Checks whether portfolio beta uses:
1. Absolute market values (always positive)
2. Signed exposures (negative for shorts)
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import PositionMarketBeta


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
        print("PORTFOLIO BETA WEIGHTING VERIFICATION")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Equity Balance: ${portfolio.equity_balance:,.2f}")
        print()

        # Get latest beta calculation date
        result = await db.execute(
            select(PositionMarketBeta.calc_date)
            .where(PositionMarketBeta.portfolio_id == portfolio.id)
            .order_by(PositionMarketBeta.calc_date.desc())
            .limit(1)
        )
        calc_date = result.scalar_one_or_none()

        if not calc_date:
            print("No beta calculations found")
            return

        print(f"Latest Beta Calculation: {calc_date}")
        print()

        # Get all beta records for this date
        result = await db.execute(
            select(PositionMarketBeta)
            .where(PositionMarketBeta.portfolio_id == portfolio.id)
            .where(PositionMarketBeta.calc_date == calc_date)
        )
        beta_records = result.scalars().all()

        # Calculate portfolio beta using ABSOLUTE market values (snapshots.py method)
        total_weighted_beta_abs = Decimal('0')

        # Calculate portfolio beta using SIGNED exposures (what we might expect for shorts)
        total_weighted_beta_signed = Decimal('0')

        print(f"{'Symbol':<8} {'Type':<6} {'Beta':>8} {'Market Val':>12} {'Weight (Abs)':>12} {'Weight (Signed)':>14}")
        print("-" * 80)

        for beta_record in beta_records:
            # Get position
            result = await db.execute(
                select(Position).where(Position.id == beta_record.position_id)
            )
            position = result.scalar_one_or_none()

            if not position or not position.market_value:
                continue

            # Absolute weighting (what snapshots.py uses)
            weight_abs = position.market_value / portfolio.equity_balance
            contribution_abs = beta_record.beta * weight_abs
            total_weighted_beta_abs += contribution_abs

            # Signed weighting (negative for shorts)
            market_value_signed = position.market_value
            if position.position_type == PositionType.SHORT:
                market_value_signed = -position.market_value

            weight_signed = market_value_signed / portfolio.equity_balance
            contribution_signed = beta_record.beta * weight_signed
            total_weighted_beta_signed += contribution_signed

            pos_type = "LONG" if position.position_type == PositionType.LONG else "SHORT"

            print(f"{position.symbol:<8} {pos_type:<6} "
                  f"{beta_record.beta:>8.4f} "
                  f"${position.market_value:>11,.2f} "
                  f"{weight_abs:>11.2%} "
                  f"{weight_signed:>13.2%}")

        print()
        print("=" * 80)
        print("PORTFOLIO BETA RESULTS")
        print("=" * 80)
        print()
        print(f"Using ABSOLUTE market values:  {total_weighted_beta_abs:>10.6f}")
        print(f"Using SIGNED exposures:        {total_weighted_beta_signed:>10.6f}")
        print(f"Difference:                    {abs(total_weighted_beta_abs - total_weighted_beta_signed):>10.6f}")
        print()
        print("INTERPRETATION:")
        print()
        print("snapshots.py uses ABSOLUTE market values (always positive)")
        print("This means:")
        print("  - Long positions: positive weight, beta contribution = beta * weight")
        print("  - Short positions: positive weight, beta contribution = beta * weight")
        print()
        print("For a SHORT position with positive beta:")
        print("  - Absolute method: Adds to portfolio beta (incorrect for hedging)")
        print("  - Signed method: Subtracts from portfolio beta (correct for hedging)")
        print()

        if total_weighted_beta_abs != total_weighted_beta_signed:
            print(f"[IMPORTANT] Portfolio has short positions!")
            print(f"The current calculation may not properly account for short hedges.")
        else:
            print("[OK] No short positions or no difference in weighting methods")


if __name__ == "__main__":
    asyncio.run(main())
