"""
Sector Analysis & Concentration Metrics
Calculates portfolio sector exposure vs S&P 500 benchmark and concentration metrics.

Created: 2025-10-17
Phase: Risk Metrics Phase 1
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.positions import Position
from app.models.market_data import BenchmarkSectorWeight
from app.core.logging import get_logger

logger = get_logger(__name__)


def calculate_hhi(weights: Dict[str, float]) -> float:
    """
    Calculate Herfindahl-Hirschman Index.

    HHI = Σ(weight_i²) × 10,000

    Interpretation:
    - 10,000 = single position (max concentration)
    - 1,000 = 10 equal positions
    - 100 = 100 equal positions (highly diversified)

    Args:
        weights: Dictionary of {position_id/sector: weight} (weights as decimals, sum to 1.0)

    Returns:
        HHI value (0 to 10,000)
    """
    if not weights:
        return 0.0
    return sum(w ** 2 for w in weights.values()) * 10000


def calculate_effective_positions(hhi: float) -> float:
    """
    Calculate effective number of positions from HHI.

    N_effective = 10,000 / HHI

    Args:
        hhi: Herfindahl-Hirschman Index

    Returns:
        Effective number of positions
    """
    if hhi == 0:
        return 0.0
    return 10000 / hhi


def get_position_market_value(position: Position) -> Decimal:
    """
    Get current market value for a position.

    Note: Position model already has market_value field populated by batch processing.
    We just return that value rather than recalculating.

    Args:
        position: Position object

    Returns:
        Market value as Decimal
    """
    # Use the pre-calculated market_value field from the Position model
    if position.market_value is not None:
        return position.market_value
    else:
        # Fallback: calculate from entry price if market_value not set
        if position.position_type in ['LONG', 'SHORT']:
            return Decimal(str(position.quantity)) * position.entry_price
        elif position.position_type in ['LC', 'LP', 'SC', 'SP']:
            # Options: contracts * 100 * price
            return Decimal(str(position.quantity)) * Decimal('100') * position.entry_price
        else:
            logger.warning(f"Unknown position type {position.position_type} for position {position.id}")
            return Decimal('0')


async def get_sector_from_market_data(db: AsyncSession, symbol: str) -> Optional[str]:
    """
    Get sector for a symbol from company_profiles table.

    Args:
        db: Database session
        symbol: Stock symbol

    Returns:
        Sector name or None if not found
    """
    try:
        # Import CompanyProfile here to avoid circular imports
        from app.models.market_data import CompanyProfile

        stmt = select(CompanyProfile.sector).where(
            CompanyProfile.symbol == symbol.upper()
        ).limit(1)

        result = await db.execute(stmt)
        sector = result.scalar_one_or_none()

        return sector
    except Exception as e:
        logger.warning(f"Could not fetch sector for {symbol}: {e}")
        return None


async def get_benchmark_sector_weights(
    db: AsyncSession,
    benchmark_code: str = "SP500",
    asof_date: Optional[date] = None
) -> Dict[str, float]:
    """
    Get S&P 500 sector weights from database.

    Args:
        db: Database session
        benchmark_code: Benchmark identifier (default SP500)
        asof_date: Date for weights (defaults to latest available)

    Returns:
        Dictionary mapping sector -> weight (as decimal)
    """
    try:
        if asof_date is None:
            # Get latest available date
            stmt = select(BenchmarkSectorWeight).where(
                BenchmarkSectorWeight.benchmark_code == benchmark_code
            ).order_by(BenchmarkSectorWeight.asof_date.desc())
        else:
            stmt = select(BenchmarkSectorWeight).where(
                and_(
                    BenchmarkSectorWeight.benchmark_code == benchmark_code,
                    BenchmarkSectorWeight.asof_date == asof_date
                )
            )

        result = await db.execute(stmt)
        records = result.scalars().all()

        if not records:
            logger.warning(f"No benchmark weights found for {benchmark_code}")
            return {}

        # Convert to dictionary
        weights = {rec.sector: float(rec.weight) for rec in records}

        logger.info(f"Loaded {len(weights)} sector weights for {benchmark_code}")
        return weights

    except Exception as e:
        logger.error(f"Error fetching benchmark weights: {e}")
        return {}


async def calculate_sector_exposure(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate sector exposure for portfolio and compare to S&P 500.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        {
            'portfolio_weights': {'Technology': 0.45, ...},
            'benchmark_weights': {'Technology': 0.28, ...},
            'over_underweight': {'Technology': 0.17, ...},
            'largest_overweight': 'Technology',
            'largest_underweight': 'Energy',
            'total_portfolio_value': float,
            'positions_by_sector': {'Technology': 15, ...},
            'unclassified_value': float,
            'unclassified_count': int,
            'success': bool
        }
    """
    logger.info(f"Calculating sector exposure for portfolio {portfolio_id}")

    try:
        # Get active positions
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'No active positions'
            }

        # Aggregate by sector
        sector_values = {}
        total_value = Decimal('0')
        positions_by_sector = {}
        unclassified_value = Decimal('0')
        unclassified_count = 0

        for position in positions:
            market_value = get_position_market_value(position)
            total_value += abs(market_value)  # Use absolute value for LONG/SHORT

            # Get sector from market_data_cache
            sector = await get_sector_from_market_data(db, position.symbol)

            if sector and sector != 'Unknown':
                if sector not in sector_values:
                    sector_values[sector] = Decimal('0')
                    positions_by_sector[sector] = 0

                sector_values[sector] += abs(market_value)
                positions_by_sector[sector] += 1
            else:
                # Unclassified position
                unclassified_value += abs(market_value)
                unclassified_count += 1
                logger.warning(f"Position {position.symbol} has no sector classification")

        # Calculate portfolio weights
        if total_value == 0:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Total portfolio value is zero'
            }

        portfolio_weights = {
            sector: float(value / total_value)
            for sector, value in sector_values.items()
        }

        # Get benchmark weights
        benchmark_weights = await get_benchmark_sector_weights(db)

        if not benchmark_weights:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Could not load benchmark sector weights'
            }

        # Calculate over/underweight
        all_sectors = set(list(portfolio_weights.keys()) + list(benchmark_weights.keys()))
        over_underweight = {}

        for sector in all_sectors:
            port_weight = portfolio_weights.get(sector, 0.0)
            bench_weight = benchmark_weights.get(sector, 0.0)
            over_underweight[sector] = port_weight - bench_weight

        # Find largest over/underweights
        largest_overweight = max(over_underweight.items(), key=lambda x: x[1])[0] if over_underweight else None
        largest_underweight = min(over_underweight.items(), key=lambda x: x[1])[0] if over_underweight else None

        return {
            'portfolio_id': str(portfolio_id),
            'portfolio_weights': portfolio_weights,
            'benchmark_weights': benchmark_weights,
            'over_underweight': over_underweight,
            'largest_overweight': largest_overweight,
            'largest_underweight': largest_underweight,
            'total_portfolio_value': float(total_value),
            'positions_by_sector': positions_by_sector,
            'unclassified_value': float(unclassified_value),
            'unclassified_count': unclassified_count,
            'success': True
        }

    except Exception as e:
        logger.error(f"Error calculating sector exposure: {e}", exc_info=True)
        return {
            'portfolio_id': str(portfolio_id),
            'success': False,
            'error': str(e)
        }


async def calculate_concentration_metrics(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate concentration metrics for portfolio.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        {
            'hhi': float,
            'effective_num_positions': float,
            'top_3_concentration': float,
            'top_10_concentration': float,
            'total_positions': int,
            'position_weights': {position_id: weight, ...},
            'success': bool
        }
    """
    logger.info(f"Calculating concentration metrics for portfolio {portfolio_id}")

    try:
        # Get active positions
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'No active positions'
            }

        # Calculate position weights
        position_values = {}
        total_value = Decimal('0')

        for position in positions:
            market_value = get_position_market_value(position)
            position_values[str(position.id)] = abs(market_value)
            total_value += abs(market_value)

        if total_value == 0:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Total portfolio value is zero'
            }

        # Calculate weights
        position_weights = {
            pos_id: float(value / total_value)
            for pos_id, value in position_values.items()
        }

        # Calculate HHI
        hhi = calculate_hhi(position_weights)

        # Calculate effective number of positions
        effective_num = calculate_effective_positions(hhi)

        # Calculate top N concentrations
        sorted_weights = sorted(position_weights.values(), reverse=True)
        top_3_concentration = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)
        top_10_concentration = sum(sorted_weights[:10]) if len(sorted_weights) >= 10 else sum(sorted_weights)

        return {
            'portfolio_id': str(portfolio_id),
            'hhi': hhi,
            'effective_num_positions': effective_num,
            'top_3_concentration': top_3_concentration,
            'top_10_concentration': top_10_concentration,
            'total_positions': len(positions),
            'position_weights': position_weights,
            'success': True
        }

    except Exception as e:
        logger.error(f"Error calculating concentration metrics: {e}", exc_info=True)
        return {
            'portfolio_id': str(portfolio_id),
            'success': False,
            'error': str(e)
        }


async def calculate_portfolio_sector_concentration(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate both sector exposure and concentration metrics for portfolio.

    This is the main entry point for batch processing.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation (defaults to today)

    Returns:
        Combined results from sector_exposure and concentration_metrics
    """
    if calculation_date is None:
        calculation_date = date.today()

    logger.info(f"Calculating sector & concentration analysis for portfolio {portfolio_id}")

    # Calculate sector exposure
    sector_result = await calculate_sector_exposure(db, portfolio_id)

    # Calculate concentration metrics
    concentration_result = await calculate_concentration_metrics(db, portfolio_id)

    # Combine results
    combined_result = {
        'portfolio_id': str(portfolio_id),
        'calculation_date': calculation_date,
        'sector_exposure': sector_result if sector_result.get('success') else None,
        'concentration': concentration_result if concentration_result.get('success') else None,
        'success': sector_result.get('success', False) and concentration_result.get('success', False)
    }

    if not combined_result['success']:
        errors = []
        if not sector_result.get('success'):
            errors.append(f"Sector: {sector_result.get('error', 'Unknown error')}")
        if not concentration_result.get('success'):
            errors.append(f"Concentration: {concentration_result.get('error', 'Unknown error')}")
        combined_result['error'] = '; '.join(errors)

    return combined_result
