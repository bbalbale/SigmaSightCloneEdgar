"""
Market Data Service - Handles external market data APIs (Polygon.io, YFinance, FMP, TradeFeeds)
Updated for Section 1.4.9 - Hybrid provider approach with mutual fund holdings support
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any
from app.core.datetime_utils import utc_now
from polygon import RESTClient
# import yfinance as yf  # Removed - using FMP primary architecture
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.market_data import MarketDataCache, CompanyProfile
from app.core.logging import get_logger
from app.services.rate_limiter import polygon_rate_limiter, ExponentialBackoff
from app.clients import market_data_factory, DataType
from app.services.yahooquery_profile_fetcher import fetch_company_profiles as fetch_profiles_yahooquery
from app.services.symbol_utils import (
    normalize_symbol,
    should_skip_symbol,
    to_provider_symbol,
)

logger = get_logger(__name__)

class MarketDataService:
    """Service for fetching and managing market data from external APIs"""

    def __init__(self):
        self.polygon_client = RESTClient(api_key=settings.POLYGON_API_KEY)
        self._cache: Dict[str, Any] = {}
        # Initialize the market data factory
        market_data_factory.initialize()

    def _filter_synthetic_symbols(self, symbols: List[str]) -> List[str]:
        """Filter out synthetic/placeholder symbols that don't have market data"""
        filtered: List[str] = []
        skipped: List[str] = []

        for symbol in symbols:
            upper = normalize_symbol(symbol)
            if not upper:
                continue

            skip, reason = should_skip_symbol(upper)
            if skip:
                skipped.append(f"{upper} ({reason})")
            else:
                filtered.append(upper)

        if skipped:
            logger.info("Skipping %d synthetic/option symbols: %s", len(skipped), ", ".join(skipped))
        return filtered
    
    # New hybrid provider methods (Section 1.4.9)
    
    async def fetch_historical_data_hybrid(
        self,
        symbols: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical stock price data using unified fallback chain

        **Unified Fallback Chain (all symbols):**
        1. YFinance BATCH (primary) - fetches multiple symbols at once for efficiency
        2. YahooQuery (secondary)
        3. Polygon (tertiary)
        4. FMP (last resort)

        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            Dictionary with symbol as key and list of price data as value
        """
        logger.info(f"Fetching historical data for {len(symbols)} symbols (unified fallback chain)")

        # Filter out synthetic symbols
        symbols = self._filter_synthetic_symbols(symbols)
        if not symbols:
            logger.info("No real symbols to fetch after filtering synthetics")
            return {}

        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()

        results = {}

        # Step 1: Try YFinance BATCH download for all symbols (much more efficient)
        logger.info(f"Step 1: Trying YFinance BATCH for {len(symbols)} symbols")
        yfinance_provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)

        if yfinance_provider and yfinance_provider.provider_name == "YFinance":
            try:
                # Convert symbols for provider
                fetch_symbols = [to_provider_symbol(s) for s in symbols]
                symbol_map = {to_provider_symbol(s): s for s in symbols}  # Map back to original

                # Use batch download method
                batch_results = await yfinance_provider.get_historical_prices_batch(
                    symbols=fetch_symbols,
                    start_date=start_date,
                    end_date=end_date,
                    batch_size=50  # Fetch 50 symbols per yfinance.download() call
                )

                # Convert results to expected format (close only)
                for fetch_symbol, historical_data in batch_results.items():
                    original_symbol = symbol_map.get(fetch_symbol, fetch_symbol)
                    if historical_data:
                        price_records = []
                        for day_data in historical_data:
                            price_records.append({
                                'symbol': original_symbol.upper(),
                                'date': day_data['date'],
                                'close': day_data['close'],
                                'volume': day_data.get('volume', 0),
                                'data_source': 'yfinance'
                            })
                        results[original_symbol] = price_records

                logger.info(f"YFinance BATCH: Retrieved data for {len(results)}/{len(symbols)} symbols")

            except Exception as e:
                logger.error(f"YFinance BATCH failed: {e}")

        # Track failures
        failed_symbols = [s for s in symbols if not results.get(s)]
        logger.info(f"YFinance: {len(symbols) - len(failed_symbols)}/{len(symbols)} succeeded, {len(failed_symbols)} failed")

        # Step 2: Try YahooQuery for failed symbols
        if failed_symbols:
            logger.info(f"Step 2: Trying YahooQuery for {len(failed_symbols)} failed symbols")
            yahooquery_provider = market_data_factory.get_client('YahooQuery')

            if yahooquery_provider:
                for symbol in failed_symbols[:]:  # Use slice to allow removal during iteration
                    try:
                        historical_data = await yahooquery_provider.get_historical_prices(symbol, days=days_back)

                        if historical_data:
                            results[symbol] = historical_data
                            failed_symbols.remove(symbol)
                            logger.debug(f"YahooQuery: ✓ {symbol} ({len(historical_data)} records)")

                    except Exception as e:
                        logger.debug(f"YahooQuery: ✗ {symbol} - {str(e)}")

                logger.info(f"YahooQuery: {len([s for s in symbols if results.get(s)])}/{len(symbols)} total succeeded, {len(failed_symbols)} still failed")

        # Step 3: Try Polygon for remaining failed symbols
        if failed_symbols:
            logger.info(f"Step 3: Trying Polygon for {len(failed_symbols)} failed symbols")
            polygon_results = await self.fetch_stock_prices(failed_symbols, start_date, end_date)

            for symbol in failed_symbols[:]:
                if polygon_results.get(symbol):
                    results[symbol] = polygon_results[symbol]
                    failed_symbols.remove(symbol)
                    logger.debug(f"Polygon: ✓ {symbol} ({len(polygon_results[symbol])} records)")

            logger.info(f"Polygon: {len([s for s in symbols if results.get(s)])}/{len(symbols)} total succeeded, {len(failed_symbols)} still failed")

        # Step 4: Try FMP for remaining failed symbols (last resort)
        if failed_symbols:
            logger.info(f"Step 4: Trying FMP for {len(failed_symbols)} failed symbols (last resort)")
            fmp_provider = market_data_factory.get_client('FMP')

            if fmp_provider:
                for symbol in failed_symbols:
                    try:
                        historical_data = await fmp_provider.get_historical_prices(symbol, days=days_back)

                        if historical_data:
                            price_records = []
                            for day_data in historical_data:
                                date_value = day_data['date']
                                if isinstance(date_value, str):
                                    date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                                elif isinstance(date_value, date):
                                    date_obj = date_value
                                else:
                                    date_obj = datetime.fromisoformat(str(date_value)).date()

                                price_records.append({
                                    'symbol': symbol.upper(),
                                    'date': date_obj,
                                    'open': Decimal(str(day_data['open'])),
                                    'high': Decimal(str(day_data['high'])),
                                    'low': Decimal(str(day_data['low'])),
                                    'close': Decimal(str(day_data['close'])),
                                    'volume': day_data['volume'],
                                    'data_source': 'fmp'
                                })
                            results[symbol] = price_records
                            logger.debug(f"FMP: ✓ {symbol} ({len(price_records)} records)")

                    except Exception as e:
                        logger.debug(f"FMP: ✗ {symbol} - {str(e)}")

        # Final summary
        successful = len([s for s in symbols if results.get(s)])
        logger.info(f"Final: {successful}/{len(symbols)} symbols retrieved data successfully")

        return results

    async def fetch_stock_prices_hybrid(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current stock prices using hybrid provider approach
        
        Priority: FMP -> TradeFeeds -> Polygon (fallback)
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary with symbol as key and price data as value
        """
        logger.info(f"Fetching stock prices (hybrid) for {len(symbols)} symbols")
        
        # Try FMP first
        provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)
        if provider:
            try:
                result = await provider.get_stock_prices(symbols)
                if result:
                    logger.info(f"Successfully fetched {len(result)} stock prices from {provider.provider_name}")
                    return result
            except Exception as e:
                logger.error(f"Error fetching stock prices from {provider.provider_name}: {str(e)}")
        
        # Fallback to current Polygon implementation
        logger.warning("Falling back to Polygon for stock prices")
        current_prices = await self.fetch_current_prices(symbols)
        
        # Convert to hybrid format
        result = {}
        for symbol, price in current_prices.items():
            if price is not None:
                result[symbol] = {
                    'price': price,
                    'change': Decimal('0'),  # Not available from current implementation
                    'change_percent': Decimal('0'),
                    'volume': 0,
                    'timestamp': utc_now(),
                    'provider': 'Polygon (fallback)'
                }
        
        return result
    
    async def fetch_mutual_fund_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch mutual fund holdings using hybrid provider approach
        
        Priority: FMP -> TradeFeeds
        
        Args:
            symbol: Mutual fund symbol (e.g., 'FXNAX')
            
        Returns:
            List of fund holdings
        """
        logger.info(f"Fetching mutual fund holdings for {symbol}")
        
        provider = market_data_factory.get_provider_for_data_type(DataType.FUNDS)
        if provider:
            try:
                holdings = await provider.get_fund_holdings(symbol)
                logger.info(f"Successfully fetched {len(holdings)} holdings for {symbol} from {provider.provider_name}")
                return holdings
            except Exception as e:
                logger.error(f"Error fetching fund holdings for {symbol} from {provider.provider_name}: {str(e)}")
                raise
        else:
            logger.error("No provider available for mutual fund holdings")
            raise Exception("No mutual fund holdings provider configured")
    
    async def fetch_etf_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch ETF holdings using hybrid provider approach
        
        Uses same endpoint as mutual funds for most providers
        
        Args:
            symbol: ETF symbol (e.g., 'VTI', 'SPY')
            
        Returns:
            List of ETF holdings
        """
        logger.info(f"Fetching ETF holdings for {symbol}")
        return await self.fetch_mutual_fund_holdings(symbol)  # Same endpoint for most providers
    
    async def validate_fund_holdings(self, holdings: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """
        Validate fund holdings data quality
        
        Args:
            holdings: List of holdings data
            symbol: Fund symbol for logging
            
        Returns:
            Validation results
        """
        total_weight = sum(h.get('weight', 0) for h in holdings)
        complete_holdings = [h for h in holdings if h.get('symbol') and h.get('name')]
        
        validation = {
            'symbol': symbol,
            'total_holdings': len(holdings),
            'complete_holdings': len(complete_holdings),
            'total_weight': float(total_weight),
            'weight_percentage': float(total_weight * 100),
            'data_quality': 'good' if total_weight >= 0.9 else 'partial',
            'completeness': len(complete_holdings) / len(holdings) if holdings else 0
        }
        
        logger.info(f"Fund holdings validation for {symbol}: {validation['total_holdings']} holdings, "
                   f"{validation['weight_percentage']:.1f}% weight coverage, "
                   f"{validation['data_quality']} quality")
        
        return validation
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status of all configured market data providers
        
        Returns:
            Dictionary with provider status information
        """
        logger.info("Checking market data provider status")
        
        # Get available providers
        providers = market_data_factory.get_available_providers()
        
        # Validate API keys
        validation_results = await market_data_factory.validate_all_providers()
        
        status = {
            'providers_configured': len(providers),
            'providers_active': sum(validation_results.values()),
            'provider_details': {}
        }
        
        for name, info in providers.items():
            status['provider_details'][name] = {
                **info,
                'api_key_valid': validation_results.get(name, False),
                'status': 'active' if validation_results.get(name, False) else 'inactive'
            }
        
        # Add configuration settings
        status['configuration'] = {
            'use_fmp_for_stocks': settings.USE_FMP_FOR_STOCKS,
            'use_fmp_for_funds': settings.USE_FMP_FOR_FUNDS,
            'polygon_available': bool(settings.POLYGON_API_KEY),
            'fmp_configured': bool(settings.FMP_API_KEY),
            'tradefeeds_configured': bool(settings.TRADEFEEDS_API_KEY)
        }
        
        logger.info(f"Provider status: {status['providers_active']}/{status['providers_configured']} active")
        return status
    
    # Legacy methods (maintained for backward compatibility)
    
    async def fetch_stock_prices(
        self, 
        symbols: List[str], 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch stock price data from Polygon.io
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dictionary with symbol as key and list of price data as value
        """
        logger.info(f"Fetching stock prices for {len(symbols)} symbols")
        
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()
            
        results = {}
        
        for symbol in symbols:
            try:
                # Apply rate limiting before API call
                await polygon_rate_limiter.acquire()
                
                # Get daily bars from Polygon with pagination support
                all_bars = []
                next_url = None
                page_count = 0
                
                while True:
                    page_count += 1
                    
                    if next_url:
                        # Fetch next page using pagination URL
                        await polygon_rate_limiter.acquire()
                        response = self.polygon_client._get_raw(next_url)
                    else:
                        # Initial request
                        response = self.polygon_client.get_aggs(
                            ticker=symbol.upper(),
                            multiplier=1,
                            timespan="day",
                            from_=start_date.strftime("%Y-%m-%d"),
                            to=end_date.strftime("%Y-%m-%d"),
                            adjusted=True,
                            sort="asc",
                            limit=50000,
                            raw=True  # Get raw response to check for pagination
                        )
                    
                    # Extract bars from response
                    if hasattr(response, 'results'):
                        bars = response.results
                    elif isinstance(response, dict) and 'results' in response:
                        bars = response['results']
                    else:
                        # Fallback for non-paginated response
                        bars = response
                        all_bars.extend(bars)
                        break
                    
                    all_bars.extend(bars)
                    
                    # Check for pagination
                    if hasattr(response, 'next_url') and response.next_url:
                        next_url = response.next_url
                        logger.debug(f"Fetching page {page_count + 1} for {symbol}")
                    elif isinstance(response, dict) and response.get('next_url'):
                        next_url = response['next_url']
                        logger.debug(f"Fetching page {page_count + 1} for {symbol}")
                    else:
                        break
                
                # Process all bars
                price_data = []
                for bar in all_bars:
                    # Handle both object and dict formats
                    if hasattr(bar, 'timestamp'):
                        timestamp = bar.timestamp
                        open_price = bar.open
                        high_price = bar.high
                        low_price = bar.low
                        close_price = bar.close
                        volume = bar.volume
                    else:
                        timestamp = bar['t']
                        open_price = bar['o']
                        high_price = bar['h']
                        low_price = bar['l']
                        close_price = bar['c']
                        volume = bar['v']
                    
                    price_data.append({
                        'symbol': symbol.upper(),
                        'date': datetime.fromtimestamp(timestamp / 1000).date(),
                        'open': Decimal(str(open_price)),
                        'high': Decimal(str(high_price)),
                        'low': Decimal(str(low_price)),
                        'close': Decimal(str(close_price)),
                        'volume': volume,
                        'data_source': 'polygon'
                    })
                
                results[symbol] = price_data
                logger.info(f"Fetched {len(price_data)} price records for {symbol} across {page_count} page(s)")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                results[symbol] = []
        
        return results
    
    async def fetch_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch current/latest prices for symbols
        
        Args:
            symbols: List of symbols to fetch prices for
            
        Returns:
            Dictionary with symbol as key and current price as value
        """
        logger.info(f"Fetching current prices for {len(symbols)} symbols")
        current_prices = {}
        
        for symbol in symbols:
            try:
                # Apply rate limiting before API call
                await polygon_rate_limiter.acquire()
                
                # Get last trade from Polygon
                last_trade = self.polygon_client.get_last_trade(ticker=symbol.upper())
                if last_trade:
                    current_prices[symbol] = Decimal(str(last_trade.price))
                    logger.debug(f"Current price for {symbol}: {last_trade.price}")
                
            except Exception as e:
                logger.error(f"Error fetching current price for {symbol}: {str(e)}")
                # Fallback to last cached price if available
                current_prices[symbol] = None
        
        return current_prices
    
    async def fetch_gics_data(self, symbols: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Fetch GICS sector/industry data 
        
        NOTE: YFinance removed for FMP-primary architecture. 
        GICS data temporarily disabled until FMP coverage improves.
        
        Args:
            symbols: List of symbols to fetch GICS data for
            
        Returns:
            Dictionary with symbol as key and sector/industry info as value
        """
        logger.warning(f"GICS data temporarily disabled - YFinance removed for FMP migration")
        logger.info(f"Returning empty GICS data for {len(symbols)} symbols")
        
        # Return empty GICS data - system handles missing data gracefully
        gics_data = {}
        for symbol in symbols:
            gics_data[symbol] = {'sector': None, 'industry': None}
        
        return gics_data
    
    async def fetch_options_chain(
        self, 
        symbol: str, 
        expiration_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch options chain data from Polygon.io
        
        Args:
            symbol: Underlying symbol
            expiration_date: Specific expiration date (optional)
            
        Returns:
            List of option contract data
        """
        logger.info(f"Fetching options chain for {symbol}")
        
        try:
            # Apply rate limiting before API call
            await polygon_rate_limiter.acquire()
            
            # Get options contracts with pagination support
            all_contracts = []
            next_url = None
            page_count = 0
            
            while True:
                page_count += 1
                
                if next_url:
                    # Fetch next page
                    await polygon_rate_limiter.acquire()
                    response = self.polygon_client._get_raw(next_url)
                    if isinstance(response, dict) and 'results' in response:
                        contracts = response['results']
                        next_url = response.get('next_url')
                    else:
                        break
                else:
                    # Initial request
                    if expiration_date:
                        exp_date_str = expiration_date.strftime("%Y-%m-%d")
                        contracts = self.polygon_client.list_options_contracts(
                            underlying_ticker=symbol.upper(),
                            expiration_date=exp_date_str,
                            limit=1000
                        )
                    else:
                        contracts = self.polygon_client.list_options_contracts(
                            underlying_ticker=symbol.upper(),
                            limit=1000
                        )
                    
                    # Check if this is a paginated response
                    if hasattr(contracts, '__iter__'):
                        all_contracts.extend(contracts)
                        break  # No pagination in current response format
                
                all_contracts.extend(contracts)
                
                if not next_url:
                    break
                
                logger.debug(f"Fetching page {page_count + 1} of options contracts for {symbol}")
            
            options_data = []
            for contract in all_contracts:
                options_data.append({
                    'ticker': contract.ticker,
                    'underlying_ticker': contract.underlying_ticker,
                    'expiration_date': datetime.strptime(contract.expiration_date, "%Y-%m-%d").date(),
                    'strike_price': Decimal(str(contract.strike_price)),
                    'contract_type': contract.contract_type,  # 'call' or 'put'
                    'exercise_style': getattr(contract, 'exercise_style', 'american'),
                })
            
            logger.info(f"Fetched {len(options_data)} option contracts for {symbol} across {page_count} page(s)")
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {str(e)}")
            return []
    
    async def update_market_data_cache(
        self, 
        db: AsyncSession, 
        symbols: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_gics: bool = False  # Fix 3: Default to False for performance
    ) -> Dict[str, int]:
        """
        Update market data cache with latest price and GICS data
        
        ENHANCED BEHAVIOR (6.1 Implementation):
        - Preserves existing historical data (no overwriting)
        - Only inserts new records that don't exist
        - Accumulates history over time
        - CHECKS CACHE FIRST to avoid unnecessary API calls
        - ONLY FETCHES EOD DATA after 4:05 PM ET (new!)
        
        Args:
            db: Database session
            symbols: List of symbols to update
            start_date: Start date for historical data
            end_date: End date for historical data
            include_gics: Whether to fetch GICS sector/industry data
            
        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating market data cache for {len(symbols)} symbols")
        
        # Check if we should fetch today's data based on time
        from pytz import timezone
        et_tz = timezone('US/Eastern')
        current_time_et = datetime.now(et_tz)
        market_close_time = current_time_et.replace(hour=16, minute=5, second=0, microsecond=0)  # 4:05 PM ET
        
        # If it's before 4:05 PM ET and we're trying to fetch today's data, skip today
        skip_today = False
        if current_time_et < market_close_time:
            skip_today = True
            logger.info(f"⏰ Current time ({current_time_et.strftime('%H:%M')} ET) is before market close (16:05 ET)")
            logger.info("  Skipping today's data fetch - will use yesterday's prices")
        
        # First, check what data we already have cached
        symbols_needing_data = []
        cached_count = 0
        
        for symbol in symbols:
            # Get cached dates for this symbol
            cached_dates = await self._get_cached_dates(db, symbol)
            
            # Generate list of dates we need
            current = start_date if start_date else date.today() - timedelta(days=90)
            # If it's before market close, don't try to fetch today's data
            end = end_date if end_date else (date.today() - timedelta(days=1) if skip_today else date.today())
            needed_dates = set()
            
            while current <= end:
                # Skip weekends
                if current.weekday() < 5:  # Monday=0, Friday=4
                    needed_dates.add(current)
                current += timedelta(days=1)
            
            # Find missing dates
            missing_dates = needed_dates - cached_dates
            
            if missing_dates:
                symbols_needing_data.append(symbol)
                if skip_today:
                    logger.debug(f"{symbol}: Missing {len(missing_dates)} days of data (excluding today - market still open)")
                else:
                    logger.debug(f"{symbol}: Missing {len(missing_dates)} days of data")
            else:
                cached_count += 1
                if skip_today:
                    logger.debug(f"{symbol}: All data cached through yesterday (today's data deferred until after market close)")
                else:
                    logger.debug(f"{symbol}: All data already cached")
        
        if skip_today:
            logger.info(f"Cache check (pre-market close): {cached_count}/{len(symbols)} symbols have data through yesterday, {len(symbols_needing_data)} need historical updates")
        else:
            logger.info(f"Cache check: {cached_count}/{len(symbols)} symbols have complete data, {len(symbols_needing_data)} need updates")
        
        # Only fetch data for symbols that need it
        if not symbols_needing_data:
            logger.info("All symbols have complete cached data, skipping API calls")
            return {
                'symbols_processed': len(symbols),
                'symbols_updated': 0,
                'total_records_attempted': 0,
                'records_inserted': 0,
                'records_skipped': 0,
                'api_calls_saved': len(symbols)
            }
        
        # Fetch price data only for symbols needing updates
        price_data = await self.fetch_historical_data_hybrid(symbols_needing_data, start_date, end_date)
        
        # Fetch GICS data if requested
        gics_data = {}
        if include_gics:
            gics_data = await self.fetch_gics_data(symbols)
        
        total_records = 0
        updated_symbols = 0
        inserted_records = 0
        skipped_records = 0
        
        for symbol, prices in price_data.items():
            if not prices:
                continue
                
            # Get GICS data for this symbol
            symbol_gics = gics_data.get(symbol, {})
            
            # Prepare records for INSERT (not UPSERT)
            records_to_insert = []
            for price_record in prices:
                record = {
                    **price_record,
                    'sector': symbol_gics.get('sector'),
                    'industry': symbol_gics.get('industry')
                }
                records_to_insert.append(record)
            
            if records_to_insert:
                # CRITICAL CHANGE: Use INSERT with ON CONFLICT DO NOTHING
                # This preserves existing historical data instead of overwriting it
                stmt = pg_insert(MarketDataCache).values(records_to_insert)
                stmt = stmt.on_conflict_do_nothing(  # <-- KEY CHANGE from on_conflict_do_update
                    constraint='uq_market_data_cache_symbol_date'
                )
                
                result = await db.execute(stmt)
                inserted = result.rowcount  # Number of rows actually inserted
                inserted_records += inserted
                skipped_records += len(records_to_insert) - inserted
                
                total_records += len(records_to_insert)
                if inserted > 0:
                    updated_symbols += 1
        
        await db.commit()
        
        stats = {
            'symbols_processed': len(symbols),
            'symbols_updated': updated_symbols,
            'total_records_attempted': total_records,
            'records_inserted': inserted_records,
            'records_skipped': skipped_records,  # Already existed, preserved
            'api_calls_saved': cached_count
        }
        
        logger.info(f"Market data cache update complete: {stats}")
        return stats
    
    async def get_cached_prices(
        self, 
        db: AsyncSession, 
        symbols: List[str], 
        target_date: Optional[date] = None
    ) -> Dict[str, Optional[Decimal]]:
        """
        Get cached prices for symbols on a specific date
        
        Args:
            db: Database session
            symbols: List of symbols
            target_date: Date to get prices for (defaults to latest available)
            
        Returns:
            Dictionary with symbol as key and price as value
        """
        if not target_date:
            target_date = date.today()
        
        # Query cached prices
        stmt = select(MarketDataCache).where(
            MarketDataCache.symbol.in_([s.upper() for s in symbols]),
            MarketDataCache.date <= target_date
        ).order_by(MarketDataCache.symbol, MarketDataCache.date.desc())
        
        result = await db.execute(stmt)
        cached_data = result.scalars().all()
        
        # Group by symbol and get most recent price
        prices = {}
        for symbol in symbols:
            symbol_upper = symbol.upper()
            symbol_data = [d for d in cached_data if d.symbol == symbol_upper]
            if symbol_data:
                prices[symbol] = symbol_data[0].close
            else:
                prices[symbol] = None
        
        return prices
    
    async def _get_cached_dates(self, db: AsyncSession, symbol: str) -> set:
        """
        Get all dates we have PRICE data for this symbol in the cache
        (Fix 2 from Section 6.1.10 - Filter out metadata rows)
        
        Args:
            db: Database session
            symbol: Symbol to check
            
        Returns:
            Set of dates with cached price data
        """
        from sqlalchemy import select, and_
        stmt = select(MarketDataCache.date).where(
            and_(
                MarketDataCache.symbol == symbol.upper(),
                MarketDataCache.close > 0,  # Filter out metadata rows
                MarketDataCache.data_source.in_(['fmp', 'polygon'])  # Only price sources
            )
        ).distinct()
        result = await db.execute(stmt)
        return set(row[0] for row in result.fetchall())
    
    async def _count_cached_days(self, db: AsyncSession, symbol: str) -> int:
        """
        Count the number of days of cached PRICE data for a symbol
        (Fix 2 from Section 6.1.10 - Filter out metadata rows)
        
        Args:
            db: Database session
            symbol: Symbol to check
            
        Returns:
            Number of days with cached price data
        """
        from sqlalchemy import func, and_, distinct
        stmt = select(func.count(distinct(MarketDataCache.date))).where(
            and_(
                MarketDataCache.symbol == symbol.upper(),
                MarketDataCache.close > 0,  # Filter out metadata rows
                MarketDataCache.data_source.in_(['fmp', 'polygon'])  # Only price sources
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    def _find_missing_trading_days(
        self, 
        existing_dates: set, 
        start_date: date, 
        end_date: date
    ) -> List[date]:
        """
        Find trading days we don't have data for
        
        Args:
            existing_dates: Set of dates we already have
            start_date: Start of range to check
            end_date: End of range to check
            
        Returns:
            List of missing trading days
        """
        missing_days = []
        current = start_date
        
        while current <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() < 5:  # Monday=0, Friday=4
                if current not in existing_dates:
                    missing_days.append(current)
            current = current + timedelta(days=1)
        
        return missing_days
    
    async def ensure_data_coverage(
        self,
        db: AsyncSession,
        symbol: str,
        min_days: int = 90
    ) -> bool:
        """
        Ensures minimum data coverage for a specific symbol (on-demand)
        Used by API endpoints when user requests data NOW
        
        Args:
            db: Database session
            symbol: Single symbol to check/fetch
            min_days: Minimum days of history required
            
        Returns:
            True if minimum coverage is met (after fetching if needed)
        """
        # Check current coverage
        existing_count = await self._count_cached_days(db, symbol)
        
        if existing_count >= min_days:
            logger.info(f"Symbol {symbol} already has {existing_count} days (>= {min_days})")
            return True
        
        # Need more data - fetch it now
        logger.info(f"Symbol {symbol} has {existing_count} days, fetching to reach {min_days}")
        
        # Fetch the data
        await self.bulk_fetch_and_cache(db, [symbol], days_back=min_days)
        
        # Verify we now have enough
        new_count = await self._count_cached_days(db, symbol)
        success = new_count >= min_days
        
        if success:
            logger.info(f"Symbol {symbol} now has {new_count} days of data")
        else:
            logger.warning(f"Symbol {symbol} only has {new_count} days after fetch (wanted {min_days})")
        
        return success
    
    async def bulk_fetch_and_cache(
        self, 
        db: AsyncSession, 
        symbols: List[str],
        days_back: int = 90,
        include_gics: bool = False  # Fix 3: Default to False for performance
    ) -> Dict[str, Any]:
        """
        Bulk fetch historical data and cache for multiple symbols
        
        Args:
            db: Database session
            symbols: List of symbols to fetch
            days_back: Number of days of historical data to fetch
            include_gics: Whether to fetch GICS sector/industry data (expensive)
            
        Returns:
            Summary statistics of the operation
        """
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()
        
        logger.info(f"Bulk fetching {days_back} days of data for {len(symbols)} symbols (GICS: {include_gics})")
        
        return await self.update_market_data_cache(
            db=db,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            include_gics=include_gics
        )
    
    
    async def fetch_company_profiles(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch company profiles including sector and industry data from FMP
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary with symbol as key and profile data including sector/industry
        """
        logger.info(f"Fetching company profiles for {len(symbols)} symbols")
        
        results = {}
        
        try:
            # Get FMP provider for stocks/ETFs
            provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)
            
            if provider and hasattr(provider, 'get_company_profile'):
                # Process in batches of 100 symbols (FMP limit)
                batch_size = 100
                for i in range(0, len(symbols), batch_size):
                    batch = symbols[i:i + batch_size]
                    
                    try:
                        batch_profiles = await provider.get_company_profile(batch)
                        results.update(batch_profiles)
                        logger.info(f"Retrieved profiles for {len(batch_profiles)}/{len(batch)} symbols in batch")
                    except Exception as e:
                        logger.error(f"Failed to fetch profiles for batch {i//batch_size + 1}: {str(e)}")
                        continue
                
                logger.info(f"Successfully retrieved {len(results)} company profiles")
            else:
                logger.warning("FMP provider not available or doesn't support company profiles")
                
        except Exception as e:
            logger.error(f"Error fetching company profiles: {str(e)}")
        
        return results
    
    async def update_security_metadata(
        self, 
        db: AsyncSession,
        symbols: List[str],
        force_refresh: bool = False
    ) -> Dict[str, bool]:
        """
        Update market_data_cache with sector/industry metadata from FMP profiles
        
        Args:
            db: Database session
            symbols: List of symbols to update
            force_refresh: Force refresh even if data exists
            
        Returns:
            Dictionary with symbol as key and success status
        """
        logger.info(f"Updating security metadata for {len(symbols)} symbols")
        
        results = {}
        
        try:
            # Check existing cache entries if not forcing refresh
            if not force_refresh:
                stmt = select(MarketDataCache).where(
                    MarketDataCache.symbol.in_(symbols),
                    MarketDataCache.sector.isnot(None)
                )
                existing = await db.execute(stmt)
                existing_symbols = {row.symbol for row in existing.scalars()}
                
                # Only fetch missing symbols
                symbols_to_fetch = [s for s in symbols if s not in existing_symbols]
                logger.info(f"Found {len(existing_symbols)} cached, fetching {len(symbols_to_fetch)} new")
            else:
                symbols_to_fetch = symbols
            
            if not symbols_to_fetch:
                return {s: True for s in symbols}
            
            # Fetch company profiles
            profiles = await self.fetch_company_profiles(symbols_to_fetch)
            
            # Update database - use today's date as a reference point for metadata
            reference_date = date.today()
            
            for symbol, profile in profiles.items():
                try:
                    # Prepare upsert statement with date field for unique constraint
                    stmt = pg_insert(MarketDataCache).values(
                        symbol=symbol,
                        date=reference_date,  # Use today's date for metadata record
                        close=Decimal('0'),  # Required field, use 0 as placeholder
                        sector=profile.get('sector'),
                        industry=profile.get('industry'),
                        exchange=profile.get('exchange'),
                        country=profile.get('country'),
                        market_cap=profile.get('market_cap'),
                        data_source='fmp_profile',  # Mark as profile data
                        updated_at=datetime.utcnow()
                    )
                    
                    # On conflict, update the metadata fields
                    stmt = stmt.on_conflict_do_update(
                        constraint='uq_market_data_cache_symbol_date',
                        set_={
                            'sector': stmt.excluded.sector,
                            'industry': stmt.excluded.industry,
                            'exchange': stmt.excluded.exchange,
                            'country': stmt.excluded.country,
                            'market_cap': stmt.excluded.market_cap,
                            'data_source': stmt.excluded.data_source,
                            'updated_at': stmt.excluded.updated_at
                        }
                    )
                    
                    await db.execute(stmt)
                    results[symbol] = True
                    
                except Exception as e:
                    logger.error(f"Failed to update metadata for {symbol}: {str(e)}")
                    results[symbol] = False
            
            # Mark symbols without profiles as processed (but unsuccessful)
            for symbol in symbols_to_fetch:
                if symbol not in results:
                    results[symbol] = False
            
            await db.commit()
            
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"Updated metadata for {success_count}/{len(symbols_to_fetch)} symbols")
            
        except Exception as e:
            logger.error(f"Error updating security metadata: {str(e)}")
            await db.rollback()
            return {s: False for s in symbols}
        
        return results

    async def store_company_profile(
        self,
        db: AsyncSession,
        symbol: str,
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        Store or update a company profile in the database.

        Args:
            db: Database session
            symbol: Ticker symbol
            profile_data: Profile data dict from yahooquery_profile_fetcher

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare upsert statement
            stmt = pg_insert(CompanyProfile).values(
                symbol=symbol,
                company_name=profile_data.get('company_name'),
                sector=profile_data.get('sector'),
                industry=profile_data.get('industry'),
                exchange=profile_data.get('exchange'),
                country=profile_data.get('country'),
                market_cap=profile_data.get('market_cap'),
                description=profile_data.get('description'),
                is_etf=profile_data.get('is_etf', False),
                is_fund=profile_data.get('is_fund', False),
                ceo=profile_data.get('ceo'),
                employees=profile_data.get('employees'),
                website=profile_data.get('website'),
                pe_ratio=profile_data.get('pe_ratio'),
                forward_pe=profile_data.get('forward_pe'),
                dividend_yield=profile_data.get('dividend_yield'),
                beta=profile_data.get('beta'),
                week_52_high=profile_data.get('week_52_high'),
                week_52_low=profile_data.get('week_52_low'),
                target_mean_price=profile_data.get('target_mean_price'),
                target_high_price=profile_data.get('target_high_price'),
                target_low_price=profile_data.get('target_low_price'),
                number_of_analyst_opinions=profile_data.get('number_of_analyst_opinions'),
                recommendation_mean=profile_data.get('recommendation_mean'),
                recommendation_key=profile_data.get('recommendation_key'),
                forward_eps=profile_data.get('forward_eps'),
                earnings_growth=profile_data.get('earnings_growth'),
                revenue_growth=profile_data.get('revenue_growth'),
                earnings_quarterly_growth=profile_data.get('earnings_quarterly_growth'),
                profit_margins=profile_data.get('profit_margins'),
                operating_margins=profile_data.get('operating_margins'),
                gross_margins=profile_data.get('gross_margins'),
                return_on_assets=profile_data.get('return_on_assets'),
                return_on_equity=profile_data.get('return_on_equity'),
                total_revenue=profile_data.get('total_revenue'),
                current_year_revenue_avg=profile_data.get('current_year_revenue_avg'),
                current_year_revenue_low=profile_data.get('current_year_revenue_low'),
                current_year_revenue_high=profile_data.get('current_year_revenue_high'),
                current_year_revenue_growth=profile_data.get('current_year_revenue_growth'),
                current_year_earnings_avg=profile_data.get('current_year_earnings_avg'),
                current_year_earnings_low=profile_data.get('current_year_earnings_low'),
                current_year_earnings_high=profile_data.get('current_year_earnings_high'),
                current_year_end_date=profile_data.get('current_year_end_date'),
                next_year_revenue_avg=profile_data.get('next_year_revenue_avg'),
                next_year_revenue_low=profile_data.get('next_year_revenue_low'),
                next_year_revenue_high=profile_data.get('next_year_revenue_high'),
                next_year_revenue_growth=profile_data.get('next_year_revenue_growth'),
                next_year_earnings_avg=profile_data.get('next_year_earnings_avg'),
                next_year_earnings_low=profile_data.get('next_year_earnings_low'),
                next_year_earnings_high=profile_data.get('next_year_earnings_high'),
                next_year_end_date=profile_data.get('next_year_end_date'),
                data_source=profile_data.get('data_source', 'yahooquery'),
                # Phase 9.0: Use timezone-aware datetime for DateTime(timezone=True) columns
                last_updated=profile_data.get('last_updated', datetime.now(timezone.utc)),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # On conflict, update all fields except symbol and created_at
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol'],
                set_={
                    'company_name': stmt.excluded.company_name,
                    'sector': stmt.excluded.sector,
                    'industry': stmt.excluded.industry,
                    'exchange': stmt.excluded.exchange,
                    'country': stmt.excluded.country,
                    'market_cap': stmt.excluded.market_cap,
                    'description': stmt.excluded.description,
                    'is_etf': stmt.excluded.is_etf,
                    'is_fund': stmt.excluded.is_fund,
                    'ceo': stmt.excluded.ceo,
                    'employees': stmt.excluded.employees,
                    'website': stmt.excluded.website,
                    'pe_ratio': stmt.excluded.pe_ratio,
                    'forward_pe': stmt.excluded.forward_pe,
                    'dividend_yield': stmt.excluded.dividend_yield,
                    'beta': stmt.excluded.beta,
                    'week_52_high': stmt.excluded.week_52_high,
                    'week_52_low': stmt.excluded.week_52_low,
                    'target_mean_price': stmt.excluded.target_mean_price,
                    'target_high_price': stmt.excluded.target_high_price,
                    'target_low_price': stmt.excluded.target_low_price,
                    'number_of_analyst_opinions': stmt.excluded.number_of_analyst_opinions,
                    'recommendation_mean': stmt.excluded.recommendation_mean,
                    'recommendation_key': stmt.excluded.recommendation_key,
                    'forward_eps': stmt.excluded.forward_eps,
                    'earnings_growth': stmt.excluded.earnings_growth,
                    'revenue_growth': stmt.excluded.revenue_growth,
                    'earnings_quarterly_growth': stmt.excluded.earnings_quarterly_growth,
                    'profit_margins': stmt.excluded.profit_margins,
                    'operating_margins': stmt.excluded.operating_margins,
                    'gross_margins': stmt.excluded.gross_margins,
                    'return_on_assets': stmt.excluded.return_on_assets,
                    'return_on_equity': stmt.excluded.return_on_equity,
                    'total_revenue': stmt.excluded.total_revenue,
                    'current_year_revenue_avg': stmt.excluded.current_year_revenue_avg,
                    'current_year_revenue_low': stmt.excluded.current_year_revenue_low,
                    'current_year_revenue_high': stmt.excluded.current_year_revenue_high,
                    'current_year_revenue_growth': stmt.excluded.current_year_revenue_growth,
                    'current_year_earnings_avg': stmt.excluded.current_year_earnings_avg,
                    'current_year_earnings_low': stmt.excluded.current_year_earnings_low,
                    'current_year_earnings_high': stmt.excluded.current_year_earnings_high,
                    'current_year_end_date': stmt.excluded.current_year_end_date,
                    'next_year_revenue_avg': stmt.excluded.next_year_revenue_avg,
                    'next_year_revenue_low': stmt.excluded.next_year_revenue_low,
                    'next_year_revenue_high': stmt.excluded.next_year_revenue_high,
                    'next_year_revenue_growth': stmt.excluded.next_year_revenue_growth,
                    'next_year_earnings_avg': stmt.excluded.next_year_earnings_avg,
                    'next_year_earnings_low': stmt.excluded.next_year_earnings_low,
                    'next_year_earnings_high': stmt.excluded.next_year_earnings_high,
                    'next_year_end_date': stmt.excluded.next_year_end_date,
                    'data_source': stmt.excluded.data_source,
                    'last_updated': stmt.excluded.last_updated,
                    'updated_at': stmt.excluded.updated_at
                }
            )

            await db.execute(stmt)
            logger.info(f"Stored company profile for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to store company profile for {symbol}: {str(e)}")
            return False

    async def fetch_and_cache_company_profiles(
        self,
        db: AsyncSession,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Fetch company profiles from yahooquery and cache them in database.

        Phase 9.0 Fix: Process in slices of 20 with per-batch error handling.
        If one batch fails, continue with remaining batches.

        Args:
            db: Database session
            symbols: List of ticker symbols

        Returns:
            Dict with:
                - symbols_attempted: int
                - symbols_successful: int
                - symbols_failed: int
                - failed_symbols: List[str]
                - profiles_cached: Dict[str, bool]
        """
        # Filter out synthetic/private symbols BEFORE hitting external APIs
        # Defense-in-depth: Even if investment_class filter missed these, we catch them here
        original_count = len(symbols)
        filtered_symbols: List[str] = []
        skipped_symbols: List[str] = []
        for symbol in symbols:
            upper = normalize_symbol(symbol)
            if not upper:
                continue
            skip, reason = should_skip_symbol(upper)
            if skip:
                skipped_symbols.append(f"{upper} ({reason})")
            else:
                filtered_symbols.append(upper)

        if skipped_symbols:
            logger.info(
                "Skipping %d PRIVATE/symbolic symbols: %s",
                len(skipped_symbols),
                skipped_symbols,
            )

        results = {
            'symbols_attempted': original_count,
            'symbols_successful': 0,
            'symbols_failed': 0,
            'failed_symbols': [],
            'profiles_cached': {}
        }

        # Mark skipped symbols as "successful" since we intentionally didn't fetch them
        for symbol in skipped_symbols:
            results['symbols_successful'] += 1
            results['profiles_cached'][symbol] = True  # Not cached, but intentionally skipped

        # If all symbols were filtered out, return early
        if not filtered_symbols:
            logger.info("All symbols were PRIVATE/synthetic, no API calls needed")
            return results

        # Phase 9.0 Fix: Process in slices of 20 to avoid all-or-nothing failure
        BATCH_SIZE = 20

        for i in range(0, len(filtered_symbols), BATCH_SIZE):
            batch = filtered_symbols[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(filtered_symbols) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} symbols)")

            try:
                # Fetch profiles for this batch
                batch_profiles = await fetch_profiles_yahooquery(batch)
                logger.info(f"Batch {batch_num}: Received profiles for {len(batch_profiles)} symbols")

                # Cache successful profiles
                for symbol, profile_data in batch_profiles.items():
                    if profile_data is not None:
                        try:
                            success = await self.store_company_profile(db, symbol, profile_data)
                            if success:
                                results['symbols_successful'] += 1
                                results['profiles_cached'][symbol] = True
                            else:
                                results['symbols_failed'] += 1
                                results['failed_symbols'].append(symbol)
                                results['profiles_cached'][symbol] = False
                        except Exception as e:
                            logger.error(f"Failed to store profile for {symbol}: {e}")
                            results['symbols_failed'] += 1
                            results['failed_symbols'].append(symbol)
                            results['profiles_cached'][symbol] = False
                    else:
                        # Profile data is None (fetcher returned None for this symbol)
                        results['symbols_failed'] += 1
                        results['failed_symbols'].append(symbol)
                        results['profiles_cached'][symbol] = False

                # Mark symbols that weren't in the response as failed
                for symbol in batch:
                    if symbol not in batch_profiles:
                        results['symbols_failed'] += 1
                        results['failed_symbols'].append(symbol)
                        results['profiles_cached'][symbol] = False

                # Commit after each successful batch
                await db.commit()
                logger.info(f"Batch {batch_num}: Committed {len(batch_profiles)} profiles to database")

            except Exception as e:
                # Entire batch failed - mark all symbols in batch as failed but continue
                logger.error(f"Batch {batch_num} failed entirely: {e}")
                await db.rollback()

                for symbol in batch:
                    results['symbols_failed'] += 1
                    results['failed_symbols'].append(symbol)
                    results['profiles_cached'][symbol] = False

        logger.info(
            f"Company profile sync complete: "
            f"{results['symbols_successful']}/{results['symbols_attempted']} successful, "
            f"{results['symbols_failed']} failed"
        )

        return results

    async def close(self):
        """Close all provider client sessions"""
        await market_data_factory.close_all()
        logger.info("MarketDataService: All provider sessions closed")


# Global service instance
market_data_service = MarketDataService()
