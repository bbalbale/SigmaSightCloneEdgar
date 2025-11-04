"""
Populate S&P 500 market cache with historical prices and company fundamentals.

This script:
1. Fetches current S&P 500 constituents from Wikipedia
2. Populates historical price data (Jan 1, 2025 → present) using yfinance
3. Populates company profiles with 53 fundamental fields using yahooquery

Target: ~503 S&P 500 companies
Estimated time: 20-25 minutes total
"""
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache, CompanyProfile
from app.services.market_data_service import market_data_service
from app.core.logging import get_logger

logger = get_logger(__name__)


def fetch_sp500_tickers():
    """Fetch current S&P 500 constituent tickers from Wikipedia."""
    logger.info("Fetching S&P 500 tickers from Wikipedia...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'class': 'wikitable'})

    tickers = []
    rows = table.find_all('tr')

    for row in rows[1:]:  # Skip header
        cells = row.find_all(['td', 'th'])
        if len(cells) > 0:
            ticker = cells[0].text.strip()
            if ticker:
                tickers.append(ticker)

    logger.info(f"✅ Found {len(tickers)} S&P 500 tickers")
    return tickers


async def populate_historical_prices(db, symbols, start_date, end_date):
    """
    Populate historical price data for given symbols.

    Args:
        db: Database session
        symbols: List of ticker symbols
        start_date: Start date for historical data
        end_date: End date for historical data
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 1: HISTORICAL PRICE DATA")
    logger.info(f"{'='*80}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"{'='*80}\n")

    success_count = 0
    failed_count = 0
    total_records = 0
    failed_symbols = []

    for idx, symbol in enumerate(symbols, 1):
        try:
            print(f"[{idx}/{len(symbols)}] Fetching {symbol}...", end=" ", flush=True)

            # Download data from yfinance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"[SKIP] No data available")
                failed_count += 1
                failed_symbols.append(f"{symbol} (no data)")
                continue

            # Insert/update records in market_data_cache
            records_inserted = 0
            for date_idx, row in hist.iterrows():
                # Check if record already exists
                existing_query = select(MarketDataCache).where(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date == date_idx.date()
                )
                existing_result = await db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    # Update existing record
                    existing.open = Decimal(str(round(row['Open'], 4)))
                    existing.high = Decimal(str(round(row['High'], 4)))
                    existing.low = Decimal(str(round(row['Low'], 4)))
                    existing.close = Decimal(str(round(row['Close'], 4)))
                    existing.volume = int(row['Volume']) if row['Volume'] else None
                    existing.data_source = 'yfinance'
                else:
                    # Create new record
                    cache_record = MarketDataCache(
                        symbol=symbol,
                        date=date_idx.date(),
                        open=Decimal(str(round(row['Open'], 4))),
                        high=Decimal(str(round(row['High'], 4))),
                        low=Decimal(str(round(row['Low'], 4))),
                        close=Decimal(str(round(row['Close'], 4))),
                        volume=int(row['Volume']) if row['Volume'] else None,
                        data_source='yfinance'
                    )
                    db.add(cache_record)

                records_inserted += 1

            await db.commit()
            print(f"[OK] {records_inserted} records")
            success_count += 1
            total_records += records_inserted

        except Exception as e:
            error_msg = str(e)[:60]
            print(f"[ERROR] {error_msg}")
            failed_count += 1
            failed_symbols.append(f"{symbol} ({error_msg})")
            await db.rollback()

    # Phase 1 Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 1 SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Symbols processed: {len(symbols)}")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failed_count}")
    logger.info(f"📊 Total price records: {total_records}")

    if failed_symbols:
        logger.info(f"\nFailed symbols (first 10):")
        for symbol in failed_symbols[:10]:
            logger.info(f"  - {symbol}")
        if len(failed_symbols) > 10:
            logger.info(f"  ... and {len(failed_symbols) - 10} more")

    return {
        'success': success_count,
        'failed': failed_count,
        'total_records': total_records,
        'failed_symbols': failed_symbols
    }


async def populate_company_profiles(db, symbols):
    """
    Populate company profile data for given symbols.

    Args:
        db: Database session
        symbols: List of ticker symbols
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 2: COMPANY FUNDAMENTALS")
    logger.info(f"{'='*80}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Fields: 53 fundamental data points")
    logger.info(f"{'='*80}\n")

    # Batch process symbols (10 at a time to respect rate limits)
    batch_size = 10
    total_batches = (len(symbols) + batch_size - 1) // batch_size

    total_success = 0
    total_failed = 0
    failed_symbols = []

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        logger.info(f"Processing batch {batch_num}/{total_batches}: {', '.join(batch)}")

        try:
            # Fetch and cache profiles for this batch
            results = await market_data_service.fetch_and_cache_company_profiles(db, batch)

            # Count successes and failures
            batch_success = results['symbols_successful']
            batch_failed = results['symbols_failed']

            total_success += batch_success
            total_failed += batch_failed

            logger.info(
                f"  ✅ Success: {batch_success}/{len(batch)} | "
                f"❌ Failed: {batch_failed}"
            )

            # Track failed symbols
            if results['failed_symbols']:
                failed_symbols.extend(results['failed_symbols'])
                for symbol in results['failed_symbols']:
                    logger.warning(f"    Failed: {symbol}")

        except Exception as e:
            logger.error(f"  ❌ Batch {batch_num} error: {e}")
            total_failed += len(batch)
            failed_symbols.extend(batch)

        # Sleep between batches to respect rate limits
        if i + batch_size < len(symbols):
            await asyncio.sleep(1)

    # Phase 2 Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 2 SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Symbols processed: {len(symbols)}")
    logger.info(f"✅ Successful: {total_success}")
    logger.info(f"❌ Failed: {total_failed}")

    if failed_symbols:
        logger.info(f"\nFailed symbols (first 10):")
        for symbol in failed_symbols[:10]:
            logger.info(f"  - {symbol}")
        if len(failed_symbols) > 10:
            logger.info(f"  ... and {len(failed_symbols) - 10} more")

    return {
        'success': total_success,
        'failed': total_failed,
        'failed_symbols': failed_symbols
    }


async def show_sample_data(db):
    """Display sample of populated data."""
    logger.info(f"\n{'='*80}")
    logger.info(f"SAMPLE DATA")
    logger.info(f"{'='*80}\n")

    # Sample historical prices
    logger.info("Recent price records (last 5):")
    price_query = select(MarketDataCache).order_by(
        MarketDataCache.date.desc()
    ).limit(5)
    price_result = await db.execute(price_query)
    prices = price_result.scalars().all()

    for price in prices:
        logger.info(
            f"  {price.symbol} | {price.date} | "
            f"Close: ${price.close} | Vol: {price.volume:,} | "
            f"Source: {price.data_source}"
        )

    # Sample company profiles
    logger.info("\nCompany profiles (first 5):")
    profile_query = select(CompanyProfile).limit(5)
    profile_result = await db.execute(profile_query)
    profiles = profile_result.scalars().all()

    for profile in profiles:
        sector = profile.sector or "N/A"
        beta = f"{profile.beta:.2f}" if profile.beta else "N/A"
        pe = f"{profile.pe_ratio:.1f}" if profile.pe_ratio else "N/A"

        cy_rev = profile.current_year_revenue_avg
        cy_rev_str = f"${cy_rev/1e9:.1f}B" if cy_rev else "N/A"

        logger.info(
            f"  {profile.symbol}: {profile.company_name or 'N/A'} | "
            f"Sector: {sector} | Beta: {beta} | PE: {pe} | "
            f"CY Rev: {cy_rev_str}"
        )


async def main():
    """Main execution function."""
    start_time = datetime.now()

    logger.info(f"\n{'='*80}")
    logger.info(f"S&P 500 MARKET CACHE POPULATION")
    logger.info(f"{'='*80}")
    logger.info(f"Started: {start_time}")
    logger.info(f"{'='*80}\n")

    try:
        # Step 1: Fetch S&P 500 tickers
        symbols = fetch_sp500_tickers()

        if not symbols:
            logger.error("❌ No symbols fetched. Exiting.")
            return

        logger.info(f"\nFirst 10 symbols: {', '.join(symbols[:10])}")
        logger.info(f"Last 10 symbols: {', '.join(symbols[-10:])}\n")

        # Calculate date range (Jan 1, 2025 to today)
        start_date = date(2025, 1, 1)
        end_date = date.today()
        trading_days = (end_date - start_date).days  # Approximate

        logger.info(f"Date range: {start_date} to {end_date} (~{trading_days} calendar days)")
        logger.info(f"Estimated trading days: ~{int(trading_days * 0.71)} (assuming 252/365 ratio)\n")

        # Open database session
        async with AsyncSessionLocal() as db:
            # Phase 1: Historical Prices
            price_results = await populate_historical_prices(
                db, symbols, start_date, end_date
            )

            # Phase 2: Company Profiles
            profile_results = await populate_company_profiles(db, symbols)

            # Show sample data
            await show_sample_data(db)

        # Final Summary
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info(f"\n{'='*80}")
        logger.info(f"FINAL SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"S&P 500 symbols: {len(symbols)}")
        logger.info(f"\nHistorical Prices:")
        logger.info(f"  ✅ Successful: {price_results['success']}")
        logger.info(f"  ❌ Failed: {price_results['failed']}")
        logger.info(f"  📊 Total records: {price_results['total_records']}")
        logger.info(f"\nCompany Profiles:")
        logger.info(f"  ✅ Successful: {profile_results['success']}")
        logger.info(f"  ❌ Failed: {profile_results['failed']}")
        logger.info(f"\nExecution time: {duration}")
        logger.info(f"{'='*80}\n")

        # Success message
        if price_results['success'] > 0 or profile_results['success'] > 0:
            logger.info("✅ S&P 500 market cache populated successfully!")
            logger.info("\nYou can now:")
            logger.info("  1. Query historical prices via MarketDataCache table")
            logger.info("  2. Access company fundamentals via CompanyProfile table")
            logger.info("  3. Run batch analytics on S&P 500 constituents")
        else:
            logger.warning("⚠️ No data was populated. Check error messages above.")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
