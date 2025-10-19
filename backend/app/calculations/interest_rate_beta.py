"""
Interest Rate Beta Calculation - Treasury Yield Sensitivity
Calculates position and portfolio interest rate beta using OLS regression against 10Y Treasury yields.

Position Return = α + β_IR × ΔYield + ε

Negative beta typical: rates up → stocks down
Interpretation: β_IR = -0.25 means 100bp rate increase → 25% position decline

Created: 2025-10-18
Integrates with: Stress testing scenarios (IR shocks)
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID
import uuid

import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import MarketDataCache, PositionInterestRateBeta
from app.constants.factors import REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_treasury_yield_changes(
    db: AsyncSession,
    symbol: str,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch 10-Year Treasury yield data and calculate daily changes in basis points.

    Treasury yields are stored as percentages (e.g., 4.5 for 4.5%).
    Changes are converted to basis points (100bp = 1%).

    Args:
        db: Database session
        symbol: Treasury symbol (e.g., 'DGS10' for 10-Year)
        start_date: Start date for data
        end_date: End date for data

    Returns:
        Pandas Series of daily yield changes in basis points with date index
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close  # Yield stored as close price
    ).where(
        and_(
            MarketDataCache.symbol == symbol.upper(),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(stmt)
    records = result.all()

    if not records:
        logger.warning(f"No Treasury yield data found for {symbol}")
        return pd.Series(dtype=float)

    # Convert to DataFrame
    df = pd.DataFrame([
        {'date': r.date, 'yield': float(r.close)}
        for r in records
    ])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate yield changes (absolute change in percentage points)
    # Then convert to basis points (×100)
    # Note: fill_method parameter removed in pandas 2.x
    yield_changes = df['yield'].diff().dropna() * 100  # Convert to bp

    return yield_changes


async def calculate_position_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    treasury_symbol: str = 'DGS10'
) -> Dict[str, Any]:
    """
    Calculate interest rate beta for a single position using OLS regression.

    IR Beta measures position sensitivity to changes in Treasury yields:
    - Negative beta: Position declines when rates rise (typical for stocks/bonds)
    - Positive beta: Position rises when rates rise (rare, some financials)

    Beta Interpretation:
    - β_IR = -0.10: 100bp rate increase → 10% position decline
    - β_IR = -0.25: 100bp rate increase → 25% position decline
    - β_IR = -0.50: 100bp rate increase → 50% position decline (very rate-sensitive)

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation (end of window)
        window_days: Lookback period in days (default 90)
        treasury_symbol: Treasury series to use (default 'DGS10')

    Returns:
        {
            'position_id': UUID,
            'ir_beta': float,
            'r_squared': float,
            'std_error': float,
            'p_value': float,
            'observations': int,
            'calculation_date': date,
            'treasury_symbol': str,
            'success': bool,
            'error': str (if failed)
        }
    """
    logger.info(f"Calculating IR beta for position {position_id} using {treasury_symbol}")

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

        # Fetch Treasury yield changes
        treasury_changes = await fetch_treasury_yield_changes(
            db, treasury_symbol, start_date, end_date
        )

        if treasury_changes.empty:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'No Treasury data available for {treasury_symbol}'
            }

        # Align dates (only use common trading days)
        common_dates = position_returns.index.intersection(treasury_changes.index)

        if len(common_dates) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient aligned data: {len(common_dates)} days',
                'observations': len(common_dates)
            }

        # Get aligned returns and yield changes
        y = position_returns.loc[common_dates].values  # Position returns (%)
        X = treasury_changes.loc[common_dates].values  # Yield changes (bp)

        # Run OLS regression: position_return = alpha + beta * yield_change + error
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Extract results
        ir_beta = float(model.params[1])  # Slope coefficient (sensitivity to rates)
        alpha = float(model.params[0])     # Intercept
        r_squared = float(model.rsquared)
        std_error = float(model.bse[1])
        p_value = float(model.pvalues[1])

        # Cap beta to prevent extreme outliers
        original_beta = ir_beta
        ir_beta = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, ir_beta))

        if abs(original_beta) > BETA_CAP_LIMIT:
            logger.warning(
                f"IR beta capped for {position.symbol}: {original_beta:.3f} -> {ir_beta:.3f}"
            )

        # Determine significance
        is_significant = p_value < 0.10  # 90% confidence

        # Interpret sensitivity level
        abs_beta = abs(ir_beta)
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
            'ir_beta': ir_beta,
            'alpha': alpha,
            'r_squared': r_squared,
            'std_error': std_error,
            'p_value': p_value,
            'observations': len(common_dates),
            'calculation_date': calculation_date,
            'treasury_symbol': treasury_symbol,
            'is_significant': is_significant,
            'sensitivity_level': sensitivity,
            'success': True
        }

        logger.info(
            f"IR beta calculated for {position.symbol}: {ir_beta:.4f} "
            f"({sensitivity} sensitivity, R²={r_squared:.3f}, p={p_value:.3f}, n={len(common_dates)})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating IR beta for position {position_id}: {e}")
        return {
            'position_id': position_id,
            'success': False,
            'error': str(e)
        }


async def persist_position_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    ir_beta_result: Dict[str, Any]
) -> None:
    """
    Persist position IR beta to position_interest_rate_betas table.

    Args:
        db: Database session
        position_id: Position UUID
        ir_beta_result: Result dictionary from calculate_position_ir_beta
    """
    try:
        # Check if record already exists for this calc date
        stmt = select(PositionInterestRateBeta).where(
            and_(
                PositionInterestRateBeta.position_id == position_id,
                PositionInterestRateBeta.calculation_date == ir_beta_result['calculation_date']
            )
        )
        existing = await db.execute(stmt)
        existing_record = existing.scalar_one_or_none()

        if existing_record:
            # Update existing record
            existing_record.ir_beta = Decimal(str(ir_beta_result['ir_beta']))
            existing_record.r_squared = Decimal(str(ir_beta_result['r_squared'])) if ir_beta_result.get('r_squared') else None
        else:
            # Create new record
            new_ir_beta = PositionInterestRateBeta(
                position_id=position_id,
                ir_beta=Decimal(str(ir_beta_result['ir_beta'])),
                r_squared=Decimal(str(ir_beta_result['r_squared'])) if ir_beta_result.get('r_squared') else None,
                calculation_date=ir_beta_result['calculation_date']
            )
            db.add(new_ir_beta)

        await db.commit()
        logger.info(f"Persisted IR beta for position {position_id}")

    except Exception as e:
        logger.error(f"Error persisting IR beta: {e}")
        await db.rollback()
        raise


async def calculate_portfolio_ir_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    treasury_symbol: str = 'DGS10',
    persist: bool = True
) -> Dict[str, Any]:
    """
    Calculate portfolio-level interest rate beta as equity-weighted average.
    Persists position-level IR betas to position_interest_rate_betas table.

    Portfolio IR Beta = Σ(position_market_value_i × position_ir_beta_i) / portfolio_equity

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        window_days: Regression window in days (default from constants)
        treasury_symbol: Treasury series to use (default 'DGS10')
        persist: If True, saves position IR betas to database

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
            'success': bool
        }
    """
    logger.info(f"Calculating portfolio IR beta for {portfolio_id}")

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

        # Calculate IR beta for each position
        position_ir_betas = {}
        position_market_values = {}
        position_r_squareds = {}
        min_observations = float('inf')

        for position in positions:
            ir_beta_result = await calculate_position_ir_beta(
                db, position.id, calculation_date, window_days, treasury_symbol
            )

            if not ir_beta_result['success']:
                logger.warning(
                    f"Could not calculate IR beta for {position.symbol}: "
                    f"{ir_beta_result.get('error', 'Unknown error')}"
                )
                continue

            # Persist position IR beta
            if persist:
                await persist_position_ir_beta(db, position.id, ir_beta_result)

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
                'error': 'No position IR betas could be calculated'
            }

        # Calculate equity-weighted portfolio IR beta
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
            'treasury_symbol': treasury_symbol,
            'position_ir_betas': {str(k): v for k, v in position_ir_betas.items()},
            'sensitivity_level': portfolio_sensitivity,
            'success': True
        }

        logger.info(
            f"Portfolio IR beta calculated: {total_weighted_ir_beta:.4f} "
            f"({portfolio_sensitivity} sensitivity, {len(position_ir_betas)} positions)"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating portfolio IR beta: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }
