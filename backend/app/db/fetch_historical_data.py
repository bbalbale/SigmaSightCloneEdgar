"""
Shared Historical Data Fetching Module

Provides reusable functions for fetching and storing historical market data
from YFinance. Used by both seeding and refresh operations.
"""
import asyncio
from datetime import date, timedelta
from typing import List, Dict, Optional
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.core.logging import get_logger
from app.models.market_data import MarketDataCache
from app.clients import market_data_factory, DataType

logger = get_logger(__name__)


async def fetch_and_store_historical_data(
    db: AsyncSession,
    symbols: List[str],
    days: int = 180,
    batch_size: int = 10
) -> Dict[str, int]:
    """
    Fetch and store historical market data from YFinance for multiple symbols.

    Args:
        db: Database session
        symbols: List of stock/ETF symbols to fetch
        days: Number of days of historical data to fetch (default 180)
        batch_size: Number of symbols to process per batch for progress tracking (default 10)

    Returns:
        Dictionary mapping symbol -> number of records stored
        Example: {'NVDA': 123, 'META': 123, ...}

    Raises:
        Exception: If YFinance provider is not available
    """
    logger.info(f"[DATA] Fetching {days} days of historical data from YFinance...")
    logger.info(f"Processing {len(symbols)} symbols (batch size: {batch_size})")

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Date range: {start_date} to {end_date}")

    # Initialize YFinance provider
    market_data_factory.initialize()
    yfinance_provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)

    if not yfinance_provider or yfinance_provider.provider_name != "YFinance":
        raise Exception("YFinance provider not available")

    logger.info(f"Using provider: {yfinance_provider.provider_name}")

    # Track results
    records_per_symbol: Dict[str, int] = {}
    total_records = 0
    error_count = 0

    # Process symbols in batches for progress tracking
    total_batches = (len(symbols) + batch_size - 1) // batch_size

    for batch_idx in range(0, len(symbols), batch_size):
        batch = symbols[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1

        logger.info(f"Batch {batch_num}/{total_batches}: Processing {len(batch)} symbols")

        for symbol in batch:
            try:
                logger.info(f"  [{symbol}] Fetching...", )

                # Fetch historical data from YFinance
                historical_data = await yfinance_provider.get_historical_prices(
                    symbol,
                    days=days
                )

                if not historical_data:
                    logger.warning(f"  [{symbol}] [ERROR] No data returned")
                    error_count += 1
                    records_per_symbol[symbol] = 0
                    continue

                # Convert to database records
                records_to_insert = []
                for day_data in historical_data:
                    records_to_insert.append({
                        'symbol': symbol.upper(),
                        'date': day_data['date'],
                        'open': day_data['open'],
                        'high': day_data['high'],
                        'low': day_data['low'],
                        'close': day_data['close'],
                        'volume': day_data['volume'],
                        'data_source': 'yfinance'
                    })

                if records_to_insert:
                    # Use PostgreSQL upsert to overwrite existing data
                    stmt = insert(MarketDataCache).values(records_to_insert)

                    # On conflict (symbol, date), UPDATE all fields
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['symbol', 'date'],
                        set_={
                            'open': stmt.excluded.open,
                            'high': stmt.excluded.high,
                            'low': stmt.excluded.low,
                            'close': stmt.excluded.close,
                            'volume': stmt.excluded.volume,
                            'data_source': stmt.excluded.data_source,
                            'updated_at': func.now()
                        }
                    )

                    await db.execute(stmt)
                    await db.commit()

                    record_count = len(records_to_insert)
                    records_per_symbol[symbol] = record_count
                    total_records += record_count
                    logger.info(f"  [{symbol}] [OK] {record_count} days stored")
                else:
                    logger.warning(f"  [{symbol}] [ERROR] No records to insert")
                    error_count += 1
                    records_per_symbol[symbol] = 0

            except Exception as e:
                logger.error(f"  [{symbol}] [ERROR] Error: {str(e)[:100]}")
                error_count += 1
                records_per_symbol[symbol] = 0
                await db.rollback()
                continue

    logger.info("")
    logger.info("=" * 80)
    logger.info("HISTORICAL DATA FETCH COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Symbols processed: {len(symbols)}")
    logger.info(f"Total records stored: {total_records}")
    logger.info(f"Errors: {error_count}")
    logger.info("")

    return records_per_symbol


async def filter_stock_symbols(symbols: List[str]) -> List[str]:
    """
    Filter out options symbols, keeping only stocks and ETFs.

    Options symbols are typically 15+ characters with dates in them.
    Example: SPY250919C00460000 (option) vs SPY (stock)

    Args:
        symbols: List of all symbols

    Returns:
        List of stock/ETF symbols only
    """
    stock_symbols = [
        s for s in symbols
        if len(s) <= 10 or not any(c.isdigit() for c in s[6:])
    ]

    logger.info(f"Filtered {len(symbols)} total symbols -> {len(stock_symbols)} stocks/ETFs")

    return stock_symbols
