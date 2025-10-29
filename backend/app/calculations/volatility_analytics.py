"""
Volatility Analytics - Phase 2 Risk Metrics

Calculates realized and expected volatility using:
1. Realized volatility (21d, 63d trading day windows)
2. HAR (Heterogeneous Autoregressive) model for forecasting
3. Volatility trend analysis
4. Volatility percentiles vs historical distribution

Key Concepts:
- Portfolio volatility ≠ weighted average of position volatilities
- Must calculate portfolio returns first, then volatility
- All windows use trading days, not calendar days
- HAR model uses daily/weekly/monthly components for forecasting
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.linear_model import LinearRegression

from app.core.logging import get_logger
from app.models.market_data import MarketDataCache, PositionVolatility
from app.models.positions import Position
from app.models.users import Portfolio
from app.calculations.market_data import get_returns

logger = get_logger(__name__)

# Trading days per period
TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_PER_MONTH = 21
TRADING_DAYS_PER_WEEK = 5


async def calculate_position_volatility(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    min_observations: int = 63
) -> Optional[Dict[str, Any]]:
    """
    Calculate volatility metrics for a single position.

    Returns:
        {
            'position_id': UUID,
            'calculation_date': date,
            'realized_vol_21d': float,        # 1-month realized vol (annualized)
            'realized_vol_63d': float,        # 3-month realized vol (annualized)
            'vol_daily': float,               # Daily component for HAR
            'vol_weekly': float,              # Weekly component for HAR
            'vol_monthly': float,             # Monthly component for HAR
            'expected_vol_21d': float,        # HAR forecast
            'vol_trend': str,                 # 'increasing', 'decreasing', 'stable'
            'vol_trend_strength': float,      # 0-1 scale
            'vol_percentile': float,          # 0-1 (vs 1-year history)
            'observations': int,              # Data points used
            'model_r_squared': float          # HAR model fit quality
        }
    """
    try:
        # Get position details
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = result.scalar_one_or_none()
        if not position:
            logger.warning(f"Position {position_id} not found")
            return None

        # For options, use underlying symbol for volatility calculation
        # For equities/other assets, use the position symbol
        symbol_for_volatility = position.underlying_symbol if position.underlying_symbol else position.symbol

        logger.debug(f"Calculating volatility for position {position.symbol} using data from {symbol_for_volatility}")

        # Get historical prices (need ~90 days for 63-day window + lookback)
        lookback_days = 365  # Get 1 year for percentile calculation
        start_date = calculation_date - timedelta(days=lookback_days)

        # Phase 8 Refactoring: Use canonical get_returns() instead of manual price fetching
        # This replaces ~30 lines of duplicate MarketDataCache querying and pct_change logic
        returns_df = await get_returns(
            db=db,
            symbols=[symbol_for_volatility],
            start_date=start_date,
            end_date=calculation_date,
            align_dates=False  # Keep all dates, allow NaN for missing data
        )

        if returns_df.empty or symbol_for_volatility not in returns_df.columns:
            logger.warning(
                f"No price data available for {symbol_for_volatility} (position: {position.symbol})"
            )
            return None

        # Extract returns series for this symbol
        returns = returns_df[symbol_for_volatility].dropna()

        if len(returns) < min_observations:
            logger.warning(
                f"Insufficient returns for {position.symbol}: "
                f"{len(returns)} < {min_observations} required"
            )
            return None

        # Calculate realized volatility at different horizons
        vol_21d = _calculate_realized_vol(returns, window=21)
        vol_63d = _calculate_realized_vol(returns, window=63)

        # Calculate HAR components
        # Daily: Use absolute value of most recent return (annualized)
        vol_daily = abs(returns.iloc[-1]) * np.sqrt(TRADING_DAYS_PER_YEAR) if len(returns) > 0 else None
        vol_weekly = _calculate_realized_vol(returns, window=5)
        vol_monthly = _calculate_realized_vol(returns, window=21)

        # HAR forecast (expected volatility)
        expected_vol, r_squared = _forecast_har(
            returns,
            vol_daily=vol_daily,
            vol_weekly=vol_weekly,
            vol_monthly=vol_monthly
        )

        # Trend analysis
        trend, trend_strength = _analyze_volatility_trend(returns, window=21)

        # Percentile calculation (vs 1-year history)
        percentile = _calculate_vol_percentile(returns, window=21)

        return {
            'position_id': position_id,
            'calculation_date': calculation_date,
            'realized_vol_21d': vol_21d,
            'realized_vol_63d': vol_63d,
            'vol_daily': vol_daily,
            'vol_weekly': vol_weekly,
            'vol_monthly': vol_monthly,
            'expected_vol_21d': expected_vol,
            'vol_trend': trend,
            'vol_trend_strength': trend_strength,
            'vol_percentile': percentile,
            'observations': len(returns),
            'model_r_squared': r_squared
        }

    except Exception as e:
        logger.error(f"Error calculating volatility for position {position_id}: {e}", exc_info=True)
        return None


async def calculate_portfolio_volatility(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    min_observations: int = 63
) -> Optional[Dict[str, Any]]:
    """
    Calculate volatility metrics for entire portfolio.

    CRITICAL: Portfolio volatility ≠ weighted average of position volatilities!
    Must calculate portfolio returns first, then volatility of those returns.

    Returns:
        {
            'portfolio_id': UUID,
            'calculation_date': date,
            'realized_volatility_21d': float,  # Annualized 21-day realized vol
            'realized_volatility_63d': float,  # Annualized 63-day realized vol
            'expected_volatility_21d': float,  # HAR forecasted vol
            'volatility_trend': str,  # 'increasing'|'decreasing'|'stable'
            'volatility_percentile': float,  # 0-1 scale vs 1-year history
            'observations': int,  # Number of return observations used
            'positions_included': int  # Number of positions in calculation
        }
    """
    try:
        # Get portfolio positions
        result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)  # Only active positions
            )
        )
        positions = result.scalars().all()

        if not positions:
            logger.warning(f"No active positions found for portfolio {portfolio_id}")
            return None

        # Get historical prices for all positions
        # For options, use underlying symbol; for equities use position symbol
        lookback_days = 365
        start_date = calculation_date - timedelta(days=lookback_days)

        # Phase 8 Refactoring: Use canonical get_returns() instead of manual price fetching
        # This replaces ~40 lines of duplicate MarketDataCache querying and DataFrame building

        # Build list of symbols to fetch (using underlying for options)
        symbols_to_fetch = []
        symbol_to_position = {}  # Maps fetch_symbol -> Position object
        for p in positions:
            fetch_symbol = p.underlying_symbol if p.underlying_symbol else p.symbol
            symbols_to_fetch.append(fetch_symbol)
            symbol_to_position[fetch_symbol] = p

        symbols_to_fetch = list(set(symbols_to_fetch))  # Deduplicate

        # Fetch returns for all symbols using canonical function
        returns_df = await get_returns(
            db=db,
            symbols=symbols_to_fetch,
            start_date=start_date,
            end_date=calculation_date,
            align_dates=False  # Keep all dates, handle missing data below
        )

        if returns_df.empty:
            logger.warning(f"No returns data found for portfolio {portfolio_id}")
            return None

        # Calculate portfolio returns using position weights
        portfolio_returns = _calculate_portfolio_returns_from_df(
            positions=positions,
            returns_df=returns_df,
            calculation_date=calculation_date
        )

        if portfolio_returns is None or len(portfolio_returns) < min_observations:
            logger.warning(
                f"Insufficient portfolio returns: "
                f"{len(portfolio_returns) if portfolio_returns is not None else 0} < {min_observations}"
            )
            return None

        # Calculate realized volatility
        vol_21d = _calculate_realized_vol(portfolio_returns, window=21)
        vol_63d = _calculate_realized_vol(portfolio_returns, window=63)

        # Calculate HAR components for forecast
        # Daily: Use absolute value of most recent return (annualized)
        vol_daily = abs(portfolio_returns.iloc[-1]) * np.sqrt(TRADING_DAYS_PER_YEAR) if len(portfolio_returns) > 0 else None
        vol_weekly = _calculate_realized_vol(portfolio_returns, window=5)
        vol_monthly = _calculate_realized_vol(portfolio_returns, window=21)

        # HAR forecast
        expected_vol, _ = _forecast_har(
            portfolio_returns,
            vol_daily=vol_daily,
            vol_weekly=vol_weekly,
            vol_monthly=vol_monthly
        )

        # Trend analysis
        trend, _ = _analyze_volatility_trend(portfolio_returns, window=21)

        # Percentile
        percentile = _calculate_vol_percentile(portfolio_returns, window=21)

        return {
            'portfolio_id': portfolio_id,
            'calculation_date': calculation_date,
            'realized_volatility_21d': vol_21d,  # Aligned with snapshot column name
            'realized_volatility_63d': vol_63d,  # Aligned with snapshot column name
            'expected_volatility_21d': expected_vol,  # Aligned with snapshot column name
            'volatility_trend': trend,  # Aligned with snapshot column name
            'volatility_percentile': percentile,  # Aligned with snapshot column name
            'observations': len(portfolio_returns),
            'positions_included': len(positions)
        }

    except Exception as e:
        logger.error(f"Error calculating portfolio volatility {portfolio_id}: {e}", exc_info=True)
        return None


async def save_position_volatility(
    db: AsyncSession,
    volatility_data: Dict[str, Any]
) -> bool:
    """
    Save position volatility results to database.

    Args:
        db: Database session
        volatility_data: Result from calculate_position_volatility()

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Helper function to convert to Decimal or None
        def to_decimal(value):
            return Decimal(str(value)) if value is not None else None

        # Check if record exists
        result = await db.execute(
            select(PositionVolatility).where(
                PositionVolatility.position_id == volatility_data['position_id'],
                PositionVolatility.calculation_date == volatility_data['calculation_date']
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.realized_vol_21d = to_decimal(volatility_data.get('realized_vol_21d'))
            existing.realized_vol_63d = to_decimal(volatility_data.get('realized_vol_63d'))
            existing.vol_daily = to_decimal(volatility_data.get('vol_daily'))
            existing.vol_weekly = to_decimal(volatility_data.get('vol_weekly'))
            existing.vol_monthly = to_decimal(volatility_data.get('vol_monthly'))
            existing.expected_vol_21d = to_decimal(volatility_data.get('expected_vol_21d'))
            existing.vol_trend = volatility_data.get('vol_trend')
            existing.vol_trend_strength = to_decimal(volatility_data.get('vol_trend_strength'))
            existing.vol_percentile = to_decimal(volatility_data.get('vol_percentile'))
            existing.observations = volatility_data.get('observations')
            existing.model_r_squared = to_decimal(volatility_data.get('model_r_squared'))
        else:
            # Create new record
            vol_record = PositionVolatility(
                position_id=volatility_data['position_id'],
                calculation_date=volatility_data['calculation_date'],
                realized_vol_21d=to_decimal(volatility_data.get('realized_vol_21d')),
                realized_vol_63d=to_decimal(volatility_data.get('realized_vol_63d')),
                vol_daily=to_decimal(volatility_data.get('vol_daily')),
                vol_weekly=to_decimal(volatility_data.get('vol_weekly')),
                vol_monthly=to_decimal(volatility_data.get('vol_monthly')),
                expected_vol_21d=to_decimal(volatility_data.get('expected_vol_21d')),
                vol_trend=volatility_data.get('vol_trend'),
                vol_trend_strength=to_decimal(volatility_data.get('vol_trend_strength')),
                vol_percentile=to_decimal(volatility_data.get('vol_percentile')),
                observations=volatility_data.get('observations'),
                model_r_squared=to_decimal(volatility_data.get('model_r_squared'))
            )
            db.add(vol_record)

        # Note: Do NOT commit here - let caller manage transaction boundaries
        # Committing expires session objects and causes greenlet errors
        return True

    except Exception as e:
        logger.error(f"Error saving position volatility: {e}", exc_info=True)
        # Note: Do NOT rollback here - let caller manage transaction
        raise


async def calculate_portfolio_volatility_batch(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate volatility for all positions in a portfolio and aggregate.

    This is the main entry point for batch processing.

    Returns:
        {
            'success': bool,
            'portfolio_volatility': Dict[str, Any],  # Portfolio-level metrics
            'position_volatilities': List[Dict],      # Position-level metrics
            'positions_processed': int,
            'positions_failed': int
        }
    """
    try:
        logger.info(f"Calculating volatility for portfolio {portfolio_id}")

        # Get all active positions (eagerly load to avoid greenlet errors)
        result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        positions = result.scalars().all()

        # Convert to list immediately to avoid lazy loading issues
        positions = list(positions)

        if not positions:
            return {
                'success': False,
                'error': 'No active positions found',
                'positions_processed': 0,
                'positions_failed': 0
            }

        # Calculate position-level volatilities
        position_results = []
        positions_processed = 0
        positions_failed = 0

        for position in positions:
            vol_data = await calculate_position_volatility(
                db=db,
                position_id=position.id,
                calculation_date=calculation_date
            )

            if vol_data:
                # Save to database
                saved = await save_position_volatility(db, vol_data)
                if saved:
                    position_results.append(vol_data)
                    positions_processed += 1
                else:
                    positions_failed += 1
            else:
                positions_failed += 1

        # Calculate portfolio-level volatility
        portfolio_vol = await calculate_portfolio_volatility(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date
        )

        return {
            'success': True,
            'portfolio_volatility': portfolio_vol,
            'position_volatilities': position_results,
            'positions_processed': positions_processed,
            'positions_failed': positions_failed
        }

    except Exception as e:
        logger.error(f"Error in volatility batch calculation: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'positions_processed': 0,
            'positions_failed': 0
        }


# ============================================================================
# PRIVATE HELPER FUNCTIONS
# ============================================================================


def _calculate_yang_zhang_volatility(df: pd.DataFrame) -> Optional[float]:
    """
    Calculate Yang-Zhang volatility estimator using OHLC data.

    Yang-Zhang (2000) is the most efficient unbiased estimator that accounts for:
    - Opening gaps
    - Drift
    - Overnight jumps

    Formula: σ²_YZ = σ²_o + k·σ²_c + (1-k)·σ²_rs

    Where:
    - σ²_o = overnight variance (ln(O/C_prev))²
    - σ²_c = close-to-close variance
    - σ²_rs = Rogers-Satchell intraday variance
    - k = weighting factor

    Args:
        df: DataFrame with columns: open, high, low, close (indexed by date)

    Returns:
        Annualized volatility (as decimal, e.g., 0.25 for 25%)
    """
    try:
        if len(df) < 2:
            return None

        # Ensure we have all required columns
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return None

        # Overnight variance: σ²_o = (1/n)Σ(ln(O_t/C_{t-1}))²
        overnight_log_returns = np.log(df['open'] / df['close'].shift(1))
        overnight_var = (overnight_log_returns ** 2).mean()

        # Close-to-close variance: σ²_c = (1/(n-1))Σ(ln(C_t/C_{t-1}) - μ_c)²
        close_log_returns = np.log(df['close'] / df['close'].shift(1))
        close_var = close_log_returns.var()

        # Rogers-Satchell intraday variance
        # σ²_rs = (1/n)Σ[ln(H_t/C_t)·ln(H_t/O_t) + ln(L_t/C_t)·ln(L_t/O_t)]
        h_c = np.log(df['high'] / df['close'])
        h_o = np.log(df['high'] / df['open'])
        l_c = np.log(df['low'] / df['close'])
        l_o = np.log(df['low'] / df['open'])
        rs_var = (h_c * h_o + l_c * l_o).mean()

        # Calculate k weighting factor
        # k = 0.34 / (1.34 + (n+1)/(n-1))
        n = len(df)
        k = 0.34 / (1.34 + (n + 1) / (n - 1)) if n > 1 else 0.5

        # Combine components: σ²_YZ = σ²_o + k·σ²_c + (1-k)·σ²_rs
        yang_zhang_var = overnight_var + k * close_var + (1 - k) * rs_var

        # Convert to volatility and annualize
        yang_zhang_vol = np.sqrt(yang_zhang_var) * np.sqrt(TRADING_DAYS_PER_YEAR)

        return float(yang_zhang_vol)

    except Exception as e:
        logger.warning(f"Yang-Zhang calculation failed: {e}")
        return None


def _calculate_realized_vol(returns: pd.Series, window: int) -> Optional[float]:
    """
    Calculate realized volatility over a rolling window.

    Args:
        returns: Daily returns series
        window: Window size in trading days (1, 5, 21, 63, etc.)

    Returns:
        Annualized volatility (as decimal, e.g., 0.25 for 25%)
    """
    if len(returns) < window:
        return None

    # Take most recent window
    recent_returns = returns.tail(window)

    # Calculate standard deviation
    vol = recent_returns.std()

    # Annualize: multiply by sqrt(252 trading days per year)
    annualized_vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)

    return float(annualized_vol)


def _calculate_realized_vol_from_ohlc(df: pd.DataFrame, window: int = None) -> Optional[float]:
    """
    Calculate realized volatility using OHLC data with Yang-Zhang estimator.

    If window is specified, uses the most recent 'window' days.
    If window is None, uses all available data.

    Args:
        df: DataFrame with open, high, low, close columns
        window: Number of days to use (None = all data)

    Returns:
        Annualized volatility (as decimal)
    """
    if len(df) < 2:
        return None

    # Take most recent window if specified
    if window is not None:
        if len(df) < window:
            return None
        df = df.tail(window)

    return _calculate_yang_zhang_volatility(df)


def _forecast_har(
    returns: pd.Series,
    vol_daily: Optional[float],
    vol_weekly: Optional[float],
    vol_monthly: Optional[float]
) -> tuple[Optional[float], Optional[float]]:
    """
    Forecast volatility using HAR (Heterogeneous Autoregressive) model.

    HAR Model (Corsi 2009):
        RV(t+1) = β0 + β1*RV_daily + β2*RV_weekly + β3*RV_monthly + ε

    For the daily component, we use squared returns (realized variance for single period).
    For weekly/monthly, we use rolling standard deviation.

    Args:
        returns: Historical daily returns
        vol_daily: Current daily volatility (annualized)
        vol_weekly: Current weekly volatility (annualized)
        vol_monthly: Current monthly volatility (annualized)

    Returns:
        (forecast, r_squared) tuple
    """
    if any(v is None for v in [vol_daily, vol_weekly, vol_monthly]):
        return None, None

    try:
        # Need at least 63 days for meaningful HAR fit
        if len(returns) < 63:
            return None, None

        # Calculate rolling volatilities for training
        # Daily: Use squared returns (annualized) - this is the actual realized variance
        rv_daily = (returns ** 2) * TRADING_DAYS_PER_YEAR  # Annualized variance
        rv_daily = np.sqrt(rv_daily)  # Convert to volatility

        # Weekly: Average volatility over 5-day rolling window
        rv_weekly = returns.rolling(5).std() * np.sqrt(TRADING_DAYS_PER_YEAR)

        # Monthly: Average volatility over 21-day rolling window
        rv_monthly = returns.rolling(21).std() * np.sqrt(TRADING_DAYS_PER_YEAR)

        # Create dataset: predict tomorrow's daily vol from today's components
        X = pd.DataFrame({
            'rv_daily': rv_daily,
            'rv_weekly': rv_weekly,
            'rv_monthly': rv_monthly
        })
        y = rv_daily.shift(-1)  # Tomorrow's volatility

        # Drop NaN values
        df = pd.concat([X, y.rename('target')], axis=1).dropna()

        if len(df) < 30:  # Need minimum data for regression
            return None, None

        X_train = df[['rv_daily', 'rv_weekly', 'rv_monthly']]
        y_train = df['target']

        # Fit HAR model
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Make forecast using current volatilities
        X_current = np.array([[vol_daily, vol_weekly, vol_monthly]])
        forecast = model.predict(X_current)[0]

        # Calculate R-squared
        r_squared = model.score(X_train, y_train)

        return float(forecast), float(r_squared)

    except Exception as e:
        logger.warning(f"HAR forecast failed: {e}")
        return None, None


def _analyze_volatility_trend(returns: pd.Series, window: int = 21) -> tuple[str, float]:
    """
    Analyze whether volatility is rising, falling, or stable.

    Uses linear regression on recent volatilities to detect trend.

    Args:
        returns: Daily returns series
        window: Lookback window for trend analysis

    Returns:
        (trend, strength) tuple
        trend: 'increasing', 'decreasing', or 'stable'
        strength: 0-1 scale (0=no trend, 1=strong trend)
    """
    try:
        if len(returns) < window * 2:
            return 'stable', 0.0

        # Calculate rolling volatility
        rolling_vol = returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        recent_vol = rolling_vol.tail(window).dropna()

        if len(recent_vol) < 10:
            return 'stable', 0.0

        # Fit linear regression to detect trend
        X = np.arange(len(recent_vol)).reshape(-1, 1)
        y = recent_vol.values

        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)

        slope = model.coef_[0]
        r_squared = model.score(X, y)

        # Normalize slope to 0-1 scale (use R² as strength indicator)
        strength = min(abs(r_squared), 1.0)

        # Classify trend
        threshold = 0.001  # Minimum slope to be considered trending
        if slope > threshold and strength > 0.3:
            trend = 'increasing'
        elif slope < -threshold and strength > 0.3:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return trend, float(strength)

    except Exception as e:
        logger.warning(f"Trend analysis failed: {e}")
        return 'stable', 0.0


def _calculate_vol_percentile(returns: pd.Series, window: int = 21) -> Optional[float]:
    """
    Calculate where current volatility ranks vs 1-year history.

    Args:
        returns: Daily returns series
        window: Window for current volatility calculation

    Returns:
        Percentile (0-1 scale), where 0.90 means current vol is higher than 90% of history
    """
    try:
        if len(returns) < 252:  # Need 1 year of data
            return None

        # Calculate rolling volatility over entire history
        rolling_vol = returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        rolling_vol = rolling_vol.dropna()

        if len(rolling_vol) < 100:
            return None

        # Get current volatility
        current_vol = rolling_vol.iloc[-1]

        # Calculate percentile
        percentile = (rolling_vol < current_vol).sum() / len(rolling_vol)

        return float(percentile)

    except Exception as e:
        logger.warning(f"Percentile calculation failed: {e}")
        return None


def _calculate_portfolio_returns_from_df(
    positions: List[Position],
    returns_df: pd.DataFrame,
    calculation_date: date
) -> Optional[pd.Series]:
    """
    Calculate daily portfolio returns using position weights from returns DataFrame.

    CRITICAL: This is the correct way to calculate portfolio volatility.
    Portfolio volatility ≠ weighted average of position volatilities!

    Method:
        1. Calculate position weights based on market values
        2. Calculate weighted sum of position returns each day
        3. Return series of portfolio daily returns

    Args:
        positions: List of Position objects
        returns_df: DataFrame with returns (from get_returns())
        calculation_date: Date for weight calculation

    Returns:
        Series of daily portfolio returns

    Phase 8 Refactoring:
        Simplified version that works with returns DataFrame from get_returns()
        instead of manually building DataFrames from raw price data.
    """
    try:
        # Map position symbols to their fetch symbols (underlying for options)
        symbol_mapping = {}  # Maps position symbol -> fetch symbol
        for position in positions:
            fetch_symbol = position.underlying_symbol if position.underlying_symbol else position.symbol
            symbol_mapping[position.symbol] = fetch_symbol

        # Calculate position weights based on market values
        total_value = sum(
            float(p.market_value) if p.market_value else 0.0
            for p in positions
        )

        if total_value == 0:
            logger.warning("Total portfolio value is zero, cannot calculate returns")
            return None

        weights = {
            p.symbol: float(p.market_value) / total_value if p.market_value else 0.0
            for p in positions
        }

        # Calculate portfolio returns for each date
        portfolio_returns = pd.Series(0.0, index=returns_df.index)

        for position in positions:
            fetch_symbol = symbol_mapping[position.symbol]
            if fetch_symbol in returns_df.columns:
                weight = weights[position.symbol]
                portfolio_returns += weight * returns_df[fetch_symbol].fillna(0)
            else:
                logger.debug(f"No returns data for {position.symbol} (fetch: {fetch_symbol})")

        return portfolio_returns.dropna()

    except Exception as e:
        logger.error(f"Error calculating portfolio returns: {e}", exc_info=True)
        return None
