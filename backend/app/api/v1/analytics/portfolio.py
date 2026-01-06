"""
Portfolio Analytics API endpoints

Endpoints for portfolio-level analytics including overview metrics,
exposures, P&L calculations, and performance data.
"""
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
import time

from app.database import get_db
from app.core.dependencies import validate_portfolio_ownership
from app.core.clerk_auth import get_current_user_clerk
from app.models.users import User
from app.models.users import Portfolio
from app.schemas.analytics import (
    PortfolioOverviewResponse,
    CorrelationMatrixResponse,
    DiversificationScoreResponse,
    PortfolioFactorExposuresResponse,
    PositionFactorExposuresResponse,
    StressTestResponse,
    PortfolioRiskMetricsResponse,
    SectorExposureResponse,
    ConcentrationMetricsResponse,
    VolatilityMetricsResponse,
    MarketBetaComparisonResponse,
    SingleFactorMarketBetaResponse,
    CalculatedBeta90dResponse,
    ProviderBeta1yResponse,
)
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.correlation_service import CorrelationService
from app.services.factor_exposure_service import FactorExposureService
from app.services.stress_test_service import StressTestService
from app.services.risk_metrics_service import RiskMetricsService
from app.services.preprocessing_service import preprocessing_service
from app.services.batch_trigger_service import batch_trigger_service
from app.batch.batch_run_tracker import batch_run_tracker
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio-analytics"])


@router.get("/{portfolio_id}/overview", response_model=PortfolioOverviewResponse)
async def get_portfolio_overview(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive portfolio overview with exposures, P&L, and position metrics.
    
    This endpoint provides portfolio-level analytics for dashboard consumption including:
    - Total portfolio value and cash balance
    - Long/short/gross/net exposure metrics with percentages
    - P&L breakdown (total, unrealized, realized)
    - Position count breakdown by type (long, short, options)
    
    **Implementation Notes**:
    - Uses existing batch processing results where available
    - Graceful degradation for missing calculation data
    - <500ms target response time with 5-minute cache TTL
    - Portfolio ownership validation ensures data security
    
    **Frontend Integration**: 
    Required for portfolio page aggregate cards at `http://localhost:3005/portfolio`
    
    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session
        
    Returns:
        PortfolioOverviewResponse with complete portfolio analytics
        
    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Get analytics service and calculate overview
        analytics_service = PortfolioAnalyticsService()
        overview_data = await analytics_service.get_portfolio_overview(db, portfolio_id)
        
        # Return validated response
        return PortfolioOverviewResponse(**overview_data)
        
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating portfolio overview {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error calculating portfolio analytics")


@router.get("/{portfolio_id}/correlation-matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=365, description="Lookback period in days"),
    min_overlap: int = Query(30, ge=10, le=365, description="Minimum overlapping data points"),
    max_symbols: int = Query(25, ge=2, le=50, description="Maximum symbols to include in matrix"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the correlation matrix for portfolio positions.
    
    Returns pre-calculated pairwise correlations between all positions in the portfolio,
    ordered by position weight (gross market value).
    
    Args:
        portfolio_id: Portfolio UUID
        lookback_days: Duration for correlation calculation (30-365 days)
        min_overlap: Minimum data points required for valid correlation (10-365)
        
    Returns:
        CorrelationMatrixResponse with matrix data or unavailable status
    """
    # Input validation
    if min_overlap > lookback_days:
        raise HTTPException(
            status_code=400, 
            detail="Min overlap cannot exceed lookback days"
        )
    
    try:
        # Performance monitoring
        start = time.time()
        
        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Get correlation matrix from service
        svc = CorrelationService(db)
        result = await svc.get_matrix(portfolio_id, lookback_days, min_overlap, max_symbols)
        
        # Log performance
        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(
                f"Slow correlation matrix response: {elapsed:.2f}s for portfolio {portfolio_id}"
            )
        else:
            logger.info(
                f"Correlation matrix retrieved in {elapsed:.3f}s for portfolio {portfolio_id}"
            )
        
        # Return appropriate response based on availability
        if "available" in result and result["available"] is False:
            # Phase 8.1 fix: Include data_quality field to expose transparency metrics
            return CorrelationMatrixResponse(
                available=False,
                data_quality=result.get("data_quality"),  # Include quality metrics computed by service
                metadata=result.get("metadata", {})
            )
        else:
            return CorrelationMatrixResponse(**result)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Correlation matrix failed for {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error computing correlation matrix"
        )


@router.get("/{portfolio_id}/diversification-score", response_model=DiversificationScoreResponse)
async def get_diversification_score(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=365, description="Lookback period in days"),
    min_overlap: int = Query(30, ge=10, le=365, description="Minimum overlapping data points"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the weighted absolute portfolio correlation (0–1) using the full
    calculation symbol set for the latest correlation run that matches the
    requested lookback window.
    """
    if min_overlap > lookback_days:
        raise HTTPException(status_code=400, detail="Min overlap cannot exceed lookback days")

    try:
        start = time.time()

        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = CorrelationService(db)
        result = await svc.get_weighted_correlation(portfolio_id, lookback_days, min_overlap)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow diversification-score response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Diversification-score retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return DiversificationScoreResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diversification score failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error computing diversification score")


@router.get("/{portfolio_id}/factor-exposures", response_model=PortfolioFactorExposuresResponse)
async def get_portfolio_factor_exposures(
    portfolio_id: UUID,
    use_latest_successful: bool = True,  # Default to graceful degradation
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio-level factor exposures for the most recent calculation date.

    Returns factor betas (and optional dollar exposures) aggregated at the
    portfolio level. Uses the latest complete set of exposures.

    Args:
        portfolio_id: Portfolio UUID
        use_latest_successful: If True (default), falls back to most recent complete
                               snapshot when today's data is incomplete. This prevents
                               blank UIs during batch execution.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(portfolio_id, use_latest_successful=use_latest_successful)

        elapsed = time.time() - start
        if elapsed > 0.2:
            logger.warning(f"Slow factor-exposures response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Factor-exposures retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PortfolioFactorExposuresResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Factor exposures failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving factor exposures")


@router.get("/{portfolio_id}/positions/factor-exposures", response_model=PositionFactorExposuresResponse)
async def list_position_factor_exposures(
    portfolio_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of positions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    symbols: str | None = Query(None, description="Optional CSV list of symbols to filter"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Position-level factor exposures for the most recent calculation date.

    Paginates by positions. Optional filter by CSV `symbols`.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

        svc = FactorExposureService(db)
        result = await svc.list_position_exposures(portfolio_id, limit=limit, offset=offset, symbols=symbols_list)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow position-factor-exposures response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Position factor-exposures retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PositionFactorExposuresResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position factor exposures failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving position factor exposures")


@router.get("/{portfolio_id}/stress-test", response_model=StressTestResponse)
async def get_stress_test_results(
    portfolio_id: UUID,
    scenarios: str | None = Query(None, description="Optional CSV list of scenario IDs to include"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Return precomputed stress testing results for the portfolio using correlated impacts.

    Read-only: joins stored results with scenario definitions; computes percentage and
    new portfolio value using baseline snapshot; no recomputation.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        scenarios_list = None
        if scenarios:
            scenarios_list = [s.strip() for s in scenarios.split(',') if s.strip()]

        svc = StressTestService(db)
        result = await svc.get_portfolio_results(portfolio_id, scenarios=scenarios_list)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow stress-test response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Stress-test retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return StressTestResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Stress test retrieval failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving stress test results")


@router.get(
    "/{portfolio_id}/risk-metrics", 
    response_model=PortfolioRiskMetricsResponse,
    deprecated=True,
    summary="WARNING: DEFERRED - Portfolio Risk Metrics (DO NOT USE)",
    description="WARNING: WARNING: PARTIALLY IMPLEMENTED BUT NOT TESTED. DEFERRED INDEFINITELY (2025-09-07). DO NOT USE IN PRODUCTION. Frontend and AI agents should NOT use this endpoint. This endpoint may return incomplete or incorrect data."
)
async def get_portfolio_risk_metrics(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=252, description="Lookback period in days (30–252)"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio risk metrics (DB-first v1).
    
    WARNING: WARNING: PARTIALLY IMPLEMENTED BUT NOT TESTED. DEFERRED INDEFINITELY (2025-09-07).
    WARNING: DO NOT USE IN PRODUCTION. Frontend and AI agents should NOT use this endpoint.
    WARNING: This endpoint may return incomplete or incorrect data.
    
    Original scope:
    - portfolio_beta from FactorExposure ("Market Beta")
    - annualized_volatility from PortfolioSnapshot.daily_return
    - max_drawdown from PortfolioSnapshot.total_value
    
    Status: Implementation incomplete, testing not performed, deferred for future release.
    """
    # WARNING: IMPORTANT: This endpoint is DEFERRED INDEFINITELY - DO NOT USE
    # Implementation is incomplete and untested. May return incorrect data.
    # Frontend developers and AI agents should avoid using this endpoint.
    
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = RiskMetricsService(db)
        result = await svc.get_portfolio_risk_metrics(portfolio_id, lookback_days=lookback_days)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow risk-metrics response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Risk-metrics retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PortfolioRiskMetricsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk metrics failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving risk metrics")


@router.get("/{portfolio_id}/sector-exposure", response_model=SectorExposureResponse)
async def get_sector_exposure(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio sector exposure vs S&P 500 benchmark.

    Returns portfolio sector weights compared to S&P 500 sector weights,
    showing over/underweight positions by sector. Uses GICS sector classifications
    from the market_data_cache table.

    This endpoint provides:
    - Portfolio sector weights (as percentage of total value)
    - S&P 500 benchmark sector weights
    - Over/underweight analysis (portfolio - benchmark)
    - Largest overweight and underweight sectors
    - Position count by sector
    - Unclassified positions (no sector data available)

    Part of Risk Metrics Phase 1 implementation.

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SectorExposureResponse with sector analysis or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Import and call sector analysis
        from app.calculations.sector_analysis import calculate_sector_exposure
        result = await calculate_sector_exposure(db, portfolio_id)

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow sector-exposure response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Sector-exposure retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not result.get('success'):
            return SectorExposureResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": result.get('error', 'Unknown error')}
            )

        from datetime import date
        return SectorExposureResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=date.today().isoformat(),
            data={
                "portfolio_weights": result.get('portfolio_weights', {}),
                "benchmark_weights": result.get('benchmark_weights', {}),
                "over_underweight": result.get('over_underweight', {}),
                "largest_overweight": result.get('largest_overweight'),
                "largest_underweight": result.get('largest_underweight'),
                "total_portfolio_value": result.get('total_portfolio_value', 0.0),
                "positions_by_sector": result.get('positions_by_sector', {}),
                "unclassified_value": result.get('unclassified_value', 0.0),
                "unclassified_count": result.get('unclassified_count', 0)
            },
            metadata={
                "benchmark": "SP500"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sector exposure failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving sector exposure")


@router.get("/{portfolio_id}/concentration", response_model=ConcentrationMetricsResponse)
async def get_concentration_metrics(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio concentration metrics.

    Returns concentration and diversification metrics including:
    - Herfindahl-Hirschman Index (HHI) - measure of concentration (0-10000)
    - Effective number of positions (10000 / HHI)
    - Top 3 position concentration (sum of 3 largest weights)
    - Top 10 position concentration (sum of 10 largest weights)

    HHI Interpretation:
    - HHI > 2500: Highly concentrated portfolio
    - HHI 1500-2500: Moderately concentrated
    - HHI < 1500: Well diversified

    Part of Risk Metrics Phase 1 implementation.

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        ConcentrationMetricsResponse with metrics or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Import and call concentration calculation
        from app.calculations.sector_analysis import calculate_concentration_metrics
        result = await calculate_concentration_metrics(db, portfolio_id)

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow concentration response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Concentration metrics retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not result.get('success'):
            return ConcentrationMetricsResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": result.get('error', 'Unknown error')}
            )

        from datetime import date
        hhi = result.get('hhi', 0.0)

        # Determine interpretation
        if hhi > 2500:
            interpretation = "Highly concentrated (HHI > 2500)"
        elif hhi > 1500:
            interpretation = "Moderately concentrated (HHI 1500-2500)"
        else:
            interpretation = "Well diversified (HHI < 1500)"

        return ConcentrationMetricsResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=date.today().isoformat(),
            data={
                "hhi": hhi,
                "effective_num_positions": result.get('effective_num_positions', 0.0),
                "top_3_concentration": result.get('top_3_concentration', 0.0),
                "top_10_concentration": result.get('top_10_concentration', 0.0),
                "total_positions": result.get('total_positions', 0),
                "position_weights": None  # Omit detailed weights for cleaner response
            },
            metadata={
                "calculation_method": "market_value_weighted",
                "interpretation": interpretation
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Concentration metrics failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving concentration metrics")


@router.get("/{portfolio_id}/volatility", response_model=VolatilityMetricsResponse)
async def get_volatility_metrics(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio volatility metrics with HAR forecasting.

    Returns portfolio volatility analytics including:
    - Realized volatility over 21-day and 63-day windows (trading days)
    - Expected volatility forecast using HAR (Heterogeneous Autoregressive) model
    - Volatility trend analysis (increasing, decreasing, or stable)
    - Volatility percentile vs 1-year historical distribution

    The HAR model uses daily, weekly, and monthly volatility components to
    forecast future volatility, providing more accurate predictions than simple
    moving averages.

    Part of Risk Metrics Phase 2 implementation.

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        VolatilityMetricsResponse with volatility metrics or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Fetch volatility data from latest snapshot that has data
        # This handles the case where today's snapshot exists but hasn't been populated yet
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select, and_

        snapshot_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.realized_volatility_21d.isnot(None)
            )
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        snapshot_result = await db.execute(snapshot_query)
        snapshot = snapshot_result.scalar_one_or_none()

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow volatility response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Volatility metrics retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not snapshot or snapshot.realized_volatility_21d is None:
            return VolatilityMetricsResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No volatility data available"}
            )

        from datetime import date
        return VolatilityMetricsResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else date.today().isoformat(),
            data={
                "realized_volatility_21d": float(snapshot.realized_volatility_21d),
                "realized_volatility_63d": float(snapshot.realized_volatility_63d) if snapshot.realized_volatility_63d else None,
                "expected_volatility_21d": float(snapshot.expected_volatility_21d) if snapshot.expected_volatility_21d else None,
                "volatility_trend": snapshot.volatility_trend,
                "volatility_percentile": float(snapshot.volatility_percentile) if snapshot.volatility_percentile else None
            },
            metadata={
                "forecast_model": "HAR",
                "trading_day_windows": "21d, 63d"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Volatility metrics failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving volatility metrics")


@router.get("/{portfolio_id}/beta-comparison", response_model=MarketBetaComparisonResponse)
async def get_market_beta_comparison(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comparison between market betas and calculated betas for portfolio positions.

    Returns a comparison showing:
    - Market beta (from company profile data provider)
    - Calculated beta (from our OLS regression analysis)
    - R-squared value for calculated beta
    - Calculation date and observation count
    - Beta difference (calculated - market)

    This helps identify discrepancies between data provider betas and our
    calculated betas, useful for validating risk factor exposures.

    Part of Risk Metrics Phase 0 implementation.

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        MarketBetaComparisonResponse with beta comparison or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Import models
        from app.models.positions import Position
        from app.models.market_data import CompanyProfile, PositionMarketBeta
        from sqlalchemy import select, func, and_
        from sqlalchemy.orm import aliased
        from datetime import date

        # Subquery to get the latest beta for each position
        latest_beta_subq = (
            select(
                PositionMarketBeta.position_id,
                func.max(PositionMarketBeta.calc_date).label("max_calc_date")
            )
            .group_by(PositionMarketBeta.position_id)
            .subquery()
        )

        # Query positions with company profile and latest calculated beta data
        query = (
            select(
                Position.id.label("position_id"),
                Position.symbol,
                CompanyProfile.beta.label("market_beta"),
                PositionMarketBeta.beta.label("calculated_beta"),
                PositionMarketBeta.r_squared,
                PositionMarketBeta.observations,
                PositionMarketBeta.calc_date,
            )
            .select_from(Position)
            .outerjoin(CompanyProfile, Position.symbol == CompanyProfile.symbol)
            .outerjoin(
                latest_beta_subq,
                latest_beta_subq.c.position_id == Position.id
            )
            .outerjoin(
                PositionMarketBeta,
                and_(
                    PositionMarketBeta.position_id == Position.id,
                    PositionMarketBeta.calc_date == latest_beta_subq.c.max_calc_date
                )
            )
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.symbol)
        )

        result = await db.execute(query)
        rows = result.all()

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow beta-comparison response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Beta comparison retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not rows:
            return MarketBetaComparisonResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No positions found for portfolio"}
            )

        # Build position comparisons
        from app.schemas.analytics import PositionBetaComparison

        positions = []
        for row in rows:
            market_beta = float(row.market_beta) if row.market_beta is not None else None
            calculated_beta = float(row.calculated_beta) if row.calculated_beta is not None else None

            # Calculate difference if both betas are available
            beta_difference = None
            if market_beta is not None and calculated_beta is not None:
                beta_difference = calculated_beta - market_beta

            positions.append(PositionBetaComparison(
                symbol=row.symbol,
                position_id=str(row.position_id),
                market_beta=market_beta,
                calculated_beta=calculated_beta,
                beta_r_squared=float(row.r_squared) if row.r_squared is not None else None,
                calculation_date=row.calc_date.isoformat() if row.calc_date else None,
                observations=row.observations,
                beta_difference=beta_difference
            ))

        return MarketBetaComparisonResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            positions=positions,
            metadata={
                "total_positions": len(positions),
                "positions_with_market_beta": sum(1 for p in positions if p.market_beta is not None),
                "positions_with_calculated_beta": sum(1 for p in positions if p.calculated_beta is not None),
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Beta comparison failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving beta comparison")


@router.get("/{portfolio_id}/market-beta", response_model=SingleFactorMarketBetaResponse)
async def get_single_factor_market_beta(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get single-factor market beta from portfolio snapshot.

    Returns portfolio-level market beta calculated from single-factor OLS regression
    (Position returns ~ SPY returns). This is the equity-weighted average of
    position-level betas.

    Different from multi-factor beta (/factor-exposures endpoint) which controls
    for additional factor exposures like Value, Growth, Momentum, etc.

    Part of Risk Metrics Phase 0 implementation.

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SingleFactorMarketBetaResponse with market beta metrics or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during retrieval
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Fetch market beta from latest snapshot
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select

        snapshot_query = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        snapshot_result = await db.execute(snapshot_query)
        snapshot = snapshot_result.scalar_one_or_none()

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow market-beta response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Market beta retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response using new field names
        if not snapshot or snapshot.beta_calculated_90d is None:
            return SingleFactorMarketBetaResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No market beta data available"}
            )

        from datetime import date
        return SingleFactorMarketBetaResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else date.today().isoformat(),
            data={
                "market_beta_weighted": float(snapshot.beta_calculated_90d),
                "market_beta_r_squared": float(snapshot.beta_calculated_90d_r_squared) if snapshot.beta_calculated_90d_r_squared else None,
                "market_beta_observations": snapshot.beta_calculated_90d_observations,
                "market_beta_direct": float(snapshot.beta_portfolio_regression) if snapshot.beta_portfolio_regression else None
            },
            metadata={
                "calculation_method": "equity_weighted_average",
                "model_type": "single_factor_ols"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Market beta retrieval failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving market beta")


class UpdateEquityRequest(BaseModel):
    """Request model for updating portfolio equity balance"""
    equity_balance: float

    class Config:
        json_schema_extra = {
            "example": {
                "equity_balance": 1000000.00
            }
        }


@router.put("/{portfolio_id}/equity")
async def update_portfolio_equity(
    portfolio_id: UUID,
    request: UpdateEquityRequest,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the equity balance (NAV) for a portfolio.
    
    This endpoint allows users to set their portfolio's equity balance, which is used
    for calculating cash positions, leverage ratios, and other risk metrics.
    
    Args:
        portfolio_id: The portfolio UUID
        request: The new equity balance value
        
    Returns:
        Success message with updated equity balance
    """
    try:
        # Validate ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Update equity balance
        stmt = (
            update(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .values(equity_balance=request.equity_balance)
        )
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Updated equity balance for portfolio {portfolio_id} to ${request.equity_balance:,.2f}")
        
        return {
            "message": "Equity balance updated successfully",
            "portfolio_id": str(portfolio_id),
            "equity_balance": request.equity_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update equity for {portfolio_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error updating equity balance")


@router.get("/{portfolio_id}/beta-calculated-90d", response_model=CalculatedBeta90dResponse)
async def get_calculated_beta_90d(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get calculated beta (90-day OLS regression) from portfolio snapshot.

    Returns portfolio-level calculated beta using 90-day rolling window OLS regression
    (Position returns ~ SPY returns), equity-weighted averaged to portfolio level.
    This represents our internally calculated beta based on historical return analysis.

    Different from provider beta which uses 1-year betas from company profile data.

    Part of Risk Metrics Phase 0 refactoring (field name clarity improvements).

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        CalculatedBeta90dResponse with calculated beta metrics or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during retrieval
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Fetch calculated beta from latest snapshot that has data
        # This handles the case where today's snapshot exists but hasn't been populated yet
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select, and_

        snapshot_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.beta_calculated_90d.isnot(None)
            )
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        snapshot_result = await db.execute(snapshot_query)
        snapshot = snapshot_result.scalar_one_or_none()

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow beta-calculated-90d response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Calculated beta (90d) retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not snapshot or snapshot.beta_calculated_90d is None:
            return CalculatedBeta90dResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No calculated beta data available"}
            )

        from datetime import date
        return CalculatedBeta90dResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else date.today().isoformat(),
            data={
                "beta_calculated_90d": float(snapshot.beta_calculated_90d),
                "beta_calculated_90d_r_squared": float(snapshot.beta_calculated_90d_r_squared) if snapshot.beta_calculated_90d_r_squared else None,
                "beta_calculated_90d_observations": snapshot.beta_calculated_90d_observations
            },
            metadata={
                "calculation_method": "equity_weighted_average_of_position_betas",
                "model_type": "single_factor_ols",
                "window_days": 90
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Calculated beta retrieval failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving calculated beta")


@router.get("/{portfolio_id}/beta-provider-1y", response_model=ProviderBeta1yResponse)
async def get_provider_beta_1y(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Get provider beta (1-year from company profiles) from portfolio snapshot.

    Returns portfolio-level provider beta using 1-year betas from company profile data
    (typically from data providers like yahooquery/FMP), equity-weighted averaged to
    portfolio level. This represents externally sourced beta values.

    Different from calculated beta which uses our 90-day OLS regression analysis.

    Part of Risk Metrics Phase 0 refactoring (field name clarity improvements).

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        ProviderBeta1yResponse with provider beta metrics or unavailable status

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during retrieval
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Fetch provider beta from latest snapshot that has data
        # This handles the case where today's snapshot exists but hasn't been populated yet
        from app.models.snapshots import PortfolioSnapshot
        from app.models.positions import Position
        from sqlalchemy import select, and_

        snapshot_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.beta_provider_1y.isnot(None)
            )
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        snapshot_result = await db.execute(snapshot_query)
        snapshot = snapshot_result.scalar_one_or_none()

        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow beta-provider-1y response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Provider beta (1y) retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        # Format response
        if not snapshot or snapshot.beta_provider_1y is None:
            return ProviderBeta1yResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No provider beta data available"}
            )

        # Get position count for metadata
        positions_query = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        positions_result = await db.execute(positions_query)
        positions = positions_result.scalars().all()
        total_positions = len(positions)

        # Get provider beta calculation details from snapshot metadata (if available)
        # For now, we'll use the snapshot data and estimate coverage
        from app.models.market_data import CompanyProfile

        # Count positions with company profile beta
        positions_with_beta = 0
        for position in positions:
            profile_query = select(CompanyProfile).where(CompanyProfile.symbol == position.symbol)
            profile_result = await db.execute(profile_query)
            profile = profile_result.scalar_one_or_none()
            if profile and profile.beta is not None:
                positions_with_beta += 1

        coverage_percentage = (positions_with_beta / total_positions * 100) if total_positions > 0 else 0.0

        from datetime import date
        return ProviderBeta1yResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else date.today().isoformat(),
            data={
                "beta_provider_1y": float(snapshot.beta_provider_1y),
                "positions_with_beta": positions_with_beta,
                "positions_total": total_positions,
                "coverage_percentage": round(coverage_percentage, 2)
            },
            metadata={
                "calculation_method": "equity_weighted_average_of_company_profile_betas",
                "data_source": "company_profile_table",
                "typical_period": "1_year"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Provider beta retrieval failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving provider beta")


# ==============================================================================
# Portfolio Calculate Endpoint (Onboarding)
# ==============================================================================

class CalculateResponse(BaseModel):
    """Portfolio calculate response"""
    status: str
    batch_run_id: str
    portfolio_id: str
    preprocessing: dict
    message: str
    poll_url: str


@router.post("/{portfolio_id}/calculate", response_model=CalculateResponse, status_code=202)
async def trigger_portfolio_calculations(
    portfolio_id: UUID,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force run even if batch already running or preprocessing already done"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger portfolio calculations with preprocessing.

    This endpoint is designed for the onboarding flow and performs two steps:

    **Step 1: Preprocessing (10-30s)**
    - Extracts symbols from portfolio positions
    - Enriches security master data (sector/industry)
    - Bootstraps price cache (30 days of historical data)

    **Step 2: Batch Processing (30-60s)**
    - Runs all 8 calculation engines
    - Populates risk metrics, Greeks, factors, correlations, etc.

    **Total Time**: 40-90 seconds (preprocessing + batch)

    **Use Cases**:
    - First-time portfolio setup (after CSV import)
    - Manual recalculation after position changes
    - Retry after network failures

    **Preprocessing Skip**:
    - Use `force=false` (default) to skip if already done
    - Use `force=true` to re-run preprocessing

    **Returns**: HTTP 202 Accepted
    - batch_run_id for status polling
    - preprocessing metrics
    - poll_url for checking status

    **Errors**:
    - 403: Not authorized to access this portfolio
    - 404: Portfolio not found
    - 409: Batch already running (unless force=true)
    """
    logger.info(f"Calculate request for portfolio {portfolio_id} by user {current_user.id}")

    # Step 1: Run preprocessing
    try:
        logger.info(f"Running preprocessing for portfolio {portfolio_id}")
        prep_result = await preprocessing_service.prepare_portfolio_for_batch(
            portfolio_id=portfolio_id,
            db=db
        )

        # Commit preprocessing changes
        await db.commit()

        logger.info(
            f"Preprocessing complete: {prep_result['symbols_count']} symbols, "
            f"{prep_result['price_coverage_percentage']:.1f}% coverage"
        )

    except Exception as e:
        logger.error(f"Preprocessing failed for portfolio {portfolio_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Preprocessing failed: {str(e)}"
        )

    # Step 2: Trigger batch processing
    try:
        batch_result = await batch_trigger_service.trigger_batch(
            background_tasks=background_tasks,
            portfolio_id=str(portfolio_id),
            force=force,
            user_id=current_user.id,
            user_email=current_user.email,
            db=db
        )

        logger.info(
            f"Batch processing triggered: run_id={batch_result['batch_run_id']}"
        )

        return CalculateResponse(
            status=batch_result["status"],
            batch_run_id=batch_result["batch_run_id"],
            portfolio_id=str(portfolio_id),
            preprocessing={
                "symbols_count": prep_result["symbols_count"],
                "security_master_enriched": prep_result["security_master_enriched"],
                "prices_bootstrapped": prep_result["prices_bootstrapped"],
                "price_coverage_percentage": prep_result["price_coverage_percentage"],
                "ready_for_batch": prep_result["ready_for_batch"],
                "warnings": prep_result.get("warnings", []),
                "recommendations": prep_result.get("recommendations", [])
            },
            message=(
                "Portfolio calculations started. "
                "This may take 30-60 seconds to complete. "
                "Poll the status endpoint to check progress."
            ),
            poll_url=batch_result["poll_url"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch trigger failed for portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger calculations: {str(e)}"
        )


# ==============================================================================
# Batch Status Endpoint (Polling)
# ==============================================================================

class BatchStatusResponse(BaseModel):
    """Batch status polling response"""
    status: str  # "running", "completed", or "idle"
    batch_run_id: str | None
    portfolio_id: str | None
    started_at: str | None
    triggered_by: str | None
    elapsed_seconds: float | None


@router.get("/{portfolio_id}/batch-status/{batch_run_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    portfolio_id: UUID,
    batch_run_id: str,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of batch calculations for a specific portfolio.

    This endpoint is designed for polling while batch calculations are running.
    Users can only check status for portfolios they own.

    **Status Values**:
    - `running`: Batch is currently processing
    - `completed`: Batch has finished (no longer tracked)
    - `idle`: No batch found with this ID

    **Poll Interval**: Recommended 2-5 seconds

    **Errors**:
    - 403: Not authorized to access this portfolio
    - 404: Portfolio not found
    """
    # Validate ownership
    await validate_portfolio_ownership(portfolio_id, current_user.id, db)

    # Get current batch status
    current = batch_run_tracker.get_current()

    if not current:
        return BatchStatusResponse(
            status="idle",
            batch_run_id=None,
            portfolio_id=None,
            started_at=None,
            triggered_by=None,
            elapsed_seconds=None
        )

    # Check if this is the batch they're asking about
    if current.batch_run_id != batch_run_id:
        # Different batch is running, or this one completed
        return BatchStatusResponse(
            status="completed",
            batch_run_id=batch_run_id,
            portfolio_id=str(portfolio_id),
            started_at=None,
            triggered_by=None,
            elapsed_seconds=None
        )

    # Batch is running
    elapsed = (time.time() - current.started_at.timestamp())

    return BatchStatusResponse(
        status="running",
        batch_run_id=current.batch_run_id,
        portfolio_id=str(portfolio_id),
        started_at=current.started_at.isoformat(),
        triggered_by=current.triggered_by,
        elapsed_seconds=round(elapsed, 1)
    )
