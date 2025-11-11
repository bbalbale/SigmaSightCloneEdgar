"""
Populate historical price data using yfinance for portfolio symbols.

This script fetches 252 trading days (~1 year) of historical price data
for all public equity symbols in the 3 demo portfolios and populates
the market_data_cache table.

This enables full volatility analytics including HAR forecasts and percentiles.
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
import yfinance as yf
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import MarketDataCache


async def populate_historical_prices():
    """Fetch and populate historical price data for portfolio symbols."""
    async with get_async_session() as db:
        # Get all portfolios
        portfolio_result = await db.execute(select(Portfolio))
        portfolios = portfolio_result.scalars().all()

        print(f"\n{'='*80}")
        print(f"POPULATING HISTORICAL PRICE DATA")
        print(f"{'='*80}\n")
        print(f"Found {len(portfolios)} portfolios")

        # Get all unique symbols from positions
        position_result = await db.execute(
            select(Position.symbol, Position.investment_class)
            .distinct()
        )
        all_positions = position_result.all()

        # Filter to PUBLIC securities only (skip private assets and options)
        public_symbols = set()
        skipped_symbols = set()

        for symbol, investment_class in all_positions:
            # Skip private assets (no public market data)
            if investment_class == 'PRIVATE':
                skipped_symbols.add(f"{symbol} (PRIVATE)")
                continue

            # Skip options (yfinance doesn't support options tickers directly)
            # Options have format: SYMBOL250815C00300000
            if len(symbol) > 10 and any(char in symbol for char in ['C', 'P']) and any(char.isdigit() for char in symbol):
                skipped_symbols.add(f"{symbol} (OPTIONS)")
                continue

            # Skip mutual funds (yfinance has mixed support)
            if symbol.endswith('X'):  # Mutual funds often end in X
                skipped_symbols.add(f"{symbol} (MUTUAL_FUND)")
                continue

            public_symbols.add(symbol)

        print(f"\nSymbols to fetch: {len(public_symbols)}")
        print(f"Symbols to skip: {len(skipped_symbols)}")
        if skipped_symbols:
            print(f"  Skipping: {', '.join(sorted(skipped_symbols)[:10])}{'...' if len(skipped_symbols) > 10 else ''}")
        print()

        # Calculate date range (252 trading days is ~365 calendar days)
        end_date = date.today()
        start_date = end_date - timedelta(days=400)  # Get ~400 calendar days to ensure 252 trading days

        print(f"Fetching data from {start_date} to {end_date}")
        print(f"{'='*80}\n")

        success_count = 0
        failed_count = 0
        total_records = 0

        for symbol in sorted(public_symbols):
            try:
                print(f"Fetching {symbol}...", end=" ", flush=True)

                # Download data from yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)

                if hist.empty:
                    print(f"[X] No data available")
                    failed_count += 1
                    continue

                # Insert/update records in market_data_cache
                records_inserted = 0
                for idx, row in hist.iterrows():
                    # Check if record already exists
                    existing_query = select(MarketDataCache).where(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date == idx.date()
                    )
                    existing_result = await db.execute(existing_query)
                    existing = existing_result.scalar_one_or_none()

                    if existing:
                        # Update existing record
                        existing.open = Decimal(str(row['Open']))
                        existing.high = Decimal(str(row['High']))
                        existing.low = Decimal(str(row['Low']))
                        existing.close = Decimal(str(row['Close']))
                        existing.volume = int(row['Volume']) if row['Volume'] else None
                        existing.data_source = 'yfinance'
                    else:
                        # Create new record
                        cache_record = MarketDataCache(
                            symbol=symbol,
                            date=idx.date(),
                            open=Decimal(str(row['Open'])),
                            high=Decimal(str(row['High'])),
                            low=Decimal(str(row['Low'])),
                            close=Decimal(str(row['Close'])),
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
                print(f"[X] Error: {str(e)[:50]}")
                failed_count += 1
                await db.rollback()

        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Symbols processed: {len(public_symbols)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total price records: {total_records}")

        if success_count > 0:
            print(f"\n[OK] Historical price data populated successfully!")
            print(f"\nNEXT STEPS:")
            print(f"  1. Run: cd backend && uv run python scripts/update_snapshot_volatility.py")
            print(f"  2. This will calculate HAR forecasts and percentiles")
            print(f"  3. Refresh frontend to see full volatility metrics")
        else:
            print(f"\n[X] NO DATA POPULATED")
            print(f"  Check error messages above for details")

        print()


if __name__ == "__main__":
    asyncio.run(populate_historical_prices())
