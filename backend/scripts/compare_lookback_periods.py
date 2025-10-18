"""
Compare correlation calculations across different lookback periods.
Uses yfinance as fallback if database data is insufficient.
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.market_data import MarketDataCache

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️  yfinance not installed. Will only use database data.")
    print("   Install with: uv pip install yfinance")


async def get_price_data_from_db(symbols, start_date, end_date):
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


def get_price_data_from_yfinance(symbols, start_date, end_date):
    """Fetch price data from yfinance as fallback."""
    if not HAS_YFINANCE:
        return {}

    print("\n📥 Fetching data from Yahoo Finance...")
    price_data = {}

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if not hist.empty:
                # Use Close prices, convert index to DatetimeIndex
                price_series = hist['Close'].copy()
                price_series.index = pd.DatetimeIndex(price_series.index.date)
                price_data[symbol] = price_series
                print(f"  ✓ {symbol}: {len(price_series)} days")
            else:
                print(f"  ✗ {symbol}: No data")
        except Exception as e:
            print(f"  ✗ {symbol}: Error - {e}")

    return price_data


def calculate_correlations(price_df, period_name):
    """Calculate correlation matrix from prices."""
    # Calculate log returns
    with np.errstate(divide='ignore', invalid='ignore'):
        returns_df = np.log(price_df / price_df.shift(1))
    returns_df = returns_df.replace([np.inf, -np.inf], np.nan)
    returns_df = returns_df.dropna()

    if len(returns_df) < 20:
        print(f"⚠️  Insufficient data for {period_name}: {len(returns_df)} days")
        return None, None

    # Calculate correlation matrix
    corr_matrix = returns_df.corr(method='pearson')

    return corr_matrix, returns_df


async def main():
    print("=" * 80)
    print("CORRELATION ANALYSIS: 90-DAY vs 180-DAY LOOKBACK")
    print("=" * 80)
    print()

    symbols = ["QQQ", "GOOGL", "AAPL", "META"]
    end_date = datetime.now()

    # Period definitions
    periods = [
        ("90-day", 90),
        ("180-day", 180),
    ]

    results = {}

    for period_name, days in periods:
        print("=" * 80)
        print(f"{period_name.upper()} LOOKBACK PERIOD")
        print("=" * 80)
        print()

        start_date = end_date - timedelta(days=days)
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print()

        # Try database first
        print("📊 Checking database...")
        price_data = await get_price_data_from_db(symbols, start_date, end_date)

        if price_data:
            print(f"✓ Found data in database:")
            for symbol, prices in price_data.items():
                print(f"  {symbol}: {len(prices)} days")

        # Check if we need yfinance
        need_yfinance = False
        if not price_data or len(price_data) < len(symbols):
            need_yfinance = True
            print(f"⚠️  Incomplete data in database, using yfinance...")
        else:
            # Check if we have enough data for the period
            min_days = min(len(prices) for prices in price_data.values())
            if min_days < days * 0.7:  # Need at least 70% of requested days
                need_yfinance = True
                print(f"⚠️  Insufficient data ({min_days} days < {days * 0.7:.0f} required), using yfinance...")

        if need_yfinance:
            price_data = get_price_data_from_yfinance(symbols, start_date, end_date)

        if not price_data or len(price_data) < len(symbols):
            print(f"❌ Could not get data for all symbols for {period_name}")
            continue

        # Create DataFrame
        price_df = pd.DataFrame(price_data)
        print(f"\n📈 Price data collected: {len(price_df)} dates")
        print(f"   Date range: {price_df.index[0].date()} to {price_df.index[-1].date()}")

        # Calculate correlations
        corr_matrix, returns_df = calculate_correlations(price_df, period_name)

        if corr_matrix is None:
            continue

        print(f"\n📊 Calculated returns: {len(returns_df)} days")
        print(f"\nCorrelation Matrix ({period_name}):")
        print(corr_matrix.to_string())

        print(f"\nQQQ Correlations ({period_name}):")
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
                print("✅ SIGNIFICANT IMPROVEMENT with longer lookback!")
                print("   Recent 90 days show lower correlations than longer-term trend.")
                print("   Recommendation: Use 180-day (or longer) lookback for stable correlations.")
            elif avg_180 > avg_90 + 0.05:
                print("✓ MODERATE IMPROVEMENT with longer lookback")
                print("  Longer period provides more stable correlations.")
            elif abs(avg_180 - avg_90) < 0.05:
                print("≈ SIMILAR CORRELATIONS across both periods")
                print("  Current 90-day period reflects longer-term relationship.")
            else:
                print("⚠️  90-day shows HIGHER correlations than 180-day")
                print("   This is unusual - may indicate recent convergence.")

            print()
            print("Expected QQQ component correlations: 70-90%")
            if avg_180 >= 0.70:
                print("✅ 180-day correlations meet expectations")
            elif avg_180 >= 0.60:
                print("⚠️  180-day correlations below expectations (60-70%)")
            else:
                print("❌ 180-day correlations significantly below expectations (<60%)")


if __name__ == "__main__":
    asyncio.run(main())
