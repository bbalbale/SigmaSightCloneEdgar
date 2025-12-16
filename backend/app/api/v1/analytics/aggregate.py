"""
Aggregate Analytics Endpoints

Provides portfolio-level analytics aggregated across multiple portfolios.
Uses portfolio-as-asset weighted average approach.

Created: 2025-11-01
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.users import User
from app.services.portfolio_aggregation_service import PortfolioAggregationService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/aggregate", tags=["aggregate-analytics"])

# Type alias
CurrentUser = User


@router.get("/overview")
async def get_aggregate_overview(
    portfolio_ids: Optional[List[UUID]] = Query(None, description="Specific portfolio IDs to aggregate. If None, aggregates all active portfolios."),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate portfolio overview across multiple portfolios.

    Provides:
    - Total portfolio value
    - Portfolio count
    - Individual portfolio breakdown with weights
    - Aggregate metrics summary

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs to aggregate
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate overview with portfolio breakdown and weights
    """
    try:
        service = PortfolioAggregationService(db)

        # Get aggregate metrics
        result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        logger.info(
            f"Aggregate overview for user {current_user.id}: "
            f"{result['portfolio_count']} portfolios, ${result['net_asset_value']:,.2f}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting aggregate overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve aggregate overview: {str(e)}"
        )


@router.get("/breakdown")
async def get_portfolio_breakdown(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed breakdown of portfolios with individual metrics.

    Returns each portfolio's contribution to the aggregate, including:
    - Account name and type
    - Current value
    - Weight (% of total)
    - Position count
    - Individual metrics (if available)

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Detailed breakdown of all portfolios
    """
    try:
        service = PortfolioAggregationService(db)

        # Get base aggregate data
        result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        # Enhance with additional details
        enhanced_portfolios = []
        for portfolio in result['portfolios']:
            enhanced_portfolios.append({
                **portfolio,
                "weight_pct": round(portfolio['weight'] * 100, 2),
                "contribution_dollars": round(portfolio['value'], 2)
            })

        response = {
            "net_asset_value": result['net_asset_value'],
            "total_value": result['total_value'],
            "portfolio_count": result['portfolio_count'],
            "portfolios": enhanced_portfolios,
            "summary": {
                "total_weight": sum(p['weight'] for p in result['portfolios']),
                "average_value": result['net_asset_value'] / result['portfolio_count'] if result['portfolio_count'] > 0 else 0
            }
        }

        return response

    except Exception as e:
        logger.error(f"Error getting portfolio breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio breakdown: {str(e)}"
        )


@router.get("/beta")
async def get_aggregate_beta(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate portfolio beta across multiple portfolios.

    Uses weighted average based on portfolio values:
    Aggregate Beta = Σ(Beta_i × Weight_i)

    Where Weight_i = Portfolio_Value_i / Total_Value

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate beta with individual portfolio contributions
    """
    try:
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_beta": None,
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Get beta for each portfolio from snapshots
        portfolio_betas: Dict[UUID, Dict[str, Any]] = {}

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            # Get latest snapshot with beta
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            beta = None
            if snapshot:
                # Prefer calculated 90d beta, fall back to provider 1y
                if snapshot.beta_calculated_90d is not None:
                    beta = float(snapshot.beta_calculated_90d)
                elif snapshot.beta_provider_1y is not None:
                    beta = float(snapshot.beta_provider_1y)

            portfolio_betas[portfolio_id] = {
                'beta': beta,
                'weight': portfolio_data['weight']
            }

        # Calculate aggregate beta
        aggregate_beta = await service.aggregate_beta(portfolio_betas)

        # Build response
        portfolio_contributions = []
        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])
            beta_data = portfolio_betas.get(portfolio_id, {})

            portfolio_contributions.append({
                "portfolio_id": str(portfolio_id),
                "account_name": portfolio_data['account_name'],
                "account_type": portfolio_data['account_type'],
                "value": portfolio_data['value'],
                "weight": portfolio_data['weight'],
                "beta": beta_data.get('beta'),
                "contribution": (beta_data.get('beta', 0) * portfolio_data['weight']) if beta_data.get('beta') is not None else None
            })

        response = {
            "aggregate_beta": aggregate_beta,
            "net_asset_value": portfolios_result['net_asset_value'],
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "portfolios": portfolio_contributions,
            "calculation_method": "weighted_average",
            "formula": "Σ(Beta_i × Weight_i) where Weight_i = Value_i / Total_Value"
        }

        logger.info(
            f"Aggregate beta for user {current_user.id}: {aggregate_beta:.4f if aggregate_beta else 'N/A'} "
            f"({portfolios_result['portfolio_count']} portfolios)"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate beta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate beta: {str(e)}"
        )


@router.get("/volatility")
async def get_aggregate_volatility(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate portfolio volatility across multiple portfolios.

    Uses weighted average (approximation):
    Aggregate Volatility ≈ Σ(Volatility_i × Weight_i)

    Note: This is a simplified approximation. True portfolio volatility
    should account for correlations between portfolios.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate volatility with individual portfolio contributions
    """
    try:
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_volatility": None,
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Get volatility for each portfolio from snapshots
        portfolio_volatilities: Dict[UUID, Dict[str, Any]] = {}

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            # Get latest snapshot with volatility
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            volatility = None
            if snapshot and snapshot.realized_volatility_21d is not None:
                volatility = float(snapshot.realized_volatility_21d)

            portfolio_volatilities[portfolio_id] = {
                'volatility': volatility,
                'weight': portfolio_data['weight']
            }

        # Calculate aggregate volatility
        aggregate_volatility = await service.aggregate_volatility(portfolio_volatilities)

        # Build response
        portfolio_contributions = []
        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])
            vol_data = portfolio_volatilities.get(portfolio_id, {})

            portfolio_contributions.append({
                "portfolio_id": str(portfolio_id),
                "account_name": portfolio_data['account_name'],
                "account_type": portfolio_data['account_type'],
                "value": portfolio_data['value'],
                "weight": portfolio_data['weight'],
                "volatility": vol_data.get('volatility'),
                "contribution": (vol_data.get('volatility', 0) * portfolio_data['weight']) if vol_data.get('volatility') is not None else None
            })

        response = {
            "aggregate_volatility": aggregate_volatility,
            "net_asset_value": portfolios_result['net_asset_value'],
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "portfolios": portfolio_contributions,
            "calculation_method": "weighted_average",
            "note": "Simplified approximation. True volatility should account for correlations.",
            "formula": "Σ(Volatility_i × Weight_i) where Weight_i = Value_i / Total_Value"
        }

        logger.info(
            f"Aggregate volatility for user {current_user.id}: {aggregate_volatility:.4f if aggregate_volatility else 'N/A'} "
            f"({portfolios_result['portfolio_count']} portfolios)"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate volatility: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate volatility: {str(e)}"
        )


@router.get("/factor-exposures")
async def get_aggregate_factor_exposures(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate factor exposures across multiple portfolios.

    Calculates weighted average exposure for each factor:
    - Market (SPY)
    - Size (IWM)
    - Value (IVE)
    - Momentum (MTUM)
    - Quality (QUAL)

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate factor exposures with portfolio contributions
    """
    try:
        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_factors": {},
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Extract portfolio IDs and weights
        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]
        weights = {UUID(p['id']): p['weight'] for p in portfolios_result['portfolios']}

        # Calculate aggregate factor exposures
        aggregate_factors = await service.aggregate_factor_exposures(
            portfolio_ids=portfolio_ids_list,
            weights=weights
        )

        # Build response
        response = {
            "aggregate_factors": aggregate_factors,
            "net_asset_value": portfolios_result['net_asset_value'],
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "calculation_method": "weighted_average",
            "factors": {
                "market": "SPY - S&P 500",
                "size": "IWM - Russell 2000",
                "value": "IVE - S&P 500 Value",
                "momentum": "MTUM - Momentum",
                "quality": "QUAL - Quality"
            },
            "formula": "For each factor: Σ(Exposure_i × Weight_i)"
        }

        logger.info(
            f"Aggregate factor exposures for user {current_user.id}: "
            f"{len(aggregate_factors)} factors calculated"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate factor exposures: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate factor exposures: {str(e)}"
        )


@router.get("/sector-exposure")
async def get_aggregate_sector_exposure(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate sector exposure across multiple portfolios.

    Combines all positions from all portfolios and calculates sector weights
    relative to total equity across all portfolios. Compares to S&P 500 benchmark.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate sector exposure with benchmark comparison
    """
    try:
        from app.calculations.sector_analysis import (
            calculate_sector_exposure,
            get_benchmark_sector_weights
        )
        from app.models.positions import Position
        from app.models.users import Portfolio
        from app.calculations.market_data import get_position_value
        from sqlalchemy import select, and_

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "available": False,
                "message": "No portfolios found",
                "portfolios": []
            }

        # Get all positions from all portfolios
        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]

        # Aggregate sector values across all portfolios
        sector_values: Dict[str, float] = {}
        total_equity = Decimal(str(portfolios_result['net_asset_value']))

        # Profile cache for sector lookups
        profile_cache: Dict[str, Dict[str, Any]] = {}

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            # Get sector exposure for this portfolio
            sector_result = await calculate_sector_exposure(db, portfolio_id, profile_cache)

            if sector_result.get('success') and sector_result.get('portfolio_weights'):
                portfolio_value = Decimal(str(portfolio_data['value']))

                # Weight each sector by this portfolio's value
                for sector, weight in sector_result['portfolio_weights'].items():
                    dollar_value = float(weight) * float(portfolio_value)
                    if sector not in sector_values:
                        sector_values[sector] = 0.0
                    sector_values[sector] += dollar_value

        # Convert to weights relative to total equity
        portfolio_weights = {}
        if float(total_equity) > 0:
            for sector, value in sector_values.items():
                portfolio_weights[sector] = value / float(total_equity)

        # Get benchmark weights
        benchmark_weights = await get_benchmark_sector_weights(db)

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

        response = {
            "available": True,
            "data": {
                "portfolio_weights": portfolio_weights,
                "benchmark_weights": benchmark_weights,
                "over_underweight": over_underweight,
                "largest_overweight": largest_overweight,
                "largest_underweight": largest_underweight
            },
            "net_asset_value": portfolios_result['net_asset_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "calculation_method": "position_aggregation",
            "formula": "Combine all positions, calculate sector weights vs total equity"
        }

        logger.info(
            f"Aggregate sector exposure for user {current_user.id}: "
            f"{len(portfolio_weights)} sectors across {portfolios_result['portfolio_count']} portfolios"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate sector exposure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate sector exposure: {str(e)}"
        )


@router.get("/concentration")
async def get_aggregate_concentration(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate concentration metrics across multiple portfolios.

    Calculates HHI and concentration metrics treating all positions across
    all portfolios as a single combined portfolio.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate concentration metrics (HHI, top positions, effective count)
    """
    try:
        from app.models.positions import Position
        from app.calculations.market_data import get_position_value
        from app.calculations.sector_analysis import calculate_hhi, calculate_effective_positions
        from sqlalchemy import select, and_

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "available": False,
                "message": "No portfolios found",
                "portfolios": []
            }

        # Get all positions from all portfolios
        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]

        # Aggregate position values by symbol across all portfolios
        symbol_values: Dict[str, Decimal] = {}
        total_value = Decimal('0')
        total_positions = 0

        for portfolio_id in portfolio_ids_list:
            # Get active positions
            stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None),
                    Position.deleted_at.is_(None)
                )
            )
            result = await db.execute(stmt)
            positions = result.scalars().all()

            for position in positions:
                market_value = get_position_value(position, signed=False)
                symbol = position.symbol

                if symbol not in symbol_values:
                    symbol_values[symbol] = Decimal('0')

                symbol_values[symbol] += abs(market_value)
                total_value += abs(market_value)
                total_positions += 1

        if total_value == 0:
            return {
                "available": False,
                "message": "Total portfolio value is zero",
                "portfolios": []
            }

        # Calculate weights at symbol level
        symbol_weights = {
            symbol: float(value / total_value)
            for symbol, value in symbol_values.items()
        }

        # Calculate HHI
        hhi = calculate_hhi(symbol_weights)
        effective_num = calculate_effective_positions(hhi)

        # Calculate top N concentrations
        sorted_weights = sorted(symbol_weights.items(), key=lambda x: x[1], reverse=True)
        top_3_concentration = sum(w for _, w in sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(w for _, w in sorted_weights)
        top_10_concentration = sum(w for _, w in sorted_weights[:10]) if len(sorted_weights) >= 10 else sum(w for _, w in sorted_weights)

        # Get top positions details
        top_positions = [
            {"symbol": symbol, "weight": weight, "value": float(symbol_values[symbol])}
            for symbol, weight in sorted_weights[:10]
        ]

        response = {
            "available": True,
            "data": {
                "hhi": hhi,
                "effective_num_positions": effective_num,
                "top_3_concentration": top_3_concentration,
                "top_10_concentration": top_10_concentration,
                "unique_symbols": len(symbol_values),
                "total_positions": total_positions,
                "top_positions": top_positions
            },
            "net_asset_value": portfolios_result['net_asset_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "calculation_method": "symbol_aggregation",
            "formula": "HHI = Σ(weight_i²) × 10,000 across all positions from all portfolios"
        }

        logger.info(
            f"Aggregate concentration for user {current_user.id}: "
            f"HHI={hhi:.0f}, {len(symbol_values)} unique symbols across {portfolios_result['portfolio_count']} portfolios"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate concentration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate concentration: {str(e)}"
        )


@router.get("/correlation-matrix")
async def get_aggregate_correlation_matrix(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    max_symbols: int = Query(25, description="Maximum symbols to include in matrix"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate correlation matrix across multiple portfolios.

    Selects the top positions by weight across all portfolios and returns
    their correlation matrix.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        max_symbols: Maximum number of symbols to include (default 25)
        current_user: Authenticated user
        db: Database session

    Returns:
        Correlation matrix for top positions across all portfolios
    """
    try:
        from app.models.positions import Position
        from app.models.correlations import PairwiseCorrelation, CorrelationCalculation
        from app.calculations.market_data import get_position_value
        from sqlalchemy import select, and_, func

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "available": False,
                "message": "No portfolios found",
                "portfolios": []
            }

        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]

        # Aggregate position values by symbol across all portfolios
        symbol_values: Dict[str, Decimal] = {}

        for portfolio_id in portfolio_ids_list:
            stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None),
                    Position.deleted_at.is_(None)
                )
            )
            result = await db.execute(stmt)
            positions = result.scalars().all()

            for position in positions:
                market_value = get_position_value(position, signed=False)
                symbol = position.symbol

                if symbol not in symbol_values:
                    symbol_values[symbol] = Decimal('0')
                symbol_values[symbol] += abs(market_value)

        # Get top symbols by value
        sorted_symbols = sorted(symbol_values.items(), key=lambda x: x[1], reverse=True)
        top_symbols = [s for s, _ in sorted_symbols[:max_symbols]]

        if len(top_symbols) < 2:
            return {
                "available": False,
                "message": "Need at least 2 symbols for correlation matrix",
                "symbols_found": len(top_symbols)
            }

        # Get correlations from the most recent calculation of any portfolio
        # We'll use the first portfolio's correlation data as representative
        latest_calc = None
        for portfolio_id in portfolio_ids_list:
            calc_stmt = select(CorrelationCalculation).where(
                CorrelationCalculation.portfolio_id == portfolio_id
            ).order_by(CorrelationCalculation.calculation_date.desc()).limit(1)

            calc_result = await db.execute(calc_stmt)
            calc = calc_result.scalar_one_or_none()

            if calc and (latest_calc is None or calc.calculation_date > latest_calc.calculation_date):
                latest_calc = calc

        if not latest_calc:
            return {
                "available": False,
                "message": "No correlation calculations available",
                "metadata": {"reason": "no_calculation_available"}
            }

        # Get pairwise correlations
        corr_stmt = select(PairwiseCorrelation).where(
            PairwiseCorrelation.correlation_calculation_id == latest_calc.id
        )
        corr_result = await db.execute(corr_stmt)
        correlations = corr_result.scalars().all()

        # Build correlation lookup
        corr_lookup: Dict[tuple, float] = {}
        for corr in correlations:
            corr_lookup[(corr.symbol_1, corr.symbol_2)] = float(corr.correlation_value)
            corr_lookup[(corr.symbol_2, corr.symbol_1)] = float(corr.correlation_value)

        # Build matrix for top symbols
        matrix = {}
        symbols_with_data = []

        for symbol in top_symbols:
            # Check if this symbol has any correlation data
            has_data = any(
                (symbol, other) in corr_lookup or (other, symbol) in corr_lookup
                for other in top_symbols if other != symbol
            )
            if has_data or symbol in [c.symbol_1 for c in correlations] + [c.symbol_2 for c in correlations]:
                symbols_with_data.append(symbol)

        for symbol1 in symbols_with_data:
            matrix[symbol1] = {}
            for symbol2 in symbols_with_data:
                if symbol1 == symbol2:
                    matrix[symbol1][symbol2] = 1.0
                else:
                    matrix[symbol1][symbol2] = corr_lookup.get((symbol1, symbol2), 0.0)

        response = {
            "available": True,
            "data": {
                "matrix": matrix,
                "symbols": symbols_with_data,
                "average_correlation": float(latest_calc.overall_correlation) if latest_calc.overall_correlation else None
            },
            "net_asset_value": portfolios_result['net_asset_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "metadata": {
                "calculation_date": latest_calc.calculation_date.isoformat() if latest_calc.calculation_date else None,
                "symbols_requested": max_symbols,
                "symbols_included": len(symbols_with_data)
            }
        }

        logger.info(
            f"Aggregate correlation matrix for user {current_user.id}: "
            f"{len(symbols_with_data)} symbols across {portfolios_result['portfolio_count']} portfolios"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate correlation matrix: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate correlation matrix: {str(e)}"
        )


@router.get("/stress-test")
async def get_aggregate_stress_test(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate stress test results across multiple portfolios.

    Aggregates stress test scenario impacts weighted by portfolio equity.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate stress test scenarios with total impacts
    """
    try:
        from app.services.stress_test_service import StressTestService

        service = PortfolioAggregationService(db)
        stress_service = StressTestService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "available": False,
                "message": "No portfolios found",
                "portfolios": []
            }

        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]
        weights = {UUID(p['id']): p['weight'] for p in portfolios_result['portfolios']}
        total_value = portfolios_result['net_asset_value']

        # Get stress test results for each portfolio
        scenario_impacts: Dict[str, Dict[str, Any]] = {}
        portfolios_with_data = 0

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            stress_result = await stress_service.get_portfolio_results(portfolio_id)

            if stress_result.get('available') and stress_result.get('data', {}).get('scenarios'):
                portfolios_with_data += 1
                portfolio_value = portfolio_data['value']

                for scenario in stress_result['data']['scenarios']:
                    scenario_id = scenario['id']

                    if scenario_id not in scenario_impacts:
                        scenario_impacts[scenario_id] = {
                            'name': scenario['name'],
                            'description': scenario.get('description', ''),
                            'category': scenario.get('category', ''),
                            'severity': scenario.get('severity', ''),
                            'total_dollar_impact': 0.0,
                            'weighted_pct_impact': 0.0,
                            'portfolios_included': 0
                        }

                    # Add this portfolio's impact
                    dollar_impact = scenario.get('impact', {}).get('dollar_impact', 0.0)
                    pct_impact = scenario.get('impact', {}).get('percentage_impact', 0.0)

                    scenario_impacts[scenario_id]['total_dollar_impact'] += dollar_impact
                    scenario_impacts[scenario_id]['weighted_pct_impact'] += pct_impact * weights[portfolio_id]
                    scenario_impacts[scenario_id]['portfolios_included'] += 1

        if not scenario_impacts:
            return {
                "available": False,
                "message": "No stress test data available for any portfolio",
                "portfolio_count": portfolios_result['portfolio_count']
            }

        # Build scenarios list
        scenarios = []
        for scenario_id, data in scenario_impacts.items():
            scenarios.append({
                "id": scenario_id,
                "name": data['name'],
                "description": data['description'],
                "category": data['category'],
                "severity": data['severity'],
                "impact": {
                    "dollar_impact": data['total_dollar_impact'],
                    "percentage_impact": (data['total_dollar_impact'] / total_value * 100) if total_value > 0 else 0,
                    "new_portfolio_value": total_value + data['total_dollar_impact']
                },
                "portfolios_included": data['portfolios_included']
            })

        # Sort by category, then name
        scenarios.sort(key=lambda x: (x.get('category', ''), x.get('name', '')))

        response = {
            "available": True,
            "data": {
                "scenarios": scenarios,
                "portfolio_value": total_value
            },
            "net_asset_value": portfolios_result['net_asset_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "portfolios_with_stress_data": portfolios_with_data,
            "calculation_method": "weighted_aggregation",
            "formula": "Total impact = Σ(portfolio_impact_i), Percentage = total_impact / total_value"
        }

        logger.info(
            f"Aggregate stress test for user {current_user.id}: "
            f"{len(scenarios)} scenarios across {portfolios_with_data}/{portfolios_result['portfolio_count']} portfolios"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate stress test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate stress test: {str(e)}"
        )
