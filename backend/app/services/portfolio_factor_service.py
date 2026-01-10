"""
Portfolio Factor Service - Aggregate symbol-level betas to portfolio level.

This service implements the LOOKUP pattern for factor exposures:
1. Symbol betas are pre-computed by the universe job (Phase 0.5)
2. Portfolio requests LOOKUP pre-computed betas (not calculate)
3. Aggregate using position weights to get portfolio-level exposures

Key insight: Factor beta is intrinsic to the symbol, not the position.
AAPL's momentum beta is the same regardless of which portfolio holds it.
So we calculate once per symbol, then aggregate per portfolio.

Created: 2025-12-20
Part of Symbol Factor Universe Architecture (Phase 3)
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import FactorDefinition, FactorExposure, PositionGreeks
from app.models.symbol_analytics import SymbolFactorExposure
from app.calculations.symbol_factors import load_symbol_betas
from app.calculations.market_data import get_position_value
from app.core.logging import get_logger

logger = get_logger(__name__)

# Factor types for aggregation
RIDGE_FACTORS = ['Value', 'Growth', 'Momentum', 'Quality', 'Size', 'Low Volatility']
SPREAD_FACTORS = ['Growth-Value Spread', 'Momentum Spread', 'Size Spread', 'Quality Spread']


@dataclass
class PositionWeight:
    """Position weight information for aggregation."""
    position_id: UUID
    symbol: str
    weight: float  # signed_market_value / portfolio_equity
    delta: Optional[float] = None  # For options delta adjustment
    is_option: bool = False


async def get_portfolio_positions_with_weights(
    db: AsyncSession,
    portfolio_id: UUID
) -> Tuple[List[PositionWeight], float]:
    """
    Load portfolio positions with their weights.

    Weight = signed_market_value / portfolio_equity

    For options, also loads delta for delta-adjusted exposure.

    Args:
        db: Database session
        portfolio_id: Portfolio to load

    Returns:
        Tuple of (list of PositionWeight, portfolio_equity)
    """
    # Load portfolio for equity balance
    portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()

    if portfolio is None:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    portfolio_equity = float(portfolio.equity_balance)
    if portfolio_equity <= 0:
        raise ValueError(f"Portfolio {portfolio_id} has invalid equity_balance: {portfolio_equity}")

    # Load positions
    positions_stmt = (
        select(Position)
        .where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),  # Active only
                Position.investment_class == 'PUBLIC'  # PUBLIC only
            )
        )
    )
    positions_result = await db.execute(positions_stmt)
    positions = list(positions_result.scalars().all())

    # Load Greeks for options (to get delta)
    option_position_ids = [
        p.id for p in positions
        if p.position_type.value in ('LC', 'LP', 'SC', 'SP')
    ]

    delta_map: Dict[UUID, float] = {}
    if option_position_ids:
        greeks_stmt = (
            select(PositionGreeks.position_id, PositionGreeks.delta)
            .where(PositionGreeks.position_id.in_(option_position_ids))
        )
        greeks_result = await db.execute(greeks_stmt)
        for pos_id, delta in greeks_result.fetchall():
            if delta is not None:
                delta_map[pos_id] = float(delta)

    # Build position weights
    position_weights: List[PositionWeight] = []

    for position in positions:
        # Get signed market value
        signed_value = float(get_position_value(position, signed=True, recalculate=False))
        weight = signed_value / portfolio_equity

        is_option = position.position_type.value in ('LC', 'LP', 'SC', 'SP')
        delta = delta_map.get(position.id)

        position_weights.append(PositionWeight(
            position_id=position.id,
            symbol=position.symbol,
            weight=weight,
            delta=delta,
            is_option=is_option
        ))

    logger.info(
        f"Loaded {len(position_weights)} positions for portfolio {portfolio_id}, "
        f"equity=${portfolio_equity:,.2f}"
    )

    return position_weights, portfolio_equity


def aggregate_symbol_betas_to_portfolio(
    position_weights: List[PositionWeight],
    symbol_betas: Dict[str, Dict[str, float]],
    use_delta_adjusted: bool = False
) -> Dict[str, float]:
    """
    Aggregate symbol-level betas to portfolio level.

    Portfolio Beta[factor] = Σ(position_weight × symbol_beta[factor])

    For options with delta adjustment:
    Portfolio Beta[factor] = Σ(position_weight × delta × symbol_beta[factor])

    Args:
        position_weights: List of PositionWeight with weights and optional deltas
        symbol_betas: Dict mapping symbol -> {factor_name: beta_value}
        use_delta_adjusted: Whether to apply delta adjustment for options

    Returns:
        Dict mapping factor_name -> portfolio_beta
    """
    # Collect all factor names from symbol betas
    factor_names = set()
    for betas in symbol_betas.values():
        factor_names.update(betas.keys())

    # Initialize portfolio betas
    portfolio_betas: Dict[str, float] = {fn: 0.0 for fn in factor_names}

    # Track coverage for diagnostics
    positions_with_betas = 0
    positions_missing_betas = 0

    for pw in position_weights:
        if pw.symbol not in symbol_betas:
            positions_missing_betas += 1
            logger.debug(f"No symbol betas for {pw.symbol}")
            continue

        positions_with_betas += 1
        symbol_beta = symbol_betas[pw.symbol]

        # Calculate effective weight
        if use_delta_adjusted and pw.is_option and pw.delta is not None:
            # Options: weight × delta gives delta-adjusted exposure
            effective_weight = pw.weight * pw.delta
        else:
            effective_weight = pw.weight

        # Add weighted contribution to each factor
        for factor_name, beta_value in symbol_beta.items():
            portfolio_betas[factor_name] += effective_weight * beta_value

    logger.info(
        f"Aggregated {positions_with_betas} positions with betas, "
        f"{positions_missing_betas} missing (will use 0)"
    )

    return portfolio_betas


async def get_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    use_delta_adjusted: bool = False,
    include_ridge: bool = True,
    include_spread: bool = True
) -> Dict[str, Any]:
    """
    Get portfolio factor exposures by aggregating pre-computed symbol betas.

    This is the main entry point for portfolio factor lookups.
    It's a LOOKUP operation, not a calculation - assumes symbol betas
    were pre-computed by the universe job (Phase 0.5).

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date to load betas for
        use_delta_adjusted: Apply delta adjustment for options
        include_ridge: Include Ridge factors (6 factors)
        include_spread: Include Spread factors (4 factors)

    Returns:
        Dict with:
        - factor_betas: {factor_name: portfolio_beta}
        - ridge_betas: Ridge factors only (if include_ridge)
        - spread_betas: Spread factors only (if include_spread)
        - metadata: Aggregation metadata
        - data_quality: Coverage and quality metrics
    """
    logger.info(
        f"Getting portfolio factor exposures for {portfolio_id} as of {calculation_date}"
    )

    # Step 1: Load positions with weights
    position_weights, portfolio_equity = await get_portfolio_positions_with_weights(
        db, portfolio_id
    )

    if not position_weights:
        logger.warning(f"No active PUBLIC positions for portfolio {portfolio_id}")
        return _build_empty_result(portfolio_id, calculation_date, 'no_positions')

    # Step 2: Get unique symbols
    symbols = list(set(pw.symbol for pw in position_weights))
    logger.info(f"Found {len(symbols)} unique symbols in portfolio")

    # Step 3: Load pre-computed symbol betas
    results = {
        'portfolio_id': str(portfolio_id),
        'calculation_date': calculation_date.isoformat(),
        'factor_betas': {},
        'ridge_betas': {},
        'spread_betas': {},
        'metadata': {
            'positions_count': len(position_weights),
            'unique_symbols': len(symbols),
            'portfolio_equity': portfolio_equity,
            'use_delta_adjusted': use_delta_adjusted
        },
        'data_quality': {
            'total_symbols': len(symbols),
            'symbols_with_ridge': 0,
            'symbols_with_spread': 0,
            'symbols_missing': 0
        }
    }

    # Load Ridge betas
    if include_ridge:
        ridge_betas = await load_symbol_betas(
            db, symbols, calculation_date, 'ridge_regression'
        )
        results['data_quality']['symbols_with_ridge'] = len(ridge_betas)

        # Aggregate Ridge factors
        ridge_portfolio_betas = aggregate_symbol_betas_to_portfolio(
            position_weights, ridge_betas, use_delta_adjusted
        )
        results['ridge_betas'] = ridge_portfolio_betas
        results['factor_betas'].update(ridge_portfolio_betas)

    # Load Spread betas
    if include_spread:
        spread_betas = await load_symbol_betas(
            db, symbols, calculation_date, 'spread_regression'
        )
        results['data_quality']['symbols_with_spread'] = len(spread_betas)

        # Aggregate Spread factors
        spread_portfolio_betas = aggregate_symbol_betas_to_portfolio(
            position_weights, spread_betas, use_delta_adjusted
        )
        results['spread_betas'] = spread_portfolio_betas
        results['factor_betas'].update(spread_portfolio_betas)

    # Calculate missing symbols
    all_loaded = set()
    if include_ridge:
        all_loaded.update(ridge_betas.keys())
    if include_spread:
        all_loaded.update(spread_betas.keys())
    results['data_quality']['symbols_missing'] = len(symbols) - len(all_loaded)

    logger.info(
        f"Portfolio factor exposures: {len(results['factor_betas'])} factors, "
        f"Ridge: {results['data_quality']['symbols_with_ridge']}/{len(symbols)} symbols, "
        f"Spread: {results['data_quality']['symbols_with_spread']}/{len(symbols)} symbols"
    )

    return results


async def store_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    portfolio_betas: Dict[str, float],
    calculation_date: date,
    portfolio_equity: float
) -> Dict[str, Any]:
    """
    Store portfolio-level factor exposures to FactorExposure table.

    Uses upsert pattern (update if exists, insert if not).
    Does NOT commit - caller manages transaction.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        portfolio_betas: {factor_name: beta_value}
        calculation_date: Calculation date
        portfolio_equity: Portfolio equity for dollar exposure

    Returns:
        Storage results with counts
    """
    from uuid import uuid4

    # Load factor definitions
    factor_stmt = select(FactorDefinition.name, FactorDefinition.id)
    factor_result = await db.execute(factor_stmt)
    factor_name_to_id = {row[0]: row[1] for row in factor_result.fetchall()}

    results = {
        'records_stored': 0,
        'factors_stored': [],
        'errors': []
    }

    for factor_name, beta_value in portfolio_betas.items():
        if factor_name not in factor_name_to_id:
            results['errors'].append(f"Factor '{factor_name}' not found in database")
            continue

        factor_id = factor_name_to_id[factor_name]
        exposure_dollar = Decimal(str(beta_value)) * Decimal(str(portfolio_equity))

        # Check if record exists
        existing_stmt = select(FactorExposure).where(
            and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id == factor_id,
                FactorExposure.calculation_date == calculation_date
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            existing_record.exposure_value = Decimal(str(beta_value))
            existing_record.exposure_dollar = exposure_dollar
        else:
            new_record = FactorExposure(
                id=uuid4(),
                portfolio_id=portfolio_id,
                factor_id=factor_id,
                calculation_date=calculation_date,
                exposure_value=Decimal(str(beta_value)),
                exposure_dollar=exposure_dollar
            )
            db.add(new_record)

        results['records_stored'] += 1
        results['factors_stored'].append(factor_name)

    logger.info(f"Stored {results['records_stored']} portfolio factor exposures")
    return results


async def calculate_and_store_portfolio_factors(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    use_delta_adjusted: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for batch processing: lookup and store portfolio factors.

    This function:
    1. Loads positions with weights
    2. Looks up pre-computed symbol betas
    3. Aggregates to portfolio level
    4. Stores to FactorExposure table
    5. Commits the transaction

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        use_delta_adjusted: Apply delta adjustment for options

    Returns:
        Complete results including betas and storage info
    """
    # Get portfolio factor exposures (lookup + aggregate)
    results = await get_portfolio_factor_exposures(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date,
        use_delta_adjusted=use_delta_adjusted,
        include_ridge=True,
        include_spread=True
    )

    if not results['factor_betas']:
        logger.warning(f"No factor betas to store for portfolio {portfolio_id}")
        return results

    # Store to database
    storage_results = await store_portfolio_factor_exposures(
        db=db,
        portfolio_id=portfolio_id,
        portfolio_betas=results['factor_betas'],
        calculation_date=calculation_date,
        portfolio_equity=results['metadata']['portfolio_equity']
    )

    results['storage_results'] = storage_results

    # Commit
    await db.commit()

    logger.info(
        f"Portfolio {portfolio_id}: stored {storage_results['records_stored']} factor exposures"
    )

    return results


def _build_empty_result(
    portfolio_id: UUID,
    calculation_date: date,
    reason: str
) -> Dict[str, Any]:
    """Build empty result for skip cases."""
    return {
        'portfolio_id': str(portfolio_id),
        'calculation_date': calculation_date.isoformat(),
        'factor_betas': {},
        'ridge_betas': {},
        'spread_betas': {},
        'metadata': {
            'skipped': True,
            'skip_reason': reason
        },
        'data_quality': {
            'total_symbols': 0,
            'symbols_with_ridge': 0,
            'symbols_with_spread': 0,
            'symbols_missing': 0
        }
    }


# NOTE: compare_symbol_vs_position_factors() removed 2025-12-22
# Position-level factor calculation is deprecated. Use external database comparison instead.
# See scripts/validation/compare_factor_exposures.py for cross-database validation.
