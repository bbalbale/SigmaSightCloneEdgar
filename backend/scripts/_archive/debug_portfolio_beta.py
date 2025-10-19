"""
Debug Portfolio Beta Calculations

Compares portfolio market beta calculated using:
1. Calculated position betas from PositionMarketBeta table (new method)
2. Position betas from CompanyProfile table (company profile method)

Focuses on the Hedge Fund portfolio.
"""

import asyncio
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import sys
import io

from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import PositionMarketBeta, CompanyProfile


# Redirect output to file and console
class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


async def main():
    print("=" * 80)
    print("PORTFOLIO BETA COMPARISON ANALYSIS")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Get hedge fund portfolio
        result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("[ERROR] Hedge fund demo user not found")
            return

        print(f"[OK] Found user: {user.email}")
        print()

        # Get portfolios for this user
        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user.id)
            .options(selectinload(Portfolio.positions))
        )
        portfolios = result.scalars().all()

        if not portfolios:
            print("[ERROR] No portfolios found for hedge fund user")
            return

        portfolio = portfolios[0]
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print(f"Total Positions: {len(portfolio.positions)}")
        print()

        # Get all positions with their market values
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.deleted_at.is_(None))
        )
        positions = result.scalars().all()

        print(f"Active Positions: {len(positions)}")
        print()

        # Calculate total portfolio value (only stock positions for beta)
        total_value = Decimal(0)
        stock_positions = []

        for pos in positions:
            if pos.position_type in [PositionType.LONG, PositionType.SHORT]:
                # Stock position
                if pos.market_value:
                    total_value += abs(pos.market_value)  # Use absolute for weighting
                    stock_positions.append(pos)

        print(f"Stock Positions (for beta calc): {len(stock_positions)}")
        print(f"Total Portfolio Value: ${total_value:,.2f}")
        print()

        if total_value == 0:
            print("❌ Total portfolio value is zero - cannot calculate weighted beta")
            return

        # Get latest calculation date
        result = await db.execute(
            select(PositionMarketBeta.calc_date)
            .where(PositionMarketBeta.portfolio_id == portfolio.id)
            .order_by(PositionMarketBeta.calc_date.desc())
            .limit(1)
        )
        latest_calc_date = result.scalar_one_or_none()

        if latest_calc_date:
            print(f"Latest calculation date: {latest_calc_date}")
            print()

        # Method 1: Calculate using PositionMarketBeta table
        print("=" * 80)
        print("METHOD 1: CALCULATED POSITION BETAS (PositionMarketBeta)")
        print("=" * 80)
        print()

        weighted_beta_method1 = Decimal(0)
        method1_count = 0
        method1_details = []

        for pos in stock_positions:
            # Get latest calculated beta for this position
            result = await db.execute(
                select(PositionMarketBeta)
                .where(PositionMarketBeta.position_id == pos.id)
                .where(PositionMarketBeta.portfolio_id == portfolio.id)
                .order_by(PositionMarketBeta.calc_date.desc())
                .limit(1)
            )
            position_beta_record = result.scalar_one_or_none()

            if position_beta_record and pos.market_value:
                beta = position_beta_record.beta
                weight = abs(pos.market_value) / total_value
                contribution = beta * weight
                weighted_beta_method1 += contribution
                method1_count += 1

                method1_details.append({
                    'symbol': pos.symbol,
                    'beta': beta,
                    'market_value': pos.market_value,
                    'weight': weight,
                    'contribution': contribution,
                    'r_squared': position_beta_record.r_squared,
                    'observations': position_beta_record.observations,
                    'calc_date': position_beta_record.calc_date
                })

        # Sort by absolute contribution
        method1_details.sort(key=lambda x: abs(x['contribution']), reverse=True)

        print(f"Positions with calculated betas: {method1_count} / {len(stock_positions)}")
        print()
        print(f"{'Symbol':<8} {'Beta':>8} {'Weight':>8} {'Contribution':>12} {'R²':>8} {'Obs':>5} {'Calc Date'}")
        print("-" * 80)

        for detail in method1_details:
            print(f"{detail['symbol']:<8} "
                  f"{detail['beta']:>8.4f} "
                  f"{detail['weight']:>7.2%} "
                  f"{detail['contribution']:>12.6f} "
                  f"{detail['r_squared']:>8.4f} "
                  f"{detail['observations']:>5} "
                  f"{detail['calc_date']}")

        print()
        print(f"PORTFOLIO BETA (Method 1): {weighted_beta_method1:.6f}")
        print()

        # Method 2: Calculate using CompanyProfile beta
        print("=" * 80)
        print("METHOD 2: COMPANY PROFILE BETAS")
        print("=" * 80)
        print()

        weighted_beta_method2 = Decimal(0)
        method2_count = 0
        method2_details = []

        for pos in stock_positions:
            # Get company profile beta
            result = await db.execute(
                select(CompanyProfile)
                .where(CompanyProfile.symbol == pos.symbol)
            )
            company_profile = result.scalar_one_or_none()

            if company_profile and company_profile.beta and pos.market_value:
                beta = company_profile.beta
                weight = abs(pos.market_value) / total_value
                contribution = beta * weight
                weighted_beta_method2 += contribution
                method2_count += 1

                method2_details.append({
                    'symbol': pos.symbol,
                    'beta': beta,
                    'market_value': pos.market_value,
                    'weight': weight,
                    'contribution': contribution,
                    'data_source': company_profile.data_source,
                    'last_updated': company_profile.last_updated
                })

        # Sort by absolute contribution
        method2_details.sort(key=lambda x: abs(x['contribution']), reverse=True)

        print(f"Positions with company profile betas: {method2_count} / {len(stock_positions)}")
        print()
        print(f"{'Symbol':<8} {'Beta':>8} {'Weight':>8} {'Contribution':>12} {'Source':<12} {'Updated'}")
        print("-" * 80)

        for detail in method2_details:
            print(f"{detail['symbol']:<8} "
                  f"{detail['beta']:>8.4f} "
                  f"{detail['weight']:>7.2%} "
                  f"{detail['contribution']:>12.6f} "
                  f"{detail['data_source']:<12} "
                  f"{detail['last_updated']}")

        print()
        print(f"PORTFOLIO BETA (Method 2): {weighted_beta_method2:.6f}")
        print()

        # Comparison
        print("=" * 80)
        print("COMPARISON")
        print("=" * 80)
        print()

        print(f"Method 1 (Calculated Betas):      {weighted_beta_method1:>10.6f}")
        print(f"Method 2 (Company Profile Betas): {weighted_beta_method2:>10.6f}")
        print(f"Difference:                        {abs(weighted_beta_method1 - weighted_beta_method2):>10.6f}")
        print()

        if weighted_beta_method2 != 0:
            pct_diff = abs((weighted_beta_method1 - weighted_beta_method2) / weighted_beta_method2) * 100
            print(f"Percentage Difference: {pct_diff:.2f}%")

        print()

        # Check which positions are missing from each method
        method1_symbols = {d['symbol'] for d in method1_details}
        method2_symbols = {d['symbol'] for d in method2_details}

        missing_from_method1 = method2_symbols - method1_symbols
        missing_from_method2 = method1_symbols - method2_symbols

        if missing_from_method1:
            print(f"[WARNING] Positions missing calculated betas: {', '.join(sorted(missing_from_method1))}")

        if missing_from_method2:
            print(f"[WARNING] Positions missing company profile betas: {', '.join(sorted(missing_from_method2))}")

        print()

        # Side-by-side comparison for positions in both methods
        print("=" * 80)
        print("SIDE-BY-SIDE BETA COMPARISON")
        print("=" * 80)
        print()

        common_symbols = method1_symbols & method2_symbols
        if common_symbols:
            print(f"{'Symbol':<8} {'Calc Beta':>10} {'Profile Beta':>12} {'Difference':>12}")
            print("-" * 50)

            for symbol in sorted(common_symbols):
                m1_detail = next(d for d in method1_details if d['symbol'] == symbol)
                m2_detail = next(d for d in method2_details if d['symbol'] == symbol)

                beta_diff = m1_detail['beta'] - m2_detail['beta']

                print(f"{symbol:<8} "
                      f"{m1_detail['beta']:>10.4f} "
                      f"{m2_detail['beta']:>12.4f} "
                      f"{beta_diff:>12.4f}")
        else:
            print("No common positions between methods")

        print()
        print("=" * 80)


if __name__ == "__main__":
    # Set up output to both console and file
    output_file = open("portfolio_beta_comparison.txt", "w", encoding="utf-8")
    original_stdout = sys.stdout
    sys.stdout = Tee(sys.stdout, output_file)

    try:
        asyncio.run(main())
        print("\nOutput saved to: portfolio_beta_comparison.txt")
    finally:
        sys.stdout = original_stdout
        output_file.close()
