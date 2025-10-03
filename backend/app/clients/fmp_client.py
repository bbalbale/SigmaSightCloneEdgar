"""
Financial Modeling Prep (FMP) API client implementation
Documentation: https://site.financialmodelingprep.com/developer/docs
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date
import aiohttp
from app.core.datetime_utils import utc_now

from app.clients.base import MarketDataProvider

logger = logging.getLogger(__name__)


class FMPClient(MarketDataProvider):
    """Financial Modeling Prep API client"""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3):
        super().__init__(api_key, timeout, max_retries)
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to FMP API with retries"""
        from app.services.rate_limiter import fmp_quota_tracker

        # Check FMP daily quota before making request
        if not await fmp_quota_tracker.can_make_request():
            raise Exception("FMP daily quota exceeded (250 calls/day). Please wait until tomorrow or use fallback providers.")

        if params is None:
            params = {}

        params['apikey'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"FMP API request: {url} (attempt {attempt + 1})")
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Record successful FMP request for quota tracking
                        await fmp_quota_tracker.record_request()
                        return data
                    elif response.status == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        logger.warning(f"FMP rate limit hit, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"FMP API error {response.status}: {error_text}")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"FMP API error {response.status}: {error_text}")
            except asyncio.TimeoutError:
                logger.warning(f"FMP API timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("FMP API timeout after all retries")
            except Exception as e:
                logger.error(f"FMP API request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception("FMP API request failed after all retries")
    
    async def get_stock_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current stock prices from FMP
        
        Uses the quote endpoint: /quote/{symbol}
        """
        results = {}
        
        # FMP allows batch quotes with comma-separated symbols
        symbols_str = ','.join(symbols)
        
        try:
            data = await self._make_request(f"quote/{symbols_str}")
            
            if not isinstance(data, list):
                logger.error(f"Unexpected FMP response format: {type(data)}")
                return results
            
            for quote in data:
                symbol = quote.get('symbol')
                if not symbol:
                    continue
                
                try:
                    price = Decimal(str(quote.get('price', 0)))
                    change = Decimal(str(quote.get('change', 0))) 
                    change_percent = Decimal(str(quote.get('changesPercentage', 0)))
                    volume = int(quote.get('volume', 0))
                    
                    results[symbol] = {
                        'price': price,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': volume,
                        'timestamp': utc_now(),
                        'provider': 'FMPClient',
                        'raw_data': quote  # Store raw data for debugging
                    }
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing FMP quote data for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"FMP: Successfully retrieved {len(results)} stock quotes")
            return results
            
        except Exception as e:
            logger.error(f"FMP get_stock_prices failed: {str(e)}")
            raise
    
    async def get_fund_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get fund holdings from FMP
        
        Uses the etf-holder endpoint: /etf-holder/{symbol}
        Note: FMP uses same endpoint for both ETFs and mutual funds
        """
        try:
            # FMP endpoint for fund holdings
            data = await self._make_request(f"etf-holder/{symbol}")
            
            if not isinstance(data, list):
                logger.error(f"Unexpected FMP fund holdings format for {symbol}: {type(data)}")
                return []
            
            holdings = []
            for holding in data:
                try:
                    # FMP returns weight as a percentage (e.g., 5.25 for 5.25%)
                    weight_percent = float(holding.get('weightPercentage', 0))
                    weight_decimal = Decimal(str(weight_percent / 100))  # Convert to decimal (0.0525)
                    
                    shares = int(holding.get('sharesNumber', 0)) if holding.get('sharesNumber') else None
                    market_value = Decimal(str(holding.get('marketValue', 0))) if holding.get('marketValue') else None
                    
                    holdings.append({
                        'symbol': holding.get('asset', '').strip(),
                        'name': holding.get('name', '').strip(),
                        'weight': weight_decimal,
                        'shares': shares,
                        'market_value': market_value,
                        'provider': 'FMPClient',
                        'raw_data': holding
                    })
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing FMP holding data for {symbol}: {str(e)}")
                    continue
            
            # Sort by weight (highest first)
            holdings.sort(key=lambda x: x['weight'], reverse=True)
            
            # Calculate total weight for validation
            total_weight = sum(h['weight'] for h in holdings)
            logger.info(f"FMP: Retrieved {len(holdings)} holdings for {symbol} (total weight: {total_weight:.2%})")
            
            return holdings
            
        except Exception as e:
            logger.error(f"FMP get_fund_holdings failed for {symbol}: {str(e)}")
            raise
    
    async def get_historical_prices(self, symbol: str, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get historical prices for a symbol
        
        Uses historical-price-full endpoint with timeseries
        """
        try:
            params = {
                'timeseries': days
            }
            data = await self._make_request(f"historical-price-full/{symbol}", params)
            
            if not isinstance(data, dict) or 'historical' not in data:
                logger.error(f"Unexpected FMP historical data format for {symbol}")
                return []
            
            historical_data = []
            for day_data in data['historical']:
                try:
                    historical_data.append({
                        'date': datetime.strptime(day_data['date'], '%Y-%m-%d').date(),
                        'open': Decimal(str(day_data['open'])),
                        'high': Decimal(str(day_data['high'])),
                        'low': Decimal(str(day_data['low'])),
                        'close': Decimal(str(day_data['close'])),
                        'volume': int(day_data['volume']),
                        'provider': 'FMPClient'
                    })
                except (ValueError, TypeError, KeyError) as e:
                    logger.error(f"Error parsing FMP historical data for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"FMP: Retrieved {len(historical_data)} historical prices for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"FMP get_historical_prices failed for {symbol}: {str(e)}")
            raise
    
    async def get_company_profile(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get company profile including sector and industry from FMP
        
        Uses the profile endpoint: /profile/{symbol}
        Returns sector, industry, and other company metadata
        """
        results = {}
        
        # FMP allows batch profile requests with comma-separated symbols
        symbols_str = ','.join(symbols)
        
        try:
            data = await self._make_request(f"profile/{symbols_str}")
            
            if not isinstance(data, list):
                logger.error(f"Unexpected FMP profile response format: {type(data)}")
                return results
            
            for profile in data:
                symbol = profile.get('symbol')
                if not symbol:
                    continue
                
                try:
                    results[symbol] = {
                        'sector': profile.get('sector'),
                        'industry': profile.get('industry'),
                        'company_name': profile.get('companyName'),
                        'exchange': profile.get('exchangeShortName'),
                        'country': profile.get('country'),
                        'market_cap': Decimal(str(profile.get('mktCap', 0))) if profile.get('mktCap') else None,
                        'description': profile.get('description'),
                        'is_etf': profile.get('isEtf', False),
                        'is_fund': profile.get('isFund', False),
                        'ceo': profile.get('ceo'),
                        'employees': profile.get('fullTimeEmployees'),
                        'website': profile.get('website'),
                        'timestamp': utc_now(),
                        'provider': 'FMPClient'
                    }
                    
                    logger.debug(f"FMP: Got profile for {symbol} - Sector: {results[symbol]['sector']}, Industry: {results[symbol]['industry']}")
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing FMP profile data for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"FMP: Successfully retrieved {len(results)} company profiles")
            return results
            
        except Exception as e:
            logger.error(f"FMP get_company_profile failed: {str(e)}")
            raise