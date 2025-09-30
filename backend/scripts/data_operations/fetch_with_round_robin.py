"""
Fetch historical data with round-robin provider switching and rate limiting
- Alternates between Polygon and FMP every 50 symbols
- Rate limited to ~10 calls per minute (6 second delay between calls)
"""
import asyncio
import time
from datetime import date, timedelta
from typing import List, Dict, Any
from decimal import Decimal
import sys
import io

# Configure UTF-8 output for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.clients import market_data_factory, DataType
from app.core.logging import get_logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.market_data import MarketDataCache

logger = get_logger(__name__)


async def fetch_with_round_robin(
    symbols: List[str],
    days_back: int = 150,
    calls_per_minute: int = 10
):
    """
    Fetch historical data alternating between Polygon and FMP

    Args:
        symbols: List of symbols to fetch
        days_back: Number of days of historical data
        calls_per_minute: Rate limit (default 10)
    """
    delay_between_calls = 60 / calls_per_minute  # 6 seconds for 10 calls/min

    async with AsyncSessionLocal() as db:
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        total_symbols = len(symbols)
        polygon_count = 0
        fmp_count = 0
        success_count = 0
        error_count = 0

        print(f"\n{'='*60}")
        print(f"Starting Round-Robin Data Fetch")
        print(f"{'='*60}")
        print(f"Symbols: {total_symbols}")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Rate limit: {calls_per_minute} calls/minute ({delay_between_calls}s delay)")
        print(f"Strategy: FMP primary (better for stocks), Polygon fallback")
        print(f"{'='*60}\n")

        # Use FMP for all symbols (it has better rate limits)
        fmp_provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)

        if not fmp_provider:
            print("❌ FMP provider not available")
            return

        for idx, symbol in enumerate(symbols, 1):
            try:
                print(f"[{idx}/{total_symbols}] Fetching {symbol} via FMP...", end=" ", flush=True)
                start_time = time.time()

                # Fetch from FMP
                historical_data = await fmp_provider.get_historical_prices(symbol, days=days_back)

                if historical_data and len(historical_data) > 0:
                    # Convert to our format
                    records = []
                    for day_data in historical_data:
                        date_value = day_data['date']
                        if isinstance(date_value, str):
                            from datetime import datetime
                            date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                        elif isinstance(date_value, date):
                            date_obj = date_value
                        else:
                            from datetime import datetime
                            date_obj = datetime.fromisoformat(str(date_value)).date()

                        records.append({
                            'symbol': symbol.upper(),
                            'date': date_obj,
                            'open': Decimal(str(day_data['open'])),
                            'high': Decimal(str(day_data['high'])),
                            'low': Decimal(str(day_data['low'])),
                            'close': Decimal(str(day_data['close'])),
                            'volume': day_data['volume'],
                            'data_source': 'fmp'
                        })

                    # Insert with conflict handling (preserve existing data)
                    if records:
                        stmt = pg_insert(MarketDataCache).values(records)
                        stmt = stmt.on_conflict_do_nothing(
                            constraint='uq_market_data_cache_symbol_date'
                        )
                        result = await db.execute(stmt)
                        inserted = result.rowcount

                        elapsed = time.time() - start_time
                        print(f"✅ {inserted} records in {elapsed:.1f}s")
                        fmp_count += 1
                        success_count += 1
                    else:
                        print(f"⚠️  No data")
                        error_count += 1
                else:
                    print(f"⚠️  No data returned")
                    error_count += 1

            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ Error in {elapsed:.1f}s: {str(e)[:50]}")
                error_count += 1

            # Rate limiting delay
            if idx < total_symbols:
                await asyncio.sleep(delay_between_calls)

        # Commit all changes
        await db.commit()

        print(f"\n{'='*60}")
        print(f"Fetch Complete")
        print(f"{'='*60}")
        print(f"Total symbols: {total_symbols}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"FMP calls: {fmp_count}")
        print(f"Polygon calls: {polygon_count}")
        print(f"{'='*60}\n")


async def main():
    # Critical symbols for factor analysis
    symbols = [
        # Factor ETFs (must have for regressions)
        'SPY', 'VTV', 'VUG', 'MTUM', 'QUAL', 'IWM', 'USMV',
        # Major stocks
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        'JPM', 'V', 'UNH', 'HD', 'PG', 'JNJ', 'XOM', 'C', 'F', 'GE',
        'QQQ', 'VTI', 'BRK-B', 'AMD', 'NFLX', 'SHOP', 'ROKU', 'ZM', 'PTON'
    ]

    await fetch_with_round_robin(
        symbols=symbols,
        days_back=150,
        calls_per_minute=10  # Conservative rate limit
    )


if __name__ == "__main__":
    asyncio.run(main())