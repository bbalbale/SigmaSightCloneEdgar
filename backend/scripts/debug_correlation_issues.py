"""
Debug Correlation Issues

Investigates:
1. Why correlation matrix is missing for high net worth portfolio
2. Why NVDA-META correlation is -0.95 (incorrect)
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.correlations import CorrelationCalculation, PairwiseCorrelation
from app.models.positions import Position
from app.models.market_data import MarketDataCache
import pandas as pd
import numpy as np

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def check_portfolio_correlations():
    """Check correlation calculations for all portfolios"""

    print("\n" + "="*80)
    print("PORTFOLIO CORRELATION STATUS")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get all portfolios
        stmt = select(Portfolio).join(User).order_by(User.email)
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            print(f"\n📊 Portfolio: {portfolio.name}")
            print(f"   ID: {portfolio.id}")

            # Check positions
            pos_stmt = select(Position).where(Position.portfolio_id == portfolio.id)
            pos_result = await db.execute(pos_stmt)
            positions = pos_result.scalars().all()

            public_positions = [p for p in positions if p.position_type in ['LONG', 'SHORT']]
            private_positions = [p for p in positions if p.position_type == 'PRIVATE']

            print(f"   Total positions: {len(positions)}")
            print(f"   Public positions: {len(public_positions)}")
            print(f"   Private positions: {len(private_positions)}")

            # Check correlation calculations
            corr_stmt = select(CorrelationCalculation).where(
                CorrelationCalculation.portfolio_id == portfolio.id
            ).order_by(CorrelationCalculation.calculation_date.desc()).limit(1)
            corr_result = await db.execute(corr_stmt)
            latest_corr = corr_result.scalar_one_or_none()

            if latest_corr:
                print(f"   ✅ Correlation calculation found:")
                print(f"      Date: {latest_corr.calculation_date}")
                print(f"      Overall correlation: {float(latest_corr.overall_correlation):.4f}")
                print(f"      Positions included: {latest_corr.positions_included}")
                print(f"      Positions excluded: {latest_corr.positions_excluded}")
                print(f"      Data quality: {latest_corr.data_quality}")
            else:
                print(f"   ❌ NO correlation calculation found")
                print(f"      This could be because:")
                print(f"      - All positions are PRIVATE (no market data)")
                print(f"      - Insufficient data for correlation")
                print(f"      - Batch calculation hasn't run yet")


async def check_nvda_meta_correlation():
    """Deep dive into NVDA-META correlation calculation"""

    print("\n" + "="*80)
    print("NVDA-META CORRELATION DEEP DIVE")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get latest correlation calculations that include both NVDA and META
        stmt = select(PairwiseCorrelation).where(
            and_(
                PairwiseCorrelation.symbol_1 == 'NVDA',
                PairwiseCorrelation.symbol_2 == 'META'
            )
        ).order_by(PairwiseCorrelation.id.desc()).limit(5)

        result = await db.execute(stmt)
        correlations = result.scalars().all()

        if correlations:
            print(f"\n📊 Found {len(correlations)} NVDA-META correlation calculations:")
            print(f"\n{'Calculation ID':<40} {'Correlation':>12} {'Data Points':>12} {'Significance':>12}")
            print("-" * 80)

            for corr in correlations:
                sig = float(corr.statistical_significance) if corr.statistical_significance else None
                sig_str = f"{sig:.4f}" if sig is not None else "N/A"
                print(
                    f"{str(corr.correlation_calculation_id):<40} "
                    f"{float(corr.correlation_value):>12.4f} "
                    f"{corr.data_points:>12} "
                    f"{sig_str:>12}"
                )

            # Check the reverse (META-NVDA) as well
            stmt_reverse = select(PairwiseCorrelation).where(
                and_(
                    PairwiseCorrelation.symbol_1 == 'META',
                    PairwiseCorrelation.symbol_2 == 'NVDA'
                )
            ).order_by(PairwiseCorrelation.id.desc()).limit(5)

            result_reverse = await db.execute(stmt_reverse)
            correlations_reverse = result_reverse.scalars().all()

            if correlations_reverse:
                print(f"\n📊 Found {len(correlations_reverse)} META-NVDA correlation calculations (reverse):")
                print(f"\n{'Calculation ID':<40} {'Correlation':>12} {'Data Points':>12} {'Significance':>12}")
                print("-" * 80)

                for corr in correlations_reverse:
                    sig = float(corr.statistical_significance) if corr.statistical_significance else None
                    sig_str = f"{sig:.4f}" if sig is not None else "N/A"
                    print(
                        f"{str(corr.correlation_calculation_id):<40} "
                        f"{float(corr.correlation_value):>12.4f} "
                        f"{corr.data_points:>12} "
                        f"{sig_str:>12}"
                    )
        else:
            print("\n❌ No NVDA-META correlations found in database")

        # Now let's manually calculate the correlation from raw price data
        print("\n" + "="*80)
        print("MANUAL CORRELATION CALCULATION (VERIFICATION)")
        print("="*80)

        # Get price data for both symbols
        end_date = datetime.now()
        from datetime import timedelta
        start_date = end_date - timedelta(days=90)

        symbols = ['NVDA', 'META']
        price_data = {}

        for symbol in symbols:
            query = select(
                MarketDataCache.date,
                MarketDataCache.close
            ).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)

            result = await db.execute(query)
            price_rows = result.all()

            if price_rows:
                dates = [row.date for row in price_rows]
                prices = [float(row.close) for row in price_rows]
                price_series = pd.Series(prices, index=pd.DatetimeIndex(dates))

                # Check for duplicates
                duplicates = price_series.index.duplicated().sum()
                if duplicates > 0:
                    print(f"\n⚠️  {symbol}: {duplicates} duplicate dates found - removing")
                    price_series = price_series[~price_series.index.duplicated(keep='last')]

                # Check for non-positive prices
                invalid = (price_series <= 0).sum()
                if invalid > 0:
                    print(f"\n⚠️  {symbol}: {invalid} non-positive prices found - removing")
                    price_series = price_series[price_series > 0]

                price_data[symbol] = price_series
                print(f"\n✅ {symbol}: {len(price_series)} data points")
                print(f"   Date range: {price_series.index.min()} to {price_series.index.max()}")
                print(f"   Price range: ${price_series.min():.2f} to ${price_series.max():.2f}")

        if len(price_data) == 2:
            # Create DataFrame and align
            price_df = pd.DataFrame(price_data)
            print(f"\n📊 Combined DataFrame: {len(price_df)} dates")

            # Drop dates where ANY position is missing
            price_df_aligned = price_df.dropna()
            print(f"   After alignment: {len(price_df_aligned)} dates")

            if len(price_df_aligned) >= 2:
                # Calculate log returns
                with np.errstate(divide='ignore', invalid='ignore'):
                    returns_df = np.log(price_df_aligned / price_df_aligned.shift(1))

                # Handle infinite values
                inf_mask = np.isinf(returns_df)
                if inf_mask.any().any():
                    print(f"\n⚠️  Infinite values found:")
                    for symbol in returns_df.columns:
                        inf_count = inf_mask[symbol].sum()
                        if inf_count > 0:
                            print(f"   {symbol}: {inf_count} infinite values")
                    returns_df = returns_df.replace([np.inf, -np.inf], np.nan)

                # Drop NaN values
                returns_df = returns_df.dropna()
                print(f"   Returns calculated: {len(returns_df)} days")

                if len(returns_df) >= 3:
                    # Calculate correlation
                    correlation_matrix = returns_df.corr()
                    nvda_meta_corr = correlation_matrix.loc['NVDA', 'META']

                    print(f"\n🎯 MANUAL CALCULATION RESULT:")
                    print(f"   NVDA-META correlation: {nvda_meta_corr:.6f}")
                    print(f"   Based on {len(returns_df)} overlapping return observations")

                    # Show the correlation matrix
                    print(f"\n   Full correlation matrix:")
                    print(correlation_matrix)

                    # Show sample returns
                    print(f"\n   Sample returns (first 10 days):")
                    print(returns_df.head(10))

                    print(f"\n   Sample returns (last 10 days):")
                    print(returns_df.tail(10))

                    # Check for anomalies
                    print(f"\n   Return statistics:")
                    print(returns_df.describe())
                else:
                    print(f"\n❌ Insufficient return data: {len(returns_df)} days (need 3+)")
            else:
                print(f"\n❌ Insufficient aligned price data: {len(price_df_aligned)} days (need 2+)")


async def main():
    """Run all diagnostic checks"""
    await check_portfolio_correlations()
    await check_nvda_meta_correlation()

    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
