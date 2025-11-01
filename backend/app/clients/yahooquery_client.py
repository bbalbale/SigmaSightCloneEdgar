"""
YahooQuery API client implementation for historical prices
Specialized for mutual funds and symbols that YFinance fails on
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from yahooquery import Ticker

from app.clients.base import MarketDataProvider

logger = logging.getLogger(__name__)


class YahooQueryClient(MarketDataProvider):
    """YahooQuery API client for historical prices"""

    def __init__(self, api_key: str = None, timeout: int = 30, max_retries: int = 3):
        # YahooQuery doesn't need an API key
        # Don't call super().__init__() to avoid conflict with provider_name property
        self.api_key = api_key or "not_required"
        self.timeout = timeout
        self.max_retries = max_retries

    async def get_historical_prices(self, symbol: str, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get historical prices for a symbol using YahooQuery

        Args:
            symbol: Stock/fund symbol
            days: Number of days of historical data

        Returns:
            List of price dictionaries with date, open, high, low, close, volume
        """
        try:
            # YahooQuery is synchronous, run in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_historical_sync,
                symbol,
                days
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error for {symbol}: {str(e)}")
            return []

    def _fetch_historical_sync(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """
        Synchronous helper to fetch historical prices

        Args:
            symbol: Stock/fund symbol
            days: Number of days of historical data

        Returns:
            List of price dictionaries
        """
        try:
            ticker = Ticker(symbol)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Fetch historical data
            history = ticker.history(start=start_date, end=end_date)

            if history is None or history.empty:
                logger.warning(f"YahooQuery: No data returned for {symbol}")
                return []

            # Convert DataFrame to our standard format
            price_records = []

            for idx, row in history.iterrows():
                # Handle multi-index (symbol, date) or single-index (date)
                if isinstance(idx, tuple):
                    _, date_value = idx
                else:
                    date_value = idx

                # Convert date_value to date object
                if isinstance(date_value, datetime):
                    date_obj = date_value.date()
                elif isinstance(date_value, date):
                    date_obj = date_value
                else:
                    # Try parsing as string
                    date_obj = datetime.fromisoformat(str(date_value)).date()

                price_records.append({
                    'symbol': symbol.upper(),
                    'date': date_obj,
                    'open': Decimal(str(row['open'])),
                    'high': Decimal(str(row['high'])),
                    'low': Decimal(str(row['low'])),
                    'close': Decimal(str(row['close'])),
                    'volume': int(row['volume']),
                    'data_source': 'yahooquery'
                })

            logger.info(f"YahooQuery: Retrieved {len(price_records)} records for {symbol}")
            return price_records

        except Exception as e:
            logger.error(f"YahooQuery sync fetch error for {symbol}: {str(e)}")
            return []

    async def get_stock_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current stock prices from YahooQuery

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary with symbol as key and price data as value
        """
        results = {}

        for symbol in symbols:
            try:
                # Run in executor since YahooQuery is synchronous
                loop = asyncio.get_event_loop()
                price_data = await loop.run_in_executor(
                    None,
                    self._fetch_current_price_sync,
                    symbol
                )

                if price_data:
                    results[symbol] = price_data

            except Exception as e:
                logger.error(f"YahooQuery error fetching current price for {symbol}: {str(e)}")

        return results

    def _fetch_current_price_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous helper to fetch current price

        Args:
            symbol: Stock/fund symbol

        Returns:
            Price data dictionary or None
        """
        try:
            ticker = Ticker(symbol)
            quote = ticker.price

            if quote is None or symbol not in quote:
                logger.warning(f"YahooQuery: No quote data for {symbol}")
                return None

            symbol_quote = quote[symbol]

            # Extract price data
            current_price = symbol_quote.get('regularMarketPrice')
            if current_price is None:
                return None

            return {
                'price': Decimal(str(current_price)),
                'change': Decimal(str(symbol_quote.get('regularMarketChange', 0))),
                'change_percent': Decimal(str(symbol_quote.get('regularMarketChangePercent', 0))),
                'volume': int(symbol_quote.get('regularMarketVolume', 0)),
                'timestamp': datetime.now(),
                'provider': 'YahooQueryClient'
            }

        except Exception as e:
            logger.error(f"YahooQuery sync price fetch error for {symbol}: {str(e)}")
            return None

    async def get_fund_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get fund holdings from YahooQuery

        Args:
            symbol: Fund symbol

        Returns:
            List of fund holdings
        """
        try:
            # Run in executor since YahooQuery is synchronous
            loop = asyncio.get_event_loop()
            holdings = await loop.run_in_executor(
                None,
                self._fetch_fund_holdings_sync,
                symbol
            )
            return holdings

        except Exception as e:
            logger.error(f"YahooQuery error fetching fund holdings for {symbol}: {str(e)}")
            return []

    def _fetch_fund_holdings_sync(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Synchronous helper to fetch fund holdings

        Args:
            symbol: Fund symbol

        Returns:
            List of holdings
        """
        try:
            ticker = Ticker(symbol)
            holdings_data = ticker.fund_holding_info

            if holdings_data is None or symbol not in holdings_data:
                logger.warning(f"YahooQuery: No fund holdings data for {symbol}")
                return []

            symbol_holdings = holdings_data[symbol]

            if 'holdings' not in symbol_holdings:
                logger.warning(f"YahooQuery: No holdings key in data for {symbol}")
                return []

            holdings = []
            for holding in symbol_holdings['holdings']:
                holdings.append({
                    'symbol': holding.get('symbol', ''),
                    'name': holding.get('holdingName', ''),
                    'weight': Decimal(str(holding.get('holdingPercent', 0))),
                    'shares': None,  # Not provided by YahooQuery
                    'market_value': None,  # Not provided by YahooQuery
                    'provider': 'YahooQueryClient'
                })

            logger.info(f"YahooQuery: Retrieved {len(holdings)} holdings for {symbol}")
            return holdings

        except Exception as e:
            logger.error(f"YahooQuery sync fund holdings fetch error for {symbol}: {str(e)}")
            return []

    async def get_income_statement(self, symbol: str, frequency: str = 'q', years: int = 4) -> Dict[str, Any]:
        """
        Get income statement data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly), 'a' (annual), or 'ttm' (trailing twelve months)
            years: Number of years of historical data (default: 4)

        Returns:
            Dictionary with income statement data by period
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_income_statement_sync,
                symbol,
                frequency,
                years
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching income statement for {symbol}: {str(e)}")
            return {}

    def _fetch_income_statement_sync(self, symbol: str, frequency: str, years: int) -> Dict[str, Any]:
        """Synchronous helper to fetch income statement"""
        try:
            ticker = Ticker(symbol)
            income_stmt = ticker.income_statement(frequency=frequency)

            if income_stmt is None or isinstance(income_stmt, str):
                logger.warning(f"YahooQuery: No income statement data for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved income statement for {symbol} (frequency={frequency})")
            # Wrap DataFrame in dict with symbol as key for consistency
            return {symbol: income_stmt}

        except Exception as e:
            logger.error(f"YahooQuery sync income statement fetch error for {symbol}: {str(e)}")
            return {}

    async def get_balance_sheet(self, symbol: str, frequency: str = 'q', years: int = 4) -> Dict[str, Any]:
        """
        Get balance sheet data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly), 'a' (annual)
            years: Number of years of historical data (default: 4)

        Returns:
            Dictionary with balance sheet data by period
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_balance_sheet_sync,
                symbol,
                frequency,
                years
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching balance sheet for {symbol}: {str(e)}")
            return {}

    def _fetch_balance_sheet_sync(self, symbol: str, frequency: str, years: int) -> Dict[str, Any]:
        """Synchronous helper to fetch balance sheet"""
        try:
            ticker = Ticker(symbol)
            balance_sheet = ticker.balance_sheet(frequency=frequency)

            if balance_sheet is None or isinstance(balance_sheet, str):
                logger.warning(f"YahooQuery: No balance sheet data for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved balance sheet for {symbol} (frequency={frequency})")
            # Wrap DataFrame in dict with symbol as key for consistency
            return {symbol: balance_sheet}

        except Exception as e:
            logger.error(f"YahooQuery sync balance sheet fetch error for {symbol}: {str(e)}")
            return {}

    async def get_cash_flow(self, symbol: str, frequency: str = 'q', years: int = 4) -> Dict[str, Any]:
        """
        Get cash flow statement data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly), 'a' (annual)
            years: Number of years of historical data (default: 4)

        Returns:
            Dictionary with cash flow data by period
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_cash_flow_sync,
                symbol,
                frequency,
                years
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching cash flow for {symbol}: {str(e)}")
            return {}

    def _fetch_cash_flow_sync(self, symbol: str, frequency: str, years: int) -> Dict[str, Any]:
        """Synchronous helper to fetch cash flow"""
        try:
            ticker = Ticker(symbol)
            cash_flow = ticker.cash_flow(frequency=frequency)

            if cash_flow is None or isinstance(cash_flow, str):
                logger.warning(f"YahooQuery: No cash flow data for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved cash flow for {symbol} (frequency={frequency})")
            return cash_flow

        except Exception as e:
            logger.error(f"YahooQuery sync cash flow fetch error for {symbol}: {str(e)}")
            return {}

    async def get_all_financials(self, symbol: str, frequency: str = 'q', years: int = 4) -> Dict[str, Any]:
        """
        Get all financial statements (income, balance sheet, cash flow) in one call

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly), 'a' (annual)
            years: Number of years of historical data (default: 4)

        Returns:
            Dictionary with all three financial statements
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_all_financials_sync,
                symbol,
                frequency,
                years
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching all financials for {symbol}: {str(e)}")
            return {}

    def _fetch_all_financials_sync(self, symbol: str, frequency: str, years: int) -> Dict[str, Any]:
        """Synchronous helper to fetch all financial statements"""
        try:
            ticker = Ticker(symbol)

            # Fetch all three statements
            income_stmt = ticker.income_statement(frequency=frequency)
            balance_sheet = ticker.balance_sheet(frequency=frequency)
            cash_flow = ticker.cash_flow(frequency=frequency)

            result = {
                'income_statement': income_stmt if not isinstance(income_stmt, str) else {},
                'balance_sheet': balance_sheet if not isinstance(balance_sheet, str) else {},
                'cash_flow': cash_flow if not isinstance(cash_flow, str) else {}
            }

            logger.info(f"YahooQuery: Retrieved all financials for {symbol} (frequency={frequency})")
            return result

        except Exception as e:
            logger.error(f"YahooQuery sync all financials fetch error for {symbol}: {str(e)}")
            return {}

    async def get_analyst_estimates(self, symbol: str) -> Dict[str, Any]:
        """
        Get analyst revenue and EPS estimates for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with analyst estimates (current Q, next Q, current Y, next Y)
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_analyst_estimates_sync,
                symbol
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching analyst estimates for {symbol}: {str(e)}")
            return {}

    def _fetch_analyst_estimates_sync(self, symbol: str) -> Dict[str, Any]:
        """Synchronous helper to fetch analyst estimates"""
        try:
            ticker = Ticker(symbol)
            earnings_trend = ticker.earnings_trend

            if earnings_trend is None or isinstance(earnings_trend, str):
                logger.warning(f"YahooQuery: No analyst estimates for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved analyst estimates for {symbol}")
            return earnings_trend

        except Exception as e:
            logger.error(f"YahooQuery sync analyst estimates fetch error for {symbol}: {str(e)}")
            return {}

    async def get_price_targets(self, symbol: str) -> Dict[str, Any]:
        """
        Get analyst price targets and recommendations for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with price targets (low, mean, high) and recommendations
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_price_targets_sync,
                symbol
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching price targets for {symbol}: {str(e)}")
            return {}

    def _fetch_price_targets_sync(self, symbol: str) -> Dict[str, Any]:
        """Synchronous helper to fetch price targets"""
        try:
            ticker = Ticker(symbol)
            financial_data = ticker.financial_data

            if financial_data is None or isinstance(financial_data, str):
                logger.warning(f"YahooQuery: No price target data for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved price targets for {symbol}")
            return financial_data

        except Exception as e:
            logger.error(f"YahooQuery sync price targets fetch error for {symbol}: {str(e)}")
            return {}

    async def get_next_earnings(self, symbol: str) -> Dict[str, Any]:
        """
        Get next earnings date and estimates for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with next earnings date and expected revenue/EPS
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_next_earnings_sync,
                symbol
            )
            return result

        except Exception as e:
            logger.error(f"YahooQuery error fetching next earnings for {symbol}: {str(e)}")
            return {}

    def _fetch_next_earnings_sync(self, symbol: str) -> Dict[str, Any]:
        """Synchronous helper to fetch next earnings"""
        try:
            ticker = Ticker(symbol)
            calendar_events = ticker.calendar_events

            if calendar_events is None or isinstance(calendar_events, str):
                logger.warning(f"YahooQuery: No earnings calendar for {symbol}")
                return {}

            logger.info(f"YahooQuery: Retrieved earnings calendar for {symbol}")
            return calendar_events

        except Exception as e:
            logger.error(f"YahooQuery sync earnings calendar fetch error for {symbol}: {str(e)}")
            return {}

    async def close(self):
        """YahooQuery doesn't maintain persistent connections, nothing to close"""
        logger.info("YahooQueryClient: No cleanup needed")

    @property
    def provider_name(self) -> str:
        """Return provider name for logging"""
        return "YahooQuery"
