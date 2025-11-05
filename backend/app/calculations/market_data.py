"""
Market Data Calculation Functions - Section 1.4.1
Implements core position valuation and P&L calculations with database integration
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import MarketDataCache
from app.models.positions import Position, PositionType
from app.services.market_data_service import market_data_service
from app.core.logging import get_logger

logger = get_logger(__name__)


def is_options_position(position: Position) -> bool:
    """
    Determine if a position is an options position
    
    Args:
        position: Position object
        
    Returns:
        True if position is options (LC, LP, SC, SP), False if stock (LONG, SHORT)
    """
    investment_class = getattr(position, "investment_class", None)
    if investment_class:
        normalized_class = str(investment_class).upper()
        if normalized_class == "PRIVATE":
            return False
        if normalized_class == "OPTIONS":
            return position.position_type in {
                PositionType.LC,
                PositionType.LP,
                PositionType.SC,
                PositionType.SP,
            }

    return position.position_type in {
        PositionType.LC,
        PositionType.LP,
        PositionType.SC,
        PositionType.SP,
    }


async def calculate_position_market_value(
    position: Position, 
    current_price: Decimal
) -> Dict[str, Decimal]:
    """
    Calculate current market value and exposure for a position
    
    Args:
        position: Position object
        current_price: Current market price (Decimal)
        
    Returns:
        Dictionary with:
        - market_value: Signed value (negative for shorts, positive for longs)
        - exposure: Same as market_value (quantity × price × multiplier) 
        - unrealized_pnl: Current value - cost basis
        - cost_basis: Entry price × quantity × multiplier
        - price_per_share: Current price per share/contract
    """
    logger.debug(f"Calculating market value for {position.symbol} at price ${current_price}")
    
    # Options: 1 contract = 100 shares multiplier
    # Stocks: multiplier = 1
    multiplier = Decimal('100') if is_options_position(position) else Decimal('1')
    
    # Market value should be signed - negative for shorts, positive for longs
    # For SHORT positions: negative quantity × positive price = negative market value
    # For LONG positions: positive quantity × positive price = positive market value
    market_value = position.quantity * current_price * multiplier
    
    # Exposure is the same as market value (signed)
    exposure = market_value
    
    # Cost basis calculation
    cost_basis = position.quantity * position.entry_price * multiplier
    
    # Unrealized P&L = current exposure - cost basis
    unrealized_pnl = exposure - cost_basis
    
    result = {
        "market_value": market_value,
        "exposure": exposure,
        "unrealized_pnl": unrealized_pnl,
        "cost_basis": cost_basis,
        "price_per_share": current_price,
        "multiplier": multiplier
    }
    
    logger.debug(f"Market value calculation result for {position.symbol}: {result}")
    return result


@dataclass(frozen=True)
class PositionValuation:
    """
    Container for per-position valuation metrics used across services.
    """
    price: Optional[Decimal]
    multiplier: Decimal
    market_value: Decimal
    abs_market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal


def get_position_valuation(
    position: Position,
    *,
    price: Optional[Decimal] = None
) -> PositionValuation:
    """
    Calculate canonical valuation metrics for a position.

    Args:
        position: Position instance.
        price: Optional override price to use instead of last_price / entry_price.

    Returns:
        PositionValuation dataclass with signed and absolute market value,
        cost basis, unrealized P&L, and the price used.
    """
    quantity = position.quantity or Decimal("0")
    multiplier = Decimal("100") if is_options_position(position) else Decimal("1")

    resolved_price: Optional[Decimal]
    if price is not None:
        resolved_price = price
    elif position.last_price is not None:
        resolved_price = position.last_price
    else:
        resolved_price = position.entry_price

    if resolved_price is None:
        market_value = Decimal("0")
    else:
        market_value = quantity * resolved_price * multiplier

    cost_basis = Decimal("0")
    unrealized_pnl = Decimal("0")
    if position.entry_price is not None:
        cost_basis = quantity * position.entry_price * multiplier
        if resolved_price is not None:
            unrealized_pnl = market_value - cost_basis

    return PositionValuation(
        price=resolved_price,
        multiplier=multiplier,
        market_value=market_value,
        abs_market_value=abs(market_value),
        cost_basis=cost_basis,
        unrealized_pnl=unrealized_pnl,
    )


def get_position_value(
    position: Position,
    signed: bool = True,
    recalculate: bool = False
) -> Decimal:
    """
    Canonical position market value retrieval - SINGLE SOURCE OF TRUTH

    This is the AUTHORITATIVE function for position valuation used throughout
    the codebase. All other modules should call this instead of implementing
    their own valuation logic.

    Replaces:
    - factor_utils.get_position_market_value() (returns absolute)
    - factor_utils.get_position_signed_exposure() (returns signed)
    - Inline calculations in stress_testing, market_risk, etc.

    Args:
        position: Position object
        signed: If True, negative for shorts; if False, absolute value
        recalculate: Force recalculation vs using cached position.market_value

    Returns:
        Signed or absolute market value as Decimal

    Examples:
        >>> # Long stock position
        >>> pos = Position(quantity=100, last_price=Decimal('50.00'),
        ...                position_type=PositionType.LONG, market_value=Decimal('5000.00'))
        >>> get_position_value(pos, signed=True)  # Decimal('5000.00')
        >>> get_position_value(pos, signed=False)  # Decimal('5000.00')

        >>> # Short stock position
        >>> pos = Position(quantity=Decimal('-100'), last_price=Decimal('50.00'),
        ...                position_type=PositionType.SHORT, market_value=Decimal('-5000.00'))
        >>> get_position_value(pos, signed=True)  # Decimal('-5000.00')
        >>> get_position_value(pos, signed=False)  # Decimal('5000.00') - absolute

        >>> # Long call option (100x multiplier)
        >>> pos = Position(quantity=Decimal('10'), last_price=Decimal('5.00'),
        ...                position_type=PositionType.LC, market_value=Decimal('5000.00'))
        >>> get_position_value(pos, signed=True)  # Decimal('5000.00') - 10 × 5 × 100

    Note:
        - Uses cached position.market_value if available and recalculate=False
        - Automatically applies 100x multiplier for options (LC, LP, SC, SP)
        - Quantity sign determines position direction (negative for shorts)
        - This function is synchronous for performance (no async overhead)
    """
    # Use cached value if available and not forcing recalculation
    if not recalculate and position.market_value is not None:
        value = position.market_value
        return value if signed else abs(value)

    valuation = get_position_valuation(position)
    return valuation.market_value if signed else valuation.abs_market_value


async def get_returns(
    db: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date,
    align_dates: bool = True
) -> pd.DataFrame:
    """
    Fetch aligned returns DataFrame for multiple symbols - CANONICAL RETURN FETCHER

    This is the AUTHORITATIVE function for return retrieval used by all regression
    modules. Replaces duplicate implementations in market_beta, interest_rate_beta,
    factors, etc.

    Replaces:
    - market_beta.fetch_returns_for_beta() (fetch + pct_change inline)
    - interest_rate_beta.fetch_tlt_returns() (fetch + pct_change inline)
    - factors.fetch_factor_returns() (fetch + pct_change inline)

    Args:
        db: Database session
        symbols: List of symbols to fetch (e.g., ['SPY', 'AAPL', 'GOOGL'])
        start_date: Start date for returns
        end_date: End date for returns
        align_dates: If True, drop dates where ANY symbol is missing (ensures aligned data)

    Returns:
        DataFrame with dates as index, symbols as columns, containing daily returns

    Examples:
        >>> # Fetch SPY and AAPL returns for regression
        >>> df = await get_returns(db, ['SPY', 'AAPL'], start_date, end_date)
        >>> spy_returns = df['SPY']  # Series of SPY daily returns
        >>> aapl_returns = df['AAPL']  # Series of AAPL daily returns
        >>>
        >>> # For beta calculation (must be aligned)
        >>> df = await get_returns(db, ['NVDA', 'SPY'], start_date, end_date, align_dates=True)
        >>> # df has no NaN values - all dates have both NVDA and SPY
        >>>
        >>> # For exploratory analysis (allow missing data)
        >>> df = await get_returns(db, ['AAPL', 'OBSCURE'], start_date, end_date, align_dates=False)
        >>> # df may have NaN for OBSCURE on some dates

    Performance:
        - Single database query for all symbols
        - Efficient pandas vectorized pct_change()
        - Date alignment done in-memory (fast)

    Note:
        - Returns are calculated as: (price_today - price_yesterday) / price_yesterday
        - align_dates=True is REQUIRED for regressions (no NaN allowed)
        - align_dates=False useful for exploratory analysis
    """
    logger.info(f"Fetching returns for {len(symbols)} symbols from {start_date} to {end_date}")

    # Fetch historical prices using existing canonical function
    price_df = await fetch_historical_prices(
        db=db,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )

    if price_df.empty:
        logger.warning("No price data available for return calculations")
        return pd.DataFrame()

    # Optionally align dates (drop rows with ANY missing values)
    if align_dates:
        rows_before = len(price_df)
        price_df = price_df.dropna()
        rows_after = len(price_df)

        if rows_after < rows_before:
            logger.info(
                f"Date alignment: dropped {rows_before - rows_after} rows with missing data "
                f"({rows_after} aligned dates remain)"
            )

        if price_df.empty:
            logger.warning("No overlapping dates found across all symbols after alignment")
            return pd.DataFrame()

    # Calculate daily returns
    # Using fill_method=None to avoid FutureWarning (Pandas 2.1+)
    returns_df = price_df.pct_change(fill_method=None).dropna()

    logger.info(
        f"Calculated returns for {len(symbols)} symbols over {len(returns_df)} days "
        f"(aligned={align_dates})"
    )

    return returns_df


async def get_previous_trading_day_price(
    db: AsyncSession, 
    symbol: str,
    current_date: Optional[date] = None,
    max_lookback_days: int = 5
) -> Optional[Tuple[Decimal, date]]:
    """
    Get the most recent price before current_date from market_data_cache
    
    Args:
        db: Database session
        symbol: Symbol to lookup
        current_date: Date to look before (defaults to today)
        max_lookback_days: Maximum number of calendar days to look back when the
            immediate prior trading day price is missing. Defaults to 5.

    Returns:
        Tuple of (price, price_date) if found within the lookback window, else None.
    """
    if not current_date:
        current_date = date.today()

    # Calculate the earliest date to search for
    max_lookback_days = max(1, max_lookback_days)
    earliest_date = current_date - timedelta(days=max_lookback_days)

    logger.debug(
        f"Looking up price for {symbol} between {earliest_date} (inclusive) and {current_date} (exclusive)"
    )

    stmt = select(MarketDataCache).where(
        MarketDataCache.symbol == symbol.upper(),
        MarketDataCache.date < current_date,
        MarketDataCache.date >= earliest_date
    ).order_by(MarketDataCache.date.desc()).limit(1)

    result = await db.execute(stmt)
    price_record = result.scalar_one_or_none()

    if price_record:
        if price_record.date < current_date - timedelta(days=1):
            logger.debug(
                f"Using fallback prior close for {symbol}: {price_record.date} (target {current_date})"
            )
        return price_record.close, price_record.date

    logger.warning(
        f"No prior close found for {symbol} within {max_lookback_days} day lookback window (target {current_date})"
    )
    return None


async def calculate_daily_pnl(
    db: AsyncSession,
    position: Position, 
    current_price: Decimal
) -> Dict[str, Decimal]:
    """
    Calculate daily P&L by fetching previous price from database
    Implements database-integrated approach with fallback hierarchy
    
    Args:
        db: Database session
        position: Position object
        current_price: Current price (Decimal)
        
    Returns:
        Dictionary with:
        - daily_pnl: Change in position value
        - daily_return: Percentage change in price
        - price_change: Absolute price change
        - previous_price: Previous trading day price used
        - previous_value: Position value at previous price
        - current_value: Position value at current price
    """
    logger.debug(f"Calculating daily P&L for {position.symbol} at current price ${current_price}")
    
    # Step 1: Try to get previous price from market_data_cache
    price_lookup = await get_previous_trading_day_price(
        db,
        position.symbol,
        current_date=date.today(),
        max_lookback_days=10,
    )

    previous_price: Optional[Decimal] = None
    previous_price_date: Optional[date] = None

    if price_lookup is not None:
        previous_price, previous_price_date = price_lookup

    # Step 2: Fallback to position.last_price if market data not available
    if previous_price is None:
        previous_price = position.last_price
        if previous_price:
            logger.info(f"Using position.last_price fallback for {position.symbol}: ${previous_price}")
    
    # Step 3: Handle case where no previous price is available
    if previous_price is None:
        logger.warning(f"No previous price available for {position.symbol}, returning zero P&L")
        return {
            "daily_pnl": Decimal('0'),
            "daily_return": Decimal('0'),
            "price_change": Decimal('0'),
            "previous_price": None,
            "previous_value": Decimal('0'),
            "current_value": Decimal('0'),
            "error": "No previous price data available"
        }
    
    # Calculate position values using same multiplier logic
    multiplier = Decimal('100') if is_options_position(position) else Decimal('1')
    
    # Position values (using signed quantity for P&L calculation)
    previous_value = position.quantity * previous_price * multiplier
    current_value = position.quantity * current_price * multiplier
    
    # Daily P&L calculation
    daily_pnl = current_value - previous_value
    
    # Daily return aligned with P&L direction (use absolute previous value)
    daily_return = (
        daily_pnl / abs(previous_value)
        if previous_value not in (None, Decimal('0')) and abs(previous_value) > 0
        else Decimal('0')
    )
    
    # Price change
    price_change = current_price - previous_price
    
    result = {
        "daily_pnl": daily_pnl,
        "daily_return": daily_return,
        "price_change": price_change,
        "previous_price": previous_price,
        "previous_value": previous_value,
        "current_value": current_value,
        "previous_price_date": previous_price_date,
    }
    
    logger.debug(f"Daily P&L calculation result for {position.symbol}: {result}")
    return result


async def fetch_and_cache_prices(
    db: AsyncSession,
    symbols_list: List[str]
) -> Dict[str, Decimal]:
    """
    Fetch current prices and update market_data_cache
    Integrates with existing MarketDataService with calculation-specific logic
    
    Args:
        db: Database session
        symbols_list: List of unique symbols from positions
        
    Returns:
        Dictionary mapping symbol to current price (Decimal)
        
    Behavior:
        1. Uses MarketDataService.fetch_current_prices() for real-time data
        2. Updates market_data_cache for valid prices  
        3. Falls back to cached prices for symbols with fetch failures
        4. Logs all price retrieval attempts and results
    """
    logger.info(f"Fetching and caching prices for {len(symbols_list)} symbols")
    
    if not symbols_list:
        logger.warning("Empty symbols list provided to fetch_and_cache_prices")
        return {}
    
    # Step 1: Fetch current prices using existing MarketDataService
    try:
        current_prices = await market_data_service.fetch_current_prices(symbols_list)
        logger.info(f"Fetched current prices from API: {len([v for v in current_prices.values() if v is not None])} successful")
    except Exception as e:
        logger.error(f"Error fetching current prices from API: {str(e)}")
        current_prices = {symbol: None for symbol in symbols_list}
    
    # Step 2: Update market_data_cache for symbols with valid prices
    valid_prices = {k: v for k, v in current_prices.items() if v is not None}
    
    if valid_prices:
        try:
            # Update cache with current prices
            await market_data_service.update_market_data_cache(
                db=db,
                symbols=list(valid_prices.keys()),
                start_date=date.today(),
                end_date=date.today(),
                include_gics=False  # Skip GICS for real-time price updates
            )
            logger.info(f"Updated market_data_cache for {len(valid_prices)} symbols")
        except Exception as e:
            logger.error(f"Error updating market_data_cache: {str(e)}")
    
    # Step 3: Fallback to cached prices for symbols with missing data
    missing_symbols = [k for k, v in current_prices.items() if v is None]
    if missing_symbols:
        logger.info(f"Attempting to retrieve cached prices for {len(missing_symbols)} symbols")
        try:
            cached_prices = await market_data_service.get_cached_prices(
                db=db,
                symbols=missing_symbols
            )
            
            # Update current_prices with cached data
            for symbol, cached_price in cached_prices.items():
                if cached_price is not None:
                    current_prices[symbol] = cached_price
                    logger.debug(f"Using cached price for {symbol}: ${cached_price}")
            
        except Exception as e:
            logger.error(f"Error retrieving cached prices: {str(e)}")
    
    # Step 4: Final validation and logging
    final_prices = {k: v for k, v in current_prices.items() if v is not None}
    missing_final = [k for k, v in current_prices.items() if v is None]
    
    logger.info(f"Price fetch complete: {len(final_prices)} prices available, {len(missing_final)} still missing")
    
    if missing_final:
        logger.warning(f"No prices available for symbols: {missing_final}")
    
    return final_prices


async def update_position_market_values(
    db: AsyncSession,
    position: Position,
    current_price: Decimal
) -> Dict[str, Any]:
    """
    Helper function to update a position's market values in the database
    Combines market value and daily P&L calculations and persists to database
    
    Args:
        db: Database session
        position: Position object to update
        current_price: Current market price
        
    Returns:
        Dictionary with all calculated values and update status
    """
    logger.debug(f"Updating market values for position {position.id} ({position.symbol})")
    
    try:
        # Calculate current market value and exposure
        market_value_data = await calculate_position_market_value(position, current_price)
        
        # Calculate daily P&L
        daily_pnl_data = await calculate_daily_pnl(db, position, current_price)
        
        # Update position fields
        position.last_price = current_price
        position.market_value = market_value_data["market_value"]
        position.unrealized_pnl = market_value_data["unrealized_pnl"]
        position.updated_at = datetime.utcnow()
        
        # Combine all calculation results
        result = {
            **market_value_data,
            **daily_pnl_data,
            "position_id": position.id,
            "symbol": position.symbol,
            "update_timestamp": position.updated_at,
            "success": True
        }
        
        logger.debug(f"Successfully updated market values for {position.symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error updating market values for position {position.id}: {str(e)}")
        return {
            "position_id": position.id,
            "symbol": position.symbol,
            "success": False,
            "error": str(e)
        }


# Convenience function for bulk position updates
async def bulk_update_position_values(
    db: AsyncSession,
    positions: List[Position]
) -> List[Dict[str, Any]]:
    """
    Bulk update market values for multiple positions
    Efficient batch processing for portfolio-wide updates
    
    Args:
        db: Database session
        positions: List of Position objects to update
        
    Returns:
        List of update results for each position
    """
    if not positions:
        return []
    
    logger.info(f"Starting bulk update for {len(positions)} positions")
    
    # Get unique symbols for batch price fetch
    symbols = list(set(position.symbol for position in positions))
    
    # Fetch all prices in one batch
    prices = await fetch_and_cache_prices(db, symbols)
    
    # Update each position
    results = []
    for position in positions:
        current_price = prices.get(position.symbol)
        
        if current_price is not None:
            result = await update_position_market_values(db, position, current_price)
            results.append(result)
        else:
            logger.warning(f"No price available for {position.symbol}, skipping update")
            results.append({
                "position_id": position.id,
                "symbol": position.symbol,
                "success": False,
                "error": "No price data available"
            })
    
    # Commit all updates
    try:
        await db.commit()
        logger.info(f"Bulk update complete: {len([r for r in results if r.get('success')])} successful")
    except Exception as e:
        logger.error(f"Error committing bulk updates: {str(e)}")
        await db.rollback()
        raise
    
    return results


async def fetch_historical_prices(
    db: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date
) -> pd.DataFrame:
    """
    Fetch historical prices for multiple symbols over a date range
    Used for factor analysis calculations requiring historical lookback

    Args:
        db: Database session
        symbols: List of symbols to fetch
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        DataFrame with dates as index and symbols as columns, containing closing prices

    Note:
        This function is designed for factor calculations requiring long lookback periods
        It ensures data availability and handles missing data gracefully
    """
    logger.info(f"Fetching historical prices for {len(symbols)} symbols from {start_date} to {end_date}")
    
    if not symbols:
        logger.warning("Empty symbols list provided")
        return pd.DataFrame()
    
    # Query historical prices from market_data_cache
    stmt = select(
        MarketDataCache.symbol,
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol.in_([s.upper() for s in symbols]),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date, MarketDataCache.symbol)
    
    result = await db.execute(stmt)
    records = result.all()
    
    if not records:
        logger.warning(f"No historical data found for symbols {symbols} between {start_date} and {end_date}")
        return pd.DataFrame()
    
    # Convert to DataFrame
    data = []
    for record in records:
        data.append({
            'symbol': record.symbol,
            'date': record.date,
            'close': float(record.close)  # Convert Decimal to float for pandas
        })
    
    df = pd.DataFrame(data)
    
    # Pivot to have dates as index and symbols as columns
    price_df = df.pivot(index='date', columns='symbol', values='close')
    
    # Convert index to DatetimeIndex for compatibility with other time series data (e.g., FRED Treasury data)
    price_df.index = pd.to_datetime(price_df.index)
    
    # Log data availability
    logger.info(f"Retrieved {len(price_df)} days of data for {len(price_df.columns)} symbols")
    
    # Check for missing data
    missing_data = price_df.isnull().sum()
    if missing_data.any():
        logger.warning(f"Missing data points: {missing_data[missing_data > 0].to_dict()}")
    
    return price_df


async def validate_historical_data_availability(
    db: AsyncSession,
    symbols: List[str],
    required_days: int = None,
    as_of_date: Optional[date] = None
) -> Dict[str, Tuple[bool, int, Optional[date], Optional[date]]]:
    """
    Validate if symbols have sufficient historical data for factor calculations

    Args:
        db: Database session
        symbols: List of symbols to validate
        required_days: Minimum number of days required (defaults to REGRESSION_WINDOW_DAYS from constants)
        as_of_date: Date to calculate lookback from (defaults to today)

    Returns:
        Dictionary mapping symbol to tuple of:
        - has_sufficient_data: Boolean indicating if minimum days available
        - actual_days: Number of days actually available
        - first_date: Earliest date with data
        - last_date: Latest date with data
    """
    # Use REGRESSION_WINDOW_DAYS if not specified
    if required_days is None:
        from app.constants.factors import REGRESSION_WINDOW_DAYS
        required_days = REGRESSION_WINDOW_DAYS
    if not as_of_date:
        as_of_date = date.today()
    
    logger.info(f"Validating data availability for {len(symbols)} symbols")
    
    results = {}
    
    for symbol in symbols:
        # Query to get date range and count
        stmt = select(
            MarketDataCache.symbol,
            func.count(MarketDataCache.date).label('day_count'),
            func.min(MarketDataCache.date).label('first_date'),
            func.max(MarketDataCache.date).label('last_date')
        ).where(
            and_(
                MarketDataCache.symbol == symbol.upper(),
                MarketDataCache.date <= as_of_date
            )
        ).group_by(MarketDataCache.symbol)
        
        result = await db.execute(stmt)
        record = result.one_or_none()
        
        if record:
            has_sufficient = record.day_count >= required_days
            results[symbol] = (
                has_sufficient,
                record.day_count,
                record.first_date,
                record.last_date
            )
            
            if not has_sufficient:
                logger.warning(
                    f"{symbol} has insufficient data: {record.day_count} days "
                    f"(required: {required_days})"
                )
        else:
            results[symbol] = (False, 0, None, None)
            logger.warning(f"{symbol} has no historical data")
    
    return results
