"""
Deep dive into QQQ and component price data to identify correlation issues.

Examines:
1. Sample price values
2. Return calculations
3. Return distributions
4. Visual patterns in the data
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.market_data import MarketDataCache


async def main():
    print("=" * 80)
    print("PRICE DATA QUALITY ANALYSIS")
    print("=" * 80)
    print()

    symbols = ["QQQ", "GOOGL", "AAPL", "META"]
    lookback_days = 90
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    async with get_async_session() as db:
        # Fetch price data
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
            rows = result.all()

            if rows:
                dates = [row.date for row in rows]
                prices = [float(row.close) for row in rows]
                price_series = pd.Series(prices, index=pd.DatetimeIndex(dates))
                price_data[symbol] = price_series

        # Create price DataFrame
        price_df = pd.DataFrame(price_data)

        # Step 1: Sample prices
        print("Step 1: SAMPLE PRICE DATA")
        print("=" * 80)
        print("\nFirst 10 trading days:")
        print(price_df.head(10).to_string())
        print("\nLast 10 trading days:")
        print(price_df.tail(10).to_string())

        # Step 2: Price statistics
        print("\n" + "=" * 80)
        print("Step 2: PRICE STATISTICS")
        print("=" * 80)
        print()
        for symbol in symbols:
            prices = price_df[symbol]
            print(f"\n{symbol}:")
            print(f"  Min:    ${prices.min():.2f}")
            print(f"  Max:    ${prices.max():.2f}")
            print(f"  Mean:   ${prices.mean():.2f}")
            print(f"  Median: ${prices.median():.2f}")
            print(f"  Std:    ${prices.std():.2f}")
            print(f"  Range:  ${prices.max() - prices.min():.2f} ({(prices.max() - prices.min()) / prices.min() * 100:.1f}%)")

        # Step 3: Calculate returns
        print("\n" + "=" * 80)
        print("Step 3: RETURN CALCULATIONS")
        print("=" * 80)
        print()

        # Calculate log returns
        with np.errstate(divide='ignore', invalid='ignore'):
            returns_df = np.log(price_df / price_df.shift(1))
        returns_df = returns_df.dropna()

        print("\nFirst 10 daily returns:")
        print((returns_df.head(10) * 100).round(2).to_string())

        # Step 4: Return statistics
        print("\n" + "=" * 80)
        print("Step 4: RETURN STATISTICS")
        print("=" * 80)
        print()
        for symbol in symbols:
            returns = returns_df[symbol]
            print(f"\n{symbol}:")
            print(f"  Mean daily return:     {returns.mean() * 100:.3f}%")
            print(f"  Daily volatility:      {returns.std() * 100:.3f}%")
            print(f"  Annualized vol:        {returns.std() * np.sqrt(252) * 100:.1f}%")
            print(f"  Min daily return:      {returns.min() * 100:.2f}%")
            print(f"  Max daily return:      {returns.max() * 100:.2f}%")
            print(f"  Skewness:              {returns.skew():.3f}")
            print(f"  Kurtosis:              {returns.kurtosis():.3f}")

        # Step 5: Cross-correlation analysis
        print("\n" + "=" * 80)
        print("Step 5: CROSS-CORRELATION ANALYSIS")
        print("=" * 80)
        print()

        corr_matrix = returns_df.corr()
        print("\nFull Correlation Matrix:")
        print(corr_matrix.to_string())

        # Step 6: Detailed pairwise analysis for QQQ
        print("\n" + "=" * 80)
        print("Step 6: DETAILED QQQ PAIRWISE ANALYSIS")
        print("=" * 80)
        print()

        for symbol in ["GOOGL", "AAPL", "META"]:
            print(f"\nQQQ vs {symbol}:")
            qqq_returns = returns_df["QQQ"]
            sym_returns = returns_df[symbol]

            # Manual correlation calculation
            cov = ((qqq_returns - qqq_returns.mean()) * (sym_returns - sym_returns.mean())).mean()
            qqq_std = qqq_returns.std()
            sym_std = sym_returns.std()
            manual_corr = cov / (qqq_std * sym_std)

            print(f"  Sample size:      {len(qqq_returns)} days")
            print(f"  Correlation:      {corr_matrix.loc['QQQ', symbol]:.3f}")
            print(f"  Manual calc:      {manual_corr:.3f}")
            print(f"  QQQ std:          {qqq_std * 100:.3f}%")
            print(f"  {symbol} std:      {sym_std * 100:.3f}%")
            print(f"  Covariance:       {cov * 10000:.3f} (basis points)")

            # Check for same-direction moves
            same_direction = ((qqq_returns > 0) == (sym_returns > 0)).sum()
            pct_same = same_direction / len(qqq_returns) * 100
            print(f"  Same direction:   {same_direction}/{len(qqq_returns)} days ({pct_same:.1f}%)")

            # Large divergences
            diff = np.abs(qqq_returns - sym_returns)
            large_divergences = (diff > diff.quantile(0.90)).sum()
            print(f"  Large divergences: {large_divergences} days (>90th percentile)")

        # Step 7: Check for data anomalies
        print("\n" + "=" * 80)
        print("Step 7: DATA ANOMALY CHECK")
        print("=" * 80)
        print()

        # Check for identical values (copy errors)
        for symbol in symbols:
            prices = price_df[symbol]
            duplicates = prices.duplicated().sum()
            if duplicates > 0:
                print(f"⚠️  {symbol}: {duplicates} duplicate price values")

        # Check for unrealistic daily moves
        for symbol in symbols:
            returns = returns_df[symbol]
            extreme_moves = (returns.abs() > 0.10).sum()  # >10% daily moves
            if extreme_moves > 0:
                print(f"⚠️  {symbol}: {extreme_moves} extreme daily moves (>10%)")
                extreme_dates = returns[returns.abs() > 0.10].index
                for date in extreme_dates:
                    print(f"     {date.date()}: {returns.loc[date] * 100:.2f}%")

        # Step 8: Summary and recommendation
        print("\n" + "=" * 80)
        print("SUMMARY & DIAGNOSIS")
        print("=" * 80)
        print()

        avg_corr = corr_matrix.loc["QQQ", ["GOOGL", "AAPL", "META"]].mean()
        print(f"Average QQQ correlation with components: {avg_corr:.1%}")
        print()

        if avg_corr < 0.60:
            print("❌ ISSUE IDENTIFIED: Correlations are unusually low")
            print()
            print("Possible causes:")
            print("1. Data quality issues (check for data source problems)")
            print("2. Wrong time period (check if using seeded/test data)")
            print("3. Data calculation error (check return calculation)")
            print("4. Actual market conditions (verify with external source)")
            print()
            print("RECOMMENDATION:")
            print("- Verify market data source is working correctly")
            print("- Check if demo/seed data is being used instead of real data")
            print("- Compare with publicly available correlation data")
            print("- Look at date range - is this recent real market data?")
        elif avg_corr < 0.70:
            print("⚠️  MARGINAL: Correlations are lower than typical")
            print()
            print("This could be:")
            print("- A genuine low-correlation period in the market")
            print("- Recent volatility affecting correlations")
            print("- Data quality issues (less severe)")
        else:
            print("✓ NORMAL: Correlations are in expected range (70%+)")


if __name__ == "__main__":
    asyncio.run(main())
