"""
Phase 3: Risk Analytics Runner
Runs all risk calculations using cached market data (NO API calls)

Analytics:
1. Market beta (90-day regression)
2. IR beta (90-day regression)
3. Factor analysis (ridge + spread)
4. Sector analysis
5. Volatility analytics
6. Correlations
7. Target returns
"""
import asyncio
from datetime import date
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.users import Portfolio

logger = get_logger(__name__)


class AnalyticsRunner:
    """
    Phase 3 of batch processing - run all risk analytics using cached data

    All calculations must use market_data_cache - NO API calls
    """

    async def run_all_portfolios_analytics(
        self,
        calculation_date: date,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Run analytics for all active portfolios

        Args:
            calculation_date: Date to run analytics for
            db: Optional database session

        Returns:
            Summary of analytics completed
        """
        logger.info(f"=" * 80)
        logger.info(f"Phase 3: Risk Analytics for {calculation_date}")
        logger.info(f"=" * 80)

        start_time = asyncio.get_event_loop().time()

        if db is None:
            async with AsyncSessionLocal() as session:
                result = await self._process_all_with_session(session, calculation_date)
        else:
            result = await self._process_all_with_session(db, calculation_date)

        duration = int(asyncio.get_event_loop().time() - start_time)
        result['duration_seconds'] = duration

        logger.info(f"Phase 3 complete in {duration}s")
        logger.info(f"  Portfolios processed: {result['portfolios_processed']}")
        logger.info(f"  Analytics completed: {result['analytics_completed']}")

        return result

    async def _process_all_with_session(
        self,
        db: AsyncSession,
        calculation_date: date
    ) -> Dict[str, Any]:
        """Process all portfolios with provided session"""
        from sqlalchemy import select

        # Get all active portfolios
        query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        result = await db.execute(query)
        portfolios = result.scalars().all()

        logger.info(f"Found {len(portfolios)} active portfolios")

        portfolios_processed = 0
        analytics_completed = 0
        errors = []

        for portfolio in portfolios:
            try:
                completed = await self.run_portfolio_analytics(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    db=db
                )

                portfolios_processed += 1
                analytics_completed += completed

            except Exception as e:
                import traceback
                logger.error(f"Error processing portfolio {portfolio.name}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                errors.append(f"{portfolio.name}: {str(e)}")

        return {
            'success': len(errors) == 0,
            'portfolios_processed': portfolios_processed,
            'analytics_completed': analytics_completed,
            'errors': errors
        }

    async def run_portfolio_analytics(
        self,
        portfolio_id: UUID,
        calculation_date: date,
        db: AsyncSession
    ) -> int:
        """
        Run all analytics for a single portfolio

        Args:
            portfolio_id: Portfolio to process
            calculation_date: Date to run analytics for
            db: Database session

        Returns:
            Number of analytics successfully completed
        """
        logger.info(f"  Running analytics for portfolio {portfolio_id}")

        completed = 0

        # Define analytics to run (sequential to avoid session conflicts)
        analytics_jobs = [
            ("Market Beta", self._calculate_market_beta),
            ("IR Beta", self._calculate_ir_beta),
            ("Spread Factors", self._calculate_spread_factors),
            ("Ridge Factors", self._calculate_ridge_factors),
            ("Sector Analysis", self._calculate_sector_analysis),
            ("Volatility Analytics", self._calculate_volatility_analytics),
            ("Correlations", self._calculate_correlations),
        ]

        # Run analytics sequentially (single session can't handle concurrent ops)
        for job_name, job_func in analytics_jobs:
            try:
                success = await job_func(db, portfolio_id, calculation_date)
                if success:
                    completed += 1
                    logger.debug(f"    ✓ {job_name}")
                else:
                    logger.warning(f"    ✗ {job_name} (skipped or failed)")
            except Exception as e:
                import traceback
                logger.error(f"    ✗ {job_name} error: {e}")
                logger.error(f"    Traceback: {traceback.format_exc()}")

        # Commit all analytics results at once (prevents object expiration between calcs)
        try:
            await db.commit()
            logger.debug(f"    Committed all analytics for portfolio {portfolio_id}")
        except Exception as e:
            logger.error(f"    Error committing analytics: {e}")
            await db.rollback()
            raise

        logger.info(f"    Analytics complete: {completed}/{len(analytics_jobs)}")
        return completed

    async def _calculate_market_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate market beta using 90-day regression"""
        try:
            from app.calculations.market_beta import calculate_portfolio_market_beta

            result = await calculate_portfolio_market_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                persist=True
            )

            return result is not None

        except Exception as e:
            logger.warning(f"Market beta calculation failed: {e}")
            return False

    async def _calculate_ir_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate interest rate beta using 90-day regression"""
        try:
            from app.calculations.interest_rate_beta import calculate_portfolio_ir_beta

            result = await calculate_portfolio_ir_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                window_days=90,
                treasury_symbol='TLT',
                persist=True
            )

            return result is not None

        except Exception as e:
            logger.warning(f"IR beta calculation failed: {e}")
            return False

    async def _calculate_ridge_factors(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate ridge factor betas"""
        try:
            from app.calculations.factors_ridge import calculate_factor_betas_ridge

            result = await calculate_factor_betas_ridge(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            return result is not None

        except Exception as e:
            logger.warning(f"Ridge factors calculation failed: {e}")
            return False

    async def _calculate_spread_factors(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate spread factor betas"""
        try:
            from app.calculations.factors_spread import calculate_portfolio_spread_betas

            result = await calculate_portfolio_spread_betas(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            return result is not None

        except Exception as e:
            logger.warning(f"Spread factors calculation failed: {e}")
            return False

    async def _calculate_sector_analysis(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate sector concentration"""
        try:
            from app.calculations.sector_analysis import calculate_portfolio_sector_concentration

            result = await calculate_portfolio_sector_concentration(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            return result is not None

        except Exception as e:
            logger.warning(f"Sector analysis calculation failed: {e}")
            return False

    async def _calculate_volatility_analytics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate volatility metrics (21d, 63d, 252d)"""
        try:
            from app.calculations.volatility_analytics import calculate_portfolio_volatility_batch

            result = await calculate_portfolio_volatility_batch(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            return result is not None

        except Exception as e:
            logger.warning(f"Volatility analytics calculation failed: {e}")
            return False

    async def _calculate_correlations(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate position correlations"""
        try:
            from app.services.correlation_service import CorrelationService

            correlation_service = CorrelationService(db)

            result = await correlation_service.calculate_portfolio_correlations(
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            # Correlation service returns None if no public positions (graceful skip)
            # This is not an error
            return True

        except Exception as e:
            logger.warning(f"Correlations calculation failed: {e}")
            return False


# Global instance
analytics_runner = AnalyticsRunner()
