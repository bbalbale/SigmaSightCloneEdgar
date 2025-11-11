"""
Three-Way Market Beta Comparison

Compares three different beta calculations:
1. Single-factor market beta from PositionMarketBeta table (OLS regression)
2. Multi-factor market beta from PositionFactorExposure table (controlled for other factors)
3. Company profile beta from CompanyProfile table (Yahoo Finance)
"""

import asyncio
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import PositionFactorExposure, FactorDefinition, PositionMarketBeta, CompanyProfile
from decimal import Decimal


async def main():
    async with get_async_session() as db:
        # Get hedge fund portfolio
        result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("User not found")
            return

        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalars().first()

        print("=" * 80)
        print("THREE-WAY MARKET BETA COMPARISON")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()

        # Get stock positions
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.deleted_at.is_(None))
        )
        positions = result.scalars().all()

        stock_positions = [p for p in positions if p.position_type in [PositionType.LONG, PositionType.SHORT]]
        print(f"Stock Positions: {len(stock_positions)}")
        print()

        # Get Market Beta factor
        result = await db.execute(
            select(FactorDefinition).where(FactorDefinition.name == "Market Beta")
        )
        market_beta_factor = result.scalar_one_or_none()

        if not market_beta_factor:
            print("[ERROR] Market Beta factor not found!")
            return

        print(f"Market Beta Factor: {market_beta_factor.name}")
        print(f"ETF Proxy: {market_beta_factor.etf_proxy}")
        print()

        # Collect all three beta sources
        comparison_data = []

        for pos in stock_positions:
            data = {
                'symbol': pos.symbol,
                'market_value': pos.market_value,
                'calc_beta': None,
                'factor_beta': None,
                'profile_beta': None,
                'calc_date': None,
                'factor_date': None
            }

            # 1. Get calculated beta from PositionMarketBeta
            result = await db.execute(
                select(PositionMarketBeta)
                .where(PositionMarketBeta.position_id == pos.id)
                .where(PositionMarketBeta.portfolio_id == portfolio.id)
                .order_by(PositionMarketBeta.calc_date.desc())
                .limit(1)
            )
            calc_beta_record = result.scalar_one_or_none()
            if calc_beta_record:
                data['calc_beta'] = float(calc_beta_record.beta)
                data['calc_date'] = calc_beta_record.calc_date

            # 2. Get multi-factor beta from PositionFactorExposure
            result = await db.execute(
                select(PositionFactorExposure)
                .where(PositionFactorExposure.position_id == pos.id)
                .where(PositionFactorExposure.factor_id == market_beta_factor.id)
                .order_by(PositionFactorExposure.calculation_date.desc())
                .limit(1)
            )
            factor_beta_record = result.scalar_one_or_none()
            if factor_beta_record:
                data['factor_beta'] = float(factor_beta_record.exposure_value)
                data['factor_date'] = factor_beta_record.calculation_date

            # 3. Get company profile beta
            result = await db.execute(
                select(CompanyProfile).where(CompanyProfile.symbol == pos.symbol)
            )
            profile = result.scalar_one_or_none()
            if profile and profile.beta:
                data['profile_beta'] = float(profile.beta)

            comparison_data.append(data)

        # Sort by market value
        comparison_data.sort(key=lambda x: abs(x['market_value']) if x['market_value'] else 0, reverse=True)

        # Display table
        print("=" * 100)
        print(f"{'Symbol':<8} {'Calc Beta':>10} {'Factor Beta':>12} {'Profile Beta':>13} {'Calc-Factor':>12} {'Calc-Profile':>13}")
        print("-" * 100)

        for data in comparison_data:
            calc_beta = data['calc_beta'] if data['calc_beta'] is not None else float('nan')
            factor_beta = data['factor_beta'] if data['factor_beta'] is not None else float('nan')
            profile_beta = data['profile_beta'] if data['profile_beta'] is not None else float('nan')

            calc_factor_diff = calc_beta - factor_beta if data['calc_beta'] and data['factor_beta'] else float('nan')
            calc_profile_diff = calc_beta - profile_beta if data['calc_beta'] and data['profile_beta'] else float('nan')

            print(f"{data['symbol']:<8} "
                  f"{calc_beta:>10.4f} "
                  f"{factor_beta:>12.4f} "
                  f"{profile_beta:>13.4f} "
                  f"{calc_factor_diff:>12.4f} "
                  f"{calc_profile_diff:>13.4f}")

        print()
        print("=" * 100)
        print("INTERPRETATION:")
        print("=" * 100)
        print()
        print("Calc Beta:       Single-factor OLS regression (Position ~ SPY)")
        print("                 Source: PositionMarketBeta table")
        print("                 Used by: Portfolio snapshots")
        print()
        print("Factor Beta:     Multi-factor regression (Position ~ Market + Value + Growth + ...)")
        print("                 Source: PositionFactorExposure table (Market Beta factor)")
        print("                 Used by: Factor analysis calculations")
        print("                 NOTE: Controlled for other factors, may differ from single-factor beta")
        print()
        print("Profile Beta:    Yahoo Finance beta (methodology unknown)")
        print("                 Source: CompanyProfile table")
        print("                 NOT used in calculations")
        print()
        print("KEY INSIGHT:")
        print("The factor calculations in factors.py calculate their own multi-factor betas.")
        print("They do NOT use the PositionMarketBeta table.")
        print("Both are valid but serve different purposes:")
        print("  - Single-factor beta: Pure market exposure")
        print("  - Multi-factor beta: Market exposure after controlling for style factors")
        print()


if __name__ == "__main__":
    asyncio.run(main())
