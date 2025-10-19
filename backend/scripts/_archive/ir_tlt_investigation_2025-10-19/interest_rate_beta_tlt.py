"""
Interest Rate Beta Calculation - TLT Bond ETF Sensitivity
Calculates position and portfolio interest rate beta using OLS regression against TLT (20+ Year Treasury Bond ETF).

Position Return = α + β_TLT × TLT_Return + ε

TLT moves inversely to interest rates (rates up → TLT down)
Interpretation: β_TLT = -0.20 means when TLT falls 10%, position falls 2%
              (i.e., when rates rise and bonds sell off, position gets hit)

Created: 2025-10-19
Purpose: Compare with DGS10 approach to determine best IR sensitivity metric
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.constants.factors import REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_tlt_returns(
    db: AsyncSession,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch TLT (20+ Year Treasury Bond ETF) price data and calculate daily returns.

    TLT is the iShares 20+ Year Treasury Bond ETF which moves inversely to long-term rates:
    - When rates rise → TLT price falls (negative returns)
    - When rates fall → TLT price rises (positive returns)

    Args:
        db: Database session
        start_date: Start date for data
        end_date: End date for data

    Returns:
        Pandas Series of daily TLT percentage returns with date index
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol == 'TLT',
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(stmt)
    records = result.all()

    if not records:
        logger.warning("No TLT price data found")
        return pd.Series(dtype=float)

    # Convert to DataFrame
    df = pd.DataFrame([
        {'date': r.date, 'price': float(r.close)}
        for r in records
    ])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate percentage returns
    tlt_returns = df['price'].pct_change().dropna() * 100  # Convert to percentage

    return tlt_returns


async def calculate_position_ir_beta_tlt(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS
) -> Dict[str, Any]:
    """
    Calculate interest rate beta for a single position using TLT (Bond ETF) returns.

    TLT Beta measures position sensitivity to bond market moves:
    - Negative beta: Position moves opposite to TLT (falls when rates rise, TLT falls)
    - Positive beta: Position moves with TLT (defensive, like bonds)
    - Near-zero beta: Low interest rate sensitivity

    Beta Interpretation:
    - β_TLT = -0.20: When TLT falls 10% (rates up), position falls 2%
    - β_TLT = -0.35: When TLT falls 10% (rates up), position falls 3.5%
    - β_TLT = +0.15: When TLT falls 10% (rates up), position rises 1.5% (rare - defensive stocks)

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation (end of window)
        window_days: Lookback period in days (default 90)

    Returns:
        {
            'position_id': UUID,
            'ir_beta': float,
            'r_squared': float,
            'std_error': float,
            'p_value': float,
            'observations': int,
            'calculation_date': date,
            'method': str ('TLT'),
            'success': bool,
            'error': str (if failed)
        }
    """
    logger.info(f"Calculating TLT-based IR beta for position {position_id}")

    try:
        # Get position details
        position_stmt = select(Position).where(Position.id == position_id)
        position_result = await db.execute(position_stmt)
        position = position_result.scalar_one_or_none()

        if not position:
            return {
                'position_id': position_id,
                'success': False,
                'error': 'Position not found'
            }

        # Define date range (add buffer for trading days)
        end_date = calculation_date
        start_date = end_date - timedelta(days=window_days + 30)

        # Fetch position returns (reuse from market_beta.py)
        from app.calculations.market_beta import fetch_returns_for_beta

        position_returns = await fetch_returns_for_beta(
            db, position.symbol, start_date, end_date
        )

        if position_returns.empty or len(position_returns) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient position data: {len(position_returns)} days',
                'observations': len(position_returns)
            }

        # Fetch TLT returns
        tlt_returns = await fetch_tlt_returns(db, start_date, end_date)

        if tlt_returns.empty:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No TLT data available'
            }

        # Align dates (only use common trading days)
        common_dates = position_returns.index.intersection(tlt_returns.index)

        if len(common_dates) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient aligned data: {len(common_dates)} days',
                'observations': len(common_dates)
            }

        # Get aligned returns
        y = position_returns.loc[common_dates].values  # Position returns (%)
        X = tlt_returns.loc[common_dates].values       # TLT returns (%)

        # Run OLS regression: position_return = alpha + beta_TLT * tlt_return + error
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Extract results
        ir_beta_tlt = float(model.params[1])  # Slope coefficient (sensitivity to TLT)
        alpha = float(model.params[0])        # Intercept
        r_squared = float(model.rsquared)
        std_error = float(model.bse[1])
        p_value = float(model.pvalues[1])

        # Cap beta to prevent extreme outliers
        original_beta = ir_beta_tlt
        ir_beta_tlt = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, ir_beta_tlt))

        if abs(original_beta) > BETA_CAP_LIMIT:
            logger.warning(
                f"TLT beta capped for {position.symbol}: {original_beta:.3f} -> {ir_beta_tlt:.3f}"
            )

        # Determine significance
        is_significant = p_value < 0.10  # 90% confidence

        # Interpret sensitivity level (based on absolute beta magnitude)
        abs_beta = abs(ir_beta_tlt)
        if abs_beta < 0.05:
            sensitivity = "very low"
        elif abs_beta < 0.15:
            sensitivity = "low"
        elif abs_beta < 0.30:
            sensitivity = "moderate"
        elif abs_beta < 0.50:
            sensitivity = "high"
        else:
            sensitivity = "very high"

        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'ir_beta': ir_beta_tlt,
            'alpha': alpha,
            'r_squared': r_squared,
            'std_error': std_error,
            'p_value': p_value,
            'observations': len(common_dates),
            'calculation_date': calculation_date,
            'method': 'TLT',
            'is_significant': is_significant,
            'sensitivity_level': sensitivity,
            'success': True
        }

        logger.info(
            f"TLT beta calculated for {position.symbol}: {ir_beta_tlt:.4f} "
            f"({sensitivity} sensitivity, R²={r_squared:.3f}, p={p_value:.3f}, n={len(common_dates)})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating TLT beta for position {position_id}: {e}")
        return {
            'position_id': position_id,
            'success': False,
            'error': str(e)
        }


async def calculate_portfolio_ir_beta_tlt(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS
) -> Dict[str, Any]:
    """
    Calculate portfolio-level interest rate beta using TLT as equity-weighted average.

    Portfolio TLT Beta = Σ(position_market_value_i × position_tlt_beta_i) / portfolio_equity

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        window_days: Regression window in days (default from constants)

    Returns:
        {
            'portfolio_id': UUID,
            'portfolio_ir_beta': float,
            'r_squared': float (weighted average),
            'observations': int (min across positions),
            'positions_count': int,
            'calculation_date': date,
            'position_ir_betas': Dict[UUID, float],
            'sensitivity_level': str,
            'method': str ('TLT'),
            'success': bool
        }
    """
    logger.info(f"Calculating portfolio TLT-based IR beta for {portfolio_id}")

    try:
        # Get portfolio
        from app.models.users import Portfolio as PortfolioModel
        portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Portfolio not found'
            }

        # Validate equity balance
        if not portfolio.equity_balance or portfolio.equity_balance <= 0:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Invalid portfolio equity balance'
            }

        portfolio_equity = float(portfolio.equity_balance)

        # Get active positions
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active positions found'
            }

        # Calculate TLT beta for each position
        position_ir_betas = {}
        position_market_values = {}
        position_r_squareds = {}
        min_observations = float('inf')

        for position in positions:
            ir_beta_result = await calculate_position_ir_beta_tlt(
                db, position.id, calculation_date, window_days
            )

            if not ir_beta_result['success']:
                logger.warning(
                    f"Could not calculate TLT beta for {position.symbol}: "
                    f"{ir_beta_result.get('error', 'Unknown error')}"
                )
                continue

            # Get position market value
            from app.calculations.factor_utils import get_position_market_value
            market_value = float(get_position_market_value(position, recalculate=True))

            position_ir_betas[position.id] = ir_beta_result['ir_beta']
            position_market_values[position.id] = market_value
            position_r_squareds[position.id] = ir_beta_result['r_squared']
            min_observations = min(min_observations, ir_beta_result['observations'])

        if not position_ir_betas:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No position TLT betas could be calculated'
            }

        # Calculate equity-weighted portfolio TLT beta
        total_weighted_ir_beta = 0.0
        total_weighted_r_squared = 0.0

        for pos_id, ir_beta in position_ir_betas.items():
            market_value = position_market_values[pos_id]
            weight = market_value / portfolio_equity

            total_weighted_ir_beta += ir_beta * weight
            total_weighted_r_squared += position_r_squareds[pos_id] * weight

        # Determine portfolio sensitivity level
        abs_beta = abs(total_weighted_ir_beta)
        if abs_beta < 0.05:
            portfolio_sensitivity = "very low"
        elif abs_beta < 0.15:
            portfolio_sensitivity = "low"
        elif abs_beta < 0.30:
            portfolio_sensitivity = "moderate"
        elif abs_beta < 0.50:
            portfolio_sensitivity = "high"
        else:
            portfolio_sensitivity = "very high"

        result = {
            'portfolio_id': portfolio_id,
            'portfolio_ir_beta': total_weighted_ir_beta,
            'r_squared': total_weighted_r_squared,
            'observations': int(min_observations) if min_observations != float('inf') else 0,
            'positions_count': len(position_ir_betas),
            'calculation_date': calculation_date,
            'method': 'TLT',
            'position_ir_betas': {str(k): v for k, v in position_ir_betas.items()},
            'sensitivity_level': portfolio_sensitivity,
            'success': True
        }

        logger.info(
            f"Portfolio TLT beta calculated: {total_weighted_ir_beta:.4f} "
            f"({portfolio_sensitivity} sensitivity, {len(position_ir_betas)} positions)"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating portfolio TLT beta: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }
