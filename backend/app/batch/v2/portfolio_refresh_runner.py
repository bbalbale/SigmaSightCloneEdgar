"""
V2 Portfolio Refresh Runner

Runs at 9:30 PM ET (30 minutes after symbol batch) to refresh all portfolios:
1. Wait for symbol batch completion
2. Wait for pending symbol onboarding
3. Initialize unified V2 cache (prices + factors)
4. Create snapshots for all portfolios using cached data (Phase 3)
5. Calculate position correlations for all portfolios (Phase 4)
6. Aggregate symbol factors to portfolio level (Phase 5)
7. Calculate stress tests for all portfolios (Phase 6)

Key Design Decisions:
- Runs AFTER symbol batch to leverage cached prices and factors
- Uses UNIFIED SymbolCacheService for both price and factor data (300x faster)
- Uses existing PnLCalculator for snapshot creation
- Phase 5 reads from symbol_factor_exposures (V2 batch) and writes to factor_exposures
- Phase 6 reads from factor_exposures for stress scenario calculations
- Writes to: PortfolioSnapshot, CorrelationCalculation, PairwiseCorrelation,
  FactorExposure, StressTestResult

Reference: PlanningDocs/V2BatchArchitecture/05-PORTFOLIO-REFRESH.md
"""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now
from app.core.trading_calendar import (
    get_most_recent_trading_day,
    get_most_recent_completed_trading_day,
    is_trading_day,
)
from app.database import get_async_session, AsyncSessionLocal
from app.models.admin import BatchRunHistory
from app.models.users import Portfolio
from app.batch.batch_run_tracker import (
    batch_run_tracker,
    BatchJobType,
    BatchJob,
)
from app.batch.pnl_calculator import pnl_calculator
from app.cache.symbol_cache import symbol_cache, SymbolCacheService

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

V2_LOG_PREFIX = "[V2_PORTFOLIO_REFRESH]"

# Maximum wait times
MAX_SYMBOL_BATCH_WAIT_SECONDS = 300  # 5 minutes
MAX_ONBOARDING_WAIT_SECONDS = 120  # 2 minutes

# Polling intervals
POLL_INTERVAL_SECONDS = 5


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class PortfolioRefreshResult:
    """Result of a portfolio refresh run."""
    success: bool
    target_date: date
    portfolios_processed: int = 0
    snapshots_created: int = 0
    correlations_calculated: int = 0
    stress_tests_calculated: int = 0
    errors: List[str] = None
    duration_seconds: float = 0.0
    waited_for_symbol_batch: bool = False
    waited_for_onboarding: bool = False
    phase_durations: Dict[str, float] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.phase_durations is None:
            self.phase_durations = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "target_date": self.target_date.isoformat(),
            "portfolios_processed": self.portfolios_processed,
            "snapshots_created": self.snapshots_created,
            "correlations_calculated": self.correlations_calculated,
            "stress_tests_calculated": self.stress_tests_calculated,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "waited_for_symbol_batch": self.waited_for_symbol_batch,
            "waited_for_onboarding": self.waited_for_onboarding,
            "phase_durations": self.phase_durations,
        }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def run_portfolio_refresh(
    target_date: Optional[date] = None,
    wait_for_symbol_batch: bool = True,
    wait_for_onboarding: bool = True,
) -> Dict[str, Any]:
    """
    Run portfolio refresh for all active portfolios.

    This is the main entry point for the V2 portfolio refresh cron job.

    Args:
        target_date: Date to refresh (defaults to most recent trading day)
        wait_for_symbol_batch: If True, wait for symbol batch to complete
        wait_for_onboarding: If True, wait for pending symbol onboarding

    Returns:
        Dict with refresh results
    """
    start_time = datetime.now()
    job_id = str(uuid4())

    # Determine target date (use completed trading day to respect market hours)
    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    logger.info(
        f"{V2_LOG_PREFIX} Starting portfolio refresh (job_id={job_id}, target={target_date})"
    )

    # Register job with tracker
    job = BatchJob(
        job_id=job_id,
        job_type=BatchJobType.PORTFOLIO_REFRESH,
        started_at=utc_now(),
        triggered_by="v2_cron",
        target_date=target_date.isoformat(),
    )

    if not batch_run_tracker.start_job_sync(job):
        logger.warning(f"{V2_LOG_PREFIX} Portfolio refresh already running, aborting")
        return {
            "success": False,
            "error": "portfolio_refresh_already_running",
            "message": "Another portfolio refresh is already in progress",
        }

    result = PortfolioRefreshResult(
        success=False,
        target_date=target_date,
    )

    try:
        import sys
        phase_durations = {}

        # Step 1: Wait for symbol batch (if enabled)
        if wait_for_symbol_batch:
            batch_complete = await _wait_for_symbol_batch(target_date)
            result.waited_for_symbol_batch = True

            if not batch_complete:
                logger.warning(
                    f"{V2_LOG_PREFIX} Symbol batch not complete after waiting, proceeding anyway"
                )

        # Step 2: Wait for onboarding (if enabled)
        if wait_for_onboarding:
            onboarding_complete = await _wait_for_onboarding()
            result.waited_for_onboarding = True

            if not onboarding_complete:
                logger.warning(
                    f"{V2_LOG_PREFIX} Symbol onboarding still pending, proceeding anyway"
                )

        # Step 3: Initialize unified V2 cache (prices + factors)
        unified_cache = await _initialize_unified_cache(target_date)

        # Phase 3: Create snapshots for all portfolios
        print(f"{V2_LOG_PREFIX} Phase 3: Creating portfolio snapshots...")
        sys.stdout.flush()
        phase_start = datetime.now()
        refresh_result = await _refresh_all_portfolios(target_date, unified_cache)
        phase_durations["phase_3_snapshots"] = (datetime.now() - phase_start).total_seconds()
        print(f"{V2_LOG_PREFIX} Phase 3 complete: {refresh_result.get('snapshots_created', 0)} snapshots in {phase_durations['phase_3_snapshots']:.1f}s")
        sys.stdout.flush()

        result.portfolios_processed = refresh_result.get("portfolios_processed", 0)
        result.snapshots_created = refresh_result.get("snapshots_created", 0)
        result.errors = refresh_result.get("errors", [])

        # Get portfolio IDs for Phase 4 and 5
        portfolio_ids = await _get_active_portfolio_ids()

        # Phase 4: Calculate correlations for all portfolios
        print(f"{V2_LOG_PREFIX} Phase 4: Calculating correlations for {len(portfolio_ids)} portfolios...")
        sys.stdout.flush()
        phase_start = datetime.now()
        correlation_result = await _run_correlations_for_all_portfolios(
            portfolio_ids, target_date, unified_cache
        )
        phase_durations["phase_4_correlations"] = (datetime.now() - phase_start).total_seconds()
        result.correlations_calculated = correlation_result.get("calculated", 0)
        print(f"{V2_LOG_PREFIX} Phase 4 complete: {result.correlations_calculated} correlations in {phase_durations['phase_4_correlations']:.1f}s")
        sys.stdout.flush()

        if correlation_result.get("errors"):
            result.errors.extend(correlation_result["errors"])

        # Phase 5: Aggregate symbol factors to portfolio level
        # This MUST happen before stress tests since they read from factor_exposures table
        print(f"{V2_LOG_PREFIX} Phase 5: Aggregating symbol factors to portfolio level...")
        sys.stdout.flush()
        phase_start = datetime.now()
        factor_agg_result = await _aggregate_portfolio_factors(
            portfolio_ids, target_date
        )
        phase_durations["phase_5_factor_aggregation"] = (datetime.now() - phase_start).total_seconds()
        print(f"{V2_LOG_PREFIX} Phase 5 complete: {factor_agg_result.get('calculated', 0)} portfolios in {phase_durations['phase_5_factor_aggregation']:.1f}s")
        sys.stdout.flush()

        if factor_agg_result.get("errors"):
            result.errors.extend(factor_agg_result["errors"])

        # Phase 6: Calculate stress tests for all portfolios
        print(f"{V2_LOG_PREFIX} Phase 6: Calculating stress tests for {len(portfolio_ids)} portfolios...")
        sys.stdout.flush()
        phase_start = datetime.now()
        stress_result = await _run_stress_tests_for_all_portfolios(
            portfolio_ids, target_date
        )
        phase_durations["phase_6_stress_tests"] = (datetime.now() - phase_start).total_seconds()
        result.stress_tests_calculated = stress_result.get("calculated", 0)
        print(f"{V2_LOG_PREFIX} Phase 6 complete: {result.stress_tests_calculated} stress tests in {phase_durations['phase_6_stress_tests']:.1f}s")
        sys.stdout.flush()

        if stress_result.get("errors"):
            result.errors.extend(stress_result["errors"])

        # Finalize results
        result.phase_durations = phase_durations
        result.success = refresh_result.get("success", False)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        # Step 6: Record completion
        await _record_portfolio_refresh_completion(target_date, result, job_id)

        # Mark job complete
        status = "completed" if result.success else "failed"
        batch_run_tracker.complete_job_sync(BatchJobType.PORTFOLIO_REFRESH, status)

        logger.info(
            f"{V2_LOG_PREFIX} Portfolio refresh complete: "
            f"portfolios={result.portfolios_processed}, snapshots={result.snapshots_created}, "
            f"duration={result.duration_seconds:.1f}s"
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Portfolio refresh failed: {e}", exc_info=True)
        batch_run_tracker.complete_job_sync(
            BatchJobType.PORTFOLIO_REFRESH,
            status="failed",
            error_message=str(e)
        )
        return {
            "success": False,
            "error": "portfolio_refresh_exception",
            "message": str(e),
        }


# =============================================================================
# WAIT FUNCTIONS
# =============================================================================

async def _wait_for_symbol_batch(target_date: date) -> bool:
    """
    Wait for symbol batch to complete for target date.

    Polls BatchRunHistory for a completed symbol batch job.

    Args:
        target_date: Date to check for

    Returns:
        True if symbol batch is complete, False if timed out
    """
    logger.info(f"{V2_LOG_PREFIX} Waiting for symbol batch completion...")

    start_time = datetime.now()
    max_wait = timedelta(seconds=MAX_SYMBOL_BATCH_WAIT_SECONDS)

    while datetime.now() - start_time < max_wait:
        # Check if symbol batch is complete
        if await _is_symbol_batch_complete(target_date):
            logger.info(f"{V2_LOG_PREFIX} Symbol batch complete, proceeding")
            return True

        # Wait before polling again
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    logger.warning(
        f"{V2_LOG_PREFIX} Symbol batch wait timed out after {MAX_SYMBOL_BATCH_WAIT_SECONDS}s"
    )
    return False


async def _is_symbol_batch_complete(target_date: date) -> bool:
    """Check if symbol batch has completed for target date."""
    async with get_async_session() as db:
        result = await db.execute(
            select(BatchRunHistory)
            .where(
                and_(
                    BatchRunHistory.status == "completed",
                    BatchRunHistory.triggered_by == "v2_cron",
                )
            )
            .order_by(desc(BatchRunHistory.completed_at))
            .limit(1)
        )
        last_run = result.scalar_one_or_none()

        if last_run:
            # Check if completed today
            if last_run.completed_at and last_run.completed_at.date() == target_date:
                return True

            # Check error_summary for calc_date match
            error_summary = last_run.error_summary or {}
            calc_date_str = error_summary.get("calc_date")
            if calc_date_str == target_date.isoformat():
                return True

    return False


async def _wait_for_onboarding() -> bool:
    """
    Wait for pending symbol onboarding jobs to complete.

    Checks the in-memory onboarding queue.

    Returns:
        True if no pending jobs, False if timed out
    """
    logger.info(f"{V2_LOG_PREFIX} Waiting for symbol onboarding completion...")

    start_time = datetime.now()
    max_wait = timedelta(seconds=MAX_ONBOARDING_WAIT_SECONDS)

    while datetime.now() - start_time < max_wait:
        # Check if onboarding queue is empty
        # Note: In-memory queue is implemented in Step 9
        # For now, assume no pending jobs
        pending_count = 0  # TODO: Get from onboarding_queue.get_pending_count()

        if pending_count == 0:
            logger.info(f"{V2_LOG_PREFIX} No pending onboarding jobs, proceeding")
            return True

        logger.debug(f"{V2_LOG_PREFIX} {pending_count} onboarding jobs pending, waiting...")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    logger.warning(
        f"{V2_LOG_PREFIX} Onboarding wait timed out after {MAX_ONBOARDING_WAIT_SECONDS}s"
    )
    return False


# =============================================================================
# UNIFIED SYMBOL CACHE (V2)
# =============================================================================

async def _initialize_unified_cache(target_date: date) -> SymbolCacheService:
    """
    Initialize the unified V2 symbol cache with both prices and factors.

    The V2 cache (SymbolCacheService) provides:
    - _price_cache: 300x faster price lookups vs DB queries
    - _factor_cache: In-memory factor data for fast aggregation
    - DB fallback if cache miss

    Args:
        target_date: Date to load data for

    Returns:
        Initialized SymbolCacheService (same global instance)
    """
    logger.info(f"{V2_LOG_PREFIX} Initializing unified symbol cache for {target_date}")

    # Initialize the global symbol_cache if not already done
    if not symbol_cache._initialized:
        await symbol_cache.initialize_async(target_date)

    # Get health status for logging
    health = symbol_cache.get_health_status()
    logger.info(
        f"{V2_LOG_PREFIX} Unified cache status: "
        f"symbols={health.get('symbols_cached', 0)}, "
        f"dates={health.get('dates_cached', 0)}, "
        f"factors={health.get('factor_cache_entries', 0)}"
    )

    return symbol_cache


# =============================================================================
# PORTFOLIO PROCESSING
# =============================================================================

async def _refresh_all_portfolios(
    target_date: date,
    unified_cache: SymbolCacheService,
) -> Dict[str, Any]:
    """
    Refresh all active portfolios using existing PnLCalculator.

    Args:
        target_date: Date to refresh
        unified_cache: V2 unified cache (SymbolCacheService) with prices and factors

    Returns:
        Dict with processing results
    """
    logger.info(f"{V2_LOG_PREFIX} Refreshing all portfolios for {target_date}")

    # Use existing PnLCalculator with the price cache component from unified cache
    result = await pnl_calculator.calculate_all_portfolios_pnl(
        calculation_date=target_date,
        db=None,  # Let it create its own session
        portfolio_ids=None,  # Process all portfolios
        price_cache=unified_cache._price_cache,  # Use price cache from unified V2 cache
    )

    return result


async def _get_active_portfolio_ids() -> List[UUID]:
    """
    Get all active (non-deleted) portfolio IDs.

    Returns:
        List of portfolio UUIDs
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio.id).where(Portfolio.deleted_at.is_(None))
        )
        return [row[0] for row in result.fetchall()]


# =============================================================================
# PHASE 4: CORRELATIONS
# =============================================================================

async def _aggregate_portfolio_factors(
    portfolio_ids: List[UUID],
    target_date: date,
) -> Dict[str, Any]:
    """
    Phase 5: Aggregate symbol-level factors to portfolio-level.

    Uses pre-computed symbol factors from symbol_factor_exposures table
    (populated by V2 symbol batch Phase 3) and aggregates them by position
    weight to create portfolio-level factor exposures.

    This MUST run before stress tests, which read from factor_exposures table.

    Args:
        portfolio_ids: List of portfolio IDs to process
        target_date: Calculation date

    Returns:
        Dict with aggregation results
    """
    from app.services.portfolio_factor_service import (
        get_portfolio_factor_exposures,
        store_portfolio_factor_exposures
    )

    logger.info(f"{V2_LOG_PREFIX} Phase 5: Factor aggregation for {len(portfolio_ids)} portfolios")

    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for i, portfolio_id in enumerate(portfolio_ids, 1):
        try:
            async with get_async_session() as db:
                # Get Ridge factors (aggregated from symbol-level)
                ridge_result = await get_portfolio_factor_exposures(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=target_date,
                    use_delta_adjusted=False,
                    include_ridge=True,
                    include_spread=False
                )

                ridge_betas = ridge_result.get('ridge_betas', {})
                metadata = ridge_result.get('metadata', {})
                portfolio_equity = metadata.get('portfolio_equity', 0.0)

                if ridge_betas:
                    await store_portfolio_factor_exposures(
                        db=db,
                        portfolio_id=portfolio_id,
                        portfolio_betas=ridge_betas,
                        calculation_date=target_date,
                        portfolio_equity=portfolio_equity
                    )

                # Get Spread factors (aggregated from symbol-level)
                spread_result = await get_portfolio_factor_exposures(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=target_date,
                    use_delta_adjusted=False,
                    include_ridge=False,
                    include_spread=True
                )

                spread_betas = spread_result.get('spread_betas', {})

                if spread_betas:
                    await store_portfolio_factor_exposures(
                        db=db,
                        portfolio_id=portfolio_id,
                        portfolio_betas=spread_betas,
                        calculation_date=target_date,
                        portfolio_equity=portfolio_equity
                    )

                if ridge_betas or spread_betas:
                    calculated += 1
                else:
                    skipped += 1
                    logger.debug(f"{V2_LOG_PREFIX} No factors for portfolio {portfolio_id}")

            if i % 10 == 0 or i == len(portfolio_ids):
                logger.info(f"{V2_LOG_PREFIX} Phase 5 progress: {i}/{len(portfolio_ids)}")

        except Exception as e:
            failed += 1
            error_msg = f"Factor aggregation failed for {portfolio_id}: {str(e)[:100]}"
            errors.append(error_msg)
            logger.warning(f"{V2_LOG_PREFIX} {error_msg}")

    logger.info(
        f"{V2_LOG_PREFIX} Phase 5 complete: calculated={calculated}, skipped={skipped}, failed={failed}"
    )

    return {
        "calculated": calculated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }




async def _run_correlations_for_all_portfolios(
    portfolio_ids: List[UUID],
    target_date: date,
    unified_cache: SymbolCacheService,
) -> Dict[str, Any]:
    """
    Phase 4: Calculate position correlations for all portfolios.

    Uses CorrelationService.calculate_portfolio_correlations() which:
    - Calculates pairwise correlations between positions
    - Stores results in CorrelationCalculation and PairwiseCorrelation tables
    - Gracefully skips portfolios with < 2 public positions

    Args:
        portfolio_ids: List of portfolio IDs to process
        target_date: Calculation date
        unified_cache: V2 unified cache (SymbolCacheService) with prices and factors

    Returns:
        Dict with calculation results
    """
    from app.services.correlation_service import CorrelationService

    logger.info(f"{V2_LOG_PREFIX} Phase 4: Correlations for {len(portfolio_ids)} portfolios")

    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for i, portfolio_id in enumerate(portfolio_ids, 1):
        try:
            async with get_async_session() as db:
                # Use price cache from unified V2 cache
                correlation_service = CorrelationService(db, price_cache=unified_cache._price_cache)

                result = await correlation_service.calculate_portfolio_correlations(
                    portfolio_id=portfolio_id,
                    calculation_date=target_date
                )

                # CorrelationService returns None if no public positions (graceful skip)
                if result is None:
                    skipped += 1
                    logger.debug(f"{V2_LOG_PREFIX} Correlations skipped for portfolio {portfolio_id} (no public positions)")
                else:
                    calculated += 1

            if i % 10 == 0 or i == len(portfolio_ids):
                logger.info(f"{V2_LOG_PREFIX} Phase 4 progress: {i}/{len(portfolio_ids)}")

        except Exception as e:
            failed += 1
            error_msg = f"Correlation failed for {portfolio_id}: {str(e)[:100]}"
            errors.append(error_msg)
            logger.warning(f"{V2_LOG_PREFIX} {error_msg}")

    logger.info(
        f"{V2_LOG_PREFIX} Phase 4 complete: calculated={calculated}, skipped={skipped}, failed={failed}"
    )

    return {
        "calculated": calculated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }


# =============================================================================
# PHASE 5: STRESS TESTS
# =============================================================================

async def _run_stress_tests_for_all_portfolios(
    portfolio_ids: List[UUID],
    target_date: date,
) -> Dict[str, Any]:
    """
    Phase 5: Calculate stress tests for all portfolios.

    Uses run_comprehensive_stress_test() and save_stress_test_results() which:
    - Runs 10+ stress scenarios (market crash, interest rate shock, etc.)
    - Uses factor correlations for impact calculation
    - Stores results in StressTestResult table

    Args:
        portfolio_ids: List of portfolio IDs to process
        target_date: Calculation date

    Returns:
        Dict with calculation results
    """
    from app.calculations.stress_testing import (
        run_comprehensive_stress_test,
        save_stress_test_results
    )

    logger.info(f"{V2_LOG_PREFIX} Phase 5: Stress tests for {len(portfolio_ids)} portfolios")

    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for i, portfolio_id in enumerate(portfolio_ids, 1):
        try:
            async with get_async_session() as db:
                # Run comprehensive stress test
                stress_results = await run_comprehensive_stress_test(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=target_date
                )

                # Check if results were returned
                if not stress_results:
                    skipped += 1
                    logger.debug(f"{V2_LOG_PREFIX} Stress test skipped for portfolio {portfolio_id} (no results)")
                    continue

                # Check if stress test was skipped (happens for portfolios with no factor exposures)
                stress_test_data = stress_results.get('stress_test_results', {})
                if stress_test_data.get('skipped'):
                    skipped += 1
                    reason = stress_test_data.get('reason', 'unknown')
                    logger.debug(f"{V2_LOG_PREFIX} Stress test skipped for portfolio {portfolio_id}: {reason}")
                    continue

                # Save results to database
                scenarios_tested = stress_results.get('config_metadata', {}).get('scenarios_tested', 0)
                if scenarios_tested > 0:
                    saved_count = await save_stress_test_results(
                        db=db,
                        portfolio_id=portfolio_id,
                        stress_test_results=stress_results
                    )
                    if saved_count > 0:
                        calculated += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1

            if i % 10 == 0 or i == len(portfolio_ids):
                logger.info(f"{V2_LOG_PREFIX} Phase 5 progress: {i}/{len(portfolio_ids)}")

        except Exception as e:
            failed += 1
            error_msg = f"Stress test failed for {portfolio_id}: {str(e)[:100]}"
            errors.append(error_msg)
            logger.warning(f"{V2_LOG_PREFIX} {error_msg}")

    logger.info(
        f"{V2_LOG_PREFIX} Phase 5 complete: calculated={calculated}, skipped={skipped}, failed={failed}"
    )

    return {
        "calculated": calculated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }


# =============================================================================
# TRACKING
# =============================================================================

async def _record_portfolio_refresh_completion(
    target_date: date,
    result: PortfolioRefreshResult,
    job_id: str,
) -> None:
    """
    Record portfolio refresh completion to BatchRunHistory.

    Args:
        target_date: Date that was processed
        result: PortfolioRefreshResult with details
        job_id: Job ID for correlation
    """
    async with get_async_session() as db:
        history = BatchRunHistory(
            batch_run_id=job_id,
            triggered_by="v2_cron_portfolio",
            started_at=utc_now() - timedelta(seconds=result.duration_seconds),
            completed_at=utc_now(),
            status="completed" if result.success else "failed",
            total_jobs=result.portfolios_processed,
            completed_jobs=result.snapshots_created,
            failed_jobs=len(result.errors),
            phase_durations={
                "portfolio_refresh": result.duration_seconds,
            },
            error_summary={
                "batch_type": "portfolio_refresh",
                "calc_date": target_date.isoformat(),
                "errors": result.errors,
            } if result.errors else {
                "batch_type": "portfolio_refresh",
                "calc_date": target_date.isoformat(),
            },
        )
        db.add(history)
        await db.commit()

    logger.info(f"{V2_LOG_PREFIX} Recorded completion for {target_date} (job_id={job_id})")


# =============================================================================
# UTILITIES
# =============================================================================

async def get_last_portfolio_refresh_date() -> Optional[date]:
    """
    Get the most recent successful portfolio refresh date.

    Returns:
        Date of last successful portfolio refresh, or None if never run
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(BatchRunHistory)
            .where(
                and_(
                    BatchRunHistory.status == "completed",
                    BatchRunHistory.triggered_by == "v2_cron_portfolio",
                )
            )
            .order_by(desc(BatchRunHistory.completed_at))
            .limit(1)
        )
        last_run = result.scalar_one_or_none()

        if last_run and last_run.completed_at:
            return last_run.completed_at.date()

    return None
