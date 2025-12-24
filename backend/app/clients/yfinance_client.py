"""
YFinance API client implementation
Free, unlimited API for stock market data
Documentation: https://github.com/ranaroussi/yfinance
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
import pandas as pd
import yfinance as yf
from app.core.datetime_utils import utc_now

from app.clients.base import MarketDataProvider

logger = logging.getLogger(__name__)


class YFinanceClient(MarketDataProvider):
    """YFinance API client - Primary data provider for stocks and ETFs"""

    def __init__(self, api_key: str = "none", timeout: int = 30, max_retries: int = 3):
        """
        Initialize YFinance client

        Args:
            api_key: Not used for yfinance, kept for interface compatibility
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        # YFinance doesn't require an API key, but we keep the interface consistent
        super().__init__(api_key or "none", timeout, max_retries)
        self.provider_name = "YFinance"

        # Rate limiting: Conservative 1 request per second to avoid being blocked
        self._last_request_time = 0
        self._request_interval = 1.0  # seconds between requests
        self._request_lock = asyncio.Lock()

    async def _rate_limit(self):
        """Apply rate limiting to avoid overwhelming yfinance servers"""
        async with self._request_lock:
            import time
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self._request_interval:
                wait_time = self._request_interval - time_since_last
                logger.debug(f"YFinance rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()

    async def _fetch_with_retry(self, func, *args, **kwargs):
        """
        Execute a yfinance function with retry logic

        Since yfinance is synchronous, we run it in a thread pool
        """
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting
                await self._rate_limit()

                # Run the synchronous yfinance function in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
                return result

            except Exception as e:
                logger.warning(f"YFinance attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"YFinance failed after {self.max_retries} attempts")
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None

    async def get_stock_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current stock prices from YFinance

        Uses the Ticker.info and Ticker.history for current data
        """
        results = {}

        try:
            # YFinance can handle multiple symbols at once using download
            # But for current prices, we need to use Ticker objects
            for symbol in symbols:
                try:
                    ticker = await self._fetch_with_retry(yf.Ticker, symbol)

                    if not ticker:
                        logger.warning(f"YFinance: No ticker object for {symbol}")
                        continue

                    # Get the ticker info - this is synchronous so we run in executor
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, lambda: ticker.info)

                    # Get current price from info or fallback to history
                    current_price = None
                    previous_close = None
                    volume = 0

                    # Try to get current price from various fields
                    if 'currentPrice' in info and info['currentPrice']:
                        current_price = info['currentPrice']
                    elif 'regularMarketPrice' in info and info['regularMarketPrice']:
                        current_price = info['regularMarketPrice']
                    elif 'price' in info and info['price']:
                        current_price = info['price']

                    # Get previous close for change calculation
                    if 'previousClose' in info and info['previousClose']:
                        previous_close = info['previousClose']
                    elif 'regularMarketPreviousClose' in info and info['regularMarketPreviousClose']:
                        previous_close = info['regularMarketPreviousClose']

                    # Get volume
                    if 'volume' in info and info['volume']:
                        volume = info['volume']
                    elif 'regularMarketVolume' in info and info['regularMarketVolume']:
                        volume = info['regularMarketVolume']

                    # If we couldn't get current price from info, try recent history
                    if current_price is None:
                        history = await loop.run_in_executor(
                            None,
                            lambda: ticker.history(period="1d", interval="1m")
                        )
                        if not history.empty:
                            current_price = float(history['Close'].iloc[-1])
                            volume = int(history['Volume'].iloc[-1])

                            # Get previous close from daily history
                            daily_history = await loop.run_in_executor(
                                None,
                                lambda: ticker.history(period="2d", interval="1d")
                            )
                            if len(daily_history) >= 2:
                                previous_close = float(daily_history['Close'].iloc[-2])

                    if current_price is not None:
                        # Calculate change and change percentage
                        change = Decimal('0')
                        change_percent = Decimal('0')

                        if previous_close and previous_close > 0:
                            change = Decimal(str(current_price - previous_close))
                            change_percent = Decimal(str((current_price - previous_close) / previous_close * 100))

                        results[symbol] = {
                            'price': Decimal(str(current_price)),
                            'change': change,
                            'change_percent': change_percent,
                            'volume': int(volume),
                            'timestamp': utc_now(),
                            'provider': 'YFinance',
                            'previous_close': Decimal(str(previous_close)) if previous_close else None
                        }

                        logger.debug(f"YFinance: Got price for {symbol}: ${current_price}")
                    else:
                        logger.warning(f"YFinance: No price data available for {symbol}")

                except Exception as e:
                    logger.error(f"YFinance error fetching {symbol}: {str(e)}")
                    continue

            logger.info(f"YFinance: Successfully retrieved {len(results)} stock quotes")
            return results

        except Exception as e:
            logger.error(f"YFinance get_stock_prices failed: {str(e)}")
            raise

    async def get_historical_prices(self, symbol: str, calculation_date: date, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get historical prices for a single symbol

        Uses the download function for efficient historical data retrieval
        """
        try:
            # Calculate date range
            end_date = calculation_date
            # yfinance end date is exclusive, so add one day to include the calculation_date
            exclusive_end_date = end_date + timedelta(days=1)
            start_date = end_date - timedelta(days=days)

            # Use yfinance download function for historical data
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    symbol,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=exclusive_end_date.strftime('%Y-%m-%d'),
                    progress=False,
                    auto_adjust=False,  # Use unadjusted prices for consistency
                    threads=False  # Avoid threading issues
                )
            )

            if data.empty:
                logger.warning(f"YFinance: No historical data for {symbol}")
                return []

            historical_data = []
            for idx, row in data.iterrows():
                try:
                    # Convert values, skipping any rows with NaN
                    # Access scalar values properly to avoid Series warnings
                    open_price = row['Open'].item() if hasattr(row['Open'], 'item') else row['Open']
                    high_price = row['High'].item() if hasattr(row['High'], 'item') else row['High']
                    low_price = row['Low'].item() if hasattr(row['Low'], 'item') else row['Low']
                    close_price = row['Close'].item() if hasattr(row['Close'], 'item') else row['Close']
                    volume = row['Volume'].item() if hasattr(row['Volume'], 'item') else row['Volume']

                    historical_data.append({
                        'date': idx.date() if hasattr(idx, 'date') else idx,
                        'open': Decimal(str(open_price)),
                        'high': Decimal(str(high_price)),
                        'low': Decimal(str(low_price)),
                        'close': Decimal(str(close_price)),
                        'volume': int(volume) if volume and str(volume) != 'nan' else 0,
                        'provider': 'YFinance'
                    })
                except (ValueError, TypeError, KeyError) as e:
                    # Skip rows with NaN or invalid values
                    logger.debug(f"Skipping row in YFinance historical data for {symbol}: {str(e)}")
                    continue

            # Sort by date (oldest first)
            historical_data.sort(key=lambda x: x['date'])

            logger.info(f"YFinance: Retrieved {len(historical_data)} historical prices for {symbol}")
            return historical_data

        except Exception as e:
            logger.error(f"YFinance get_historical_prices failed for {symbol}: {str(e)}")
            raise

    async def get_historical_prices_batch(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        batch_size: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical prices for multiple symbols using yfinance batch download.

        This is much more efficient than calling get_historical_prices one symbol at a time.
        yfinance.download() natively supports downloading multiple tickers in one call.

        Args:
            symbols: List of ticker symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            batch_size: Number of symbols to fetch per batch (default 50)

        Returns:
            Dictionary with symbol as key and list of price records as value
        """
        results = {}
        # yfinance end date is exclusive, add one day
        exclusive_end_date = end_date + timedelta(days=1)

        # Process in batches
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"YFinance batch {batch_num}/{total_batches}: Fetching {len(batch)} symbols...")

            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    None,
                    lambda b=batch: yf.download(
                        tickers=b,
                        start=start_date.strftime('%Y-%m-%d'),
                        end=exclusive_end_date.strftime('%Y-%m-%d'),
                        progress=False,
                        auto_adjust=False,  # Use unadjusted prices for consistency
                        threads=True,  # Enable threading for batch downloads
                        group_by='ticker'
                    )
                )

                if data.empty:
                    logger.warning(f"YFinance batch {batch_num}: No data returned")
                    continue

                # Handle single ticker vs multiple tickers response format
                if len(batch) == 1:
                    # Single ticker - data columns are just OHLCV
                    symbol = batch[0]
                    symbol_data = self._parse_single_ticker_data(symbol, data)
                    if symbol_data:
                        results[symbol] = symbol_data
                else:
                    # Multiple tickers - data has multi-level columns (ticker, field)
                    for symbol in batch:
                        try:
                            if symbol in data.columns.get_level_values(0):
                                ticker_data = data[symbol]
                                symbol_data = self._parse_single_ticker_data(symbol, ticker_data)
                                if symbol_data:
                                    results[symbol] = symbol_data
                        except Exception as e:
                            logger.debug(f"YFinance: Could not extract data for {symbol}: {e}")
                            continue

                logger.info(f"YFinance batch {batch_num}: Retrieved data for {len([s for s in batch if s in results])}/{len(batch)} symbols")

            except Exception as e:
                logger.error(f"YFinance batch {batch_num} failed: {e}")
                continue

        logger.info(f"YFinance batch download complete: {len(results)}/{len(symbols)} symbols successful")
        return results

    def _parse_single_ticker_data(self, symbol: str, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Parse a single ticker's DataFrame into list of price records (close only)."""
        if data.empty:
            return []

        historical_data = []
        for idx, row in data.iterrows():
            try:
                # Handle both Series and scalar values
                def get_value(col):
                    val = row[col]
                    if hasattr(val, 'item'):
                        return val.item()
                    return val

                close_price = get_value('Close')
                volume = get_value('Volume')

                # Skip rows with NaN close prices
                if pd.isna(close_price):
                    continue

                # Only store close price - open/high/low not needed
                historical_data.append({
                    'date': idx.date() if hasattr(idx, 'date') else idx,
                    'close': Decimal(str(close_price)),
                    'volume': int(volume) if volume and not pd.isna(volume) else 0,
                    'provider': 'YFinance'
                })
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"Skipping row for {symbol}: {e}")
                continue

        # Sort by date (oldest first)
        historical_data.sort(key=lambda x: x['date'])
        return historical_data

    async def get_company_profile(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get company profile including sector and industry from YFinance

        Uses the Ticker.info endpoint
        """
        results = {}

        try:
            for symbol in symbols:
                try:
                    ticker = await self._fetch_with_retry(yf.Ticker, symbol)

                    if not ticker:
                        logger.warning(f"YFinance: No ticker object for {symbol}")
                        continue

                    # Get the ticker info
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, lambda: ticker.info)

                    if not info:
                        logger.warning(f"YFinance: No info available for {symbol}")
                        continue

                    # Extract relevant profile information
                    results[symbol] = {
                        'sector': info.get('sector'),
                        'industry': info.get('industry'),
                        'company_name': info.get('longName') or info.get('shortName'),
                        'exchange': info.get('exchange'),
                        'country': info.get('country'),
                        'market_cap': Decimal(str(info.get('marketCap', 0))) if info.get('marketCap') else None,
                        'description': info.get('longBusinessSummary'),
                        'is_etf': info.get('quoteType') == 'ETF',
                        'is_fund': info.get('quoteType') == 'MUTUALFUND',
                        'ceo': info.get('companyOfficers', [{}])[0].get('name') if info.get('companyOfficers') else None,
                        'employees': info.get('fullTimeEmployees'),
                        'website': info.get('website'),
                        'timestamp': utc_now(),
                        'provider': 'YFinance',
                        # Additional useful fields from yfinance
                        'pe_ratio': info.get('trailingPE'),
                        'forward_pe': info.get('forwardPE'),
                        'dividend_yield': info.get('dividendYield'),
                        'beta': info.get('beta'),
                        '52_week_high': info.get('fiftyTwoWeekHigh'),
                        '52_week_low': info.get('fiftyTwoWeekLow')
                    }

                    logger.debug(f"YFinance: Got profile for {symbol} - Sector: {results[symbol]['sector']}, Industry: {results[symbol]['industry']}")

                except Exception as e:
                    logger.error(f"Error fetching YFinance profile for {symbol}: {str(e)}")
                    continue

            logger.info(f"YFinance: Successfully retrieved {len(results)} company profiles")
            return results

        except Exception as e:
            logger.error(f"YFinance get_company_profile failed: {str(e)}")
            raise

    async def get_fund_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get fund holdings from YFinance

        Note: YFinance has limited ETF holdings data.
        This will return empty list and should fallback to FMP.
        """
        logger.warning(f"YFinance: Fund holdings not available for {symbol}, use FMP fallback")
        return []  # YFinance doesn't provide reliable holdings data

    async def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get options chain data from YFinance

        Returns options chain with expiration dates and contracts
        """
        try:
            ticker = await self._fetch_with_retry(yf.Ticker, symbol)

            if not ticker:
                logger.warning(f"YFinance: No ticker object for {symbol}")
                return {}

            loop = asyncio.get_event_loop()

            # Get available expiration dates
            expirations = await loop.run_in_executor(None, lambda: ticker.options)

            if not expirations:
                logger.warning(f"YFinance: No options available for {symbol}")
                return {}

            options_data = {
                'symbol': symbol,
                'expirations': expirations,
                'calls': {},
                'puts': {}
            }

            # Get options data for the nearest expiration (as an example)
            # In production, you might want to get multiple or specific expirations
            nearest_expiry = expirations[0]

            opt_chain = await loop.run_in_executor(
                None,
                lambda: ticker.option_chain(nearest_expiry)
            )

            # Convert calls DataFrame to dict
            if not opt_chain.calls.empty:
                calls_data = []
                for _, row in opt_chain.calls.iterrows():
                    calls_data.append({
                        'strike': float(row['strike']),
                        'last_price': float(row['lastPrice']) if 'lastPrice' in row else None,
                        'bid': float(row['bid']) if 'bid' in row else None,
                        'ask': float(row['ask']) if 'ask' in row else None,
                        'volume': int(row['volume']) if 'volume' in row and row['volume'] else 0,
                        'open_interest': int(row['openInterest']) if 'openInterest' in row and row['openInterest'] else 0,
                        'implied_volatility': float(row['impliedVolatility']) if 'impliedVolatility' in row else None
                    })
                options_data['calls'][nearest_expiry] = calls_data

            # Convert puts DataFrame to dict
            if not opt_chain.puts.empty:
                puts_data = []
                for _, row in opt_chain.puts.iterrows():
                    puts_data.append({
                        'strike': float(row['strike']),
                        'last_price': float(row['lastPrice']) if 'lastPrice' in row else None,
                        'bid': float(row['bid']) if 'bid' in row else None,
                        'ask': float(row['ask']) if 'ask' in row else None,
                        'volume': int(row['volume']) if 'volume' in row and row['volume'] else 0,
                        'open_interest': int(row['openInterest']) if 'openInterest' in row and row['openInterest'] else 0,
                        'implied_volatility': float(row['impliedVolatility']) if 'impliedVolatility' in row else None
                    })
                options_data['puts'][nearest_expiry] = puts_data

            logger.info(f"YFinance: Retrieved options chain for {symbol} with {len(expirations)} expirations")
            return options_data

        except Exception as e:
            logger.error(f"YFinance get_options_chain failed for {symbol}: {str(e)}")
            return {}

    async def validate_api_key(self) -> bool:
        """
        Validate that YFinance is working

        YFinance doesn't need an API key, so we just test connectivity
        """
        try:
            # Test with a simple request (Apple stock)
            result = await self.get_stock_prices(['AAPL'])
            return bool(result and 'AAPL' in result)
        except Exception as e:
            logger.error(f"YFinance validation failed: {str(e)}")
            return False

    async def close(self):
        """Close any resources (not needed for yfinance)"""
        pass