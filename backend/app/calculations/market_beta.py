"""
Market Beta Calculation - Single Factor Model
Calculates position and portfolio market beta using OLS regression against SPY.

Created: 2025-10-17
Replaces: Broken multi-factor model in factors.py
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any
from uuid import UUID
import uuid

import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import MarketDataCache, PositionMarketBeta
from app.constants.factors import REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
from app.calculations.factor_utils import get_position_signed_exposure
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_returns_for_beta(
    db: AsyncSession,
    symbol: str,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch historical prices and calculate returns for a symbol.

    Args:
        db: Database session
        symbol: Symbol to fetch (e.g., 'NVDA', 'SPY')
        start_date: Start date for data
        end_date: End date for data

    Returns:
        Pandas Series of daily returns with date index
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close
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
        logger.warning(f"No price data found for {symbol}")
        return pd.Series(dtype=float)

    # Convert to DataFrame
    df = pd.DataFrame([
        {'date': r.date, 'close': float(r.close)}
        for r in records
    ])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate returns
    returns = df['close'].pct_change(fill_method=None).dropna()

    return returns


async def calculate_position_market_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS
) -> Dict[str, Any]:
    """
    Calculate market beta for a single position using OLS regression.

    Beta = Cov(Position_Return, Market_Return) / Var(Market_Return)

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation (end of window)
        window_days: Lookback period in days (default 90)

    Returns:
        {
            'position_id': UUID,
            'beta': float,
            'r_squared': float,
            'std_error': float,
            'p_value': float,
            'observations': int,
            'calculation_date': date,
            'success': bool,
            'error': str (if failed)
        }
    """
    logger.info(f"Calculating market beta for position {position_id}")

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

        # Fetch position returns
        position_returns = await fetch_returns_for_beta(
            db, position.symbol, start_date, end_date
        )

        if position_returns.empty or len(position_returns) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient data: {len(position_returns)} days',
                'observations': len(position_returns)
            }

        # Fetch SPY returns (market)
        spy_returns = await fetch_returns_for_beta(
            db, 'SPY', start_date, end_date
        )

        if spy_returns.empty:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No SPY data available'
            }

        # Align dates (only use common trading days)
        common_dates = position_returns.index.intersection(spy_returns.index)

        if len(common_dates) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient aligned data: {len(common_dates)} days',
                'observations': len(common_dates)
            }

        # Get aligned returns
        y = position_returns.loc[common_dates].values  # Position returns
        X = spy_returns.loc[common_dates].values        # Market returns

        # Run OLS regression: position_return = alpha + beta * market_return + error
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Extract results
        beta = float(model.params[1])  # Slope coefficient
        alpha = float(model.params[0])  # Intercept
        r_squared = float(model.rsquared)
        std_error = float(model.bse[1])
        p_value = float(model.pvalues[1])

        # Cap beta to prevent extreme outliers
        original_beta = beta
        beta = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, beta))

        if abs(original_beta) > BETA_CAP_LIMIT:
            logger.warning(
                f"Beta capped for {position.symbol}: {original_beta:.3f} -> {beta:.3f}"
            )

        # Determine significance
        is_significant = p_value < 0.10  # 90% confidence

        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'beta': beta,
            'alpha': alpha,
            'r_squared': r_squared,
            'std_error': std_error,
            'p_value': p_value,
            'observations': len(common_dates),
            'calculation_date': calculation_date,
            'is_significant': is_significant,
            'success': True
        }

        logger.info(
            f"Beta calculated for {position.symbol}: {beta:.3f} "
            f"(R²={r_squared:.3f}, p={p_value:.3f}, n={len(common_dates)})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating beta for position {position_id}: {e}")
        return {
            'position_id': position_id,
            'success': False,
            'error': str(e)
        }


async def persist_position_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    position_id: UUID,
    beta_result: Dict[str, Any],
    window_days: int,
    market_index: str = 'SPY'
) -> None:
    """
    Persist position beta to position_market_betas table with historical tracking.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        position_id: Position UUID
        beta_result: Result dictionary from calculate_position_market_beta
        window_days: Regression window in days
        market_index: Market index symbol (default 'SPY')
    """
    try:
        # Check if record already exists for this calc date
        stmt = select(PositionMarketBeta).where(
            and_(
                PositionMarketBeta.portfolio_id == portfolio_id,
                PositionMarketBeta.position_id == position_id,
                PositionMarketBeta.calc_date == beta_result['calculation_date'],
                PositionMarketBeta.method == 'OLS_SIMPLE',
                PositionMarketBeta.window_days == window_days
            )
        )
        existing = await db.execute(stmt)
        existing_record = existing.scalar_one_or_none()

        if existing_record:
            # Update existing record
            existing_record.beta = Decimal(str(beta_result['beta']))
            existing_record.alpha = Decimal(str(beta_result.get('alpha', 0.0)))
            existing_record.r_squared = Decimal(str(beta_result['r_squared']))
            existing_record.std_error = Decimal(str(beta_result['std_error']))
            existing_record.p_value = Decimal(str(beta_result['p_value']))
            existing_record.observations = beta_result['observations']
        else:
            # Create new record
            new_beta = PositionMarketBeta(
                id=uuid.uuid4(),
                portfolio_id=portfolio_id,
                position_id=position_id,
                calc_date=beta_result['calculation_date'],
                beta=Decimal(str(beta_result['beta'])),
                alpha=Decimal(str(beta_result.get('alpha', 0.0))),
                r_squared=Decimal(str(beta_result['r_squared'])),
                std_error=Decimal(str(beta_result['std_error'])),
                p_value=Decimal(str(beta_result['p_value'])),
                observations=beta_result['observations'],
                window_days=window_days,
                method='OLS_SIMPLE',
                market_index=market_index
            )
            db.add(new_beta)

        await db.commit()
        logger.info(f"Persisted beta for position {position_id} to position_market_betas table")

    except Exception as e:
        logger.error(f"Error persisting position beta: {e}")
        await db.rollback()
        raise


async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    persist: bool = True
) -> Dict[str, Any]:
    """
    Calculate portfolio-level market beta using signed exposure-weighted position betas.
    Persists position-level betas to position_market_betas table with historical tracking.

    Portfolio Beta = Σ(signed_exposure_i × position_beta_i) / portfolio_equity

    where signed_exposure_i is:
    - Positive for LONG positions (LONG, LC, LP)
    - Negative for SHORT positions (SHORT, SC, SP)

    This ensures short positions reduce overall portfolio market exposure.
    For example, shorting a high-beta stock will lower the portfolio's beta.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        window_days: Regression window in days (default from constants)
        persist: If True, saves position betas to position_market_betas table

    Returns:
        {
            'portfolio_id': UUID,
            'market_beta': float,
            'r_squared': float (weighted average),
            'observations': int (min across positions),
            'positions_count': int,
            'calculation_date': date,
            'position_betas': Dict[UUID, float],
            'success': bool
        }
    """
    logger.info(f"Calculating portfolio market beta for {portfolio_id}")

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

        # Calculate beta for each position
        position_betas = {}
        position_signed_exposures = {}
        position_r_squareds = {}
        position_objects = {}
        min_observations = float('inf')

        for position in positions:
            beta_result = await calculate_position_market_beta(
                db, position.id, calculation_date, window_days
            )

            if not beta_result['success']:
                logger.warning(
                    f"Could not calculate beta for {position.symbol}: "
                    f"{beta_result.get('error', 'Unknown error')}"
                )
                continue

            # Persist position beta to position_market_betas table
            if persist:
                await persist_position_beta(
                    db, portfolio_id, position.id, beta_result, window_days
                )

            # Get position signed exposure (positive for longs, negative for shorts)
            signed_exposure = float(get_position_signed_exposure(position))

            position_betas[position.id] = beta_result['beta']
            position_signed_exposures[position.id] = signed_exposure
            position_r_squareds[position.id] = beta_result['r_squared']
            position_objects[position.id] = position
            min_observations = min(min_observations, beta_result['observations'])

        if not position_betas:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No position betas could be calculated'
            }

        # Calculate equity-weighted portfolio beta using signed exposures
        # This ensures short positions reduce overall market exposure
        total_weighted_beta_numerator = 0.0
        total_weighted_r_squared = 0.0
        total_abs_exposure = 0.0

        for pos_id, beta in position_betas.items():
            signed_exposure = position_signed_exposures[pos_id]

            # Portfolio beta: sum of (signed_exposure × beta) / equity
            total_weighted_beta_numerator += signed_exposure * beta

            # For R² weighting, use absolute exposure
            abs_exposure = abs(signed_exposure)
            total_abs_exposure += abs_exposure
            total_weighted_r_squared += position_r_squareds[pos_id] * abs_exposure

        # Calculate final portfolio beta
        portfolio_beta = total_weighted_beta_numerator / portfolio_equity

        # Calculate weighted R² (use absolute exposures for averaging)
        if total_abs_exposure > 0:
            avg_r_squared = total_weighted_r_squared / total_abs_exposure
        else:
            avg_r_squared = 0.0

        result = {
            'portfolio_id': portfolio_id,
            'market_beta': portfolio_beta,
            'r_squared': avg_r_squared,
            'observations': int(min_observations) if min_observations != float('inf') else 0,
            'positions_count': len(position_betas),
            'calculation_date': calculation_date,
            'position_betas': {str(k): v for k, v in position_betas.items()},
            'success': True
        }

        logger.info(
            f"Portfolio beta calculated: {portfolio_beta:.3f} "
            f"({len(position_betas)} positions, persisted to position_market_betas)"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating portfolio beta: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }


async def calculate_portfolio_provider_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio-level beta using provider betas from CompanyProfile.

    Returns signed exposure-weighted average of company profile betas (typically 1-year beta from
    data providers like yahooquery/FMP). This provides an alternative beta estimate
    that doesn't require historical returns data or regression calculations.

    Portfolio Provider Beta = Σ(signed_exposure_i × provider_beta_i) / portfolio_equity

    where signed_exposure_i is:
    - Positive for LONG positions
    - Negative for SHORT positions

    This ensures short positions reduce overall portfolio market exposure.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation (not used for provider betas, but kept for API consistency)

    Returns:
        {
            'portfolio_id': UUID,
            'portfolio_beta': float,
            'positions_count': int,
            'positions_with_beta': int,
            'positions_without_beta': int,
            'calculation_date': date,
            'success': bool,
            'error': str (if failed)
        }
    """
    logger.info(f"Calculating provider beta for portfolio {portfolio_id}")

    try:
        # Get portfolio
        from app.models.users import Portfolio as PortfolioModel
        from app.models.market_data import CompanyProfile
        from app.models.positions import PositionType

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

        # Get active stock positions (LONG/SHORT only, exclude options)
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),
                Position.position_type.in_([PositionType.LONG, PositionType.SHORT])
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active stock positions found'
            }

        # Calculate provider beta for each position using signed exposures
        total_weighted_beta_numerator = 0.0
        positions_with_beta = 0
        positions_without_beta = 0

        for position in positions:
            # Get company profile beta
            profile_stmt = select(CompanyProfile).where(CompanyProfile.symbol == position.symbol)
            profile_result = await db.execute(profile_stmt)
            company_profile = profile_result.scalar_one_or_none()

            if company_profile and company_profile.beta and position.market_value:
                beta = float(company_profile.beta)
                # Use signed exposure (positive for longs, negative for shorts)
                signed_exposure = float(get_position_signed_exposure(position))

                # Contribution to portfolio beta
                contribution = signed_exposure * beta
                total_weighted_beta_numerator += contribution
                positions_with_beta += 1

                logger.debug(
                    f"{position.symbol}: beta={beta:.4f}, "
                    f"signed_exposure=${signed_exposure:,.2f}, contribution={contribution:.4f}"
                )
            else:
                positions_without_beta += 1
                if not company_profile:
                    logger.warning(f"No company profile for {position.symbol}")
                elif not company_profile.beta:
                    logger.warning(f"No provider beta for {position.symbol}")

        if positions_with_beta == 0:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': f'No positions have provider beta data (0/{len(positions)})'
            }

        # Calculate final portfolio beta
        portfolio_beta = total_weighted_beta_numerator / portfolio_equity

        result = {
            'portfolio_id': portfolio_id,
            'portfolio_beta': portfolio_beta,
            'positions_count': len(positions),
            'positions_with_beta': positions_with_beta,
            'positions_without_beta': positions_without_beta,
            'calculation_date': calculation_date,
            'success': True
        }

        logger.info(
            f"Provider beta calculated: {portfolio_beta:.3f} "
            f"({positions_with_beta}/{len(positions)} positions with beta data)"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating provider beta: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }
