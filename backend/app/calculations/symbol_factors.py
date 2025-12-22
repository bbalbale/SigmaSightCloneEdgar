"""
Symbol-Level Factor Calculations

This module calculates factor betas at the SYMBOL level (not position level).
Key insight: Factor beta is intrinsic to the symbol - AAPL's momentum beta is the
same regardless of which portfolio holds it.

Architecture:
1. Get all unique symbols from positions table
2. Check which symbols need calculation (not cached for today)
3. Batch symbols into groups (safe parallelization pattern)
4. Process batches in parallel (each batch = isolated session)
5. Store results in symbol_factor_exposures table

Benefits:
- Calculate each symbol ONCE per day (not once per position)
- Enable parallel processing with isolated sessions
- Support predictive "what-if" analysis for new portfolios
- Align with industry risk model architecture (Barra, Axioma, MSCI)

Created: 2025-12-20
Part of Symbol Factor Universe Architecture (Phase 2)
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from uuid import UUID, uuid4

import pandas as pd
import numpy as np
from sqlalchemy import select, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.market_data import FactorDefinition
from app.models.symbol_analytics import SymbolUniverse, SymbolFactorExposure
from app.calculations.market_data import get_returns
from app.calculations.factors_ridge import (
    calculate_single_position_ridge_betas,
    RIDGE_STYLE_FACTORS,
    EXPECTED_RIDGE_FACTOR_COUNT,
)
from app.calculations.factors_spread import (
    calculate_single_position_spread_betas,
    fetch_spread_returns,
    EXPECTED_SPREAD_FACTOR_COUNT,
)
from app.constants.factors import (
    REGRESSION_WINDOW_DAYS,
    SPREAD_REGRESSION_WINDOW_DAYS,
    MIN_REGRESSION_DAYS,
    SPREAD_MIN_REGRESSION_DAYS,
    QUALITY_FLAG_FULL_HISTORY,
    QUALITY_FLAG_LIMITED_HISTORY,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Parallelization parameters
BATCH_SIZE = 15  # Symbols per batch (balance parallelism vs session overhead)
MAX_CONCURRENT_BATCHES = 5  # Limit concurrent DB connections
DEFAULT_REGULARIZATION_ALPHA = 1.0


async def get_all_active_symbols(db: AsyncSession) -> List[str]:
    """
    Get all unique symbols that need factor calculations.

    Sources:
    1. PUBLIC equity positions (LONG/SHORT) - portfolio holdings
    2. market_data_cache - full universe (S&P 500, Nasdaq 100, Russell 2000, etc.)

    This ensures factor betas are pre-computed for:
    - All current portfolio holdings (for P&L and analytics)
    - All symbols in the universe (for equity search and what-if analysis)
    """
    from app.models.market_data import MarketDataCache

    # Get symbols from positions
    position_stmt = (
        select(distinct(Position.symbol))
        .where(
            and_(
                Position.investment_class == 'PUBLIC',
                Position.position_type.in_(['LONG', 'SHORT']),
                Position.symbol.isnot(None),
                Position.symbol != ''
            )
        )
    )
    position_result = await db.execute(position_stmt)
    position_symbols = {row[0] for row in position_result.fetchall()}

    # Get symbols from market_data_cache (full universe)
    cache_stmt = select(distinct(MarketDataCache.symbol)).where(
        MarketDataCache.symbol.isnot(None),
        MarketDataCache.symbol != ''
    )
    cache_result = await db.execute(cache_stmt)
    cache_symbols = {row[0] for row in cache_result.fetchall()}

    # Union of both sources
    all_symbols = list(position_symbols | cache_symbols)

    logger.info(
        f"Found {len(all_symbols)} unique symbols for factor calculation "
        f"(positions: {len(position_symbols)}, market_data_cache: {len(cache_symbols)})"
    )
    return all_symbols


async def get_uncached_symbols(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date,
    calculation_method: str
) -> List[str]:
    """
    Find symbols that don't have cached factor exposures for the given date.

    Args:
        db: Database session
        symbols: List of symbols to check
        calculation_date: Date to check for cached values
        calculation_method: 'ridge_regression' or 'spread_regression'

    Returns:
        List of symbols that need calculation
    """
    if not symbols:
        return []

    # Count factors per symbol for this date and method
    expected_count = (
        EXPECTED_RIDGE_FACTOR_COUNT if calculation_method == 'ridge_regression'
        else EXPECTED_SPREAD_FACTOR_COUNT
    )

    stmt = (
        select(
            SymbolFactorExposure.symbol,
            func.count(SymbolFactorExposure.id).label('factor_count')
        )
        .where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date == calculation_date,
                SymbolFactorExposure.calculation_method == calculation_method
            )
        )
        .group_by(SymbolFactorExposure.symbol)
        .having(func.count(SymbolFactorExposure.id) >= expected_count)
    )

    result = await db.execute(stmt)
    cached_symbols = {row[0] for row in result.fetchall()}

    uncached = [s for s in symbols if s not in cached_symbols]

    logger.info(
        f"Cache check for {calculation_method}: "
        f"{len(cached_symbols)} cached, {len(uncached)} need calculation"
    )

    return uncached


async def ensure_symbols_in_universe(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date
) -> None:
    """
    Ensure all symbols exist in symbol_universe table.
    Creates entries for new symbols with today's date as first_seen_date.
    """
    if not symbols:
        return

    # Get existing symbols
    stmt = select(SymbolUniverse.symbol).where(SymbolUniverse.symbol.in_(symbols))
    result = await db.execute(stmt)
    existing_symbols = {row[0] for row in result.fetchall()}

    # Insert new symbols
    new_symbols = [s for s in symbols if s not in existing_symbols]

    if new_symbols:
        for symbol in new_symbols:
            new_entry = SymbolUniverse(
                symbol=symbol,
                asset_type='equity',
                first_seen_date=calculation_date,
                last_seen_date=calculation_date,
                is_active=True
            )
            db.add(new_entry)

        await db.commit()
        logger.info(f"Added {len(new_symbols)} new symbols to universe")

    # Update last_seen_date for existing symbols
    if existing_symbols:
        from sqlalchemy import update
        stmt = (
            update(SymbolUniverse)
            .where(SymbolUniverse.symbol.in_(list(existing_symbols)))
            .values(last_seen_date=calculation_date)
        )
        await db.execute(stmt)
        await db.commit()


async def persist_symbol_factors(
    db: AsyncSession,
    symbol: str,
    factor_betas: Dict[str, float],
    calculation_date: date,
    factor_name_to_id: Dict[str, UUID],
    calculation_method: str,
    r_squared: Optional[float] = None,
    observations: Optional[int] = None,
    quality_flag: Optional[str] = None,
    regularization_alpha: Optional[float] = None,
    regression_window_days: Optional[int] = None
) -> int:
    """
    Persist symbol factor exposures to database using upsert pattern.

    Args:
        db: Database session
        symbol: Symbol to save factors for
        factor_betas: Dict mapping factor names to beta values
        calculation_date: Calculation date
        factor_name_to_id: Mapping of factor names to UUIDs
        calculation_method: 'ridge_regression' or 'spread_regression'
        r_squared: Optional R² value
        observations: Optional observation count
        quality_flag: Optional quality flag
        regularization_alpha: Optional alpha (for ridge only)
        regression_window_days: Optional window size

    Returns:
        Number of records stored
    """
    records_stored = 0

    for factor_name, beta_value in factor_betas.items():
        # Get factor_id from mapping
        factor_id = factor_name_to_id.get(factor_name)
        if factor_id is None:
            logger.warning(f"Factor '{factor_name}' not found in factor definitions")
            continue

        # Check if record exists
        existing_stmt = select(SymbolFactorExposure).where(
            and_(
                SymbolFactorExposure.symbol == symbol,
                SymbolFactorExposure.factor_id == factor_id,
                SymbolFactorExposure.calculation_date == calculation_date
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            # Update existing
            existing_record.beta_value = Decimal(str(beta_value))
            existing_record.r_squared = Decimal(str(r_squared)) if r_squared else None
            existing_record.observations = observations
            existing_record.quality_flag = quality_flag
            existing_record.calculation_method = calculation_method
            existing_record.regularization_alpha = Decimal(str(regularization_alpha)) if regularization_alpha else None
            existing_record.regression_window_days = regression_window_days
        else:
            # Insert new
            new_record = SymbolFactorExposure(
                id=uuid4(),
                symbol=symbol,
                factor_id=factor_id,
                calculation_date=calculation_date,
                beta_value=Decimal(str(beta_value)),
                r_squared=Decimal(str(r_squared)) if r_squared else None,
                observations=observations,
                quality_flag=quality_flag,
                calculation_method=calculation_method,
                regularization_alpha=Decimal(str(regularization_alpha)) if regularization_alpha else None,
                regression_window_days=regression_window_days
            )
            db.add(new_record)

        records_stored += 1

    return records_stored


async def calculate_symbol_ridge_factors(
    db: AsyncSession,
    symbol: str,
    factor_returns: pd.DataFrame,
    calculation_date: date,
    factor_name_to_id: Dict[str, UUID],
    regularization_alpha: float = DEFAULT_REGULARIZATION_ALPHA,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate Ridge regression factor betas for a single symbol.

    This is the core calculation function for Ridge factors at symbol level.
    Reuses the same regression logic as position-level calculations.

    Args:
        db: Database session
        symbol: Symbol to calculate factors for
        factor_returns: Pre-fetched factor ETF returns (passed in for efficiency)
        calculation_date: Calculation date
        factor_name_to_id: Mapping of factor names to UUIDs
        regularization_alpha: L2 penalty strength
        price_cache: Optional price cache

    Returns:
        Dict with betas, r_squared, success, etc.
    """
    # Fetch symbol returns
    start_date = calculation_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)

    symbol_returns_df = await get_returns(
        db=db,
        symbols=[symbol],
        start_date=start_date,
        end_date=calculation_date,
        align_dates=True,
        price_cache=price_cache
    )

    if symbol_returns_df.empty or symbol not in symbol_returns_df.columns:
        return {
            'symbol': symbol,
            'success': False,
            'error': f'No return data for {symbol}',
            'betas': {},
            'r_squared': 0.0,
            'observations': 0
        }

    symbol_returns = symbol_returns_df[symbol]

    # Align with factor returns
    common_dates = factor_returns.index.intersection(symbol_returns.index)
    if len(common_dates) < MIN_REGRESSION_DAYS:
        return {
            'symbol': symbol,
            'success': False,
            'error': f'Insufficient aligned data: {len(common_dates)} days',
            'betas': {},
            'r_squared': 0.0,
            'observations': len(common_dates)
        }

    symbol_returns_aligned = symbol_returns.loc[common_dates]
    factor_returns_aligned = factor_returns.loc[common_dates]

    # Run Ridge regression
    result = calculate_single_position_ridge_betas(
        position_returns=symbol_returns_aligned,
        factor_returns=factor_returns_aligned,
        regularization_alpha=regularization_alpha
    )

    if result['success']:
        # Persist to database
        quality_flag = (
            QUALITY_FLAG_FULL_HISTORY if result['observations'] >= MIN_REGRESSION_DAYS
            else QUALITY_FLAG_LIMITED_HISTORY
        )

        records_stored = await persist_symbol_factors(
            db=db,
            symbol=symbol,
            factor_betas=result['betas'],
            calculation_date=calculation_date,
            factor_name_to_id=factor_name_to_id,
            calculation_method='ridge_regression',
            r_squared=result['r_squared'],
            observations=result['observations'],
            quality_flag=quality_flag,
            regularization_alpha=regularization_alpha,
            regression_window_days=REGRESSION_WINDOW_DAYS
        )

        return {
            'symbol': symbol,
            'success': True,
            'betas': result['betas'],
            'r_squared': result['r_squared'],
            'observations': result['observations'],
            'records_stored': records_stored
        }
    else:
        return {
            'symbol': symbol,
            'success': False,
            'error': result.get('error', 'Ridge regression failed'),
            'betas': {},
            'r_squared': 0.0,
            'observations': result.get('observations', 0)
        }


async def calculate_symbol_spread_factors(
    db: AsyncSession,
    symbol: str,
    spread_returns: pd.DataFrame,
    calculation_date: date,
    factor_name_to_id: Dict[str, UUID],
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate Spread factor betas for a single symbol.

    This is the core calculation function for Spread factors at symbol level.
    Reuses the same regression logic as position-level calculations.

    Args:
        db: Database session
        symbol: Symbol to calculate factors for
        spread_returns: Pre-fetched spread returns (passed in for efficiency)
        calculation_date: Calculation date
        factor_name_to_id: Mapping of factor names to UUIDs
        price_cache: Optional price cache

    Returns:
        Dict with betas, r_squared, success, etc.
    """
    # Fetch symbol returns
    start_date = calculation_date - timedelta(days=SPREAD_REGRESSION_WINDOW_DAYS + 30)

    symbol_returns_df = await get_returns(
        db=db,
        symbols=[symbol],
        start_date=start_date,
        end_date=calculation_date,
        align_dates=True,
        price_cache=price_cache
    )

    if symbol_returns_df.empty or symbol not in symbol_returns_df.columns:
        return {
            'symbol': symbol,
            'success': False,
            'error': f'No return data for {symbol}',
            'betas': {},
            'r_squared': 0.0,
            'observations': 0
        }

    symbol_returns = symbol_returns_df[symbol]

    # Align with spread returns
    common_dates = spread_returns.index.intersection(symbol_returns.index)
    if len(common_dates) < SPREAD_MIN_REGRESSION_DAYS:
        return {
            'symbol': symbol,
            'success': False,
            'error': f'Insufficient aligned data: {len(common_dates)} days',
            'betas': {},
            'r_squared': 0.0,
            'observations': len(common_dates)
        }

    symbol_returns_aligned = symbol_returns.loc[common_dates]
    spread_returns_aligned = spread_returns.loc[common_dates]

    # Run OLS regressions
    result = calculate_single_position_spread_betas(
        position_returns=symbol_returns_aligned,
        spread_returns=spread_returns_aligned
    )

    if result['success'] and result['betas']:
        # Persist to database
        quality_flag = (
            QUALITY_FLAG_FULL_HISTORY if result['observations'] >= SPREAD_MIN_REGRESSION_DAYS
            else QUALITY_FLAG_LIMITED_HISTORY
        )

        records_stored = await persist_symbol_factors(
            db=db,
            symbol=symbol,
            factor_betas=result['betas'],
            calculation_date=calculation_date,
            factor_name_to_id=factor_name_to_id,
            calculation_method='spread_regression',
            r_squared=result['avg_r_squared'],
            observations=result['observations'],
            quality_flag=quality_flag,
            regularization_alpha=None,  # Not used for spread
            regression_window_days=SPREAD_REGRESSION_WINDOW_DAYS
        )

        return {
            'symbol': symbol,
            'success': True,
            'betas': result['betas'],
            'r_squared': result['avg_r_squared'],
            'observations': result['observations'],
            'records_stored': records_stored
        }
    else:
        return {
            'symbol': symbol,
            'success': False,
            'error': result.get('error', 'Spread regression failed'),
            'betas': {},
            'r_squared': 0.0,
            'observations': result.get('observations', 0)
        }


async def _load_factor_definitions(db: AsyncSession) -> Dict[str, UUID]:
    """Load factor name to ID mapping from database."""
    stmt = select(FactorDefinition.name, FactorDefinition.id)
    result = await db.execute(stmt)
    return {row[0]: row[1] for row in result.fetchall()}


async def calculate_universe_factors(
    calculation_date: date,
    regularization_alpha: float = DEFAULT_REGULARIZATION_ALPHA,
    calculate_ridge: bool = True,
    calculate_spread: bool = True,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate factor betas for all symbols in the universe using parallel batches.

    This is the main entry point for Phase 0.5 of batch processing.
    Uses the safe parallelization pattern: each batch gets its own session.

    Args:
        calculation_date: Date for the calculation
        regularization_alpha: L2 penalty for Ridge (default 1.0)
        calculate_ridge: Whether to calculate Ridge factors
        calculate_spread: Whether to calculate Spread factors
        price_cache: Optional price cache

    Returns:
        Dict with:
        - symbols_processed: Total symbols processed
        - ridge_results: Ridge calculation summary
        - spread_results: Spread calculation summary
        - errors: List of errors
    """
    logger.info(f"Starting universe factor calculation for {calculation_date}")

    results = {
        'calculation_date': calculation_date.isoformat(),
        'symbols_processed': 0,
        'ridge_results': {'calculated': 0, 'cached': 0, 'failed': 0},
        'spread_results': {'calculated': 0, 'cached': 0, 'failed': 0},
        'errors': []
    }

    # Step 1: Get all unique symbols (single query)
    async with AsyncSessionLocal() as db:
        all_symbols = await get_all_active_symbols(db)
        factor_name_to_id = await _load_factor_definitions(db)

        if not all_symbols:
            logger.warning("No symbols found in positions table")
            return results

        # Ensure all symbols are in universe table
        await ensure_symbols_in_universe(db, all_symbols, calculation_date)

    results['symbols_processed'] = len(all_symbols)

    # Step 2: Calculate Ridge factors
    if calculate_ridge:
        logger.info("Phase 0.5a: Calculating Ridge factors for universe")

        # Check which symbols need calculation
        async with AsyncSessionLocal() as db:
            symbols_needing_ridge = await get_uncached_symbols(
                db, all_symbols, calculation_date, 'ridge_regression'
            )

        results['ridge_results']['cached'] = len(all_symbols) - len(symbols_needing_ridge)

        if symbols_needing_ridge:
            # Fetch factor ETF returns ONCE (shared across all batches)
            async with AsyncSessionLocal() as db:
                start_date = calculation_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)
                factor_symbols = list(RIDGE_STYLE_FACTORS.values())
                factor_returns = await get_returns(
                    db=db,
                    symbols=factor_symbols,
                    start_date=start_date,
                    end_date=calculation_date,
                    align_dates=True,
                    price_cache=price_cache
                )

                # Map ETF symbols to factor names
                symbol_to_factor = {v: k for k, v in RIDGE_STYLE_FACTORS.items()}
                factor_returns = factor_returns.rename(columns=symbol_to_factor)

            if factor_returns.empty:
                logger.error("No factor ETF returns available for Ridge")
                results['errors'].append("No factor ETF returns available")
            else:
                # Process in parallel batches
                ridge_batch_results = await _process_batches(
                    symbols=symbols_needing_ridge,
                    calculation_date=calculation_date,
                    factor_name_to_id=factor_name_to_id,
                    factor_returns=factor_returns,
                    calculation_method='ridge',
                    regularization_alpha=regularization_alpha,
                    price_cache=price_cache
                )

                results['ridge_results']['calculated'] = ridge_batch_results['success']
                results['ridge_results']['failed'] = ridge_batch_results['failed']
                results['errors'].extend(ridge_batch_results['errors'])

    # Step 3: Calculate Spread factors
    if calculate_spread:
        logger.info("Phase 0.5b: Calculating Spread factors for universe")

        # Check which symbols need calculation
        async with AsyncSessionLocal() as db:
            symbols_needing_spread = await get_uncached_symbols(
                db, all_symbols, calculation_date, 'spread_regression'
            )

        results['spread_results']['cached'] = len(all_symbols) - len(symbols_needing_spread)

        if symbols_needing_spread:
            # Fetch spread returns ONCE (shared across all batches)
            async with AsyncSessionLocal() as db:
                start_date = calculation_date - timedelta(days=SPREAD_REGRESSION_WINDOW_DAYS + 30)
                spread_returns = await fetch_spread_returns(
                    db, start_date, calculation_date, price_cache
                )

            if spread_returns.empty:
                logger.error("No spread returns available")
                results['errors'].append("No spread returns available")
            else:
                # Process in parallel batches
                spread_batch_results = await _process_batches(
                    symbols=symbols_needing_spread,
                    calculation_date=calculation_date,
                    factor_name_to_id=factor_name_to_id,
                    factor_returns=spread_returns,
                    calculation_method='spread',
                    regularization_alpha=None,
                    price_cache=price_cache
                )

                results['spread_results']['calculated'] = spread_batch_results['success']
                results['spread_results']['failed'] = spread_batch_results['failed']
                results['errors'].extend(spread_batch_results['errors'])

    # Log summary
    logger.info(
        f"Universe factor calculation complete: "
        f"{results['symbols_processed']} symbols, "
        f"Ridge: {results['ridge_results']}, "
        f"Spread: {results['spread_results']}"
    )

    return results


async def _process_batches(
    symbols: List[str],
    calculation_date: date,
    factor_name_to_id: Dict[str, UUID],
    factor_returns: pd.DataFrame,
    calculation_method: str,
    regularization_alpha: Optional[float],
    price_cache=None
) -> Dict[str, Any]:
    """
    Process symbols in parallel batches with isolated sessions.

    This is the safe parallelization pattern that avoids SQLAlchemy session conflicts.
    """
    # Batch symbols
    batches = [
        symbols[i:i + BATCH_SIZE]
        for i in range(0, len(symbols), BATCH_SIZE)
    ]

    logger.info(f"Processing {len(symbols)} symbols in {len(batches)} batches")

    async def process_batch(batch_symbols: List[str]) -> Dict[str, Any]:
        """Process a batch of symbols with its own database session."""
        batch_result = {'success': 0, 'failed': 0, 'errors': []}

        async with AsyncSessionLocal() as batch_db:
            for symbol in batch_symbols:
                try:
                    if calculation_method == 'ridge':
                        result = await calculate_symbol_ridge_factors(
                            db=batch_db,
                            symbol=symbol,
                            factor_returns=factor_returns,
                            calculation_date=calculation_date,
                            factor_name_to_id=factor_name_to_id,
                            regularization_alpha=regularization_alpha or DEFAULT_REGULARIZATION_ALPHA,
                            price_cache=price_cache
                        )
                    else:  # spread
                        result = await calculate_symbol_spread_factors(
                            db=batch_db,
                            symbol=symbol,
                            spread_returns=factor_returns,
                            calculation_date=calculation_date,
                            factor_name_to_id=factor_name_to_id,
                            price_cache=price_cache
                        )

                    if result['success']:
                        batch_result['success'] += 1
                    else:
                        batch_result['failed'] += 1
                        if result.get('error'):
                            batch_result['errors'].append(f"{symbol}: {result['error']}")

                except Exception as e:
                    logger.error(f"Error calculating factors for {symbol}: {e}")
                    batch_result['failed'] += 1
                    batch_result['errors'].append(f"{symbol}: {str(e)}")

            # Commit all symbols in this batch at once
            await batch_db.commit()

        return batch_result

    # Process batches with limited concurrency
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

    async def limited_process_batch(batch: List[str]) -> Dict[str, Any]:
        async with semaphore:
            return await process_batch(batch)

    batch_tasks = [limited_process_batch(batch) for batch in batches]
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

    # Aggregate results
    aggregate = {'success': 0, 'failed': 0, 'errors': []}

    for result in batch_results:
        if isinstance(result, Exception):
            logger.error(f"Batch failed with exception: {result}")
            aggregate['errors'].append(str(result))
        else:
            aggregate['success'] += result['success']
            aggregate['failed'] += result['failed']
            aggregate['errors'].extend(result['errors'])

    return aggregate


async def load_symbol_betas(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date,
    calculation_method: Optional[str] = None
) -> Dict[str, Dict[str, float]]:
    """
    Bulk load symbol betas in a single query.

    This is used by portfolio aggregation to look up pre-computed symbol betas.

    Args:
        db: Database session
        symbols: List of symbols to load
        calculation_date: Date to load betas for
        calculation_method: Optional filter ('ridge_regression' or 'spread_regression')

    Returns:
        {symbol: {factor_name: beta_value}}
    """
    if not symbols:
        return {}

    stmt = (
        select(
            SymbolFactorExposure.symbol,
            FactorDefinition.name,
            SymbolFactorExposure.beta_value
        )
        .join(FactorDefinition, SymbolFactorExposure.factor_id == FactorDefinition.id)
        .where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date == calculation_date
            )
        )
    )

    if calculation_method:
        stmt = stmt.where(SymbolFactorExposure.calculation_method == calculation_method)

    result = await db.execute(stmt)
    rows = result.fetchall()

    # Build nested dict
    betas: Dict[str, Dict[str, float]] = {}
    for symbol, factor_name, beta_value in rows:
        if symbol not in betas:
            betas[symbol] = {}
        betas[symbol][factor_name] = float(beta_value)

    logger.debug(f"Loaded betas for {len(betas)} symbols")
    return betas
