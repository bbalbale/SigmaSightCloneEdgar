"""
Hybrid profile fetcher - uses yfinance for basics + yahooquery for revenue estimates.
- yfinance: company name, sector, industry, description (reliable, no rate limits)
- yahooquery: revenue/earnings estimates only (unique data not in yfinance)
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, date
import logging
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


async def fetch_company_profiles(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch company profiles using hybrid approach:
    - yfinance: Basic company info (reliable, no rate limits)
    - yahooquery: Revenue/earnings estimates (unique data)

    Args:
        symbols: List of ticker symbols

    Returns:
        Dict mapping symbol to profile data dict matching CompanyProfile schema
    """
    results = {}

    try:
        # Use yahooquery ONLY for earnings_trend (revenue/earnings estimates)
        ticker = Ticker(symbols)
        earnings_trend = ticker.earnings_trend

        # Process each symbol
        for symbol in symbols:
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
                    profile_data['country'] = (info.get('country') or '')[:10]
                    profile_data['exchange'] = (info.get('exchange') or '')[:20]
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

                # Add tracking fields
                profile_data['data_source'] = 'yfinance+yahooquery'
                profile_data['last_updated'] = datetime.utcnow()

                results[symbol] = profile_data
                logger.info(f"Successfully fetched profile for {symbol}, company_name={profile_data.get('company_name')}")

            except Exception as e:
                logger.warning(f"Error processing profile for {symbol}: {e}")
                # Return partial data if available
                if profile_data:
                    results[symbol] = profile_data
                continue

    except Exception as e:
        logger.error(f"Error fetching company profiles: {e}")

    return results
