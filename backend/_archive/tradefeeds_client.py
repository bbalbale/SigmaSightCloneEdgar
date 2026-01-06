"""
TradeFeeds API client implementation (backup provider)
Documentation: https://tradefeeds.com/api-documentation/
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


class TradeFeedsClient(MarketDataProvider):
    """TradeFeeds API client (backup provider)"""
    
    BASE_URL = "https://tradefeeds.com/api/v1"
    
    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3, rate_limit: int = 10):
        super().__init__(api_key, timeout, max_retries)
        self.rate_limit = rate_limit  # calls per minute (reduced for CAPTCHA avoidance)
        self.last_request_time = 0
        self.session = None
        self.credits_used = 0  # Track credit usage
        self.captcha_detected = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with CAPTCHA mitigation headers"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _rate_limit_check(self):
        """Implement aggressive rate limiting to avoid CAPTCHA (10 calls/minute)"""
        current_time = utc_now().timestamp()
        time_since_last = current_time - self.last_request_time
        min_interval = 60 / self.rate_limit  # seconds between calls
        
        # Add extra delay if CAPTCHA was detected recently
        if self.captcha_detected:
            min_interval = max(min_interval, 30)  # Wait at least 30 seconds
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logger.debug(f"TradeFeeds rate limiting: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = utc_now().timestamp()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None, credit_multiplier: int = 1) -> Dict[str, Any]:
        """Make HTTP request to TradeFeeds API with CAPTCHA detection"""
        if params is None:
            params = {}
        
        # Add API key to params (TradeFeeds uses query parameter authentication)
        params['key'] = self.api_key
        
        await self._rate_limit_check()
        
        url = f"{self.BASE_URL}/{endpoint}"
        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"TradeFeeds API request: {url} (attempt {attempt + 1})")
                async with session.get(url, params=params) as response:
                    response_text = await response.text()
                    
                    # Check for CAPTCHA protection
                    if (response.status == 202 and 'sgcaptcha' in response_text.lower()) or 'captcha' in response_text.lower():
                        logger.error(f"TradeFeeds CAPTCHA protection detected for {endpoint}")
                        self.captcha_detected = True
                        raise Exception(f"TradeFeeds API blocked by CAPTCHA protection. Contact TradeFeeds support to whitelist API access.")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            # Reset CAPTCHA detection on success
                            self.captcha_detected = False
                            # Track credit usage (ETF/MF calls have 20X multiplier)
                            self.credits_used += credit_multiplier
                            logger.debug(f"TradeFeeds credits used: {self.credits_used}")
                            return data
                        except Exception:
                            # If JSON parsing fails, it might be HTML (CAPTCHA)
                            if 'html' in response_text.lower():
                                logger.error(f"TradeFeeds returned HTML instead of JSON - CAPTCHA likely")
                                self.captcha_detected = True
                                raise Exception("TradeFeeds API returned HTML instead of JSON - CAPTCHA protection active")
                            raise
                    elif response.status == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        logger.warning(f"TradeFeeds rate limit hit, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"TradeFeeds API error {response.status}: {response_text[:200]}...")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"TradeFeeds API error {response.status}: {response_text[:200]}...")
            except asyncio.TimeoutError:
                logger.warning(f"TradeFeeds API timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("TradeFeeds API timeout after all retries")
            except Exception as e:
                logger.error(f"TradeFeeds API request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("TradeFeeds API request failed after all retries")
    
    async def get_stock_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current stock prices from TradeFeeds
        
        Uses the quotes endpoint with 1X credit multiplier
        """
        results = {}
        
        # TradeFeeds may require individual requests for each symbol
        for symbol in symbols:
            try:
                data = await self._make_request(f"comp_info", {'ticker': symbol}, credit_multiplier=1)
                
                if not data or 'quote' not in data:
                    logger.warning(f"No quote data from TradeFeeds for {symbol}")
                    continue
                
                quote = data['quote']
                
                try:
                    price = Decimal(str(quote.get('last', 0)))
                    change = Decimal(str(quote.get('change', 0)))
                    change_percent = Decimal(str(quote.get('changePercent', 0)))
                    volume = int(quote.get('volume', 0))
                    
                    results[symbol] = {
                        'price': price,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': volume,
                        'timestamp': utc_now(),
                        'provider': 'TradeFeedsClient',
                        'raw_data': quote
                    }
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing TradeFeeds quote data for {symbol}: {str(e)}")
                    continue
            
            except Exception as e:
                logger.error(f"TradeFeeds get_stock_prices failed for {symbol}: {str(e)}")
                continue
        
        logger.info(f"TradeFeeds: Successfully retrieved {len(results)} stock quotes")
        return results
    
    async def get_fund_holdings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get fund holdings from TradeFeeds
        
        Uses holdings endpoint with 20X credit multiplier (important cost consideration)
        """
        try:
            # TradeFeeds charges 20 credits for each fund holdings call
            data = await self._make_request(f"etfholdings", {'etf_ticker_symbol': symbol}, credit_multiplier=20)
            
            if not data or 'results' not in data:
                logger.warning(f"No holdings data from TradeFeeds for {symbol}")
                return []
            
            holdings = []
            for result in data['results']:
                if 'output' not in result:
                    continue
                holding = result['output']
                try:
                    # TradeFeeds returns percent_of_portfolio as string (e.g., "5.25" for 5.25%)
                    weight_str = holding.get('percent_of_portfolio', '0')
                    weight = Decimal(str(weight_str)) / 100  # Convert percentage to decimal
                    
                    shares = int(holding.get('shares', 0)) if holding.get('shares') else None
                    market_value = Decimal(str(holding.get('marketValue', 0))) if holding.get('marketValue') else None
                    
                    holdings.append({
                        'symbol': holding.get('stock_ticker_symbol', '').strip(),
                        'name': holding.get('name', '').strip(),
                        'weight': weight,
                        'shares': shares,
                        'market_value': market_value,
                        'provider': 'TradeFeedsClient',
                        'raw_data': holding
                    })
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing TradeFeeds holding data for {symbol}: {str(e)}")
                    continue
            
            # Sort by weight (highest first)
            holdings.sort(key=lambda x: x['weight'], reverse=True)
            
            # Calculate total weight for validation
            total_weight = sum(h['weight'] for h in holdings)
            logger.info(f"TradeFeeds: Retrieved {len(holdings)} holdings for {symbol} (total weight: {total_weight:.2%})")
            logger.warning(f"TradeFeeds: Used 20 credits for {symbol} holdings (total credits: {self.credits_used})")
            
            return holdings
            
        except Exception as e:
            logger.error(f"TradeFeeds get_fund_holdings failed for {symbol}: {str(e)}")
            raise
    
    async def get_historical_prices(self, symbol: str, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get historical prices from TradeFeeds
        
        Uses historical endpoint
        """
        try:
            params = {
                'period': f'{days}d'
            }
            data = await self._make_request(f"historical/{symbol}", params, credit_multiplier=1)
            
            if not data or 'prices' not in data:
                logger.warning(f"No historical data from TradeFeeds for {symbol}")
                return []
            
            historical_data = []
            for day_data in data['prices']:
                try:
                    historical_data.append({
                        'date': datetime.strptime(day_data['date'], '%Y-%m-%d').date(),
                        'open': Decimal(str(day_data['open'])),
                        'high': Decimal(str(day_data['high'])),
                        'low': Decimal(str(day_data['low'])),
                        'close': Decimal(str(day_data['close'])),
                        'volume': int(day_data['volume']),
                        'provider': 'TradeFeedsClient'
                    })
                except (ValueError, TypeError, KeyError) as e:
                    logger.error(f"Error parsing TradeFeeds historical data for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"TradeFeeds: Retrieved {len(historical_data)} historical prices for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"TradeFeeds get_historical_prices failed for {symbol}: {str(e)}")
            raise
    
    def get_credit_usage(self) -> Dict[str, int]:
        """Get current credit usage statistics"""
        return {
            'credits_used': self.credits_used,
            'credits_remaining': 22000 - self.credits_used,  # TradeFeeds Professional Plan limit
            'usage_percentage': round((self.credits_used / 22000) * 100, 2)
        }