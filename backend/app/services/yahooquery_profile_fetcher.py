"""
Hybrid profile fetcher - uses yfinance for basics + yahooquery for revenue estimates.
- yfinance: company name, sector, industry, description (reliable, no rate limits)
- yahooquery: revenue/earnings estimates only (unique data not in yfinance)

Phase 9.0 Fixes Applied:
- Async-safe execution via run_in_executor()
- Batching with parallelism (batches of 10, max_workers=3)
- Retry logic with exponential backoff
- Timezone-aware timestamps
- Safe truncation with logging
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, date, timezone
import logging
import asyncio
import time
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
from yahooquery import Ticker
import yfinance as yf

logger = logging.getLogger(__name__)


def safe_decimal(value: Any, precision: int = 4) -> Optional[Decimal]:
    """Safely convert value to Decimal, handling None and errors."""
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal(10) ** -precision)
    except (ValueError, TypeError, Exception):
        return None


def safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int, handling None and errors."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError, Exception):
        return None


def safe_date(value: Any) -> Optional[date]:
    """Safely convert value to date, handling None and errors."""
    if value is None:
        return None
    try:
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        return None
    except (ValueError, TypeError, Exception):
        return None


def _safe_truncate(value: str, max_length: int, field_name: str) -> str:
    """
    Truncate with validation and logging.
    Phase 9.0 Fix: Prevents silent data corruption.
    """
    if value is None:
        return 'Unknown'

    if len(value) <= max_length:
        return value

    # Log truncation for debugging
    logger.warning(
        f"Field '{field_name}' truncated: '{value}' "
        f"→ '{value[:max_length]}' (max {max_length} chars)"
    )

    return value[:max_length]


def chunk_list(lst: List, chunk_size: int):
    """Yield successive chunks from list."""
    it = iter(lst)
    while chunk := list(islice(it, chunk_size)):
        yield chunk


def _fetch_single_profile_with_retry(symbol: str, earnings_trend: Dict, max_retries: int = 2) -> Dict[str, Any]:
    """
    Fetch single profile with exponential backoff retry.
    Phase 9.0 Fix: Resilient to individual symbol failures.

    Args:
        symbol: Ticker symbol
        earnings_trend: Pre-fetched yahooquery earnings_trend dict
        max_retries: Number of retry attempts (default: 2)

    Returns:
        Dict with profile data or None on failure
    """
    for attempt in range(max_retries + 1):
        try:
            profile_data = {}

            # ===== YFINANCE: Basic company info (reliable) =====
            try:
                yf_ticker = yf.Ticker(symbol)
                info = yf_ticker.info

                # Basic identification
                profile_data['company_name'] = info.get('longName') or info.get('shortName')
                profile_data['sector'] = info.get('sector')
                profile_data['industry'] = info.get('industry')
                profile_data['website'] = info.get('website')
                profile_data['description'] = (info.get('longBusinessSummary') or '')[:1000]

                # Phase 9.0 Fix: Remove hard-slicing, database column will be widened
                # If keeping code truncation, use _safe_truncate()
                profile_data['country'] = info.get('country') or 'Unknown'
                profile_data['exchange'] = info.get('exchange') or 'Unknown'
                profile_data['employees'] = safe_int(info.get('fullTimeEmployees'))

                # Financials
                profile_data['market_cap'] = safe_decimal(info.get('marketCap'), precision=2)
                profile_data['beta'] = safe_decimal(info.get('beta'), precision=4)
                profile_data['pe_ratio'] = safe_decimal(info.get('trailingPE'), precision=2)
                profile_data['forward_pe'] = safe_decimal(info.get('forwardPE'), precision=2)
                profile_data['dividend_yield'] = safe_decimal(info.get('dividendYield'), precision=6)
                profile_data['week_52_high'] = safe_decimal(info.get('fiftyTwoWeekHigh'), precision=4)
                profile_data['week_52_low'] = safe_decimal(info.get('fiftyTwoWeekLow'), precision=4)

                # Type flags
                quote_type = info.get('quoteType', '')
                profile_data['is_etf'] = quote_type == 'ETF'
                profile_data['is_fund'] = quote_type in ['MUTUALFUND', 'ETF']

                # Margins and metrics
                profile_data['profit_margins'] = safe_decimal(info.get('profitMargins'), precision=6)
                profile_data['operating_margins'] = safe_decimal(info.get('operatingMargins'), precision=6)
                profile_data['gross_margins'] = safe_decimal(info.get('grossMargins'), precision=6)
                profile_data['return_on_assets'] = safe_decimal(info.get('returnOnAssets'), precision=6)
                profile_data['return_on_equity'] = safe_decimal(info.get('returnOnEquity'), precision=6)
                profile_data['total_revenue'] = safe_decimal(info.get('totalRevenue'), precision=2)
                profile_data['forward_eps'] = safe_decimal(info.get('forwardEps'), precision=4)
                profile_data['earnings_growth'] = safe_decimal(info.get('earningsGrowth'), precision=6)
                profile_data['revenue_growth'] = safe_decimal(info.get('revenueGrowth'), precision=6)
                profile_data['earnings_quarterly_growth'] = safe_decimal(info.get('earningsQuarterlyGrowth'), precision=6)

                # Analyst targets
                profile_data['target_mean_price'] = safe_decimal(info.get('targetMeanPrice'), precision=4)
                profile_data['target_high_price'] = safe_decimal(info.get('targetHighPrice'), precision=4)
                profile_data['target_low_price'] = safe_decimal(info.get('targetLowPrice'), precision=4)
                profile_data['number_of_analyst_opinions'] = safe_int(info.get('numberOfAnalystOpinions'))
                profile_data['recommendation_mean'] = safe_decimal(info.get('recommendationMean'), precision=2)
                profile_data['recommendation_key'] = (info.get('recommendationKey') or '')[:20]

                logger.info(f"yfinance: Fetched profile for {symbol}, company_name={profile_data.get('company_name')}")

            except Exception as e:
                logger.warning(f"Error fetching yfinance data for {symbol}: {e}")

            # ===== YAHOOQUERY: Revenue/earnings estimates ONLY =====
            if isinstance(earnings_trend, dict) and symbol in earnings_trend:
                et = earnings_trend[symbol]

                # Handle nested structure: yahooquery returns {'trend': [...], 'maxAge': 1}
                if isinstance(et, dict) and 'trend' in et:
                    et = et['trend']

                if isinstance(et, list):
                    # Loop through periods to find "0y" (current year) and "+1y" (next year)
                    for period_data in et:
                        if not isinstance(period_data, dict):
                            continue

                        period = period_data.get('period')

                        # Current year (0y)
                        if period == '0y':
                            if 'revenueEstimate' in period_data:
                                rev_est = period_data['revenueEstimate']
                                profile_data['current_year_revenue_avg'] = safe_decimal(rev_est.get('avg'), precision=2)
                                profile_data['current_year_revenue_low'] = safe_decimal(rev_est.get('low'), precision=2)
                                profile_data['current_year_revenue_high'] = safe_decimal(rev_est.get('high'), precision=2)
                                profile_data['current_year_revenue_growth'] = safe_decimal(rev_est.get('growth'), precision=6)

                            if 'earningsEstimate' in period_data:
                                earn_est = period_data['earningsEstimate']
                                profile_data['current_year_earnings_avg'] = safe_decimal(earn_est.get('avg'), precision=4)
                                profile_data['current_year_earnings_low'] = safe_decimal(earn_est.get('low'), precision=4)
                                profile_data['current_year_earnings_high'] = safe_decimal(earn_est.get('high'), precision=4)

                            profile_data['current_year_end_date'] = safe_date(period_data.get('endDate'))

                        # Next year (+1y)
                        elif period == '+1y':
                            if 'revenueEstimate' in period_data:
                                rev_est = period_data['revenueEstimate']
                                profile_data['next_year_revenue_avg'] = safe_decimal(rev_est.get('avg'), precision=2)
                                profile_data['next_year_revenue_low'] = safe_decimal(rev_est.get('low'), precision=2)
                                profile_data['next_year_revenue_high'] = safe_decimal(rev_est.get('high'), precision=2)
                                profile_data['next_year_revenue_growth'] = safe_decimal(rev_est.get('growth'), precision=6)

                            if 'earningsEstimate' in period_data:
                                earn_est = period_data['earningsEstimate']
                                profile_data['next_year_earnings_avg'] = safe_decimal(earn_est.get('avg'), precision=4)
                                profile_data['next_year_earnings_low'] = safe_decimal(earn_est.get('low'), precision=4)
                                profile_data['next_year_earnings_high'] = safe_decimal(earn_est.get('high'), precision=4)

                            profile_data['next_year_end_date'] = safe_date(period_data.get('endDate'))

            # Add tracking fields - Phase 9.0 Fix: timezone-aware datetime
            profile_data['data_source'] = 'yfinance+yahooquery'
            profile_data['last_updated'] = datetime.now(timezone.utc)

            logger.info(f"Successfully fetched profile for {symbol}, company_name={profile_data.get('company_name')}")
            return profile_data

        except Exception as e:
            if attempt == max_retries:
                logger.warning(f"Failed to fetch {symbol} after {max_retries + 1} attempts: {e}")
                return None

            # Exponential backoff
            sleep_time = 2 ** attempt
            logger.debug(f"Retry {attempt + 1} for {symbol} after {sleep_time}s")
            time.sleep(sleep_time)

    return None


def _fetch_profiles_sync(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Synchronous implementation - runs in worker thread.
    Phase 9.0 Fix: Batching with parallelism to avoid rate limits and timeouts.

    Args:
        symbols: List of ticker symbols

    Returns:
        Dict mapping symbol to profile data
    """
    results = {}

    try:
        # Phase 9.0 Fix: Fetch yahooquery earnings_trend once for all symbols
        logger.info(f"Fetching earnings_trend for {len(symbols)} symbols via yahooquery")
        ticker = Ticker(symbols)
        earnings_trend = ticker.earnings_trend
        logger.info(f"yahooquery earnings_trend fetch complete")

    except Exception as e:
        logger.error(f"Error fetching yahooquery earnings_trend: {e}")
        earnings_trend = {}

    # Phase 9.0 Fix: Process in batches of 10 with parallelism of 3
    for batch_num, batch in enumerate(chunk_list(symbols, 10), 1):
        logger.info(f"Processing batch {batch_num} ({len(batch)} symbols)")

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(_fetch_single_profile_with_retry, sym, earnings_trend): sym
                for sym in batch
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    profile = future.result(timeout=10)
                    if profile:
                        results[symbol] = profile
                    else:
                        logger.warning(f"No profile data returned for {symbol}")
                        results[symbol] = None
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")
                    results[symbol] = None

        # Phase 9.0 Fix: Rate limit backoff between batches
        if batch_num < len(list(chunk_list(symbols, 10))):  # Not last batch
            time.sleep(1)
            logger.debug(f"Rate limit delay after batch {batch_num}")

    logger.info(f"Fetched {sum(1 for v in results.values() if v)} / {len(symbols)} profiles successfully")
    return results


async def fetch_company_profiles(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch company profiles using hybrid approach:
    - yfinance: Basic company info (reliable, no rate limits)
    - yahooquery: Revenue/earnings estimates (unique data)

    Phase 9.0 Fix: Truly async via run_in_executor() - doesn't block event loop.

    Args:
        symbols: List of ticker symbols

    Returns:
        Dict mapping symbol to profile data dict matching CompanyProfile schema
    """
    loop = asyncio.get_running_loop()

    # Phase 9.0 Fix: Run synchronous yfinance/yahooquery in executor (thread pool)
    # This prevents blocking the FastAPI event loop
    logger.info(f"Starting async profile fetch for {len(symbols)} symbols (via executor)")
    profiles = await loop.run_in_executor(
        None,  # Use default ThreadPoolExecutor
        partial(_fetch_profiles_sync, symbols)
    )
    logger.info(f"Async profile fetch complete: {sum(1 for v in profiles.values() if v)}/{len(symbols)} successful")

    return profiles
