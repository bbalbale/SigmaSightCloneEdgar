"""
Diagnostic script to debug beta calculation issues.
Shows NVDA and SPY prices with calculated returns to verify calculation logic.
"""
import asyncio
import pandas as pd
from datetime import datetime
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_symbol_data(session, symbol: str) -> pd.DataFrame:
    """Fetch historical price data for a symbol and convert to DataFrame."""
    stmt = (
        select(MarketDataCache)
        .where(MarketDataCache.symbol == symbol)
        .order_by(MarketDataCache.date)  # ASCENDING - oldest first
    )
    result = await session.execute(stmt)
    prices = result.scalars().all()

    if not prices:
        return pd.DataFrame()

    # Convert to DataFrame
    data = []
    for p in prices:
        data.append({
            'date': p.date,
            'close': float(p.close)
        })

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    return df


async def debug_beta_calculation():
    """
    Debug beta calculation by showing actual price data and calculated returns.
    This replicates what the factor calculation code does.
    """
    async with AsyncSessionLocal() as session:
        try:
            print("\n" + "="*100)
            print("BETA CALCULATION DIAGNOSTIC - NVDA vs SPY")
            print("="*100)

            # Fetch data for both symbols
            print("\nFetching data...")
            nvda_df = await fetch_symbol_data(session, "NVDA")
            spy_df = await fetch_symbol_data(session, "SPY")

            if nvda_df.empty:
                print("[ERROR] No NVDA data found")
                return
            if spy_df.empty:
                print("[ERROR] No SPY data found")
                return

            print(f"[OK] NVDA: {len(nvda_df)} days of data")
            print(f"[OK] SPY: {len(spy_df)} days of data")

            # Combine into single DataFrame (align dates)
            combined = pd.DataFrame({
                'NVDA_Close': nvda_df['close'],
                'SPY_Close': spy_df['close']
            })

            # Drop rows where either symbol is missing (same as factor calculation does)
            combined_aligned = combined.dropna()
            print(f"[OK] Aligned data: {len(combined_aligned)} common trading days")

            # Calculate returns using pct_change (EXACTLY as factor calculation does)
            # This is the critical line - same as factors.py line 115 and 258
            returns = combined_aligned.pct_change(fill_method=None).dropna()
            returns.columns = ['NVDA_Return', 'SPY_Return']

            print(f"[OK] Calculated returns: {len(returns)} days")

            # Combine prices and returns for display
            display_df = pd.DataFrame({
                'NVDA_Close': combined_aligned['NVDA_Close'],
                'SPY_Close': combined_aligned['SPY_Close'],
                'NVDA_Return': returns['NVDA_Return'],
                'SPY_Return': returns['SPY_Return']
            })

            # Show first 20 rows
            print("\n" + "="*100)
            print("FIRST 20 DAYS (Oldest Data)")
            print("="*100)
            print(f"{'Date':<12} {'NVDA $':>10} {'NVDA Ret%':>12} {'SPY $':>10} {'SPY Ret%':>12}")
            print("-"*100)

            for idx in range(min(20, len(display_df))):
                row = display_df.iloc[idx]
                date_str = row.name.strftime('%Y-%m-%d')
                nvda_close = row['NVDA_Close']
                spy_close = row['SPY_Close']
                nvda_ret = row['NVDA_Return'] * 100 if pd.notna(row['NVDA_Return']) else None
                spy_ret = row['SPY_Return'] * 100 if pd.notna(row['SPY_Return']) else None

                if nvda_ret is not None:
                    print(f"{date_str:<12} {nvda_close:>10.2f} {nvda_ret:>11.2f}% {spy_close:>10.2f} {spy_ret:>11.2f}%")
                else:
                    print(f"{date_str:<12} {nvda_close:>10.2f} {'N/A':>12} {spy_close:>10.2f} {'N/A':>12}")

            # Show last 20 rows
            print("\n" + "="*100)
            print("LAST 20 DAYS (Most Recent Data)")
            print("="*100)
            print(f"{'Date':<12} {'NVDA $':>10} {'NVDA Ret%':>12} {'SPY $':>10} {'SPY Ret%':>12}")
            print("-"*100)

            start_idx = max(0, len(display_df) - 20)
            for idx in range(start_idx, len(display_df)):
                row = display_df.iloc[idx]
                date_str = row.name.strftime('%Y-%m-%d')
                nvda_close = row['NVDA_Close']
                spy_close = row['SPY_Close']
                nvda_ret = row['NVDA_Return'] * 100 if pd.notna(row['NVDA_Return']) else None
                spy_ret = row['SPY_Return'] * 100 if pd.notna(row['SPY_Return']) else None

                if nvda_ret is not None:
                    print(f"{date_str:<12} {nvda_close:>10.2f} {nvda_ret:>11.2f}% {spy_close:>10.2f} {spy_ret:>11.2f}%")
                else:
                    print(f"{date_str:<12} {nvda_close:>10.2f} {'N/A':>12} {spy_close:>10.2f} {'N/A':>12}")

            # Calculate correlation
            print("\n" + "="*100)
            print("STATISTICAL ANALYSIS")
            print("="*100)

            correlation = returns['NVDA_Return'].corr(returns['SPY_Return'])

            print(f"\nReturn Statistics (in %):")
            print(f"  NVDA Average Daily Return: {returns['NVDA_Return'].mean() * 100:>8.3f}%")
            print(f"  NVDA Std Deviation:        {returns['NVDA_Return'].std() * 100:>8.3f}%")
            print(f"  SPY Average Daily Return:  {returns['SPY_Return'].mean() * 100:>8.3f}%")
            print(f"  SPY Std Deviation:         {returns['SPY_Return'].std() * 100:>8.3f}%")

            print(f"\nCorrelation Analysis:")
            print(f"  NVDA vs SPY Correlation:   {correlation:>8.4f}")
            print(f"  Expected for NVDA:         ~0.70-0.80 (high beta stock)")

            # Simple beta estimate (for comparison)
            # Beta ≈ Cov(NVDA, SPY) / Var(SPY)
            covariance = returns['NVDA_Return'].cov(returns['SPY_Return'])
            spy_variance = returns['SPY_Return'].var()
            simple_beta = covariance / spy_variance if spy_variance > 0 else 0

            print(f"\nSimple Beta Estimate (NVDA vs SPY):")
            print(f"  Calculated Beta:           {simple_beta:>8.4f}")
            print(f"  Expected Beta:             ~2.12 (from market sources)")
            print(f"  Match:                     {'[GOOD]' if abs(simple_beta - 2.12) < 0.5 else '[MISMATCH]'}")

            # Data quality checks
            print(f"\nData Quality:")
            print(f"  Date range:                {display_df.index[0].strftime('%Y-%m-%d')} to {display_df.index[-1].strftime('%Y-%m-%d')}")
            print(f"  Total days:                {len(display_df)}")
            print(f"  NVDA NaN returns:          {returns['NVDA_Return'].isna().sum()}")
            print(f"  SPY NaN returns:           {returns['SPY_Return'].isna().sum()}")
            print(f"  Date sort order:           {'[ASCENDING - correct]' if display_df.index.is_monotonic_increasing else '[WRONG ORDER]'}")

            print("\n" + "="*100)
            print("DIAGNOSTIC COMPLETE")
            print("="*100 + "\n")

        except Exception as e:
            logger.error(f"Error in diagnostic: {e}")
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(debug_beta_calculation())
