"""
Async-safe Market Data Service - Fixes blocking I/O issues (Section 1.6.7)
Wraps synchronous API calls in thread pool executor to prevent blocking
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from functools import partial
import yfinance as yf
from polygon import RESTClient

from app.config import settings
from app.core.logging import get_logger
from app.services.rate_limiter import polygon_rate_limiter

logger = get_logger(__name__)

# Thread pool for running blocking I/O
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="market_data")


class AsyncMarketDataService:
    """
    Market data service with proper async handling of synchronous API calls.
    Prevents blocking the FastAPI event loop.
    """
    
    def __init__(self):
        self.polygon_client = RESTClient(api_key=settings.POLYGON_API_KEY)
        self._cache: Dict[str, Any] = {}
        self._loop = None
    
    def _ensure_loop(self):
        """Ensure we have a reference to the event loop."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop
    
    # Synchronous API wrapper functions (run in thread pool)
    
    def _fetch_polygon_aggs_sync(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> Any:
        """Synchronous wrapper for Polygon aggregates API."""
        return self.polygon_client.get_aggs(
            ticker=symbol.upper(),
            multiplier=1,
            timespan="day",
            from_=start_date,
            to=end_date,
            adjusted=True,
            sort="asc",
            limit=50000,
            raw=True
        )
    
    def _fetch_polygon_last_trade_sync(self, symbol: str) -> Any:
        """Synchronous wrapper for Polygon last trade API."""
        return self.polygon_client.get_last_trade(ticker=symbol.upper())
    
    def _fetch_polygon_options_sync(
        self, 
        symbol: str, 
        expiration_date: Optional[str] = None
    ) -> Any:
        """Synchronous wrapper for Polygon options contracts API."""
        if expiration_date:
            return self.polygon_client.list_options_contracts(
                underlying_ticker=symbol.upper(),
                expiration_date=expiration_date,
                limit=1000
            )
        else:
            return self.polygon_client.list_options_contracts(
                underlying_ticker=symbol.upper(),
                limit=1000
            )
    
    def _fetch_yfinance_info_sync(self, symbol: str) -> Dict[str, Any]:
        """Synchronous wrapper for YFinance ticker info."""
        ticker = yf.Ticker(symbol.upper())
        return ticker.info
    
    # Async methods that properly wrap synchronous calls
    
    async def fetch_stock_prices(
        self,
        symbols: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch stock price data from Polygon.io without blocking the event loop.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dictionary with symbol as key and list of price data as value
        """
        logger.info(f"Fetching stock prices for {len(symbols)} symbols (async-safe)")
        
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()
        
        loop = self._ensure_loop()
        results = {}
        
        for symbol in symbols:
            try:
                # Apply rate limiting
                await polygon_rate_limiter.acquire()
                
                # Run blocking API call in thread pool
                response = await loop.run_in_executor(
                    _executor,
                    partial(
                        self._fetch_polygon_aggs_sync,
                        symbol,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d")
                    )
                )
                
                # Process response
                price_data = []
                if response and 'results' in response:
                    for bar in response['results']:
                        price_data.append({
                            'symbol': symbol.upper(),
                            'date': datetime.fromtimestamp(bar['t'] / 1000).date(),
                            'open': Decimal(str(bar['o'])),
                            'high': Decimal(str(bar['h'])),
                            'low': Decimal(str(bar['l'])),
                            'close': Decimal(str(bar['c'])),
                            'volume': bar['v'],
                            'data_source': 'polygon'
                        })
                
                results[symbol] = price_data
                logger.info(f"Fetched {len(price_data)} price records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                results[symbol] = []
        
        return results
    
    async def fetch_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch current/latest prices without blocking the event loop.
        
        Args:
            symbols: List of symbols to fetch prices for
            
        Returns:
            Dictionary with symbol as key and current price as value
        """
        logger.info(f"Fetching current prices for {len(symbols)} symbols (async-safe)")
        
        loop = self._ensure_loop()
        current_prices = {}
        
        for symbol in symbols:
            try:
                # Apply rate limiting
                await polygon_rate_limiter.acquire()
                
                # Run blocking API call in thread pool
                last_trade = await loop.run_in_executor(
                    _executor,
                    partial(self._fetch_polygon_last_trade_sync, symbol)
                )
                
                if last_trade and hasattr(last_trade, 'price'):
                    current_prices[symbol] = Decimal(str(last_trade.price))
                    logger.debug(f"Current price for {symbol}: {last_trade.price}")
                else:
                    current_prices[symbol] = None
                    
            except Exception as e:
                logger.error(f"Error fetching current price for {symbol}: {str(e)}")
                current_prices[symbol] = None
        
        return current_prices
    
    async def fetch_gics_data(self, symbols: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Fetch GICS sector/industry data without blocking the event loop.
        
        Args:
            symbols: List of symbols to fetch GICS data for
            
        Returns:
            Dictionary with symbol as key and sector/industry info as value
        """
        logger.info(f"Fetching GICS data for {len(symbols)} symbols (async-safe)")
        
        loop = self._ensure_loop()
        gics_data = {}
        
        # Process symbols in batches to avoid overwhelming YFinance
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            
            # Create tasks for batch
            tasks = []
            for symbol in batch:
                task = loop.run_in_executor(
                    _executor,
                    partial(self._fetch_yfinance_info_sync, symbol)
                )
                tasks.append((symbol, task))
            
            # Wait for batch to complete
            for symbol, task in tasks:
                try:
                    info = await task
                    gics_data[symbol] = {
                        'sector': info.get('sector'),
                        'industry': info.get('industry')
                    }
                    logger.debug(f"GICS data for {symbol}: {gics_data[symbol]}")
                except Exception as e:
                    logger.error(f"Error fetching GICS data for {symbol}: {str(e)}")
                    gics_data[symbol] = {'sector': None, 'industry': None}
            
            # Small delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        return gics_data
    
    async def fetch_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch options chain data without blocking the event loop.
        
        Args:
            symbol: Underlying symbol
            expiration_date: Specific expiration date (optional)
            
        Returns:
            List of option contract data
        """
        logger.info(f"Fetching options chain for {symbol} (async-safe)")
        
        loop = self._ensure_loop()
        
        try:
            # Apply rate limiting
            await polygon_rate_limiter.acquire()
            
            # Prepare expiration date string if provided
            exp_date_str = expiration_date.strftime("%Y-%m-%d") if expiration_date else None
            
            # Run blocking API call in thread pool
            contracts = await loop.run_in_executor(
                _executor,
                partial(self._fetch_polygon_options_sync, symbol, exp_date_str)
            )
            
            # Process contracts
            options_data = []
            if contracts:
                for contract in contracts:
                    if hasattr(contract, 'ticker'):
                        options_data.append({
                            'ticker': contract.ticker,
                            'underlying': symbol.upper(),
                            'strike': float(contract.strike_price),
                            'expiration': contract.expiration_date,
                            'type': contract.contract_type,
                            'shares_per_contract': getattr(contract, 'shares_per_contract', 100)
                        })
            
            logger.info(f"Fetched {len(options_data)} option contracts for {symbol}")
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {str(e)}")
            return []
    
    async def cleanup(self):
        """Cleanup resources when shutting down."""
        # The executor will be cleaned up automatically, but we can be explicit
        pass


# Create singleton instance with proper async handling
async_market_data_service = AsyncMarketDataService()