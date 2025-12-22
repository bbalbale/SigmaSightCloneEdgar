"""
Symbol Metrics Service - Calculates and stores daily metrics for all symbols.

Part of the Symbol Factor Universe architecture (Phase 5).

This service runs early in batch processing (Phase 1.75) to:
1. Calculate returns (1d, MTD, YTD, 1m, 3m, 1y) for all symbols
2. Fetch valuations from company profiles
3. Denormalize factor exposures from symbol_factor_exposures
4. Store everything in symbol_daily_metrics for fast dashboard queries

The P&L calculator can then look up pre-computed returns instead of
recalculating for each position.

Created: 2025-12-20
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.symbol_analytics import SymbolUniverse, SymbolDailyMetrics, SymbolFactorExposure

logger = get_logger(__name__)


# =============================================================================
# Return Calculation Helpers
# =============================================================================

def calculate_return(current_price: float, reference_price: float) -> Optional[float]:
    """Calculate percentage return between two prices."""
    if reference_price is None or reference_price == 0 or current_price is None:
        return None
    return (current_price - reference_price) / reference_price


def get_month_start(d: date) -> date:
    """Get the first day of the month for a given date."""
    return date(d.year, d.month, 1)


def get_year_start(d: date) -> date:
    """Get the first day of the year for a given date."""
    return date(d.year, 1, 1)


def get_previous_trading_day(d: date) -> date:
    """
    Get the previous trading day (skip weekends).
    Note: This is a simplified version. For production, use a trading calendar.
    """
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:  # Saturday = 5, Sunday = 6
        prev -= timedelta(days=1)
    return prev


# =============================================================================
# Main Service Functions
# =============================================================================

async def calculate_symbol_metrics(
    calculation_date: date,
    price_cache=None,
) -> Dict[str, Any]:
    """
    Calculate returns and metrics for all symbols in the universe.

    This is the main entry point for Phase 1.75 of batch processing.
    MUST run after market data is loaded (Phase 1) and before P&L calculation (Phase 2).

    Args:
        calculation_date: The date to calculate metrics for
        price_cache: Optional PriceCache instance for efficient price lookups

    Returns:
        Dict with symbols_updated count and any errors
    """
    logger.info(f"Phase 1.75: Calculating symbol metrics for {calculation_date}")

    async with AsyncSessionLocal() as db:
        # Step 1: Get all active symbols from universe
        symbols = await get_all_active_symbols(db)
        logger.info(f"Found {len(symbols)} active symbols in universe")

        if not symbols:
            return {'symbols_updated': 0, 'errors': ['No active symbols found']}

        # Step 2: Bulk fetch prices for all symbols
        prices_data = await bulk_fetch_prices(db, symbols, calculation_date, price_cache)
        logger.info(f"Loaded prices for {len(prices_data)} symbols")

        # Step 3: Bulk fetch company profiles
        profiles = await bulk_fetch_company_profiles(db, symbols)
        logger.info(f"Loaded profiles for {len(profiles)} symbols")

        # Step 4: Bulk fetch factor exposures (from Phase 1.5)
        factors = await bulk_fetch_factor_exposures(db, symbols, calculation_date)
        logger.info(f"Loaded factor exposures for {len(factors)} symbols")

        # Step 5: Calculate returns and build metrics
        metrics_to_upsert = []
        errors = []

        for symbol in symbols:
            try:
                symbol_prices = prices_data.get(symbol, {})
                profile = profiles.get(symbol, {})
                symbol_factors = factors.get(symbol, {})

                # Calculate returns
                current_price = symbol_prices.get('close')
                prev_close = symbol_prices.get('prev_close')
                month_start_price = symbol_prices.get('month_start')
                year_start_price = symbol_prices.get('year_start')
                price_1m = symbol_prices.get('price_1m')
                price_3m = symbol_prices.get('price_3m')
                price_1y = symbol_prices.get('price_1y')

                return_1d = calculate_return(current_price, prev_close)
                return_mtd = calculate_return(current_price, month_start_price)
                return_ytd = calculate_return(current_price, year_start_price)
                return_1m = calculate_return(current_price, price_1m)
                return_3m = calculate_return(current_price, price_3m)
                return_1y = calculate_return(current_price, price_1y)

                # Calculate data quality score
                data_quality = calculate_data_quality_score(
                    has_price=current_price is not None,
                    has_returns=return_1d is not None,
                    has_profile=bool(profile),
                    has_factors=bool(symbol_factors)
                )

                metrics = {
                    'symbol': symbol,
                    'metrics_date': calculation_date,
                    # Price & Returns
                    'current_price': current_price,
                    'return_1d': return_1d,
                    'return_mtd': return_mtd,
                    'return_ytd': return_ytd,
                    'return_1m': return_1m,
                    'return_3m': return_3m,
                    'return_1y': return_1y,
                    # Company Profile
                    'market_cap': profile.get('market_cap'),
                    'enterprise_value': profile.get('enterprise_value'),
                    'pe_ratio': profile.get('pe_ratio'),
                    'ps_ratio': profile.get('ps_ratio'),
                    'pb_ratio': profile.get('pb_ratio'),
                    'sector': profile.get('sector'),
                    'industry': profile.get('industry'),
                    'company_name': profile.get('company_name'),
                    # Ridge Factors
                    'factor_value': symbol_factors.get('Value'),
                    'factor_growth': symbol_factors.get('Growth'),
                    'factor_momentum': symbol_factors.get('Momentum'),
                    'factor_quality': symbol_factors.get('Quality'),
                    'factor_size': symbol_factors.get('Size'),
                    'factor_low_vol': symbol_factors.get('Low Volatility'),
                    # Spread Factors
                    'factor_growth_value_spread': symbol_factors.get('Growth-Value Spread'),
                    'factor_momentum_spread': symbol_factors.get('Momentum Spread'),
                    'factor_size_spread': symbol_factors.get('Size Spread'),
                    'factor_quality_spread': symbol_factors.get('Quality Spread'),
                    # Metadata
                    'data_quality_score': data_quality,
                    'updated_at': datetime.now(timezone.utc),
                }
                metrics_to_upsert.append(metrics)

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.warning(f"Error calculating metrics for {symbol}: {e}")

        # Step 6: Bulk upsert to database
        if metrics_to_upsert:
            upserted_count = await bulk_upsert_metrics(db, metrics_to_upsert)
            logger.info(f"Upserted {upserted_count} symbol metrics")
        else:
            upserted_count = 0

        await db.commit()

        return {
            'symbols_updated': upserted_count,
            'symbols_total': len(symbols),
            'errors': errors if errors else None
        }


async def get_all_active_symbols(db: AsyncSession) -> List[str]:
    """
    Get all symbols that need metrics calculation.

    Sources:
    1. symbol_universe (active symbols from Phase 1.5)
    2. market_data_cache (full universe - S&P 500, Nasdaq 100, Russell 2000, etc.)

    Using both sources ensures we calculate metrics even if Phase 1.5 hasn't
    populated symbol_universe yet, or if there are symbols in market_data_cache
    that haven't been added to the universe.
    """
    from sqlalchemy import distinct
    from app.models.market_data import MarketDataCache

    # Get symbols from symbol_universe
    universe_stmt = select(SymbolUniverse.symbol).where(SymbolUniverse.is_active == True)
    universe_result = await db.execute(universe_stmt)
    universe_symbols = {row[0] for row in universe_result.fetchall()}

    # Get symbols from market_data_cache (full universe)
    cache_stmt = select(distinct(MarketDataCache.symbol)).where(
        MarketDataCache.symbol.isnot(None),
        MarketDataCache.symbol != ''
    )
    cache_result = await db.execute(cache_stmt)
    cache_symbols = {row[0] for row in cache_result.fetchall()}

    # Union of both sources
    all_symbols = list(universe_symbols | cache_symbols)

    logger.info(
        f"Found {len(all_symbols)} symbols for metrics calculation "
        f"(universe: {len(universe_symbols)}, market_data_cache: {len(cache_symbols)})"
    )
    return all_symbols


async def bulk_fetch_prices(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date,
    price_cache=None
) -> Dict[str, Dict[str, float]]:
    """
    Bulk fetch price data for all symbols.

    Returns dict: {symbol: {close, prev_close, month_start, year_start, ...}}
    """
    prices_data = {}

    # Calculate reference dates
    prev_day = get_previous_trading_day(calculation_date)
    month_start = get_month_start(calculation_date)
    year_start = get_year_start(calculation_date)
    date_1m = calculation_date - timedelta(days=30)
    date_3m = calculation_date - timedelta(days=90)
    date_1y = calculation_date - timedelta(days=365)

    # Use price cache if available
    if price_cache:
        for symbol in symbols:
            close = price_cache.get(symbol, calculation_date)
            prev_close = price_cache.get(symbol, prev_day)
            month_start_price = price_cache.get(symbol, month_start)
            year_start_price = price_cache.get(symbol, year_start)
            price_1m_val = price_cache.get(symbol, date_1m)
            price_3m_val = price_cache.get(symbol, date_3m)
            price_1y_val = price_cache.get(symbol, date_1y)

            prices_data[symbol] = {
                'close': close,
                'prev_close': prev_close,
                'month_start': month_start_price,
                'year_start': year_start_price,
                'price_1m': price_1m_val,
                'price_3m': price_3m_val,
                'price_1y': price_1y_val,
            }
        return prices_data

    # Fallback: Query from market_data_cache
    all_dates = [calculation_date, prev_day, month_start, year_start, date_1m, date_3m, date_1y]

    stmt = text("""
        SELECT symbol, date, close
        FROM market_data_cache
        WHERE symbol = ANY(:symbols)
        AND date = ANY(:dates)
        AND close > 0
    """)

    result = await db.execute(stmt, {'symbols': symbols, 'dates': all_dates})
    rows = result.fetchall()

    # Build lookup
    price_lookup = {}
    for symbol, dt, close in rows:
        if symbol not in price_lookup:
            price_lookup[symbol] = {}
        price_lookup[symbol][dt] = float(close)

    # Map to expected structure
    for symbol in symbols:
        symbol_prices = price_lookup.get(symbol, {})
        prices_data[symbol] = {
            'close': symbol_prices.get(calculation_date),
            'prev_close': symbol_prices.get(prev_day),
            'month_start': symbol_prices.get(month_start),
            'year_start': symbol_prices.get(year_start),
            'price_1m': symbol_prices.get(date_1m),
            'price_3m': symbol_prices.get(date_3m),
            'price_1y': symbol_prices.get(date_1y),
        }

    return prices_data


async def bulk_fetch_company_profiles(
    db: AsyncSession,
    symbols: List[str]
) -> Dict[str, Dict[str, Any]]:
    """
    Bulk fetch company profile data for all symbols.

    Returns dict: {symbol: {market_cap, pe_ratio, sector, ...}}

    Note: Only fetches columns known to exist in company_profiles table.
    """
    profiles = {}

    # Use only columns known to exist in company_profiles
    stmt = text("""
        SELECT
            symbol,
            company_name,
            sector,
            industry,
            market_cap,
            pe_ratio
        FROM company_profiles
        WHERE symbol = ANY(:symbols)
    """)

    try:
        result = await db.execute(stmt, {'symbols': symbols})
        rows = result.fetchall()

        for row in rows:
            profiles[row[0]] = {
                'company_name': row[1],
                'sector': row[2],
                'industry': row[3],
                'market_cap': float(row[4]) if row[4] else None,
                'pe_ratio': float(row[5]) if row[5] else None,
                'ps_ratio': None,  # Not available in current schema
                'pb_ratio': None,  # Not available in current schema
                'enterprise_value': None,  # Not available in current schema
            }
    except Exception as e:
        logger.warning(f"Error fetching company profiles: {e}")
        # Return empty dict on failure - metrics will still work without profiles

    return profiles


async def bulk_fetch_factor_exposures(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date
) -> Dict[str, Dict[str, float]]:
    """
    Bulk fetch factor exposures for all symbols.

    Returns dict: {symbol: {factor_name: beta_value}}
    """
    factors = {}

    stmt = text("""
        SELECT
            sfe.symbol,
            fd.name as factor_name,
            sfe.beta_value
        FROM symbol_factor_exposures sfe
        JOIN factor_definitions fd ON sfe.factor_id = fd.id
        WHERE sfe.symbol = ANY(:symbols)
        AND sfe.calculation_date = :calc_date
    """)

    result = await db.execute(stmt, {'symbols': symbols, 'calc_date': calculation_date})
    rows = result.fetchall()

    for symbol, factor_name, beta_value in rows:
        if symbol not in factors:
            factors[symbol] = {}
        factors[symbol][factor_name] = float(beta_value)

    return factors


def calculate_data_quality_score(
    has_price: bool,
    has_returns: bool,
    has_profile: bool,
    has_factors: bool
) -> float:
    """Calculate a 0-100 data quality score based on data completeness."""
    score = 0
    if has_price:
        score += 30  # Price is critical
    if has_returns:
        score += 30  # Returns are critical
    if has_profile:
        score += 20  # Profile data is helpful
    if has_factors:
        score += 20  # Factor data is helpful
    return score


async def bulk_upsert_metrics(
    db: AsyncSession,
    metrics_list: List[Dict[str, Any]]
) -> int:
    """
    Bulk upsert symbol_daily_metrics using PostgreSQL ON CONFLICT.

    Returns count of upserted records.
    """
    if not metrics_list:
        return 0

    # Use PostgreSQL insert with ON CONFLICT DO UPDATE
    stmt = insert(SymbolDailyMetrics).values(metrics_list)

    # Update all columns on conflict (except primary key)
    update_dict = {
        col.name: stmt.excluded[col.name]
        for col in SymbolDailyMetrics.__table__.columns
        if col.name != 'symbol'  # Primary key
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=['symbol'],
        set_=update_dict
    )

    await db.execute(stmt)
    return len(metrics_list)


# =============================================================================
# Utility Functions for P&L Calculation
# =============================================================================

async def load_symbol_returns(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date
) -> Dict[str, float]:
    """
    Load pre-calculated daily returns for P&L calculation.

    This is used by pnl_calculator.py to look up returns instead of
    recalculating them for each position.

    Returns: {symbol: return_1d}
    """
    stmt = select(
        SymbolDailyMetrics.symbol,
        SymbolDailyMetrics.return_1d
    ).where(
        and_(
            SymbolDailyMetrics.symbol.in_(symbols),
            SymbolDailyMetrics.metrics_date == calculation_date
        )
    )

    result = await db.execute(stmt)
    return {
        row[0]: float(row[1]) if row[1] else 0.0
        for row in result.fetchall()
    }


async def get_symbol_metrics(
    db: AsyncSession,
    symbol: str
) -> Optional[Dict[str, Any]]:
    """Get full metrics for a single symbol."""
    stmt = select(SymbolDailyMetrics).where(SymbolDailyMetrics.symbol == symbol)
    result = await db.execute(stmt)
    metrics = result.scalar()

    if not metrics:
        return None

    return {
        'symbol': metrics.symbol,
        'metrics_date': metrics.metrics_date,
        'current_price': float(metrics.current_price) if metrics.current_price else None,
        'return_1d': float(metrics.return_1d) if metrics.return_1d else None,
        'return_mtd': float(metrics.return_mtd) if metrics.return_mtd else None,
        'return_ytd': float(metrics.return_ytd) if metrics.return_ytd else None,
        'market_cap': float(metrics.market_cap) if metrics.market_cap else None,
        'sector': metrics.sector,
        'industry': metrics.industry,
        'company_name': metrics.company_name,
        'data_quality_score': float(metrics.data_quality_score) if metrics.data_quality_score else None,
    }
