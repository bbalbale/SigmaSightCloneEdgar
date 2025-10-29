"""
YahooQuery Service - Primary data source for historical price data

Priority chain: YahooQuery → YFinance → FMP → Polygon

YahooQuery advantages:
- Free tier with good rate limits
- Reliable for daily OHLCV data
- Better batch performance than YFinance
- Good coverage for US stocks/ETFs
"""
import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from yahooquery import Ticker

from app.core.logging import get_logger

logger = get_logger(__name__)


class YahooQueryService:
    """
    Service for fetching historical price data using YahooQuery

    Supports:
    - Bulk symbol fetching (efficient batch processing)
    - Historical data with configurable date ranges
    - Async-safe execution
    """

    def __init__(self):
        self.session_cache = {}  # Symbol -> Ticker object cache

    async def fetch_historical_prices(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        max_workers: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical price data for multiple symbols

        Args:
            symbols: List of stock/ETF symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            max_workers: Number of parallel workers (default: 3 to avoid rate limits)

        Returns:
            Dict mapping symbol -> list of daily price records
            {
                'AAPL': [
                    {
                        'date': date(2025, 7, 1),
                        'open': Decimal('225.00'),
                        'high': Decimal('227.50'),
                        'low': Decimal('224.00'),
                        'close': Decimal('226.50'),
                        'volume': 50000000,
                        'data_source': 'yahooquery'
                    },
                    ...
                ],
                ...
            }
        """
        if not symbols:
            logger.warning("No symbols provided to fetch_historical_prices")
            return {}

        logger.info(f"Fetching YahooQuery data for {len(symbols)} symbols from {start_date} to {end_date}")

        # Run in thread pool executor to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._fetch_batch_sync,
            symbols,
            start_date,
            end_date
        )

        return result

    def _fetch_batch_sync(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Synchronous batch fetch (runs in thread pool)

        YahooQuery supports batch fetching - much faster than individual requests
        """
        results = {}

        try:
            # Batch fetch using YahooQuery's Ticker class
            # It handles multiple symbols efficiently
            tickers = Ticker(symbols, asynchronous=False)

            # Fetch history for all symbols at once
            history_df = tickers.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='1d'
            )

            # Check if we got an error response
            if isinstance(history_df, dict) and 'error' in str(history_df).lower():
                logger.error(f"YahooQuery API error: {history_df}")
                return results

            # Convert DataFrame to our format
            if history_df is not None and not history_df.empty:
                # YahooQuery returns multi-index (symbol, date)
                for symbol in symbols:
                    try:
                        if symbol in history_df.index.get_level_values(0):
                            symbol_data = history_df.loc[symbol]

                            symbol_records = []
                            for idx, row in symbol_data.iterrows():
                                # idx is the date
                                record = {
                                    'date': idx.date() if hasattr(idx, 'date') else idx,
                                    'open': self._safe_decimal(row.get('open')),
                                    'high': self._safe_decimal(row.get('high')),
                                    'low': self._safe_decimal(row.get('low')),
                                    'close': self._safe_decimal(row.get('close')),
                                    'volume': int(row.get('volume', 0)) if row.get('volume') else None,
                                    'data_source': 'yahooquery'
                                }

                                # Only add if we have valid close price
                                if record['close'] is not None and record['close'] > 0:
                                    symbol_records.append(record)

                            if symbol_records:
                                results[symbol] = symbol_records
                                logger.debug(f"  {symbol}: fetched {len(symbol_records)} records")
                            else:
                                logger.warning(f"  {symbol}: no valid price data")

                    except Exception as e:
                        logger.warning(f"  {symbol}: error parsing data - {e}")
                        continue

            logger.info(f"YahooQuery: Successfully fetched {len(results)}/{len(symbols)} symbols")

        except Exception as e:
            logger.error(f"YahooQuery batch fetch failed: {e}")

        return results

    async def fetch_latest_price(
        self,
        symbols: List[str]
    ) -> Dict[str, Optional[Decimal]]:
        """
        Fetch just the latest close price for multiple symbols

        Useful for quick price checks without full historical data

        Returns:
            Dict mapping symbol -> latest close price
        """
        if not symbols:
            return {}

        logger.info(f"Fetching latest prices for {len(symbols)} symbols")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._fetch_latest_sync,
            symbols
        )

        return result

    def _fetch_latest_sync(self, symbols: List[str]) -> Dict[str, Optional[Decimal]]:
        """Synchronous latest price fetch"""
        results = {}

        try:
            tickers = Ticker(symbols, asynchronous=False)

            # Use price property for latest quotes
            price_data = tickers.price

            if isinstance(price_data, dict):
                for symbol in symbols:
                    if symbol in price_data:
                        symbol_data = price_data[symbol]

                        # Try different price fields in order of preference
                        price = (
                            symbol_data.get('regularMarketPrice') or
                            symbol_data.get('postMarketPrice') or
                            symbol_data.get('preMarketPrice')
                        )

                        if price:
                            results[symbol] = self._safe_decimal(price)
                        else:
                            logger.warning(f"  {symbol}: no price data available")

        except Exception as e:
            logger.error(f"YahooQuery latest price fetch failed: {e}")

        return results

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert to Decimal"""
        if value is None or value == '' or value != value:  # NaN check
            return None
        try:
            dec_value = Decimal(str(value))
            if dec_value <= 0:
                return None
            return dec_value.quantize(Decimal('0.01'))
        except (ValueError, TypeError, Exception):
            return None

    def clear_cache(self):
        """Clear the session cache (call periodically to free memory)"""
        self.session_cache.clear()


# Global instance
yahooquery_service = YahooQueryService()
