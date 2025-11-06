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
from app.calculations.market_data import get_position_value
from app.core.logging import get_logger

logger = get_logger(__name__)


# Sector name mapping: Company Profile sectors → S&P 500 GICS sectors
# YFinance/FMP use different sector names than the S&P 500 GICS standard
# This mapping standardizes all sectors to GICS names for consistent comparison
SECTOR_MAPPING = {
    # Direct matches (no change needed)
    "Communication Services": "Communication Services",
    "Energy": "Energy",
    "Healthcare": "Healthcare",
    "Industrials": "Industrials",
    "Technology": "Technology",

    # Name variations that need mapping
    "Financial Services": "Financials",  # YFinance/FMP → GICS
    "Consumer Cyclical": "Consumer Discretionary",  # YFinance/FMP → GICS
    "Consumer Defensive": "Consumer Staples",  # YFinance/FMP → GICS
    "Basic Materials": "Materials",  # Alternative name → GICS
    "Real Estate": "Real Estate",  # Direct match
    "Utilities": "Utilities",  # Direct match
}


def normalize_sector_name(sector: Optional[str]) -> Optional[str]:
    """
    Normalize sector name from company profile data to S&P 500 GICS standard.

    Args:
        sector: Raw sector name from company profile

    Returns:
        Normalized GICS sector name, or None if unmapped
    """
    if not sector or sector == "Unknown":
        return None

    # Apply mapping if exists, otherwise return original
    normalized = SECTOR_MAPPING.get(sector, sector)

    # Log if we encounter an unmapped sector
    if normalized == sector and sector not in SECTOR_MAPPING.values():
        logger.info(f"Unmapped sector encountered: '{sector}' - using as-is")

    return normalized

async def _get_company_profile_metadata(
    db: AsyncSession,
    symbol: str,
    profile_cache: Optional[Dict[str, Dict[str, Optional[Any]]]] = None,
) -> Dict[str, Optional[Any]]:
    """
    Fetch normalized sector and ETF flag information with optional caching.
    """
    symbol_key = symbol.upper()

    if profile_cache is not None and symbol_key in profile_cache:
        return profile_cache[symbol_key]

    from app.models.market_data import CompanyProfile

    stmt = (
        select(CompanyProfile.sector, CompanyProfile.is_etf)
        .where(CompanyProfile.symbol == symbol_key)
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()

    sector_raw = row[0] if row else None
    normalized_sector = normalize_sector_name(sector_raw)
    is_etf = bool(row[1]) if row and row[1] is not None else False

    metadata = {"sector": normalized_sector, "is_etf": is_etf}

    if profile_cache is not None:
        profile_cache[symbol_key] = metadata

    return metadata



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


async def get_sector_from_market_data(
    db: AsyncSession,
    symbol: str,
    profile_cache: Optional[Dict[str, Dict[str, Optional[Any]]]] = None,
) -> Optional[str]:
    try:
        metadata = await _get_company_profile_metadata(db, symbol, profile_cache)
        return metadata['sector']
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
    portfolio_id: UUID,
    profile_cache: Optional[Dict[str, Dict[str, Optional[Any]]]] = None,
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
        # Get portfolio to access equity_balance
        from app.models.users import Portfolio
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Portfolio not found'
            }

        # Use portfolio equity balance as denominator
        portfolio_equity = portfolio.equity_balance or Decimal('0')

        if portfolio_equity == 0:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Portfolio equity balance is zero'
            }

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
        etf_value = Decimal('0')
        etf_count = 0

        for position in positions:
            market_value = get_position_value(position, signed=False)
            total_value += abs(market_value)  # Use absolute value for LONG/SHORT

            # Only PUBLIC stocks participate in sector analysis
            # PRIVATE/OPTIONS positions are always Unclassified
            if position.investment_class in ('PRIVATE', 'OPTIONS'):
                # Truly unclassifiable positions (private equity, real estate, etc.)
                unclassified_value += abs(market_value)
                unclassified_count += 1
                continue

            metadata = await _get_company_profile_metadata(db, position.symbol, profile_cache)

            if metadata['is_etf']:
                # ETF - categorize separately
                etf_value += abs(market_value)
                etf_count += 1
                logger.info(f"Position {position.symbol} identified as ETF")
                continue

            # For non-ETF PUBLIC positions, get sector classification
            sector = metadata['sector']

            logger.info(f"Symbol {position.symbol} got sector: '{sector}'")

            if sector and sector != 'Unknown':
                if sector not in sector_values:
                    sector_values[sector] = Decimal('0')
                    positions_by_sector[sector] = 0

                sector_values[sector] += abs(market_value)
                positions_by_sector[sector] += 1
            else:
                # PUBLIC position without sector and not an ETF
                # These are excluded from sector analysis entirely
                logger.warning(f"PUBLIC position {position.symbol} has no sector classification and is not an ETF - excluded from sector analysis")

        # Calculate portfolio weights using portfolio equity balance as denominator
        # This accurately represents each sector as % of total portfolio equity
        portfolio_weights = {
            sector: float(value / portfolio_equity)
            for sector, value in sector_values.items()
        }

        logger.info(f"📊 Final portfolio_weights keys: {list(portfolio_weights.keys())}")

        # Add ETFs to portfolio weights if there are ETF positions
        if etf_value > 0:
            portfolio_weights['ETFs'] = float(etf_value / portfolio_equity)

        # Add unclassified to portfolio weights if there are unclassified positions
        if unclassified_value > 0:
            portfolio_weights['Unclassified'] = float(unclassified_value / portfolio_equity)

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
            'etf_value': float(etf_value),
            'etf_count': etf_count,
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

        # Calculate symbol-level weights (aggregate multiple lots of same symbol)
        # FIX (Nov 3, 2025): Aggregate by symbol to correctly handle multi-lot positions
        symbol_values = {}
        total_value = Decimal('0')

        for position in positions:
            market_value = get_position_value(position, signed=False)
            symbol = position.symbol

            if symbol not in symbol_values:
                symbol_values[symbol] = Decimal('0')

            symbol_values[symbol] += abs(market_value)
            total_value += abs(market_value)

        if total_value == 0:
            return {
                'portfolio_id': str(portfolio_id),
                'success': False,
                'error': 'Total portfolio value is zero'
            }

        # Calculate weights at symbol level (not position level)
        symbol_weights = {
            symbol: float(value / total_value)
            for symbol, value in symbol_values.items()
        }

        # Calculate HHI using symbol-level weights
        hhi = calculate_hhi(symbol_weights)

        # Calculate effective number of positions
        effective_num = calculate_effective_positions(hhi)

        # Calculate top N concentrations using symbol-level weights
        sorted_weights = sorted(symbol_weights.values(), reverse=True)
        top_3_concentration = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)
        top_10_concentration = sum(sorted_weights[:10]) if len(sorted_weights) >= 10 else sum(sorted_weights)

        return {
            'portfolio_id': str(portfolio_id),
            'hhi': hhi,
            'effective_num_positions': effective_num,
            'top_3_concentration': top_3_concentration,
            'top_10_concentration': top_10_concentration,
            'total_positions': len(positions),  # Total position count (including multi-lots)
            'unique_symbols': len(symbol_values),  # Number of unique symbols
            'position_weights': symbol_weights,  # Return symbol weights, not position weights
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
    calculation_date: Optional[date] = None,
    profile_cache: Optional[Dict[str, Dict[str, Optional[Any]]]] = None,
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
    sector_result = await calculate_sector_exposure(db, portfolio_id, profile_cache)

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

