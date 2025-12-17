"""
Provider-agnostic tool implementations for portfolio data access.
These handlers contain all business logic and are 100% portable across AI providers.
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import httpx
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.core.datetime_utils import utc_now, to_utc_iso8601

logger = logging.getLogger(__name__)


class PortfolioTools:
    """
    Provider-independent tool implementations.
    All business logic for data fetching, filtering, and formatting lives here.
    This class is 100% portable across all AI providers (OpenAI, Anthropic, Gemini, etc.)
    """
    
    def __init__(self, base_url: str = None, auth_token: str = None):
        """
        Initialize the tools with API configuration.
        
        Args:
            base_url: Base URL for the API (defaults to settings)
            auth_token: Bearer token for authentication
        """
        self.base_url = base_url or settings.BACKEND_URL
        self.auth_token = auth_token
        self.timeout = httpx.Timeout(30.0, connect=10.0)  # 30s read, 10s connect
        logger.info(f"PortfolioTools initialized with base_url={self.base_url}")
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        retry_count: int = 2
    ) -> Dict[str, Any]:
        """
        Make HTTP request to backend API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Number of retries for transient errors
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making request to: {url}")
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(retry_count + 1):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response.json()
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [429, 500, 502, 503, 504]:
                        # Retryable errors
                        if attempt < retry_count:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                    # Non-retryable or max retries exceeded
                    logger.error(f"HTTP error for {endpoint}: {e}")
                    raise
                    
                except httpx.TimeoutException as e:
                    if attempt < retry_count:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    logger.error(f"Timeout for {endpoint}: {e}")
                    raise
                    
                except Exception as e:
                    logger.error(f"Unexpected error for {endpoint}: {e}")
                    raise
    
    async def _get_portfolio_complete_single(
        self,
        portfolio_id: str,
        include_holdings: bool,
        include_timeseries: bool,
        include_attrib: bool,
    ) -> Dict[str, Any]:
        params = {
            "include_holdings": include_holdings,
            "include_timeseries": include_timeseries,
            "include_attrib": include_attrib
        }

        endpoint = f"/api/v1/data/portfolio/{portfolio_id}/complete"
        logger.info(f"[SEARCH] TRACE-3 Tool URL: portfolio_id={portfolio_id} | final_url={endpoint}")

        response = await self._make_request(
            method="GET",
            endpoint=endpoint,
            params=params
        )

        if response.get("meta", {}).get("truncated"):
            response["_tool_note"] = "Data was truncated. Consider narrowing your query."

        return response


    async def get_portfolio_complete(
        self,
        portfolio_id: Optional[str] = None,
        portfolio_ids: Optional[list[str]] = None,
        include_holdings: bool = True,
        include_timeseries: bool = False,
        include_attrib: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get complete portfolio data with optional sections.

        Supports single portfolio_id or multi-portfolio via portfolio_ids.
        Returns aggregated structure when multiple portfolios are requested.
        """
        try:
            # Multi-portfolio aggregation
            if portfolio_ids and len(portfolio_ids) > 0:
                portfolios_data = []
                for pid in portfolio_ids:
                    try:
                        data = await self._get_portfolio_complete_single(
                            portfolio_id=pid,
                            include_holdings=include_holdings,
                            include_timeseries=include_timeseries,
                            include_attrib=include_attrib,
                        )
                        portfolios_data.append({
                            "portfolio_id": pid,
                            "data": data
                        })
                    except Exception as e:
                        portfolios_data.append({
                            "portfolio_id": pid,
                            "error": str(e)
                        })

                return {
                    "multi_portfolio": True,
                    "portfolios": portfolios_data
                }

            # Single portfolio path (existing behavior)
            if not portfolio_id:
                raise ValueError("portfolio_id is required when portfolio_ids is not provided")

            return await self._get_portfolio_complete_single(
                portfolio_id=portfolio_id,
                include_holdings=include_holdings,
                include_timeseries=include_timeseries,
                include_attrib=include_attrib,
            )

        except Exception as e:
            logger.error(f"Error in get_portfolio_complete: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_positions_details(
        self,
        portfolio_id: Optional[str] = None,
        position_ids: Optional[str] = None,
        include_closed: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get detailed position information.
        
        Business logic:
        - Validates that either portfolio_id OR position_ids is provided
        - Enforces max_rows=200 cap with truncation
        - Adds summary statistics
        
        Args:
            portfolio_id: Optional portfolio UUID
            position_ids: Comma-separated position IDs
            include_closed: Include closed positions
            
        Returns:
            Position details with meta object
        """
        try:
            # Validation: Need either portfolio_id or position_ids
            if not portfolio_id and not position_ids:
                return {
                    "error": "Either portfolio_id or position_ids is required",
                    "retryable": False
                }
            
            # Build query parameters
            params = {"include_closed": include_closed}
            if portfolio_id:
                params["portfolio_id"] = portfolio_id
            if position_ids:
                params["position_ids"] = position_ids
                
            # Call API endpoint
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/data/positions/details",
                params=params
            )
            
            # Business logic: Calculate summary statistics
            if "positions" in response:
                positions = response["positions"]
                if len(positions) > 200:
                    # Apply cap
                    response["positions"] = positions[:200]
                    response["meta"] = response.get("meta", {})
                    response["meta"]["truncated"] = True
                    response["meta"]["original_count"] = len(positions)
                    
            return response
            
        except Exception as e:
            logger.error(f"Error in get_positions_details: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_prices_historical(
        self,
        portfolio_id: str,
        lookback_days: int = 90,
        max_symbols: int = 5,
        include_factor_etfs: bool = True,
        date_format: str = "iso",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get historical prices for portfolio positions.
        
        Business logic:
        - Fetches portfolio positions first
        - Identifies top N symbols by market value
        - Applies lookback_days cap (max 180)
        - Filters to max_symbols (default 5)
        
        Args:
            portfolio_id: Portfolio UUID
            lookback_days: Days of history (max 180)
            max_symbols: Maximum symbols to return (max 5)
            include_factor_etfs: Include factor ETF prices
            date_format: Date format (iso or unix)
            
        Returns:
            Historical price data with meta object
        """
        try:
            # Business logic: Apply caps
            lookback_days = min(lookback_days, 180)
            max_symbols = min(max_symbols, 5)
            
            # First, get top positions to identify symbols
            positions_response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/data/positions/top/{portfolio_id}",
                params={"limit": max_symbols, "sort_by": "market_value"}
            )
            
            if "error" in positions_response:
                return positions_response
                
            # Extract symbols from top positions
            symbols = [pos["symbol"] for pos in positions_response.get("data", [])]
            
            if not symbols:
                return {
                    "error": "No positions found in portfolio",
                    "retryable": False
                }
            
            # Get historical prices for these symbols
            params = {
                "symbols": ",".join(symbols),
                "lookback_days": lookback_days,
                "include_factor_etfs": include_factor_etfs,
                "date_format": date_format
            }
            
            response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/data/prices/historical/{portfolio_id}",
                params=params
            )
            
            # Add meta information about selection
            if "meta" not in response:
                response["meta"] = {}
            response["meta"]["symbols_selected"] = symbols
            response["meta"]["selection_method"] = "top_by_market_value"
            response["meta"]["max_symbols"] = max_symbols
            response["meta"]["lookback_days"] = lookback_days
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_prices_historical: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_current_quotes(
        self,
        symbols: str,
        include_options: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get current market quotes for symbols.
        
        Business logic:
        - Parses comma-separated symbols
        - Enforces max_symbols=5 cap
        - Validates symbol format
        
        Args:
            symbols: Comma-separated list of symbols
            include_options: Include options data if available
            
        Returns:
            Current quote data with meta object
        """
        try:
            # Parse and validate symbols
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            
            # Apply cap
            if len(symbol_list) > 5:
                symbol_list = symbol_list[:5]
                truncated = True
                suggested_symbols = symbol_list
            else:
                truncated = False
                suggested_symbols = None
                
            # Call API endpoint
            params = {
                "symbols": ",".join(symbol_list),
                "include_options": include_options
            }
            
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/data/prices/quotes",
                params=params
            )
            
            # Add meta information
            if "meta" not in response:
                response["meta"] = {}
            response["meta"]["requested_symbols"] = symbols
            response["meta"]["applied_symbols"] = symbol_list
            response["meta"]["truncated"] = truncated
            if suggested_symbols:
                response["meta"]["suggested_symbols"] = suggested_symbols
                
            return response
            
        except Exception as e:
            logger.error(f"Error in get_current_quotes: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_portfolio_data_quality(
        self,
        portfolio_id: str,
        check_factors: bool = True,
        check_correlations: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get data quality assessment for portfolio.
        
        Business logic:
        - Returns feasibility assessment for various analyses
        - Identifies data gaps
        - Suggests remediation steps
        
        Args:
            portfolio_id: Portfolio UUID
            check_factors: Check factor data availability
            check_correlations: Check correlation data availability
            
        Returns:
            Data quality assessment with recommendations
        """
        try:
            # Call API endpoint
            params = {
                "check_factors": check_factors,
                "check_correlations": check_correlations
            }
            
            response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/data/portfolio/{portfolio_id}/data-quality",
                params=params
            )
            
            # Business logic: Add recommendations based on quality
            if "data_quality_score" in response:
                score = response["data_quality_score"]
                if score < 0.5:
                    response["_tool_recommendation"] = "Data quality is low. Many analyses may not be feasible."
                elif score < 0.8:
                    response["_tool_recommendation"] = "Data quality is moderate. Some analyses may have limitations."
                else:
                    response["_tool_recommendation"] = "Data quality is good. Most analyses should be feasible."
                    
            return response
            
        except Exception as e:
            logger.error(f"Error in get_portfolio_data_quality: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_factor_etf_prices(
        self,
        lookback_days: int = 90,
        factors: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get factor ETF prices for factor analysis.
        
        Business logic:
        - Maps factor names to ETF symbols
        - Applies lookback_days cap
        - Returns prices for factor proxies
        
        Args:
            lookback_days: Days of history (max 180)
            factors: Comma-separated factor names (optional)
            
        Returns:
            Factor ETF price data with meta object
        """
        try:
            # Apply caps
            lookback_days = min(lookback_days, 180)
            
            # Build parameters
            params = {"lookback_days": lookback_days}
            if factors:
                params["factors"] = factors
                
            # Call API endpoint
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/data/factors/etf-prices",
                params=params
            )
            
            # Add meta information about factor mapping
            if "meta" not in response:
                response["meta"] = {}
            response["meta"]["lookback_days"] = lookback_days
            if factors:
                response["meta"]["requested_factors"] = factors
                
            return response
            
        except Exception as e:
            logger.error(f"Error in get_factor_etf_prices: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }
    
    async def get_prices_historical(
        self,
        portfolio_id: str,
        lookback_days: int = 60,
        include_factor_etfs: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get historical price data for portfolio positions.
        
        Business logic:
        - Validates portfolio_id format
        - Applies lookback_days cap (max 180)
        - Returns OHLCV data with metadata
        
        Args:
            portfolio_id: Portfolio UUID
            lookback_days: Days of history to retrieve (max 180)
            include_factor_etfs: Include factor ETF prices
            
        Returns:
            Historical price data with metadata
        """
        try:
            # Validate portfolio_id
            if not portfolio_id:
                return {
                    "error": "portfolio_id is required",
                    "error_type": "validation",
                    "retryable": False
                }
            
            # Apply caps
            lookback_days = min(lookback_days, 180)
            
            # Build parameters
            params = {
                "lookback_days": lookback_days,
                "include_factor_etfs": include_factor_etfs
            }
            
            # Call API endpoint
            endpoint = f"/api/v1/data/prices/historical/{portfolio_id}"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint,
                params=params
            )
            
            # Add meta information
            if isinstance(response, dict):
                if "metadata" not in response:
                    response["metadata"] = {}
                response["metadata"]["parameters_used"] = {
                    "portfolio_id": portfolio_id,
                    "lookback_days": lookback_days,
                    "include_factor_etfs": include_factor_etfs
                }
                
                # Count data points
                if "symbols" in response:
                    total_points = sum(
                        symbol_data.get("data_points", 0) 
                        for symbol_data in response["symbols"].values()
                    )
                    response["metadata"]["total_data_points"] = total_points
                    response["metadata"]["symbols_returned"] = len(response["symbols"])
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_prices_historical: {e}")
            return {
                "error": str(e),
                "error_type": "api",
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_analytics_overview(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get comprehensive portfolio risk analytics.

        Returns beta, volatility, Sharpe ratio, max drawdown, tracking error.
        Use when user asks about portfolio risk, performance metrics, or health.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Risk metrics with meta object
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/overview"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_analytics_overview: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_factor_exposures(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get portfolio factor exposures (Market Beta, Value, Growth, Momentum, Quality, Size, Low Vol).

        Returns factor betas showing portfolio tilts vs benchmarks.
        Use when user asks about factor exposures, style analysis, or what's driving returns.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Factor exposure data with meta object
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/factor-exposures"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_factor_exposures: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_sector_exposure(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get sector exposure breakdown with S&P 500 benchmark comparison.

        Shows over/underweights by sector vs market.
        Use when user asks about sector allocation, diversification, or comparison vs market.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Sector exposure data with benchmark comparison
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/sector-exposure"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_sector_exposure: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_correlation_matrix(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get correlation matrix showing how positions move together.

        Returns pairwise correlations between positions.
        Use when user asks about diversification, correlation risk, or if positions are related.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Correlation matrix with meta object
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/correlation-matrix"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_correlation_matrix: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_stress_test_results(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get stress test scenario results.

        Shows portfolio impact under various market conditions (tech selloff, rate shock, recession, etc.).
        Use when user asks "what if" questions or wants to see downside risk.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Stress test scenarios with impact estimates
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/stress-test"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_stress_test_results: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_company_profile(
        self,
        symbol: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get detailed company profile.

        Includes sector, industry, market cap, revenue, earnings, P/E ratio, description, and fundamentals.
        Use when user asks about a specific company or wants to understand a position better.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Company profile with 53 fields
        """
        try:
            endpoint = f"/api/v1/data/company-profiles?symbols={symbol}"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_company_profile: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    # Phase 5: Enhanced Analytics Tools (Added December 3, 2025)

    async def get_concentration_metrics(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get concentration risk metrics.

        Returns Herfindahl-Hirschman Index (HHI), top N concentration, and single-name risk.
        Use when user asks about diversification, concentration risk, or if portfolio is too concentrated.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Concentration metrics with HHI and top position analysis
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/concentration"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_concentration_metrics: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_volatility_analysis(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get volatility analytics with HAR forecasting.

        Returns realized volatility, forecasted volatility (HAR model), vol decomposition, and regime detection.
        Use when user asks about volatility trends, vol forecasts, or what's driving portfolio volatility.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Volatility analysis with realized vol, HAR forecast, and attribution
        """
        try:
            endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/volatility"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_volatility_analysis: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_target_prices(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get target prices for portfolio positions.

        Returns all target prices with upside/downside calculations for each position.
        Use when user asks about investment goals, which positions are near target, or price targets.

        Args:
            portfolio_id: Portfolio UUID

        Returns:
            Target prices per position with current vs target analysis
        """
        try:
            endpoint = f"/api/v1/target-prices/{portfolio_id}"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_target_prices: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_position_tags(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get tags for positions (e.g., 'core holdings', 'speculative', 'income', etc.).

        Returns position tags and categorizations for filtering and organization.
        Use when user asks to filter positions by strategy, category, or custom tags.

        Args:
            portfolio_id: Portfolio UUID (not used in API call but kept for consistency)

        Returns:
            All user tags with usage statistics
        """
        try:
            endpoint = f"/api/v1/tags"
            params = {"include_usage_stats": True}
            response = await self._make_request(
                method="GET",
                endpoint=endpoint,
                params=params
            )
            return response

        except Exception as e:
            logger.error(f"Error in get_position_tags: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def list_user_portfolios(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """
        List all portfolios for the authenticated user.

        Returns a list of all portfolios the user has access to, including:
        - Portfolio ID, name, and description
        - Number of positions in each portfolio
        - Total market value (if available)
        - Investment class breakdown

        Use this tool FIRST when:
        - User asks about "all my portfolios" or "my portfolios"
        - User wants to compare portfolios
        - User asks about aggregate holdings across accounts
        - User hasn't specified which portfolio they're asking about

        Returns:
            List of user portfolios with summary info
        """
        try:
            endpoint = "/api/v1/portfolios"
            response = await self._make_request(
                method="GET",
                endpoint=endpoint
            )

            # Add helper info about portfolios
            if isinstance(response, list):
                response = {
                    "portfolios": response,
                    "total_portfolios": len(response),
                    "_tool_note": f"User has {len(response)} portfolio(s). Use portfolio_id from this list to query specific portfolios."
                }

            return response

        except Exception as e:
            logger.error(f"Error in list_user_portfolios: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    # ==========================================
    # Daily Insight Tools (December 15, 2025)
    # ==========================================

    async def get_daily_movers(
        self,
        portfolio_id: str,
        threshold_pct: float = 2.0,
        include_weekly: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get today's and this week's biggest movers (gainers and losers) in the portfolio.

        Returns positions sorted by absolute daily change percentage, plus weekly data.
        Use when generating daily insights, morning briefings, or answering "what moved today/this week?"

        Args:
            portfolio_id: Portfolio UUID
            threshold_pct: Minimum absolute % change to include (default 2%)
            include_weekly: Include weekly performance data (default True)

        Returns:
            Dictionary with daily and weekly gainers, losers, and portfolio changes
        """
        try:
            # Get complete portfolio data with current prices
            portfolio_response = await self.get_portfolio_complete(portfolio_id=portfolio_id)

            if "error" in portfolio_response:
                return portfolio_response

            holdings = portfolio_response.get("data", {}).get("holdings", [])

            if not holdings:
                return {
                    "error": "No holdings found in portfolio",
                    "retryable": False
                }

            # Build symbol to weekly price map if weekly data requested
            weekly_prices = {}
            if include_weekly:
                try:
                    # Get historical prices for weekly calculation (7 days lookback for ~5 trading days)
                    historical_response = await self.get_prices_historical(
                        portfolio_id=portfolio_id,
                        lookback_days=10,  # 10 days to ensure we have 5 trading days
                        include_factor_etfs=False
                    )
                    if "error" not in historical_response:
                        prices_data = historical_response.get("data", {}).get("prices", {})
                        for symbol, price_history in prices_data.items():
                            if isinstance(price_history, list) and len(price_history) >= 5:
                                # Get the price from ~5 trading days ago (index -5 or earlier)
                                week_ago_idx = min(5, len(price_history) - 1)
                                week_ago_price = price_history[-week_ago_idx - 1].get("close") if week_ago_idx < len(price_history) else None
                                if week_ago_price:
                                    weekly_prices[symbol] = week_ago_price
                except Exception as e:
                    logger.warning(f"Could not fetch weekly prices: {e}")

            # Calculate daily and weekly changes for each position
            movers = []
            for holding in holdings:
                symbol = holding.get("symbol", "UNKNOWN")
                current_price = holding.get("current_price", 0)
                previous_close = holding.get("previous_close") or holding.get("entry_price", 0)
                market_value = holding.get("market_value", 0)
                quantity = holding.get("quantity", 0)

                # Calculate daily change
                if previous_close and previous_close > 0:
                    daily_change_pct = ((current_price - previous_close) / previous_close) * 100
                    daily_change_dollar = (current_price - previous_close) * abs(quantity)
                else:
                    daily_change_pct = 0
                    daily_change_dollar = 0

                # Calculate weekly change if data available
                weekly_change_pct = 0
                weekly_change_dollar = 0
                week_ago_price = weekly_prices.get(symbol)
                if week_ago_price and week_ago_price > 0 and current_price:
                    weekly_change_pct = ((current_price - week_ago_price) / week_ago_price) * 100
                    weekly_change_dollar = (current_price - week_ago_price) * abs(quantity)

                movers.append({
                    "symbol": symbol,
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "daily_change_pct": round(daily_change_pct, 2),
                    "daily_change_dollar": round(daily_change_dollar, 2),
                    "weekly_change_pct": round(weekly_change_pct, 2),
                    "weekly_change_dollar": round(weekly_change_dollar, 2),
                    "week_ago_price": week_ago_price,
                    "market_value": market_value,
                    "quantity": quantity
                })

            # Sort by absolute daily change percentage
            movers.sort(key=lambda x: abs(x["daily_change_pct"]), reverse=True)

            # Separate daily gainers and losers
            gainers = [m for m in movers if m["daily_change_pct"] > threshold_pct]
            losers = [m for m in movers if m["daily_change_pct"] < -threshold_pct]

            # Calculate portfolio-level daily P&L
            total_daily_pnl = sum(m["daily_change_dollar"] for m in movers)
            total_market_value = sum(m["market_value"] for m in movers)
            portfolio_daily_change_pct = (total_daily_pnl / total_market_value * 100) if total_market_value > 0 else 0

            # Weekly data
            weekly_data = {}
            if include_weekly:
                # Sort by absolute weekly change for weekly movers
                weekly_movers = sorted(movers, key=lambda x: abs(x["weekly_change_pct"]), reverse=True)
                weekly_gainers = [m for m in weekly_movers if m["weekly_change_pct"] > threshold_pct]
                weekly_losers = [m for m in weekly_movers if m["weekly_change_pct"] < -threshold_pct]

                # Calculate portfolio-level weekly P&L
                total_weekly_pnl = sum(m["weekly_change_dollar"] for m in movers)
                portfolio_weekly_change_pct = (total_weekly_pnl / total_market_value * 100) if total_market_value > 0 else 0

                weekly_data = {
                    "weekly_gainers": weekly_gainers[:5],
                    "weekly_losers": weekly_losers[:5],
                    "portfolio_weekly_change": {
                        "pnl_dollar": round(total_weekly_pnl, 2),
                        "pnl_pct": round(portfolio_weekly_change_pct, 2),
                    },
                    "biggest_weekly_winner": weekly_gainers[0] if weekly_gainers else None,
                    "biggest_weekly_loser": weekly_losers[0] if weekly_losers else None,
                }

            return {
                "data": {
                    # Daily data
                    "gainers": gainers[:5],  # Top 5 daily gainers
                    "losers": losers[:5],    # Top 5 daily losers
                    "all_movers": movers[:10],  # Top 10 by absolute daily movement
                    "portfolio_daily_change": {
                        "pnl_dollar": round(total_daily_pnl, 2),
                        "pnl_pct": round(portfolio_daily_change_pct, 2),
                        "total_market_value": round(total_market_value, 2)
                    },
                    "biggest_winner": gainers[0] if gainers else None,
                    "biggest_loser": losers[0] if losers else None,
                    # Weekly data (if included)
                    **weekly_data
                },
                "meta": {
                    "threshold_pct": threshold_pct,
                    "total_positions": len(holdings),
                    "positions_above_threshold": len(gainers) + len(losers),
                    "includes_weekly": include_weekly,
                    "weekly_data_available": bool(weekly_prices),
                    "as_of": to_utc_iso8601(utc_now())
                }
            }

        except Exception as e:
            logger.error(f"Error in get_daily_movers: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }

    async def get_morning_briefing(
        self,
        portfolio_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get the most recent morning briefing for the portfolio.

        Retrieves the latest AI-generated morning briefing including:
        - Performance summary (daily and weekly)
        - Top movers and their drivers
        - News affecting positions
        - Watch list items
        - Action recommendations

        Use when:
        - User asks "what did the briefing say?"
        - User wants to reference this morning's analysis
        - You need to recall specific findings from the briefing

        Args:
            portfolio_id: Portfolio UUID to get briefing for

        Returns:
            Dictionary with briefing title, summary, key findings, and recommendations
        """
        try:
            from sqlalchemy import select
            from app.models.ai_insights import AIInsight, InsightType
            from app.database import get_async_session
            from uuid import UUID

            portfolio_uuid = UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id

            async with get_async_session() as db:
                result = await db.execute(
                    select(AIInsight)
                    .where(AIInsight.portfolio_id == portfolio_uuid)
                    .where(AIInsight.insight_type == InsightType.MORNING_BRIEFING)
                    .order_by(AIInsight.created_at.desc())
                    .limit(1)
                )
                briefing = result.scalar_one_or_none()

                if not briefing:
                    return {
                        "error": "No morning briefing found for this portfolio",
                        "suggestion": "Generate a morning briefing first using the insights feature"
                    }

                # Format the briefing data
                return {
                    "data": {
                        "title": briefing.title,
                        "summary": briefing.summary,
                        "full_analysis": briefing.full_analysis,
                        "key_findings": briefing.key_findings or [],
                        "recommendations": briefing.recommendations or [],
                        "severity": briefing.severity.value if briefing.severity else "normal",
                        "generated_at": briefing.created_at.isoformat(),
                        "model_used": briefing.model_used,
                    },
                    "meta": {
                        "portfolio_id": str(portfolio_id),
                        "insight_type": "morning_briefing",
                        "age_hours": round((utc_now() - briefing.created_at).total_seconds() / 3600, 1),
                    }
                }

        except Exception as e:
            logger.error(f"Error in get_morning_briefing: {e}")
            return {
                "error": str(e),
                "retryable": False
            }

    async def get_market_news(
        self,
        symbols: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get market news relevant to portfolio positions.

        Fetches recent news headlines for specified symbols or all portfolio positions.
        Use when generating daily insights or answering "what's in the news?"

        Args:
            symbols: Comma-separated list of symbols (optional)
            portfolio_id: Portfolio UUID to get symbols from (optional)
            limit: Maximum number of news items (default 10, max 25)

        Returns:
            Dictionary with news items per symbol
        """
        try:
            # Get symbols from portfolio if not provided
            if not symbols and portfolio_id:
                portfolio_response = await self.get_portfolio_complete(portfolio_id=portfolio_id)
                if "error" not in portfolio_response:
                    holdings = portfolio_response.get("data", {}).get("holdings", [])
                    # Get top 10 positions by market value
                    holdings_sorted = sorted(holdings, key=lambda x: x.get("market_value", 0), reverse=True)
                    symbols = ",".join([h.get("symbol") for h in holdings_sorted[:10] if h.get("symbol")])

            if not symbols:
                return {
                    "error": "Either symbols or portfolio_id is required",
                    "retryable": False
                }

            # Apply limit cap
            limit = min(limit, 25)

            # Parse symbols
            symbol_list = [s.strip().upper() for s in symbols.split(",")][:10]

            # Try to fetch news from backend API (if endpoint exists)
            # Fall back to a structured response indicating news would go here
            try:
                params = {
                    "symbols": ",".join(symbol_list),
                    "limit": limit
                }
                response = await self._make_request(
                    method="GET",
                    endpoint="/api/v1/data/news",
                    params=params
                )
                return response
            except Exception:
                # News endpoint doesn't exist yet - return placeholder
                # This allows the LLM to use its training knowledge
                logger.info("News endpoint not available - returning guidance for LLM")
                return {
                    "data": {
                        "symbols_requested": symbol_list,
                        "news_available": False,
                        "_guidance": (
                            "News API not configured. Use your training knowledge to provide "
                            "relevant market context for these symbols. Consider: "
                            "1) Recent earnings reports, 2) Sector trends, "
                            "3) Major market events, 4) Fed/macro news affecting these stocks."
                        )
                    },
                    "meta": {
                        "symbols": symbol_list,
                        "limit": limit,
                        "as_of": to_utc_iso8601(utc_now()),
                        "source": "llm_knowledge"
                    }
                }

        except Exception as e:
            logger.error(f"Error in get_market_news: {e}")
            return {
                "error": str(e),
                "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
            }


# Import asyncio for retry logic
import asyncio
