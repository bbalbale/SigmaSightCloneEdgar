"""
Analytics Bundle Service

Fetches all pre-calculated analytics for a portfolio.
Used by AI insight generation to provide context for interpretation.

NO CALCULATIONS ARE DONE HERE - just fetching from existing services.

Created: December 17, 2025
"""

from uuid import UUID
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.correlation_service import CorrelationService
from app.services.factor_exposure_service import FactorExposureService
from app.services.stress_test_service import StressTestService
from app.services.risk_metrics_service import RiskMetricsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsBundleService:
    """Fetches pre-calculated analytics from existing service layer"""

    async def fetch_portfolio_analytics_bundle(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all pre-calculated analytics for a portfolio.

        This is the data that batch_orchestrator already calculated.
        AI will interpret this data, not recalculate it.

        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            focus_area: Optional focus area to prioritize certain metrics
                       (concentration, liquidity, factor_exposure, sector, volatility, options)

        Returns:
            Dict with all pre-calculated metrics including:
            - overview: Portfolio summary (beta, Sharpe, volatility, etc.)
            - sector_exposure: Sector breakdown vs S&P 500
            - concentration: HHI, top positions percentages
            - volatility: HAR forecasting, realized volatility
            - factor_exposures: Factor loadings (value, growth, momentum, etc.)
            - correlation_matrix: Position correlations
            - stress_test: Scenario analysis results
            - focus_area: Optional focus area (if specified)

        Raises:
            Exception: If analytics fetching fails (gracefully degraded)
        """
        logger.info(f"Fetching analytics bundle for portfolio {portfolio_id}")

        bundle = {}

        # Fetch all metrics - use graceful degradation on failures
        # This allows AI to work with partial data if some metrics unavailable
        # Instantiate services with db session

        try:
            portfolio_analytics_service = PortfolioAnalyticsService()
            bundle["overview"] = await portfolio_analytics_service.get_portfolio_overview(db, portfolio_id)
            logger.debug("Overview metrics fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch overview: {e}")
            bundle["overview"] = None

        try:
            risk_metrics_service = RiskMetricsService(db)
            bundle["sector_exposure"] = await risk_metrics_service.get_sector_exposure(portfolio_id)
            logger.debug("Sector exposure fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch sector exposure: {e}")
            bundle["sector_exposure"] = None

        try:
            risk_metrics_service = RiskMetricsService(db)
            bundle["concentration"] = await risk_metrics_service.get_concentration_metrics(portfolio_id)
            logger.debug("Concentration metrics fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch concentration: {e}")
            bundle["concentration"] = None

        try:
            risk_metrics_service = RiskMetricsService(db)
            bundle["volatility"] = await risk_metrics_service.get_volatility_metrics(portfolio_id)
            logger.debug("Volatility metrics fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch volatility: {e}")
            bundle["volatility"] = None

        try:
            factor_exposure_service = FactorExposureService(db)
            bundle["factor_exposures"] = await factor_exposure_service.get_portfolio_factor_exposures(portfolio_id)
            logger.debug("Factor exposures fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch factor exposures: {e}")
            bundle["factor_exposures"] = None

        try:
            correlation_service = CorrelationService(db)
            bundle["correlation_matrix"] = await correlation_service.get_portfolio_correlation_matrix(portfolio_id)
            logger.debug("Correlation matrix fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch correlation matrix: {e}")
            bundle["correlation_matrix"] = None

        try:
            stress_test_service = StressTestService(db)
            bundle["stress_test"] = await stress_test_service.get_stress_test_results(portfolio_id)
            logger.debug("Stress test results fetched")
        except Exception as e:
            logger.warning(f"Failed to fetch stress test: {e}")
            bundle["stress_test"] = None

        # Add focus area if specified
        if focus_area:
            bundle["focus_area"] = focus_area
            logger.info(f"Focus area set: {focus_area}")

        # Count how many metrics we successfully fetched
        successful_fetches = sum(1 for v in bundle.values() if v is not None and v != focus_area)
        logger.info(f"Analytics bundle fetched: {successful_fetches}/7 metric categories")

        return bundle


# Singleton instance
analytics_bundle_service = AnalyticsBundleService()
