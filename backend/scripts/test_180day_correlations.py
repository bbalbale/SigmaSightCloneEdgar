"""
Test 180-day vs 90-day correlations for QQQ and components.
Simple version without emojis for Windows terminal compatibility.
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.market_data import MarketDataCache


async def get_price_data(symbols, start_date, end_date):
    """Fetch price data from database."""
    price_data = {}
    async with get_async_session() as db:
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

    return price_data


def calculate_correlations(price_df):
    """Calculate correlation matrix from prices."""
    # Calculate log returns
    with np.errstate(divide='ignore', invalid='ignore'):
        returns_df = np.log(price_df / price_df.shift(1))
    returns_df = returns_df.replace([np.inf, -np.inf], np.nan)
    returns_df = returns_df.dropna()

    if len(returns_df) < 20:
        return None, None

    # Calculate correlation matrix
    corr_matrix = returns_df.corr(method='pearson')

    return corr_matrix, returns_df


async def main():
    print("=" * 80)
    print("QQQ CORRELATION ANALYSIS: 90-DAY vs 180-DAY LOOKBACK")
    print("=" * 80)
    print()

    symbols = ["QQQ", "GOOGL", "AAPL", "META"]
    end_date = datetime.now()

    results = {}

    # Test both periods
    for period_name, days in [("90-day", 90), ("180-day", 180)]:
        print("-" * 80)
        print(f"{period_name.upper()} LOOKBACK PERIOD")
        print("-" * 80)

        start_date = end_date - timedelta(days=days)
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print()

        # Fetch data
        price_data = await get_price_data(symbols, start_date, end_date)

        if not price_data or len(price_data) < len(symbols):
            print(f"ERROR: Could not get data for all symbols")
            continue

        # Create DataFrame
        price_df = pd.DataFrame(price_data)
        print(f"Price data collected: {len(price_df)} dates")
        print(f"Date range actual: {price_df.index[0].date()} to {price_df.index[-1].date()}")
        print()

        # Calculate correlations
        corr_matrix, returns_df = calculate_correlations(price_df)

        if corr_matrix is None:
            print(f"ERROR: Insufficient data for {period_name}")
            continue

        print(f"Return data: {len(returns_df)} days")
        print()
        print("Correlation Matrix:")
        print(corr_matrix.to_string())
        print()

        print(f"QQQ Correlations:")
        for symbol in ["GOOGL", "AAPL", "META"]:
            corr_value = corr_matrix.loc["QQQ", symbol]
            print(f"  QQQ <-> {symbol}: {corr_value:.1%}")

        # Store results
        results[period_name] = {
            "corr_matrix": corr_matrix,
            "sample_size": len(returns_df),
            "qqq_correlations": {
                sym: corr_matrix.loc["QQQ", sym]
                for sym in ["GOOGL", "AAPL", "META"]
            }
        }
        print()

    # Comparison
    if len(results) == 2:
        print("=" * 80)
        print("COMPARISON: 90-DAY vs 180-DAY")
        print("=" * 80)
        print()

        period_90 = results.get("90-day")
        period_180 = results.get("180-day")

        if period_90 and period_180:
            print(f"Sample sizes:")
            print(f"  90-day:  {period_90['sample_size']} days")
            print(f"  180-day: {period_180['sample_size']} days")
            print()

            print("QQQ Correlation Changes:")
            for symbol in ["GOOGL", "AAPL", "META"]:
                corr_90 = period_90['qqq_correlations'][symbol]
                corr_180 = period_180['qqq_correlations'][symbol]
                change = corr_180 - corr_90
                pct_change = (change / corr_90 * 100) if corr_90 != 0 else 0

                print(f"\n  QQQ <-> {symbol}:")
                print(f"    90-day:  {corr_90:.1%}")
                print(f"    180-day: {corr_180:.1%}")
                print(f"    Change:  {change:+.1%} ({pct_change:+.1f}%)")

            # Calculate averages
            avg_90 = np.mean(list(period_90['qqq_correlations'].values()))
            avg_180 = np.mean(list(period_180['qqq_correlations'].values()))

            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print()
            print(f"Average QQQ correlation (90-day):  {avg_90:.1%}")
            print(f"Average QQQ correlation (180-day): {avg_180:.1%}")
            print(f"Difference: {avg_180 - avg_90:+.1%}")
            print()

            if avg_180 > avg_90 + 0.10:
                print("RESULT: SIGNIFICANT IMPROVEMENT with longer lookback period")
                print("The 90-day period shows lower correlations than long-term trend.")
                print("Recommendation: Use 180-day lookback for stable correlations.")
            elif avg_180 > avg_90 + 0.05:
                print("RESULT: MODERATE IMPROVEMENT with longer lookback")
                print("Longer period provides more stable correlations.")
            elif abs(avg_180 - avg_90) < 0.05:
                print("RESULT: SIMILAR CORRELATIONS across both periods")
                print("Current 90-day reflects longer-term relationship.")
            else:
                print("RESULT: 90-day shows HIGHER correlations than 180-day")
                print("This is unusual - may indicate recent convergence.")

            print()
            print("Expected QQQ component correlations: 70-90%")
            if avg_180 >= 0.70:
                print("PASS: 180-day correlations meet expectations")
            elif avg_180 >= 0.60:
                print("MARGINAL: 180-day correlations below expectations (60-70%)")
            else:
                print("FAIL: 180-day correlations significantly below expectations (<60%)")


if __name__ == "__main__":
    asyncio.run(main())
