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
7. Stress testing (market risk scenarios)
8. Target returns
"""
import asyncio
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.telemetry.metrics import record_metric

logger = get_logger(__name__)


class AnalyticsRunner:
    """
    Phase 3 of batch processing - run all risk analytics using cached data

    All calculations must use market_data_cache - NO API calls
    """

    def __init__(self) -> None:
        self._profile_cache: Dict[str, Dict[str, Optional[Any]]] = {}
        self._price_cache: Optional[Any] = None  # PriceCache instance

    def reset_caches(self) -> None:
        """Clear per-run caches so repeated runs don't reuse stale data."""
        self._profile_cache.clear()

    async def run_all_portfolios_analytics(
        self,
        calculation_date: date,
        db: Optional[AsyncSession] = None,
        portfolio_ids: Optional[List[UUID]] = None,
        run_sector_analysis: bool = True,
        price_cache: Optional[Any] = None,  # PriceCache instance for optimization
    ) -> Dict[str, Any]:
        """
        Run analytics for all active portfolios

        Args:
            calculation_date: Date to run analytics for
            db: Optional database session
            price_cache: Optional PriceCache instance for fast price lookups

        Returns:
            Summary of analytics completed
        """
        logger.info(f"=" * 80)
        logger.info(f"Phase 3: Risk Analytics for {calculation_date}")
        logger.info(f"=" * 80)

        # Store price cache for use by calculation methods
        self._price_cache = price_cache
        if price_cache:
            stats = price_cache.get_stats()
            logger.info(f"OPTIMIZATION: Using price cache with {stats.get('total_prices', 0)} preloaded prices")
        else:
            logger.warning("Price cache not provided - will use slower database queries")

        start_time = asyncio.get_event_loop().time()

        if db is None:
            async with AsyncSessionLocal() as session:
                result = await self._process_all_with_session(
                    session,
                    calculation_date,
                    portfolio_ids,
                    run_sector_analysis,
                    price_cache,
                )
        else:
            result = await self._process_all_with_session(
                db,
                calculation_date,
                portfolio_ids,
                run_sector_analysis,
                price_cache,
            )

        duration = int(asyncio.get_event_loop().time() - start_time)
        result['duration_seconds'] = duration

        logger.info(f"Phase 3 complete in {duration}s")
        logger.info(f"  Portfolios processed: {result['portfolios_processed']}")
        logger.info(f"  Analytics completed: {result['analytics_completed']}")

        return result

    async def _process_all_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]] = None,
        run_sector_analysis: bool = True,
        price_cache: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Process all portfolios with provided session"""
        from sqlalchemy import select

        # Get all active portfolios
        query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        if portfolio_ids is not None:
            query = query.where(Portfolio.id.in_(portfolio_ids))
        result = await db.execute(query)
        portfolios = result.scalars().all()

        logger.info(f"Found {len(portfolios)} active portfolios")

        portfolios_processed = 0
        analytics_completed = 0
        errors = []
        portfolio_reports: List[Dict[str, Any]] = []

        for portfolio in portfolios:
            try:
                report = await self.run_portfolio_analytics(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    db=db,
                    run_sector_analysis=run_sector_analysis,
                )

                portfolios_processed += 1
                analytics_completed += report["completed_count"]
                portfolio_reports.append(
                    {
                        'portfolio_id': str(portfolio.id),
                        'portfolio_name': portfolio.name,
                        'completed_count': report["completed_count"],
                        'jobs': report["jobs"],
                    }
                )
            except Exception as e:
                import traceback
                logger.error(f"Error processing portfolio {portfolio.name}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                errors.append(f"{portfolio.name}: {str(e)}")

        return {
            'success': len(errors) == 0,
            'portfolios_processed': portfolios_processed,
            'analytics_completed': analytics_completed,
            'errors': errors,
            'portfolio_reports': portfolio_reports,
        }

    async def run_portfolio_analytics(
        self,
        portfolio_id: UUID,
        calculation_date: date,
        db: AsyncSession,
        run_sector_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        Run all analytics for a single portfolio

        Args:
            portfolio_id: Portfolio to process
            calculation_date: Date to run analytics for
            db: Database session

        Returns:
            Dictionary containing job-level results and completion counts
        """
        logger.info(f"  Running analytics for portfolio {portfolio_id}")

        completed = 0
        job_results: List[Dict[str, Any]] = []
        loop = asyncio.get_running_loop()

        # Define analytics to run (sequential to avoid session conflicts)
        analytics_jobs = [
            ("Market Beta (90D)", self._calculate_market_beta),
            ("Provider Beta (1Y)", self._calculate_provider_beta),
            ("IR Beta", self._calculate_ir_beta),
            ("Spread Factors", self._calculate_spread_factors),
            ("Ridge Factors", self._calculate_ridge_factors),
        ]

        if run_sector_analysis:
            analytics_jobs.append(("Sector Analysis", self._calculate_sector_analysis))

        analytics_jobs.extend(
            [
                ("Volatility Analytics", self._calculate_volatility_analytics),
                ("Correlations", self._calculate_correlations),
                ("Stress Testing", self._calculate_stress_testing),
            ]
        )

        if not run_sector_analysis:
            logger.debug(
                "Skipping sector analysis for portfolio %s on %s (not target date)",
                portfolio_id,
                calculation_date,
            )

        # Run analytics sequentially (single session can't handle concurrent ops)
        for job_name, job_func in analytics_jobs:
            job_start = loop.time()
            success_flag = False
            message: Optional[str] = None
            extra_payload: Dict[str, Any] = {}

            try:
                raw_result = await job_func(db, portfolio_id, calculation_date)
                success_flag, message, extra_payload = self._normalize_job_result(raw_result)
                if success_flag:
                    completed += 1
                    logger.debug(f"    OK {job_name}")
                else:
                    if not message:
                        message = "Job returned falsy result"
                    logger.warning(f"    WARN {job_name}: {message}")
            except Exception as e:
                import traceback
                success_flag = False
                message = str(e)
                logger.error(f"    FAIL {job_name} error: {e}")
                logger.error(f"    Traceback: {traceback.format_exc()}")
            finally:
                duration = loop.time() - job_start
                job_record: Dict[str, Any] = {
                    'name': job_name,
                    'success': success_flag,
                    'duration_seconds': round(duration, 3),
                }
                if message:
                    job_record['message'] = message
                if extra_payload:
                    job_record['details'] = extra_payload

                job_results.append(job_record)
                record_metric(
                    "analytics_job_result",
                    {
                        'portfolio_id': str(portfolio_id),
                        'calculation_date': calculation_date.isoformat(),
                        **job_record,
                    },
                    source="analytics_runner",
                )

        # Commit all analytics results at once (prevents object expiration between calcs)
        try:
            await db.commit()
            logger.debug(f"    Committed all analytics for portfolio {portfolio_id}")
        except Exception as e:
            logger.error(f"    Error committing analytics: {e}")
            await db.rollback()
            raise

        logger.info(f"    Analytics complete: {completed}/{len(analytics_jobs)}")
        return {
            'completed_count': completed,
            'jobs': job_results,
        }

    def _normalize_job_result(self, raw_result: Any) -> (bool, Optional[str], Dict[str, Any]):
        """
        Normalize mixed return types from analytics jobs into a common structure.

        Supported formats:
            - bool
            - (success, message)
            - (success, message, details_dict)
            - dict with keys: success (bool) and optional message/details
        """
        message: Optional[str] = None
        extra: Dict[str, Any] = {}

        if isinstance(raw_result, dict):
            success = bool(raw_result.get('success'))
            message = raw_result.get('message') or raw_result.get('reason') or raw_result.get('error')
            extra = {
                key: value
                for key, value in raw_result.items()
                if key not in {'success', 'message'}
            }
        elif isinstance(raw_result, (tuple, list)):
            success = bool(raw_result[0]) if raw_result else False
            if len(raw_result) > 1:
                message = raw_result[1]
            if len(raw_result) > 2 and isinstance(raw_result[2], dict):
                extra = raw_result[2]
        else:
            success = bool(raw_result)

        return success, message, extra

    async def _calculate_market_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """
        Calculate market beta using 90-day regression

        PHASE 3 FIX (2025-11-17): After calculating beta, update the snapshot
        created in Phase 3 with the beta values.
        """
        try:
            from app.calculations.market_beta import calculate_portfolio_market_beta

            result = await calculate_portfolio_market_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                persist=True,
                price_cache=self._price_cache  # Pass through cache for optimization
            )

            # PHASE 3 FIX: Update snapshot with calculated beta
            if result:
                await self._update_snapshot_beta(db, portfolio_id, calculation_date, result)

            return result.get('success', False) if result else False

        except Exception as e:
            logger.warning(f"Market beta calculation failed: {e}")
            return False

    async def _calculate_provider_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate provider beta (1-year) from company profiles with fallback to calculated beta"""
        try:
            from app.calculations.market_beta import calculate_portfolio_provider_beta
            from app.models.market_data import FactorExposure, FactorDefinition
            from sqlalchemy import select, and_
            from decimal import Decimal

            result = await calculate_portfolio_provider_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if result.get('success'):
                # Save as "Provider Beta (1Y)" factor exposure
                # Get or create factor definition
                factor_stmt = select(FactorDefinition).where(FactorDefinition.name == "Provider Beta (1Y)")
                factor_result = await db.execute(factor_stmt)
                provider_beta_factor = factor_result.scalar_one_or_none()

                if not provider_beta_factor:
                    # Create the factor definition if it doesn't exist
                    from uuid import uuid4
                    provider_beta_factor = FactorDefinition(
                        id=uuid4(),
                        name="Provider Beta (1Y)",
                        description="1-year market beta from data providers (yfinance) with fallback to calculated beta",
                        factor_type="style",
                        is_active=True,
                        display_order=0  # Show first, before 90-day beta
                    )
                    db.add(provider_beta_factor)
                    await db.flush()

                portfolio_beta = result.get('portfolio_beta', 0.0)

                # Calculate dollar exposure
                from app.models.users import Portfolio as PortfolioModel
                portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
                portfolio_result = await db.execute(portfolio_stmt)
                portfolio = portfolio_result.scalar_one_or_none()

                if portfolio and portfolio.equity_balance:
                    exposure_dollar = Decimal(str(portfolio_beta)) * Decimal(str(portfolio.equity_balance))
                else:
                    exposure_dollar = Decimal('0')

                # Create or update factor exposure
                exposure_stmt = select(FactorExposure).where(
                    and_(
                        FactorExposure.portfolio_id == portfolio_id,
                        FactorExposure.factor_id == provider_beta_factor.id,
                        FactorExposure.calculation_date == calculation_date
                    )
                )
                exposure_result = await db.execute(exposure_stmt)
                existing_exposure = exposure_result.scalar_one_or_none()

                if existing_exposure:
                    existing_exposure.exposure_value = Decimal(str(portfolio_beta))
                    existing_exposure.exposure_dollar = exposure_dollar
                    logger.debug(f"Updated Provider Beta (1Y) factor exposure: {portfolio_beta:.3f}")
                else:
                    from uuid import uuid4
                    new_exposure = FactorExposure(
                        id=uuid4(),
                        portfolio_id=portfolio_id,
                        factor_id=provider_beta_factor.id,
                        calculation_date=calculation_date,
                        exposure_value=Decimal(str(portfolio_beta)),
                        exposure_dollar=exposure_dollar
                    )
                    db.add(new_exposure)
                    logger.debug(f"Created Provider Beta (1Y) factor exposure: {portfolio_beta:.3f}")

                return True
            else:
                logger.warning(f"Provider beta calculation returned error: {result.get('error')}")
                return False

        except Exception as e:
            logger.warning(f"Provider beta calculation failed: {e}")
            return False

    async def _calculate_ir_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate interest rate beta using 90-day regression and persist as FactorExposure"""
        try:
            from app.calculations.interest_rate_beta import calculate_portfolio_ir_beta
            from app.models.market_data import FactorExposure, FactorDefinition
            from sqlalchemy import select, and_
            from decimal import Decimal

            result = await calculate_portfolio_ir_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                window_days=90,
                treasury_symbol='TLT',
                persist=True,
                price_cache=self._price_cache  # Pass through cache for optimization
            )

            if result.get('success'):
                # Save as "IR Beta" factor exposure
                # Get or create factor definition
                factor_stmt = select(FactorDefinition).where(FactorDefinition.name == "IR Beta")
                factor_result = await db.execute(factor_stmt)
                ir_beta_factor = factor_result.scalar_one_or_none()

                if not ir_beta_factor:
                    # Create the factor definition if it doesn't exist
                    from uuid import uuid4
                    ir_beta_factor = FactorDefinition(
                        id=uuid4(),
                        name="IR Beta",
                        description="Interest rate beta - sensitivity to bond market (TLT) movements",
                        factor_type="macro",
                        is_active=True,
                        display_order=2  # Show after Market Beta (90D)
                    )
                    db.add(ir_beta_factor)
                    await db.flush()

                portfolio_ir_beta = result.get('portfolio_ir_beta', 0.0)

                # Calculate dollar exposure
                from app.models.users import Portfolio as PortfolioModel
                portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
                portfolio_result = await db.execute(portfolio_stmt)
                portfolio = portfolio_result.scalar_one_or_none()

                if portfolio and portfolio.equity_balance:
                    exposure_dollar = Decimal(str(portfolio_ir_beta)) * Decimal(str(portfolio.equity_balance))
                else:
                    exposure_dollar = Decimal('0')

                # Create or update factor exposure
                exposure_stmt = select(FactorExposure).where(
                    and_(
                        FactorExposure.portfolio_id == portfolio_id,
                        FactorExposure.factor_id == ir_beta_factor.id,
                        FactorExposure.calculation_date == calculation_date
                    )
                )
                exposure_result = await db.execute(exposure_stmt)
                existing_exposure = exposure_result.scalar_one_or_none()

                if existing_exposure:
                    existing_exposure.exposure_value = Decimal(str(portfolio_ir_beta))
                    existing_exposure.exposure_dollar = exposure_dollar
                    logger.debug(f"Updated IR Beta factor exposure: {portfolio_ir_beta:.3f}")
                else:
                    from uuid import uuid4
                    new_exposure = FactorExposure(
                        id=uuid4(),
                        portfolio_id=portfolio_id,
                        factor_id=ir_beta_factor.id,
                        calculation_date=calculation_date,
                        exposure_value=Decimal(str(portfolio_ir_beta)),
                        exposure_dollar=exposure_dollar
                    )
                    db.add(new_exposure)
                    logger.debug(f"Created IR Beta factor exposure: {portfolio_ir_beta:.3f}")

                return True
            else:
                logger.warning(f"IR beta calculation returned error: {result.get('error')}")
                return False

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
                calculation_date=calculation_date,
                price_cache=self._price_cache  # Pass through cache for optimization
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
        logger.info(f"[SPREAD_FACTORS_DEBUG] CALLED for portfolio {portfolio_id} on {calculation_date}")
        try:
            from app.calculations.factors_spread import calculate_portfolio_spread_betas

            logger.info(f"[SPREAD_FACTORS_DEBUG] About to call calculate_portfolio_spread_betas")
            result = await calculate_portfolio_spread_betas(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                price_cache=self._price_cache  # Pass through cache for optimization
            )

            logger.info(f"[SPREAD_FACTORS_DEBUG] Result is None: {result is None}")
            if result:
                logger.info(f"[SPREAD_FACTORS_DEBUG] Result has position_betas: {len(result.get('position_betas', {}))}")
                logger.info(f"[SPREAD_FACTORS_DEBUG] Result success: {result.get('success', False)}")

            return result.get('success', False) if result else False

        except Exception as e:
            logger.error(f"[SPREAD_FACTORS_DEBUG] Exception: {e}")
            logger.warning(f"Spread factors calculation failed: {e}")
            import traceback
            logger.error(f"[SPREAD_FACTORS_DEBUG] Traceback: {traceback.format_exc()}")
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
                calculation_date=calculation_date,
                profile_cache=self._profile_cache,
            )

            return result.get('success', False) if result else False

        except Exception as e:
            logger.warning(f"Sector analysis calculation failed: {e}")
            return False

    async def _calculate_volatility_analytics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> Dict[str, Any]:
        """
        Calculate volatility metrics (21d, 63d, 252d)

        PHASE 3 FIX (2025-11-17): After calculating volatility, update the snapshot
        created in Phase 3 with the volatility values.
        """
        try:
            from app.calculations.volatility_analytics import calculate_portfolio_volatility_batch

            result = await calculate_portfolio_volatility_batch(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                price_cache=self._price_cache  # Pass through cache for optimization
            )

            # PHASE 3 FIX: Update snapshot with calculated volatility
            if result:
                await self._update_snapshot_volatility(db, portfolio_id, calculation_date, result)

            success = bool(result.get('success'))
            message = result.get('message')
            if not success and not message:
                failure_reasons = result.get('failure_reasons') or []
                if failure_reasons:
                    message = f"Failed for {len(failure_reasons)} positions (example reason: {failure_reasons[0].get('reason')})"
            return {
                'success': success,
                'message': message,
                'details': result,
            }

        except Exception as e:
            logger.warning(f"Volatility analytics calculation failed: {e}")
            return {
                'success': False,
                'message': str(e),
            }

    async def _calculate_correlations(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> bool:
        """Calculate position correlations"""
        try:
            from app.services.correlation_service import CorrelationService

            correlation_service = CorrelationService(db, price_cache=self._price_cache)

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

    async def _calculate_stress_testing(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date
    ) -> Dict[str, Any]:
        """Run comprehensive stress test and save results"""
        try:
            from app.calculations.stress_testing import (
                run_comprehensive_stress_test,
                save_stress_test_results
            )

            logger.info(f"Starting stress test for portfolio {portfolio_id} on {calculation_date}")

            # Run comprehensive stress test
            stress_results = await run_comprehensive_stress_test(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            # Check if results were returned
            if not stress_results:
                message = "Stress testing did not return any results."
                logger.warning(message)
                return {
                    'success': False,
                    'message': message,
                }

            # Check if stress test was skipped (happens for portfolios with no factor exposures)
            stress_test_data = stress_results.get('stress_test_results', {})
            if stress_test_data.get('skipped'):
                reason = stress_test_data.get('reason', 'unknown')
                info_message = f"Stress testing skipped: {reason}"
                logger.info(f"{info_message} for portfolio {portfolio_id}")
                return {
                    'success': True,
                    'message': info_message,
                    'skipped': True,
                    'details': stress_results,
                }

            # Check if any scenarios were tested
            scenarios_tested = stress_results.get('config_metadata', {}).get('scenarios_tested', 0)
            if scenarios_tested == 0:
                message = "Stress testing ran but produced zero scenarios."
                logger.warning(f"{message} for portfolio {portfolio_id}")
                return {
                    'success': False,
                    'message': message,
                    'details': stress_results,
                }

            logger.info(f"Stress test completed with {scenarios_tested} scenarios, saving results...")

            # Save results to database
            saved_count = await save_stress_test_results(
                db=db,
                portfolio_id=portfolio_id,
                stress_test_results=stress_results
            )

            logger.info(f"Saved {saved_count} stress test results to database")
            return {
                'success': saved_count > 0,
                'message': None if saved_count > 0 else "Stress results failed to persist.",
                'details': {
                    'scenarios_tested': scenarios_tested,
                    'saved_count': saved_count,
                },
            }

        except Exception as e:
            import traceback
            logger.error(f"Stress testing calculation failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'message': str(e),
            }

    async def _update_snapshot_beta(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
        beta_result: Dict[str, Any]
    ) -> None:
        """
        Update snapshot with market beta from Phase 6

        PHASE 3 FIX (2025-11-17): Phase 3 creates snapshots with NULL beta fields.
        Phase 6 calculates betas (after Phase 4 sets position.market_value) and
        updates existing snapshots with the calculated values.
        """
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select, and_
        from decimal import Decimal

        if not beta_result.get('success'):
            logger.debug(f"Beta calculation failed, skipping snapshot update")
            return

        try:
            # Query existing snapshot
            snapshot_stmt = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date == calculation_date
                )
            )
            result = await db.execute(snapshot_stmt)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                logger.warning(
                    f"No snapshot found for portfolio {portfolio_id} on {calculation_date}, "
                    f"cannot update beta"
                )
                return

            # Update beta fields from Phase 6 calculation
            portfolio_beta = beta_result.get('portfolio_beta')
            if portfolio_beta is not None:
                snapshot.beta_calculated_90d = Decimal(str(portfolio_beta))

            r_squared = beta_result.get('r_squared')
            if r_squared is not None:
                snapshot.beta_calculated_90d_r_squared = Decimal(str(r_squared))

            observations = beta_result.get('observations')
            if observations is not None:
                snapshot.beta_calculated_90d_observations = observations

            logger.info(
                f"Updated snapshot beta: β={float(snapshot.beta_calculated_90d):.3f}, "
                f"R²={float(snapshot.beta_calculated_90d_r_squared):.3f}, "
                f"obs={snapshot.beta_calculated_90d_observations}"
            )

        except Exception as e:
            logger.error(f"Error updating snapshot beta: {e}")

    async def _update_snapshot_volatility(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
        vol_result: Dict[str, Any]
    ) -> None:
        """
        Update snapshot with volatility from Phase 6

        PHASE 3 FIX (2025-11-17): Phase 3 creates snapshots with NULL volatility fields.
        Phase 6 calculates volatility (after Phase 4 sets position.market_value) and
        updates existing snapshots with the calculated values.
        """
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select, and_
        from decimal import Decimal

        if not vol_result.get('success'):
            logger.debug(f"Volatility calculation failed, skipping snapshot update")
            return

        portfolio_vol = vol_result.get('portfolio_volatility')
        if not portfolio_vol:
            logger.debug(f"No portfolio volatility data in result, skipping snapshot update")
            return

        try:
            # Query existing snapshot
            snapshot_stmt = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date == calculation_date
                )
            )
            result = await db.execute(snapshot_stmt)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                logger.warning(
                    f"No snapshot found for portfolio {portfolio_id} on {calculation_date}, "
                    f"cannot update volatility"
                )
                return

            # Update volatility fields from Phase 6 calculation
            vol_21d = portfolio_vol.get('realized_volatility_21d')
            if vol_21d is not None:
                snapshot.realized_volatility_21d = Decimal(str(vol_21d))

            vol_63d = portfolio_vol.get('realized_volatility_63d')
            if vol_63d is not None:
                snapshot.realized_volatility_63d = Decimal(str(vol_63d))

            expected_21d = portfolio_vol.get('expected_volatility_21d')
            if expected_21d is not None:
                snapshot.expected_volatility_21d = Decimal(str(expected_21d))

            trend = portfolio_vol.get('volatility_trend')
            if trend is not None:
                snapshot.volatility_trend = trend

            percentile = portfolio_vol.get('volatility_percentile')
            if percentile is not None:
                snapshot.volatility_percentile = Decimal(str(percentile))

            logger.info(
                f"Updated snapshot volatility: 21d={float(snapshot.realized_volatility_21d or 0):.2%}, "
                f"expected={float(snapshot.expected_volatility_21d or 0):.2%}, "
                f"trend={snapshot.volatility_trend}"
            )

        except Exception as e:
            logger.error(f"Error updating snapshot volatility: {e}")


# Global instance
analytics_runner = AnalyticsRunner()

