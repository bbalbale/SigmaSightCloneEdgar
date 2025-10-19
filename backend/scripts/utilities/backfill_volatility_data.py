"""
Backfill Historical Market Data for Volatility Analysis

Downloads 365 days of historical OHLC data from yfinance for:
- PUBLIC positions (equities, ETFs, mutual funds)
- OPTION positions (using underlying symbols: TSLA, SPY, MSFT, etc.)

Skips:
- PRIVATE positions (no market data available)

This ensures HAR model has sufficient data (252+ trading days) for:
- Realized volatility calculation (21d, 63d windows)
- Expected volatility forecasting
- Volatility percentile calculation (requires 1 year of history)
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Set, Dict, List
from sqlalchemy import select
from app.database import get_async_session
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.core.logging import get_logger

# yfinance import
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Install with: uv add yfinance")
    exit(1)

logger = get_logger(__name__)


async def backfill_volatility_data(days: int = 365):
    """
    Main backfill function - downloads historical data for all marketable positions.

    Args:
        days: Number of days of historical data to download (default 365 for 1 year)
    """
    print(f"\n{'='*80}")
    print(f"HISTORICAL DATA BACKFILL - {days} days for Volatility Analysis")
    print(f"{'='*80}\n")

    async with get_async_session() as db:
        # Get all PUBLIC and OPTION positions (skip PRIVATE)
        result = await db.execute(
            select(Position).where(
                Position.investment_class.in_(['PUBLIC', 'OPTION']),
                Position.exit_date.is_(None)
            )
        )
        positions = result.scalars().all()

        if not positions:
            print("[!] No PUBLIC or OPTION positions found")
            return

        print(f"Found {len(positions)} marketable positions:")

        # Build set of unique symbols to fetch
        symbols_to_fetch: Set[str] = set()
        symbol_details: Dict[str, List[str]] = {}  # symbol -> [position_symbols using it]

        public_count = 0
        option_count = 0

        for pos in positions:
            if pos.investment_class == 'PUBLIC':
                # Use position symbol for public equities
                symbol = pos.symbol
                public_count += 1
            else:  # OPTION
                # Use underlying symbol for options
                symbol = pos.underlying_symbol
                option_count += 1

            symbols_to_fetch.add(symbol)

            if symbol not in symbol_details:
                symbol_details[symbol] = []
            symbol_details[symbol].append(f"{pos.symbol} ({pos.investment_class})")

        print(f"  - {public_count} PUBLIC positions")
        print(f"  - {option_count} OPTION positions")
        print(f"  - {len(symbols_to_fetch)} unique symbols to fetch\n")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        print(f"Date range: {start_date} to {end_date}")
        print(f"\nStarting download...\n")

        # Download data for each symbol
        success_count = 0
        failed_count = 0
        total_records_saved = 0

        for i, symbol in enumerate(sorted(symbols_to_fetch), 1):
            print(f"[{i}/{len(symbols_to_fetch)}] {symbol}")
            print(f"    Used by: {', '.join(symbol_details[symbol][:3])}{'...' if len(symbol_details[symbol]) > 3 else ''}")

            try:
                # Check if we already have recent data
                existing_count_result = await db.execute(
                    select(MarketDataCache).where(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date >= start_date
                    )
                )
                existing_records = existing_count_result.scalars().all()
                existing_dates = {r.date for r in existing_records}

                if len(existing_dates) >= 250:  # Already have ~1 year
                    print(f"    [OK] Already have {len(existing_dates)} days of data (skipping)")
                    success_count += 1
                    continue

                # Download from yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(
                    start=start_date,
                    end=end_date + timedelta(days=1),  # yfinance end is exclusive
                    interval='1d'
                )

                if hist.empty:
                    print(f"    [FAIL] No data returned from yfinance")
                    failed_count += 1
                    continue

                # Save to database
                records_saved = 0
                for dt, row in hist.iterrows():
                    # Convert pandas Timestamp to date
                    trade_date = dt.date()

                    # Skip if we already have this date
                    if trade_date in existing_dates:
                        continue

                    # Create or update record
                    existing_result = await db.execute(
                        select(MarketDataCache).where(
                            MarketDataCache.symbol == symbol,
                            MarketDataCache.date == trade_date
                        )
                    )
                    existing = existing_result.scalar_one_or_none()

                    if not existing:
                        # Create new record
                        cache_record = MarketDataCache(
                            symbol=symbol,
                            date=trade_date,
                            open=Decimal(str(row['Open'])),
                            high=Decimal(str(row['High'])),
                            low=Decimal(str(row['Low'])),
                            close=Decimal(str(row['Close'])),
                            volume=int(row['Volume']) if row['Volume'] else 0
                        )
                        db.add(cache_record)
                        records_saved += 1

                await db.commit()
                total_records_saved += records_saved

                total_after_save = len(existing_dates) + records_saved
                print(f"    [OK] Saved {records_saved} new records ({total_after_save} total days)")
                success_count += 1

            except Exception as e:
                print(f"    [FAIL] Error: {str(e)}")
                logger.error(f"Failed to download {symbol}: {e}", exc_info=True)
                await db.rollback()
                failed_count += 1

        # Summary
        print(f"\n{'='*80}")
        print(f"BACKFILL SUMMARY")
        print(f"{'='*80}")
        print(f"Symbols processed: {len(symbols_to_fetch)}")
        print(f"  [OK] Successful: {success_count}")
        print(f"  [FAIL] Failed: {failed_count}")
        print(f"Total new records saved: {total_records_saved}")

        if success_count > 0:
            print(f"\n[OK] Data backfill complete!")
            print(f"\nNEXT STEPS:")
            print(f"  1. Run batch calculations to compute HAR volatility:")
            print(f"     cd backend && uv run python scripts/run_batch_calculations.py")
            print(f"  2. Verify results:")
            print(f"     cd backend && uv run python scripts/verification/check_volatility_data.py")
        elif failed_count == len(symbols_to_fetch):
            print(f"\n[X] ALL DOWNLOADS FAILED")
            print(f"\nPOSSIBLE CAUSES:")
            print(f"  1. No internet connection")
            print(f"  2. yfinance API issues")
            print(f"  3. Invalid ticker symbols")
            print(f"\nTROUBLESHOOTING:")
            print(f"  - Check logs above for specific error messages")
            print(f"  - Try downloading a single ticker manually:")
            print(f"    python -c \"import yfinance as yf; print(yf.Ticker('AAPL').history(period='5d'))\"")
        else:
            print(f"\n[!] PARTIAL SUCCESS")
            print(f"  Some symbols succeeded, others failed.")
            print(f"  Check logs above for details on failures.")

        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill historical market data for volatility analysis")
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days to backfill (default: 365 for 1 year)'
    )
    args = parser.parse_args()

    asyncio.run(backfill_volatility_data(days=args.days))
