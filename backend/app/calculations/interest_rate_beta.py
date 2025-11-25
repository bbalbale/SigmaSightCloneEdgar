"""
Interest Rate Beta Calculation - TLT Bond ETF Sensitivity
Calculates position and portfolio interest rate beta using OLS regression against TLT (20+ Year Treasury Bond ETF).

Position Return = α + β_TLT × TLT_Return + ε

TLT moves inversely to interest rates (rates up → TLT down)
Interpretation: β_TLT = -0.20 means when TLT falls 10%, position falls 2%
              (i.e., when rates rise and bonds sell off, position gets hit)

Created: 2025-10-18
Updated: 2025-10-19 - Switched from DGS10 (Fed yields) to TLT (Bond ETF) for realistic P&L impacts
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
from app.calculations.regression_utils import run_single_factor_regression
from app.calculations.market_data import get_returns
from app.core.logging import get_logger

logger = get_logger(__name__)


async def calculate_position_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    treasury_symbol: str = 'TLT',  # Changed from DGS10 to TLT
    price_cache=None
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
        treasury_symbol: Bond ETF symbol to use (default 'TLT', kept as 'treasury_symbol' for backward compatibility)
        price_cache: Optional PriceCache for optimized price lookups (300x speedup)

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

        # Fetch aligned returns for position and TLT using canonical function
        # This replaces duplicate fetch + manual alignment logic
        returns_df = await get_returns(
            db=db,
            symbols=[position.symbol, 'TLT'],
            start_date=start_date,
            end_date=end_date,
            align_dates=True,  # Ensures no NaN - only common trading days
            price_cache=price_cache  # Pass through cache for optimization
        )

        # Check if we have sufficient data
        if returns_df.empty:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No aligned data available for position and TLT'
            }

        if position.symbol not in returns_df.columns:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'No data found for {position.symbol}'
            }

        if 'TLT' not in returns_df.columns:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No TLT data available'
            }

        if len(returns_df) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient aligned data: {len(returns_df)} days',
                'observations': len(returns_df)
            }

        # Get aligned returns (already aligned by get_returns with align_dates=True)
        y = returns_df[position.symbol].values  # Position returns
        x = returns_df['TLT'].values            # TLT returns

        # Run OLS regression using canonical function from regression_utils
        # This handles: OLS regression, beta capping, significance testing
        regression_result = run_single_factor_regression(
            y=y,
            x=x,
            cap=BETA_CAP_LIMIT,  # Cap beta at ±5.0
            confidence=0.10,     # 90% confidence level (relaxed)
            return_diagnostics=True
        )

        # Extract IR beta (TLT sensitivity)
        ir_beta_tlt = regression_result['beta']

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

        # Build result dictionary with consistent structure
        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'ir_beta': ir_beta_tlt,
            'alpha': regression_result['alpha'],
            'r_squared': regression_result['r_squared'],
            'std_error': regression_result['std_error'],
            'p_value': regression_result['p_value'],
            'observations': len(returns_df),
            'calculation_date': calculation_date,
            'treasury_symbol': 'TLT',  # Always TLT now
            'is_significant': regression_result['is_significant'],
            'sensitivity_level': sensitivity,
            'success': True
        }

        logger.info(
            f"TLT beta calculated for {position.symbol}: {result['ir_beta']:.4f} "
            f"({sensitivity} sensitivity, R²={result['r_squared']:.3f}, p={result['p_value']:.3f}, n={len(returns_df)})"
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
    portfolio_id: UUID,
    ir_beta_result: Dict[str, Any]
) -> None:
    """
    Persist position IR beta to position_interest_rate_betas table.

    Args:
        db: Database session
        position_id: Position UUID
        portfolio_id: Portfolio UUID (required for database constraint)
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
                portfolio_id=portfolio_id,  # Fix: Added missing portfolio_id
                position_id=position_id,
                ir_beta=Decimal(str(ir_beta_result['ir_beta'])),
                r_squared=Decimal(str(ir_beta_result['r_squared'])) if ir_beta_result.get('r_squared') else None,
                calculation_date=ir_beta_result['calculation_date']
            )
            db.add(new_ir_beta)

        # Note: Do NOT commit here - let caller manage transaction boundaries
        # Committing after each position expires session objects and causes greenlet errors
        logger.debug(f"Staged IR beta for position {position_id} (will be committed by caller)")

    except Exception as e:
        logger.error(f"Error persisting IR beta: {e}")
        # Note: Do NOT rollback here - let caller manage transaction
        raise


async def calculate_portfolio_ir_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    treasury_symbol: str = 'TLT',  # Changed from DGS10 to TLT
    persist: bool = True,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate portfolio-level interest rate beta as equity-weighted average using TLT.
    Persists position-level IR betas to position_interest_rate_betas table.

    Portfolio IR Beta = Σ(position_market_value_i × position_ir_beta_i) / portfolio_equity

    TLT-based beta provides realistic, measurable P&L impacts for stress testing.
    Typical portfolio TLT betas: -0.001 to -0.006 (negative = falls when rates rise).

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        window_days: Regression window in days (default from constants)
        treasury_symbol: Bond ETF symbol to use (default 'TLT', kept as 'treasury_symbol' for backward compatibility)
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

        # Get active positions (exclude soft-deleted)
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),
                Position.deleted_at.is_(None)
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

        # OPTIMIZATION: Check which positions already have cached IR betas for this date
        # This prevents recalculating betas for positions shared across portfolios
        position_ids = [p.id for p in positions]
        cached_betas_stmt = select(PositionInterestRateBeta).where(
            and_(
                PositionInterestRateBeta.position_id.in_(position_ids),
                PositionInterestRateBeta.calculation_date == calculation_date
            )
        )
        cached_result = await db.execute(cached_betas_stmt)
        cached_betas = {row.position_id: row for row in cached_result.scalars().all()}

        if cached_betas:
            logger.info(
                f"Found {len(cached_betas)}/{len(positions)} positions with cached IR betas "
                f"for {calculation_date} (skipping recalculation)"
            )

        # Calculate IR beta for each position
        position_ir_betas = {}
        position_market_values = {}
        position_r_squareds = {}
        min_observations = float('inf')
        positions_calculated = 0
        positions_from_cache = 0

        # Import get_position_value once (not in loop)
        from app.calculations.market_data import get_position_value

        for position in positions:
            # Check if we have a cached IR beta for this position
            if position.id in cached_betas:
                cached = cached_betas[position.id]
                ir_beta_result = {
                    'position_id': position.id,
                    'symbol': position.symbol,
                    'ir_beta': float(cached.ir_beta),
                    'r_squared': float(cached.r_squared) if cached.r_squared else 0.0,
                    'observations': 60,  # Default observation count for cached
                    'calculation_date': calculation_date,
                    'success': True,
                    'from_cache': True
                }
                positions_from_cache += 1
            else:
                # Calculate IR beta (not cached)
                ir_beta_result = await calculate_position_ir_beta(
                    db, position.id, calculation_date, window_days, treasury_symbol, price_cache
                )
                positions_calculated += 1

                if not ir_beta_result['success']:
                    logger.warning(
                        f"Could not calculate IR beta for {position.symbol}: "
                        f"{ir_beta_result.get('error', 'Unknown error')}"
                    )
                    continue

                # Persist position IR beta (only for newly calculated)
                if persist:
                    await persist_position_ir_beta(db, position.id, portfolio_id, ir_beta_result)

            # Get position market value (absolute value for weighting)
            # Use canonical position value function (signed=False for absolute value)
            market_value = float(get_position_value(position, signed=False, recalculate=True))

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

        # Log cache optimization stats
        if positions_from_cache > 0 or positions_calculated > 0:
            logger.info(
                f"IR beta stats: {positions_from_cache} from cache, "
                f"{positions_calculated} calculated, {len(positions) - positions_from_cache - positions_calculated} failed"
            )

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
