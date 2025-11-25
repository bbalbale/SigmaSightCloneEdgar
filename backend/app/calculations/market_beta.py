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
from app.calculations.market_data import get_position_value, get_returns
from app.calculations.regression_utils import run_single_factor_regression
from app.core.logging import get_logger

logger = get_logger(__name__)


async def calculate_position_market_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate market beta for a single position using OLS regression.

    Beta = Cov(Position_Return, Market_Return) / Var(Market_Return)

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation (end of window)
        window_days: Lookback period in days (default 90)
        price_cache: Optional PriceCache for optimized price lookups (300x speedup)

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

        # Fetch aligned returns for position and SPY using canonical function
        # This replaces duplicate fetch + manual alignment logic
        returns_df = await get_returns(
            db=db,
            symbols=[position.symbol, 'SPY'],
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
                'error': 'No aligned data available for position and SPY'
            }

        if position.symbol not in returns_df.columns:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'No data found for {position.symbol}'
            }

        if 'SPY' not in returns_df.columns:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No SPY data available'
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
        x = returns_df['SPY'].values            # Market returns

        # Run OLS regression using canonical function from regression_utils
        # This handles: OLS regression, beta capping, significance testing
        regression_result = run_single_factor_regression(
            y=y,
            x=x,
            cap=BETA_CAP_LIMIT,  # Cap beta at ±5.0
            confidence=0.10,     # 90% confidence level (relaxed)
            return_diagnostics=True
        )

        # Build result dictionary with consistent structure
        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'beta': regression_result['beta'],
            'alpha': regression_result['alpha'],
            'r_squared': regression_result['r_squared'],
            'std_error': regression_result['std_error'],
            'p_value': regression_result['p_value'],
            'observations': len(returns_df),
            'calculation_date': calculation_date,
            'is_significant': regression_result['is_significant'],
            'success': True
        }

        logger.info(
            f"Beta calculated for {position.symbol}: {result['beta']:.3f} "
            f"(R²={result['r_squared']:.3f}, p={result['p_value']:.3f}, n={len(returns_df)})"
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

        # Note: Do NOT commit here - let caller manage transaction boundaries
        # Committing after each position expires session objects and causes greenlet errors
        logger.debug(f"Staged beta for position {position_id} (will be committed by caller)")

    except Exception as e:
        logger.error(f"Error persisting position beta: {e}")
        # Note: Do NOT rollback here - let caller manage transaction
        raise


async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,
    persist: bool = True,
    price_cache=None
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

        # OPTIMIZATION: Check which positions already have cached betas for this date
        # This prevents recalculating betas for positions shared across portfolios
        position_ids = [p.id for p in positions]
        cached_betas_stmt = select(PositionMarketBeta).where(
            and_(
                PositionMarketBeta.position_id.in_(position_ids),
                PositionMarketBeta.calc_date == calculation_date,
                PositionMarketBeta.method == 'OLS_SIMPLE',
                PositionMarketBeta.window_days == window_days
            )
        )
        cached_result = await db.execute(cached_betas_stmt)
        cached_betas = {row.position_id: row for row in cached_result.scalars().all()}

        if cached_betas:
            logger.info(
                f"Found {len(cached_betas)}/{len(positions)} positions with cached market betas "
                f"for {calculation_date} (skipping recalculation)"
            )

        # Calculate beta for each position
        position_betas = {}
        position_signed_exposures = {}
        position_r_squareds = {}
        position_objects = {}
        min_observations = float('inf')
        positions_calculated = 0
        positions_from_cache = 0

        for position in positions:
            # Check if we have a cached beta for this position
            if position.id in cached_betas:
                cached = cached_betas[position.id]
                beta_result = {
                    'position_id': position.id,
                    'symbol': position.symbol,
                    'beta': float(cached.beta),
                    'r_squared': float(cached.r_squared) if cached.r_squared else 0.0,
                    'observations': cached.observations or 60,
                    'calculation_date': calculation_date,
                    'success': True,
                    'from_cache': True
                }
                positions_from_cache += 1
            else:
                # Calculate beta (not cached)
                beta_result = await calculate_position_market_beta(
                    db, position.id, calculation_date, window_days, price_cache
                )
                positions_calculated += 1

                if not beta_result['success']:
                    logger.warning(
                        f"Could not calculate beta for {position.symbol}: "
                        f"{beta_result.get('error', 'Unknown error')}"
                    )
                    continue

                # Persist position beta to position_market_betas table (only for newly calculated)
                if persist:
                    await persist_position_beta(
                        db, portfolio_id, position.id, beta_result, window_days
                    )

            # Get position signed exposure (positive for longs, negative for shorts)
            # Use canonical position value function (signed=True for directional exposure)
            signed_exposure = float(get_position_value(position, signed=True))

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

        # Log cache optimization stats
        if positions_from_cache > 0 or positions_calculated > 0:
            logger.info(
                f"Market beta stats: {positions_from_cache} from cache, "
                f"{positions_calculated} calculated, {len(positions) - positions_from_cache - positions_calculated} failed"
            )

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

        # CRITICAL FIX: Save Market Beta as a factor exposure for stress testing
        # Stress testing requires portfolio-level factor exposures, not just position betas
        if persist:
            try:
                from app.models.market_data import FactorExposure, FactorDefinition
                from decimal import Decimal

                # Get Market Beta (90D) factor definition
                factor_stmt = select(FactorDefinition).where(FactorDefinition.name == "Market Beta (90D)")
                factor_result = await db.execute(factor_stmt)
                market_beta_factor = factor_result.scalar_one_or_none()

                # Fallback to old "Market Beta" name for compatibility
                if not market_beta_factor:
                    factor_stmt = select(FactorDefinition).where(FactorDefinition.name == "Market Beta")
                    factor_result = await db.execute(factor_stmt)
                    market_beta_factor = factor_result.scalar_one_or_none()

                    # Update the name if found
                    if market_beta_factor:
                        market_beta_factor.name = "Market Beta (90D)"
                        market_beta_factor.description = "90-day market beta calculated via OLS regression"
                        market_beta_factor.display_order = 1  # Show after Provider Beta (1Y)

                if market_beta_factor:
                    # Calculate dollar exposure (beta * portfolio equity)
                    exposure_dollar = Decimal(str(portfolio_beta)) * Decimal(str(portfolio_equity))

                    # Create or update factor exposure
                    exposure_stmt = select(FactorExposure).where(
                        and_(
                            FactorExposure.portfolio_id == portfolio_id,
                            FactorExposure.factor_id == market_beta_factor.id,
                            FactorExposure.calculation_date == calculation_date
                        )
                    )
                    exposure_result = await db.execute(exposure_stmt)
                    existing_exposure = exposure_result.scalar_one_or_none()

                    if existing_exposure:
                        # Update existing record
                        existing_exposure.exposure_value = Decimal(str(portfolio_beta))
                        existing_exposure.exposure_dollar = exposure_dollar
                        logger.debug(f"Updated Market Beta factor exposure: {portfolio_beta:.3f}")
                    else:
                        # Create new record
                        from uuid import uuid4
                        new_exposure = FactorExposure(
                            id=uuid4(),
                            portfolio_id=portfolio_id,
                            factor_id=market_beta_factor.id,
                            calculation_date=calculation_date,
                            exposure_value=Decimal(str(portfolio_beta)),
                            exposure_dollar=exposure_dollar
                        )
                        db.add(new_exposure)
                        logger.debug(f"Created Market Beta factor exposure: {portfolio_beta:.3f}")
                else:
                    logger.warning("Market Beta factor definition not found - cannot save factor exposure")

            except Exception as e:
                logger.error(f"Error saving Market Beta factor exposure: {e}")
                # Don't fail the entire calculation if factor exposure saving fails

        logger.info(
            f"Portfolio beta calculated: {portfolio_beta:.3f} "
            f"({len(position_betas)} positions, persisted to position_market_betas & factor_exposures)"
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

    FALLBACK LOGIC (Added 2025-11-09):
    If a position's company profile beta is missing or zero, falls back to using the
    latest calculated beta from position_market_betas table (OLS regression).

    Portfolio Provider Beta = Σ(signed_exposure_i × beta_i) / portfolio_equity

    where signed_exposure_i is:
    - Positive for LONG positions
    - Negative for SHORT positions

    and beta_i is:
    - Company profile beta (from yfinance) if available
    - Calculated beta (from OLS regression) if company profile beta is missing/zero

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
    logger.info(f"[PROVIDER BETA] Starting calculation for portfolio {portfolio_id}")

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

        # Get active PUBLIC stock positions only (exclude OPTIONS, PRIVATE, and soft-deleted)
        # OPTIMIZATION: Provider beta only makes sense for public equities
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),
                Position.deleted_at.is_(None),
                Position.position_type.in_([PositionType.LONG, PositionType.SHORT]),
                Position.investment_class == 'PUBLIC'  # Only public stocks/ETFs
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active public stock positions found'
            }

        # OPTIMIZATION: Bulk-load all company profile betas in ONE query (fixes N+1 issue)
        position_symbols = [p.symbol for p in positions]
        position_ids = [p.id for p in positions]

        # Bulk fetch provider betas from company_profiles
        profiles_stmt = select(CompanyProfile.symbol, CompanyProfile.beta).where(
            CompanyProfile.symbol.in_(position_symbols)
        )
        profiles_result = await db.execute(profiles_stmt)
        provider_betas = {row.symbol: row.beta for row in profiles_result.all()}
        logger.info(f"[PROVIDER BETA] Bulk-loaded {len(provider_betas)} company profile betas (1 query)")

        # Bulk fetch calculated betas as fallback (latest per position)
        from sqlalchemy import func as sqlfunc
        # Subquery to get max calc_date per position
        latest_dates_subq = (
            select(
                PositionMarketBeta.position_id,
                sqlfunc.max(PositionMarketBeta.calc_date).label('max_date')
            )
            .where(PositionMarketBeta.position_id.in_(position_ids))
            .group_by(PositionMarketBeta.position_id)
            .subquery()
        )
        # Join to get the beta values at those dates
        calculated_betas_stmt = (
            select(PositionMarketBeta.position_id, PositionMarketBeta.beta)
            .join(
                latest_dates_subq,
                and_(
                    PositionMarketBeta.position_id == latest_dates_subq.c.position_id,
                    PositionMarketBeta.calc_date == latest_dates_subq.c.max_date
                )
            )
        )
        calculated_result = await db.execute(calculated_betas_stmt)
        calculated_betas = {row.position_id: row.beta for row in calculated_result.all()}
        logger.info(f"[PROVIDER BETA] Bulk-loaded {len(calculated_betas)} calculated betas as fallback (1 query)")

        # Calculate provider beta for each position using signed exposures
        total_weighted_beta_numerator = 0.0
        positions_with_beta = 0
        positions_without_beta = 0

        logger.info(f"[PROVIDER BETA] Processing {len(positions)} positions...")

        for position in positions:
            # Get provider beta from bulk-loaded cache
            provider_beta = provider_betas.get(position.symbol)

            # FALLBACK: If company profile beta is missing or zero, try calculated beta
            if not provider_beta or float(provider_beta) == 0.0:
                calculated_beta = calculated_betas.get(position.id)
                if calculated_beta is not None:
                    provider_beta = calculated_beta
                    logger.debug(
                        f"Using calculated beta ({float(calculated_beta):.4f}) "
                        f"as fallback for {position.symbol}"
                    )

            if provider_beta and position.market_value:
                beta = float(provider_beta)
                # Use signed exposure (positive for longs, negative for shorts)
                # Use canonical position value function (signed=True for directional exposure)
                signed_exposure = float(get_position_value(position, signed=True))

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
                if not provider_beta:
                    logger.warning(
                        f"No provider beta or calculated beta available for {position.symbol}"
                    )

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
            f"[PROVIDER BETA] Complete: {portfolio_beta:.3f} "
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
