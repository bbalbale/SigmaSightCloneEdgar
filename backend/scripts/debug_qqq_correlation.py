"""
Diagnostic script to investigate QQQ correlation issue with its major components.

This script compares two correlation calculation methods:
1. STRICT: Align to common dates across ALL symbols (current implementation)
2. PAIRWISE: Use all available pairwise overlapping dates (proposed fix)

Expected: QQQ should show 70-90% correlation with GOOGL/AAPL/META (major components)
Current Issue: Showing ~56% correlation due to overly strict date alignment
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
    print("QQQ CORRELATION DIAGNOSTIC")
    print("=" * 80)
    print()

    symbols = ["QQQ", "GOOGL", "AAPL", "META"]
    lookback_days = 90
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    async with get_async_session() as db:
        # Step 1: Fetch price data for all symbols
        print("Step 1: Fetching price data...")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print()

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
                print(f"✓ {symbol}: {len(price_series)} trading days")
            else:
                print(f"✗ {symbol}: No data found!")

        if len(price_data) != len(symbols):
            print(f"\n❌ ERROR: Missing data for some symbols!")
            return

        # Step 2: Create price DataFrame
        print("\n" + "=" * 80)
        print("Step 2: Data Alignment Analysis")
        print("=" * 80)
        print()

        price_df = pd.DataFrame(price_data)

        # Method 1: STRICT alignment (current implementation)
        price_df_strict = price_df.dropna()
        print(f"STRICT ALIGNMENT (dropna - current method):")
        print(f"  - Original dates: {len(price_df)}")
        print(f"  - After dropna: {len(price_df_strict)}")
        print(f"  - Lost {len(price_df) - len(price_df_strict)} dates ({100 * (len(price_df) - len(price_df_strict)) / len(price_df):.1f}%)")
        print()

        # Pairwise overlap statistics
        print("PAIRWISE OVERLAP STATISTICS:")
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                pairwise_data = price_df[[sym1, sym2]].dropna()
                print(f"  {sym1} <-> {sym2}: {len(pairwise_data)} overlapping days")
        print()

        # Step 3: Calculate correlations with STRICT method
        print("=" * 80)
        print("Step 3: Correlation Calculation - STRICT Method")
        print("=" * 80)
        print()

        # Calculate returns with strict alignment
        with np.errstate(divide='ignore', invalid='ignore'):
            returns_strict = np.log(price_df_strict / price_df_strict.shift(1))
        returns_strict = returns_strict.dropna()

        corr_strict = returns_strict.corr(method='pearson')

        print(f"Sample size (strict): {len(returns_strict)} days")
        print("\nCorrelation Matrix (STRICT):")
        print(corr_strict.to_string())
        print("\nQQQ Correlations (STRICT):")
        for symbol in ["GOOGL", "AAPL", "META"]:
            corr_value = corr_strict.loc["QQQ", symbol]
            print(f"  QQQ <-> {symbol}: {corr_value:.1%}")

        # Step 4: Calculate correlations with PAIRWISE method
        print("\n" + "=" * 80)
        print("Step 4: Correlation Calculation - PAIRWISE Method (PROPOSED FIX)")
        print("=" * 80)
        print()

        # Calculate returns WITHOUT strict alignment
        with np.errstate(divide='ignore', invalid='ignore'):
            returns_pairwise = np.log(price_df / price_df.shift(1))
        returns_pairwise = returns_pairwise.replace([np.inf, -np.inf], np.nan)

        # Use pandas corr() with min_periods for pairwise deletion
        corr_pairwise = returns_pairwise.corr(method='pearson', min_periods=30)

        print("Sample sizes (pairwise):")
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                paired_returns = returns_pairwise[[sym1, sym2]].dropna()
                print(f"  {sym1} <-> {sym2}: {len(paired_returns)} days")

        print("\nCorrelation Matrix (PAIRWISE):")
        print(corr_pairwise.to_string())
        print("\nQQQ Correlations (PAIRWISE):")
        for symbol in ["GOOGL", "AAPL", "META"]:
            corr_value = corr_pairwise.loc["QQQ", symbol]
            print(f"  QQQ <-> {symbol}: {corr_value:.1%}")

        # Step 5: Comparison and Analysis
        print("\n" + "=" * 80)
        print("Step 5: COMPARISON & DIAGNOSIS")
        print("=" * 80)
        print()

        print("Correlation Differences:")
        for symbol in ["GOOGL", "AAPL", "META"]:
            strict_corr = corr_strict.loc["QQQ", symbol]
            pairwise_corr = corr_pairwise.loc["QQQ", symbol]
            diff = pairwise_corr - strict_corr
            pct_change = (diff / strict_corr) * 100 if strict_corr != 0 else 0

            print(f"\n  QQQ <-> {symbol}:")
            print(f"    Strict:    {strict_corr:.1%}")
            print(f"    Pairwise:  {pairwise_corr:.1%}")
            print(f"    Difference: {diff:+.1%} ({pct_change:+.1f}% change)")

        # Diagnosis
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        print()

        avg_strict = corr_strict.loc["QQQ", ["GOOGL", "AAPL", "META"]].mean()
        avg_pairwise = corr_pairwise.loc["QQQ", ["GOOGL", "AAPL", "META"]].mean()

        print(f"Average QQQ correlation (strict):   {avg_strict:.1%}")
        print(f"Average QQQ correlation (pairwise): {avg_pairwise:.1%}")
        print()

        if avg_pairwise > avg_strict + 0.15:  # 15% improvement
            print("✅ HYPOTHESIS CONFIRMED!")
            print("   Strict date alignment is causing artificially LOW correlations.")
            print("   Fix: Remove line 428 `price_df_aligned = price_df.dropna()`")
            print("   This will allow pairwise deletion and use all available overlapping dates.")
        elif avg_strict < 0.65:  # Less than 65%
            print("⚠️  CORRELATIONS ARE LOW")
            print("   Even with pairwise deletion, correlations seem low.")
            print("   This could indicate:")
            print("   - Data quality issues")
            print("   - Different time periods for symbols")
            print("   - Actual low correlation in the data")
        else:
            print("✓ Correlations look reasonable.")
            print("  Pairwise method provides modest improvement.")

        # Expected vs Actual
        print("\n" + "=" * 80)
        print("EXPECTED vs ACTUAL")
        print("=" * 80)
        print()
        print("EXPECTED: QQQ should show 70-90% correlation with major components")
        print("         (GOOGL, AAPL, META are top holdings in QQQ)")
        print()
        print("ACTUAL (current - strict):")
        for symbol in ["GOOGL", "AAPL", "META"]:
            corr_value = corr_strict.loc["QQQ", symbol]
            status = "✓" if corr_value >= 0.70 else "✗"
            print(f"  {status} QQQ <-> {symbol}: {corr_value:.1%}")
        print()
        print("ACTUAL (proposed - pairwise):")
        for symbol in ["GOOGL", "AAPL", "META"]:
            corr_value = corr_pairwise.loc["QQQ", symbol]
            status = "✓" if corr_value >= 0.70 else "✗"
            print(f"  {status} QQQ <-> {symbol}: {corr_value:.1%}")


if __name__ == "__main__":
    asyncio.run(main())
