"""
Backfill market data for S&P 500, Nasdaq 100, and Russell 2000 tickers.

This script:
1. Collects unique tickers from all three indices (handles overlap)
2. Checks existing data coverage in Railway Core database
3. Uses yfinance batch download for missing data
4. Upserts into market_data_cache table

Usage (on Railway):
    railway run python scripts/backfill_index_market_data.py [--dry-run] [--batch-size 50]

Or locally with DATABASE_URL set:
    DATABASE_URL=... python scripts/backfill_index_market_data.py
"""

import asyncio
import argparse
import logging
import os
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Set, Dict, List, Optional
from uuid import uuid4

import requests
import pandas as pd
import yfinance as yf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Headers to avoid Wikipedia 403 errors
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Use DATABASE_URL from environment (Railway sets this automatically)
# Fallback to hardcoded for local testing
RAILWAY_CORE_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
)

# Ensure async driver
if RAILWAY_CORE_DB_URL and "postgresql://" in RAILWAY_CORE_DB_URL and "+asyncpg" not in RAILWAY_CORE_DB_URL:
    RAILWAY_CORE_DB_URL = RAILWAY_CORE_DB_URL.replace("postgresql://", "postgresql+asyncpg://")

# Date range for backfill
START_DATE = "2024-01-01"
END_DATE = date.today().strftime("%Y-%m-%d")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_wikipedia_table(url: str) -> List[pd.DataFrame]:
    """Fetch tables from Wikipedia with proper headers to avoid 403."""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return pd.read_html(io.StringIO(response.text))


def get_sp500_tickers() -> Set[str]:
    """Get S&P 500 tickers from Wikipedia."""
    logger.info("Fetching S&P 500 tickers from Wikipedia...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = fetch_wikipedia_table(url)
        df = tables[0]
        tickers = set(df['Symbol'].str.replace('.', '-', regex=False).tolist())
        logger.info(f"  Found {len(tickers)} S&P 500 tickers")
        return tickers
    except Exception as e:
        logger.error(f"  Failed to fetch S&P 500 tickers: {e}")
        return set()


def get_nasdaq100_tickers() -> Set[str]:
    """Get Nasdaq 100 tickers from Wikipedia."""
    logger.info("Fetching Nasdaq 100 tickers from Wikipedia...")
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = fetch_wikipedia_table(url)
        # Find the table with ticker symbols
        for table in tables:
            if 'Ticker' in table.columns:
                tickers = set(table['Ticker'].str.replace('.', '-', regex=False).tolist())
                logger.info(f"  Found {len(tickers)} Nasdaq 100 tickers")
                return tickers
            elif 'Symbol' in table.columns:
                tickers = set(table['Symbol'].str.replace('.', '-', regex=False).tolist())
                logger.info(f"  Found {len(tickers)} Nasdaq 100 tickers")
                return tickers
        logger.warning("  Could not find ticker column in Nasdaq 100 tables")
        return set()
    except Exception as e:
        logger.error(f"  Failed to fetch Nasdaq 100 tickers: {e}")
        return set()


def get_russell2000_tickers() -> Set[str]:
    """Get Russell 2000 tickers via S&P 600 as proxy (small caps)."""
    logger.info("Fetching Russell 2000 tickers (S&P 600 proxy)...")
    try:
        # Russell 2000 doesn't have a full public list
        # Use S&P SmallCap 600 as a proxy for small-cap exposure
        sp600_url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
        tables = fetch_wikipedia_table(sp600_url)
        sp600_df = tables[0]
        tickers = set(sp600_df['Symbol'].str.replace('.', '-', regex=False).tolist())
        logger.info(f"  Found {len(tickers)} S&P 600 tickers (as Russell 2000 proxy)")
        return tickers
    except Exception as e:
        logger.error(f"  Failed to fetch S&P 600 tickers: {e}")
        return set()


def get_additional_etfs() -> Set[str]:
    """Get common ETFs we want to track."""
    etfs = {
        # Major index ETFs
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO',
        # Sector ETFs
        'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLC', 'XLY', 'XLP', 'XLB', 'XLU', 'XLRE',
        # Factor ETFs
        'MTUM', 'QUAL', 'VLUE', 'SIZE', 'USMV', 'VTV', 'VUG',
        # Bond ETFs
        'TLT', 'IEF', 'SHY', 'BND', 'LQD', 'HYG', 'BIL',
        # International
        'EFA', 'EEM', 'VEA', 'VWO',
        # Commodities
        'GLD', 'SLV', 'USO', 'DJP',
        # Volatility
        'VXX', 'UVXY',
        # Semiconductor
        'SMH', 'SOXX',
        # Software
        'IGV',
        # Real Estate
        'VNQ', 'IYR',
        # Dividend
        'SCHD', 'VYM', 'DVY',
    }
    logger.info(f"Adding {len(etfs)} common ETFs")
    return etfs


async def get_existing_coverage(engine) -> Dict[str, Dict]:
    """
    Get existing data coverage for all symbols in the database.
    Returns dict: {symbol: {'min_date': date, 'max_date': date, 'count': int}}
    """
    logger.info("Checking existing data coverage in Railway database...")

    async with AsyncSession(engine) as session:
        result = await session.execute(text("""
            SELECT
                symbol,
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(*) as record_count
            FROM market_data_cache
            GROUP BY symbol
        """))
        rows = result.fetchall()

    coverage = {}
    for row in rows:
        coverage[row[0]] = {
            'min_date': row[1],
            'max_date': row[2],
            'count': row[3]
        }

    logger.info(f"  Found existing data for {len(coverage)} symbols")
    return coverage


def determine_tickers_to_fetch(
    all_tickers: Set[str],
    coverage: Dict[str, Dict],
    start_date: date,
    end_date: date
) -> Dict[str, Dict]:
    """
    Determine which tickers need data fetched and for what date ranges.
    Returns dict: {symbol: {'start': date, 'end': date, 'reason': str}}
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date

    to_fetch = {}

    for ticker in all_tickers:
        if ticker not in coverage:
            # No data at all - fetch full range
            to_fetch[ticker] = {
                'start': start_dt,
                'end': end_dt,
                'reason': 'no_data'
            }
        else:
            existing = coverage[ticker]
            needs_fetch = False
            fetch_start = start_dt
            fetch_end = end_dt
            reason = []

            # Check if we need earlier data
            if existing['min_date'] > start_dt:
                needs_fetch = True
                reason.append(f"missing_before_{existing['min_date']}")

            # Check if we need more recent data (allow 3 day gap for weekends)
            days_stale = (end_dt - existing['max_date']).days
            if days_stale > 3:
                needs_fetch = True
                reason.append(f"stale_by_{days_stale}_days")
                fetch_start = existing['max_date']  # Only fetch from last date

            if needs_fetch:
                to_fetch[ticker] = {
                    'start': fetch_start,
                    'end': fetch_end,
                    'reason': ','.join(reason)
                }

    return to_fetch


def fetch_market_data_batch(
    tickers: List[str],
    start_date: str,
    end_date: str,
    batch_size: int = 50
) -> pd.DataFrame:
    """
    Fetch market data for multiple tickers using yfinance batch download.
    Returns combined DataFrame with all ticker data.
    """
    all_data = []

    # Process in batches
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tickers) + batch_size - 1) // batch_size

        logger.info(f"  Fetching batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

        try:
            # Use yfinance download for batch fetching
            data = yf.download(
                tickers=batch,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
                threads=True,
                group_by='ticker'
            )

            if data.empty:
                logger.warning(f"    No data returned for batch {batch_num}")
                continue

            # Handle single ticker vs multiple tickers response format
            if len(batch) == 1:
                # Single ticker - data columns are just OHLCV
                ticker = batch[0]
                df = data.copy()
                df['symbol'] = ticker
                df = df.reset_index()
                df = df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                all_data.append(df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])
            else:
                # Multiple tickers - data has multi-level columns
                for ticker in batch:
                    try:
                        if ticker in data.columns.get_level_values(0):
                            ticker_data = data[ticker].copy()
                            ticker_data['symbol'] = ticker
                            ticker_data = ticker_data.reset_index()
                            ticker_data = ticker_data.rename(columns={
                                'Date': 'date',
                                'Open': 'open',
                                'High': 'high',
                                'Low': 'low',
                                'Close': 'close',
                                'Volume': 'volume'
                            })
                            # Drop rows with NaN close prices
                            ticker_data = ticker_data.dropna(subset=['close'])
                            if not ticker_data.empty:
                                all_data.append(ticker_data[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])
                    except Exception as e:
                        logger.debug(f"    Could not extract data for {ticker}: {e}")
                        continue

            logger.info(f"    Batch {batch_num} complete")

        except Exception as e:
            logger.error(f"    Batch {batch_num} failed: {e}")
            continue

    if not all_data:
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"  Total records fetched: {len(combined)}")
    return combined


async def upsert_market_data(engine, df: pd.DataFrame, dry_run: bool = False) -> int:
    """
    Upsert market data into market_data_cache table.
    Uses ON CONFLICT to handle duplicates.
    Returns number of records upserted.
    """
    if df.empty:
        return 0

    if dry_run:
        logger.info(f"  [DRY RUN] Would upsert {len(df)} records")
        return len(df)

    logger.info(f"  Upserting {len(df)} records to database...")

    # Prepare records for insert
    records = []
    for _, row in df.iterrows():
        try:
            records.append({
                'id': str(uuid4()),
                'symbol': row['symbol'],
                'date': row['date'].date() if hasattr(row['date'], 'date') else row['date'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']),
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                'data_source': 'yfinance'
            })
        except Exception as e:
            logger.debug(f"    Skipping invalid record: {e}")
            continue

    if not records:
        return 0

    # Batch insert with ON CONFLICT
    async with AsyncSession(engine) as session:
        # Insert in chunks to avoid memory issues
        chunk_size = 1000
        total_inserted = 0

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]

            # Build the upsert query
            values_list = []
            for r in chunk:
                date_str = r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])
                open_val = str(r['open']) if r['open'] is not None else 'NULL'
                high_val = str(r['high']) if r['high'] is not None else 'NULL'
                low_val = str(r['low']) if r['low'] is not None else 'NULL'
                volume_val = str(r['volume']) if r['volume'] is not None else 'NULL'

                values_list.append(
                    f"('{r['id']}', '{r['symbol']}', '{date_str}', "
                    f"{open_val}, {high_val}, {low_val}, {r['close']}, {volume_val}, "
                    f"'{r['data_source']}', NOW(), NOW())"
                )

            values_sql = ",\n".join(values_list)

            upsert_sql = f"""
                INSERT INTO market_data_cache
                    (id, symbol, date, open, high, low, close, volume, data_source, created_at, updated_at)
                VALUES {values_sql}
                ON CONFLICT (symbol, date)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    data_source = EXCLUDED.data_source,
                    updated_at = NOW()
            """

            try:
                await session.execute(text(upsert_sql))
                await session.commit()
                total_inserted += len(chunk)
                logger.info(f"    Inserted chunk {i // chunk_size + 1}: {len(chunk)} records")
            except Exception as e:
                logger.error(f"    Failed to insert chunk: {e}")
                await session.rollback()
                continue

        return total_inserted


async def main(dry_run: bool = False, batch_size: int = 50):
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Market Data Backfill Script")
    logger.info(f"Date Range: {START_DATE} to {END_DATE}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("=" * 60)

    # Step 1: Collect all unique tickers
    logger.info("\n[Step 1] Collecting tickers from indices...")
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    russell2000 = get_russell2000_tickers()
    etfs = get_additional_etfs()

    all_tickers = sp500 | nasdaq100 | russell2000 | etfs

    logger.info(f"\nTicker Summary:")
    logger.info(f"  S&P 500:      {len(sp500)}")
    logger.info(f"  Nasdaq 100:   {len(nasdaq100)}")
    logger.info(f"  Russell 2000: {len(russell2000)} (S&P 600 proxy)")
    logger.info(f"  ETFs:         {len(etfs)}")
    logger.info(f"  Total Unique: {len(all_tickers)}")

    # Step 2: Check existing coverage
    logger.info("\n[Step 2] Checking existing data coverage...")
    engine = create_async_engine(RAILWAY_CORE_DB_URL)
    coverage = await get_existing_coverage(engine)

    # Step 3: Determine what needs fetching
    logger.info("\n[Step 3] Determining tickers that need data...")
    to_fetch = determine_tickers_to_fetch(
        all_tickers,
        coverage,
        START_DATE,
        END_DATE
    )

    already_covered = len(all_tickers) - len(to_fetch)
    logger.info(f"  Already covered: {already_covered}")
    logger.info(f"  Need to fetch:   {len(to_fetch)}")

    if not to_fetch:
        logger.info("\nAll tickers already have sufficient data coverage!")
        await engine.dispose()
        return

    # Show breakdown by reason
    reasons = {}
    for ticker, info in to_fetch.items():
        reason = info['reason']
        reasons[reason] = reasons.get(reason, 0) + 1

    logger.info("\n  Fetch reasons breakdown:")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        logger.info(f"    {reason}: {count}")

    # Step 4: Fetch data in batches
    logger.info(f"\n[Step 4] Fetching market data (batch size: {batch_size})...")

    # For simplicity, fetch full date range for all tickers that need data
    # (yfinance handles this efficiently)
    tickers_to_fetch = list(to_fetch.keys())

    df = fetch_market_data_batch(
        tickers_to_fetch,
        START_DATE,
        END_DATE,
        batch_size=batch_size
    )

    if df.empty:
        logger.warning("\nNo data was fetched from yfinance!")
        await engine.dispose()
        return

    # Step 5: Upsert to database
    logger.info(f"\n[Step 5] Upserting data to Railway database...")
    records_inserted = await upsert_market_data(engine, df, dry_run=dry_run)

    logger.info(f"\n{'=' * 60}")
    logger.info("COMPLETE!")
    logger.info(f"  Records processed: {records_inserted}")
    logger.info(f"  Tickers updated:   {df['symbol'].nunique() if not df.empty else 0}")
    logger.info("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill market data for major indices")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually insert data")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for yfinance downloads")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, batch_size=args.batch_size))
