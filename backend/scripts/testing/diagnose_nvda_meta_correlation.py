#!/usr/bin/env python
"""
Diagnostic script to investigate NVDA/META correlation calculation issues

Checks 4 potential problems:
1. Data misalignment in p-value calculation
2. Bad price data (inverted, splits, corrupted values)
3. Log returns with extreme values
4. DataFrame construction issues

Results will be printed to console AND saved to:
backend/correlation_diagnostic_report.txt
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import pandas as pd
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.market_data import MarketDataCache
from app.config import settings

# Output file
REPORT_FILE = Path(__file__).parent.parent.parent / "correlation_diagnostic_report.txt"


class DiagnosticReporter:
    """Helper to write to both console and file"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.file = open(filepath, 'w', encoding='utf-8')

    def print(self, *args, **kwargs):
        """Print to both console and file"""
        message = ' '.join(str(arg) for arg in args)
        print(message, **kwargs)
        self.file.write(message + '\n')
        self.file.flush()

    def close(self):
        self.file.close()


async def diagnose_correlation_issues():
    """Run all diagnostic checks"""

    reporter = DiagnosticReporter(REPORT_FILE)

    reporter.print("=" * 80)
    reporter.print("NVDA/META Correlation Diagnostic Report")
    reporter.print(f"Generated: {datetime.now()}")
    reporter.print("=" * 80)
    reporter.print()

    # Setup database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Define date range (90 days for correlation calculation)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)

        reporter.print(f"Analysis Period: {start_date} to {end_date} (90 days)")
        reporter.print()

        # Fetch price data for NVDA and META
        reporter.print("=" * 80)
        reporter.print("STEP 1: Fetching raw price data from database")
        reporter.print("=" * 80)

        nvda_data = await fetch_price_data(db, "NVDA", start_date, end_date)
        meta_data = await fetch_price_data(db, "META", start_date, end_date)

        reporter.print(f"NVDA: {len(nvda_data)} records")
        reporter.print(f"META: {len(meta_data)} records")
        reporter.print()

        if len(nvda_data) == 0 or len(meta_data) == 0:
            reporter.print("❌ ERROR: No data found for one or both symbols!")
            reporter.close()
            return

        # Convert to DataFrames
        nvda_df = pd.DataFrame(nvda_data)
        nvda_df['date'] = pd.to_datetime(nvda_df['date'])
        nvda_df = nvda_df.set_index('date').sort_index()

        meta_df = pd.DataFrame(meta_data)
        meta_df['date'] = pd.to_datetime(meta_df['date'])
        meta_df = meta_df.set_index('date').sort_index()

        reporter.print("✅ Data loaded successfully")
        reporter.print()

        # CHECK 1: Data Quality Issues
        reporter.print("=" * 80)
        reporter.print("CHECK 1: Bad Price Data (inverted, splits, corrupted)")
        reporter.print("=" * 80)
        check_price_data_quality(nvda_df, "NVDA", reporter)
        check_price_data_quality(meta_df, "META", reporter)
        reporter.print()

        # CHECK 2: Date Overlap and Alignment
        reporter.print("=" * 80)
        reporter.print("CHECK 2: Date Overlap and Alignment")
        reporter.print("=" * 80)
        check_date_alignment(nvda_df, meta_df, reporter)
        reporter.print()

        # CHECK 3: Log Returns Calculation
        reporter.print("=" * 80)
        reporter.print("CHECK 3: Log Returns with Extreme Values")
        reporter.print("=" * 80)
        nvda_returns = calculate_log_returns(nvda_df['close'], "NVDA", reporter)
        meta_returns = calculate_log_returns(meta_df['close'], "META", reporter)
        reporter.print()

        # CHECK 4: DataFrame Construction and Correlation
        reporter.print("=" * 80)
        reporter.print("CHECK 4: DataFrame Construction and Correlation Calculation")
        reporter.print("=" * 80)
        check_correlation_calculation(nvda_returns, meta_returns, reporter)
        reporter.print()

        # Summary
        reporter.print("=" * 80)
        reporter.print("DIAGNOSTIC COMPLETE")
        reporter.print("=" * 80)
        reporter.print(f"Full report saved to: {REPORT_FILE}")
        reporter.print()

    reporter.close()
    await engine.dispose()


async def fetch_price_data(db: AsyncSession, symbol: str, start_date, end_date):
    """Fetch price data for a symbol"""
    query = select(
        MarketDataCache.date,
        MarketDataCache.close,
        MarketDataCache.open,
        MarketDataCache.high,
        MarketDataCache.low,
        MarketDataCache.volume
    ).where(
        and_(
            MarketDataCache.symbol == symbol,
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            'date': row.date,
            'close': float(row.close),
            'open': float(row.open) if row.open else None,
            'high': float(row.high) if row.high else None,
            'low': float(row.low) if row.low else None,
            'volume': row.volume
        }
        for row in rows
    ]


def check_price_data_quality(df: pd.DataFrame, symbol: str, reporter):
    """Check for price data quality issues"""
    reporter.print(f"\n{symbol} Price Data Quality:")
    reporter.print("-" * 40)

    prices = df['close']

    # Check for zeros or negatives
    zero_count = (prices == 0).sum()
    negative_count = (prices < 0).sum()

    if zero_count > 0:
        reporter.print(f"  ⚠️  WARNING: {zero_count} zero prices found!")
    else:
        reporter.print(f"  ✅ No zero prices")

    if negative_count > 0:
        reporter.print(f"  ❌ ERROR: {negative_count} negative prices found!")
    else:
        reporter.print(f"  ✅ No negative prices")

    # Check for duplicates
    duplicate_dates = df.index.duplicated().sum()
    if duplicate_dates > 0:
        reporter.print(f"  ⚠️  WARNING: {duplicate_dates} duplicate dates!")
        reporter.print(f"      Duplicate dates: {df.index[df.index.duplicated()].tolist()}")
    else:
        reporter.print(f"  ✅ No duplicate dates")

    # Check for monotonicity (should generally increase over time for growth stocks)
    if len(prices) > 1:
        first_price = prices.iloc[0]
        last_price = prices.iloc[-1]
        pct_change = ((last_price - first_price) / first_price) * 100
        reporter.print(f"  📊 Period return: {pct_change:+.2f}% (${first_price:.2f} → ${last_price:.2f})")

    # Check for extreme daily changes (potential splits or bad data)
    daily_pct_change = prices.pct_change()
    extreme_moves = daily_pct_change.abs() > 0.25  # More than 25% in a day
    extreme_count = extreme_moves.sum()

    if extreme_count > 0:
        reporter.print(f"  ⚠️  WARNING: {extreme_count} extreme daily moves (>25%):")
        for date, pct in daily_pct_change[extreme_moves].items():
            reporter.print(f"      {date.date()}: {pct*100:+.2f}%")
    else:
        reporter.print(f"  ✅ No extreme daily moves detected")

    # Price range
    reporter.print(f"  📈 Price range: ${prices.min():.2f} to ${prices.max():.2f}")
    reporter.print(f"  📊 Mean: ${prices.mean():.2f}, Std: ${prices.std():.2f}")


def check_date_alignment(nvda_df: pd.DataFrame, meta_df: pd.DataFrame, reporter):
    """Check for date alignment issues"""

    nvda_dates = set(nvda_df.index)
    meta_dates = set(meta_df.index)

    common_dates = nvda_dates & meta_dates
    nvda_only = nvda_dates - meta_dates
    meta_only = meta_dates - nvda_dates

    reporter.print(f"Date Overlap Analysis:")
    reporter.print("-" * 40)
    reporter.print(f"  NVDA trading days: {len(nvda_dates)}")
    reporter.print(f"  META trading days: {len(meta_dates)}")
    reporter.print(f"  Common trading days: {len(common_dates)}")
    reporter.print(f"  NVDA-only days: {len(nvda_only)}")
    reporter.print(f"  META-only days: {len(meta_only)}")

    overlap_pct = (len(common_dates) / max(len(nvda_dates), len(meta_dates))) * 100
    reporter.print(f"  Overlap: {overlap_pct:.1f}%")

    if len(nvda_only) > 0:
        reporter.print(f"  ⚠️  Sample NVDA-only dates: {sorted(list(nvda_only))[:5]}")

    if len(meta_only) > 0:
        reporter.print(f"  ⚠️  Sample META-only dates: {sorted(list(meta_only))[:5]}")

    if overlap_pct < 90:
        reporter.print(f"  ⚠️  WARNING: Low date overlap ({overlap_pct:.1f}%) may affect correlation")
    else:
        reporter.print(f"  ✅ Good date overlap")


def calculate_log_returns(prices: pd.Series, symbol: str, reporter):
    """Calculate log returns and check for issues"""

    reporter.print(f"\n{symbol} Log Returns Calculation:")
    reporter.print("-" * 40)

    # Calculate log returns (same as correlation service)
    with np.errstate(divide='ignore', invalid='ignore'):
        log_returns = np.log(prices / prices.shift(1))

    # Check for infinite values
    inf_count = np.isinf(log_returns).sum()
    if inf_count > 0:
        reporter.print(f"  ⚠️  WARNING: {inf_count} infinite log returns (from zero/negative prices)")
        log_returns = log_returns.replace([np.inf, -np.inf], np.nan)
    else:
        reporter.print(f"  ✅ No infinite values")

    # Drop NaN values
    log_returns_clean = log_returns.dropna()

    reporter.print(f"  📊 Returns count: {len(log_returns_clean)} (dropped {len(log_returns) - len(log_returns_clean)} NaN)")

    if len(log_returns_clean) > 0:
        reporter.print(f"  📊 Mean return: {log_returns_clean.mean():.6f}")
        reporter.print(f"  📊 Std dev: {log_returns_clean.std():.6f}")
        reporter.print(f"  📊 Min: {log_returns_clean.min():.6f}, Max: {log_returns_clean.max():.6f}")

        # Check for extreme returns
        extreme_threshold = 0.15  # 15% single-day return
        extreme_returns = log_returns_clean.abs() > extreme_threshold
        if extreme_returns.any():
            reporter.print(f"  ⚠️  WARNING: {extreme_returns.sum()} extreme returns (>{extreme_threshold*100:.0f}%):")
            for date, ret in log_returns_clean[extreme_returns].items():
                reporter.print(f"      {date.date()}: {ret*100:+.2f}%")

    return log_returns_clean


def check_correlation_calculation(nvda_returns: pd.Series, meta_returns: pd.Series, reporter):
    """Check DataFrame construction and correlation calculation"""

    reporter.print(f"Correlation Calculation:")
    reporter.print("-" * 40)

    # Method 1: Pandas DataFrame (what the service does)
    returns_dict = {
        'NVDA': nvda_returns,
        'META': meta_returns
    }
    returns_df = pd.DataFrame(returns_dict)

    reporter.print(f"  DataFrame shape: {returns_df.shape}")
    reporter.print(f"  Dates in DataFrame: {len(returns_df)}")
    reporter.print(f"  NVDA non-null: {returns_df['NVDA'].notna().sum()}")
    reporter.print(f"  META non-null: {returns_df['META'].notna().sum()}")
    reporter.print(f"  Both non-null: {returns_df.dropna().shape[0]}")

    # Calculate correlation (pandas default - pairwise deletion)
    corr_matrix = returns_df.corr(method='pearson', min_periods=30)

    reporter.print(f"\n  Correlation Matrix (min_periods=30):")
    reporter.print(f"  {corr_matrix}")

    nvda_meta_corr = corr_matrix.loc['NVDA', 'META']
    reporter.print(f"\n  📊 NVDA-META Correlation: {nvda_meta_corr:.6f}")

    # Method 2: Only overlapping dates (strict alignment)
    aligned_df = returns_df.dropna()
    if len(aligned_df) >= 30:
        corr_aligned = aligned_df['NVDA'].corr(aligned_df['META'])
        reporter.print(f"  📊 Correlation (strict alignment, n={len(aligned_df)}): {corr_aligned:.6f}")

        if abs(nvda_meta_corr - corr_aligned) > 0.05:
            reporter.print(f"  ⚠️  WARNING: Significant difference between methods!")
    else:
        reporter.print(f"  ⚠️  WARNING: Only {len(aligned_df)} overlapping dates (need 30+)")

    # Check the problematic p-value calculation (Issue #1)
    reporter.print(f"\n  Checking p-value calculation method:")
    reporter.print(f"  --------------------------------------")

    # The WRONG way (what correlation_service does on line 721-724)
    from scipy import stats
    nvda_dropped = returns_df['NVDA'].dropna()
    meta_dropped = returns_df['META'].dropna()

    reporter.print(f"  Method A (WRONG - independent dropna):")
    reporter.print(f"    NVDA after dropna: {len(nvda_dropped)} values")
    reporter.print(f"    META after dropna: {len(meta_dropped)} values")

    if len(nvda_dropped) != len(meta_dropped):
        reporter.print(f"    ❌ ERROR: Misaligned arrays! Cannot calculate valid p-value this way.")
        reporter.print(f"    This is BUG #1 in _store_correlation_matrix (line 721-724)")
    else:
        # They happen to be the same length, but might not be aligned by date
        reporter.print(f"    Arrays are same length, but may not be date-aligned")

    # The RIGHT way
    reporter.print(f"\n  Method B (CORRECT - aligned dropna):")
    aligned_for_pvalue = returns_df.dropna()
    if len(aligned_for_pvalue) >= 3:
        _, p_value = stats.pearsonr(
            aligned_for_pvalue['NVDA'],
            aligned_for_pvalue['META']
        )
        reporter.print(f"    Aligned observations: {len(aligned_for_pvalue)}")
        reporter.print(f"    Correlation: {corr_aligned:.6f}")
        reporter.print(f"    P-value: {p_value:.6f}")
        reporter.print(f"    Statistically significant: {'Yes' if p_value < 0.05 else 'No'}")

    # Final assessment
    reporter.print(f"\n  EXPECTED vs ACTUAL:")
    reporter.print(f"  -------------------")
    reporter.print(f"  Both NVDA and META are mega-cap tech stocks.")
    reporter.print(f"  Expected correlation: 0.60 to 0.85 (positive, strong)")
    reporter.print(f"  Actual correlation: {nvda_meta_corr:+.6f}")

    if nvda_meta_corr < 0:
        reporter.print(f"  ❌ PROBLEM: Negative correlation is WRONG!")
        reporter.print(f"  This indicates a data quality or calculation bug.")
    elif nvda_meta_corr < 0.30:
        reporter.print(f"  ⚠️  WARNING: Correlation is suspiciously low")
    elif 0.60 <= nvda_meta_corr <= 0.85:
        reporter.print(f"  ✅ Correlation looks reasonable")
    else:
        reporter.print(f"  ⚠️  Correlation is outside expected range")


if __name__ == "__main__":
    print("Starting NVDA/META correlation diagnostic...")
    print(f"Results will be saved to: {REPORT_FILE}")
    print()

    asyncio.run(diagnose_correlation_issues())

    print()
    print(f"✅ Diagnostic complete! Check the report at:")
    print(f"   {REPORT_FILE}")
