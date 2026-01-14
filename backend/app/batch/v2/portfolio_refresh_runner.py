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
    get_trading_days_between,
)
from app.database import get_async_session
from app.models.admin import BatchRunHistory
from app.models.users import Portfolio
from app.batch.batch_run_tracker import (
    batch_run_tracker,
    BatchJobType,
    BatchJob,
)
from app.batch.pnl_calculator import pnl_calculator

# =============================================================================
# CONCURRENCY CONFIGURATION
# =============================================================================
# Maximum number of portfolios to process in parallel
# Railway tested with 3 processes × 10 concurrent API calls = 30 total
# Conservative default for database operations
MAX_PORTFOLIO_CONCURRENCY = 10
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

# Maximum dates to backfill in one run (safety limit)
MAX_BACKFILL_DATES = 30


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


@dataclass
class BackfillResult:
    """Result of a multi-date backfill run."""
    success: bool
    dates_processed: int = 0
    dates_failed: int = 0
    total_snapshots_created: int = 0
    total_duration_seconds: float = 0.0
    per_date_results: List[Dict[str, Any]] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.per_date_results is None:
            self.per_date_results = []
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dates_processed": self.dates_processed,
            "dates_failed": self.dates_failed,
            "total_snapshots_created": self.total_snapshots_created,
            "total_duration_seconds": self.total_duration_seconds,
            "per_date_results": self.per_date_results,
            "errors": self.errors,
        }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def run_portfolio_refresh(
    target_date: Optional[date] = None,
    wait_for_symbol_batch: bool = True,
    wait_for_onboarding: bool = True,
    backfill: bool = True,
) -> Dict[str, Any]:
    """
    Run portfolio refresh for all active portfolios with optional backfill.

    This is the main entry point for the V2 portfolio refresh cron job.

    Args:
        target_date: Date to refresh (defaults to most recent trading day)
        wait_for_symbol_batch: If True, wait for symbol batch to complete
        wait_for_onboarding: If True, wait for pending symbol onboarding
        backfill: If True, find and process all missed dates since last run

    Returns:
        Dict with refresh results

    Examples:
        # Normal cron run (backfills if needed)
        result = await run_portfolio_refresh()

        # Single date run (no backfill)
        result = await run_portfolio_refresh(date(2026, 1, 10), backfill=False)
    """
    import sys
    start_time = datetime.now()
    job_id = str(uuid4())

    # Determine target date (use completed trading day to respect market hours)
    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    print(f"{V2_LOG_PREFIX} Starting portfolio refresh (job_id={job_id[:8]}, target={target_date}, backfill={backfill})")
    sys.stdout.flush()
    logger.info(
        f"{V2_LOG_PREFIX} Starting portfolio refresh (job_id={job_id}, target={target_date}, backfill={backfill})"
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

    try:
        # Backfill mode: process all missing dates
        if backfill:
            print(f"{V2_LOG_PREFIX} Running with backfill...")
            sys.stdout.flush()
            result = await _run_with_backfill(target_date, job_id, wait_for_symbol_batch, wait_for_onboarding)

            # Mark job complete
            status = "completed" if result.success else "failed"
            batch_run_tracker.complete_job_sync(BatchJobType.PORTFOLIO_REFRESH, status)

            return result.to_dict()

        # Single date mode: process only target_date
        single_result = await _run_portfolio_refresh_for_date(
            target_date, wait_for_symbol_batch, wait_for_onboarding
        )
        await _record_portfolio_refresh_completion(target_date, single_result, job_id)

        # Mark job complete
        status = "completed" if single_result.success else "failed"
        batch_run_tracker.complete_job_sync(BatchJobType.PORTFOLIO_REFRESH, status)

        return single_result.to_dict()

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


async def _run_with_backfill(
    target_date: date,
    job_id: str,
    wait_for_symbol_batch: bool,
    wait_for_onboarding: bool,
) -> BackfillResult:
    """
    Run portfolio refresh using DATA-DRIVEN approach.

    Instead of checking batch_run_history, we check actual data:
    - Which portfolios are missing snapshots for target_date?
    - If none missing, we're caught up
    - If some missing, process them

    This is more resilient than date-based backfill because:
    - Self-healing: If a batch fails halfway, next run catches what's missing
    - Timezone-proof: No UTC vs ET confusion
    - More accurate: Checks actual data, not batch history records

    Args:
        target_date: Date to check and process
        job_id: Job ID for tracking
        wait_for_symbol_batch: Whether to wait for symbol batch
        wait_for_onboarding: Whether to wait for onboarding

    Returns:
        BackfillResult with processing results
    """
    import sys
    from app.batch.v2.data_checks import get_portfolios_missing_snapshots

    start_time = datetime.now()

    print(f"{V2_LOG_PREFIX} DATA-DRIVEN CHECK: Checking if portfolios have snapshots for {target_date}...")
    sys.stdout.flush()

    # Check actual data - which portfolios are missing snapshots?
    portfolios_missing, all_portfolios = await get_portfolios_missing_snapshots(target_date)

    if not portfolios_missing:
        print(f"{V2_LOG_PREFIX} All {len(all_portfolios)} portfolios have snapshots for {target_date} - nothing to do")
        sys.stdout.flush()
        logger.info(f"{V2_LOG_PREFIX} All portfolios have snapshots for {target_date}, skipping")
        return BackfillResult(
            success=True,
            dates_processed=0,
            dates_failed=0,
            total_duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    # Some portfolios are missing snapshots - need to process
    print(f"{V2_LOG_PREFIX} {len(portfolios_missing)}/{len(all_portfolios)} portfolios missing snapshots for {target_date}")
    sys.stdout.flush()
    logger.info(
        f"{V2_LOG_PREFIX} {len(portfolios_missing)} portfolios missing snapshots for {target_date}, processing..."
    )

    # Process the target date (this will create snapshots for all portfolios)
    # TODO: Future optimization - only process missing portfolios
    results = []
    dates_failed = 0
    total_snapshots = 0

    try:
        print(f"{V2_LOG_PREFIX} Processing {target_date}...")
        sys.stdout.flush()

        result = await _run_portfolio_refresh_for_date(
            target_date,
            wait_for_symbol_batch,
            wait_for_onboarding
        )
        results.append(result.to_dict())

        # Record completion for this date
        await _record_portfolio_refresh_completion(target_date, result, job_id)

        if result.success:
            total_snapshots += result.snapshots_created
        else:
            dates_failed += 1

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Failed to process {target_date}: {e}", exc_info=True)
        dates_failed += 1
        results.append({
            "success": False,
            "target_date": target_date.isoformat(),
            "error": str(e),
        })

    total_duration = (datetime.now() - start_time).total_seconds()

    return BackfillResult(
        success=dates_failed == 0,
        dates_processed=1 if dates_failed == 0 else 0,
        dates_failed=dates_failed,
        total_snapshots_created=total_snapshots,
        total_duration_seconds=total_duration,
        per_date_results=results,
    )


async def _run_portfolio_refresh_for_date(
    target_date: date,
    wait_for_symbol_batch: bool = False,
    wait_for_onboarding: bool = False,
) -> PortfolioRefreshResult:
    """
    Run portfolio refresh for a single date.

    This is the core logic extracted for use by both single-date and backfill modes.

    Args:
        target_date: Date to process
        wait_for_symbol_batch: Whether to wait for symbol batch
        wait_for_onboarding: Whether to wait for onboarding

    Returns:
        PortfolioRefreshResult for this date
    """
    import sys

    result = PortfolioRefreshResult(
        success=False,
        target_date=target_date,
    )

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

    start_time = datetime.now()

    # Phase 3: Create snapshots and populate risk analytics
    # Step 1: Create base snapshots with P&L data
    print(f"{V2_LOG_PREFIX} Phase 3: Creating portfolio snapshots...")
    sys.stdout.flush()
    phase_start = datetime.now()
    refresh_result = await _refresh_all_portfolios(target_date, unified_cache)

    result.portfolios_processed = refresh_result.get("portfolios_processed", 0)
    result.snapshots_created = refresh_result.get("snapshots_created", 0)
    result.errors = refresh_result.get("errors", [])

    # Get portfolio IDs for analytics
    portfolio_ids = await _get_active_portfolio_ids()

    # Step 2: Update snapshots with risk analytics (beta, volatility, concentration)
    print(f"{V2_LOG_PREFIX} Phase 3: Updating snapshots with risk analytics...")
    sys.stdout.flush()
    analytics_result = await _run_snapshot_analytics(
        portfolio_ids, target_date, unified_cache
    )

    phase_durations["phase_3_snapshots"] = (datetime.now() - phase_start).total_seconds()
    snapshots_updated = analytics_result.get('updated', 0)
    print(f"{V2_LOG_PREFIX} Phase 3 complete: {result.snapshots_created} snapshots, {snapshots_updated} with analytics in {phase_durations['phase_3_snapshots']:.1f}s")
    sys.stdout.flush()

    if analytics_result.get("errors"):
        result.errors.extend(analytics_result["errors"])

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

    logger.info(
        f"{V2_LOG_PREFIX} Portfolio refresh for {target_date} complete: "
        f"portfolios={result.portfolios_processed}, snapshots={result.snapshots_created}, "
        f"duration={result.duration_seconds:.1f}s"
    )

    return result


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

async def _process_single_portfolio_factors(
    portfolio_id: UUID,
    target_date: date,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Process factor aggregation for a single portfolio (helper for parallel execution)."""
    from app.services.portfolio_factor_service import (
        get_portfolio_factor_exposures,
        store_portfolio_factor_exposures
    )

    async with semaphore:
        try:
            async with get_async_session() as db:
                # Get Ridge factors (aggregated from symbol-level)
                ridge_result = await get_portfolio_factor_exposures(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=target_date,
                    use_delta_adjusted=False,
                    include_ridge=True,
                    include_spread=False,
                    include_ols=False
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
                    include_spread=True,
                    include_ols=False
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

                # Get OLS factors (Market Beta 90D, IR Beta, Provider Beta 1Y)
                ols_result = await get_portfolio_factor_exposures(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=target_date,
                    use_delta_adjusted=False,
                    include_ridge=False,
                    include_spread=False,
                    include_ols=True
                )

                ols_betas = ols_result.get('ols_betas', {})

                if ols_betas:
                    await store_portfolio_factor_exposures(
                        db=db,
                        portfolio_id=portfolio_id,
                        portfolio_betas=ols_betas,
                        calculation_date=target_date,
                        portfolio_equity=portfolio_equity
                    )

                # CRITICAL: Commit the transaction (store_portfolio_factor_exposures doesn't commit)
                if ridge_betas or spread_betas or ols_betas:
                    await db.commit()
                    return {"status": "calculated", "portfolio_id": portfolio_id}
                else:
                    return {"status": "skipped", "portfolio_id": portfolio_id}

        except Exception as e:
            return {
                "status": "failed",
                "portfolio_id": portfolio_id,
                "error": f"Factor aggregation failed for {portfolio_id}: {str(e)[:100]}"
            }


async def _aggregate_portfolio_factors(
    portfolio_ids: List[UUID],
    target_date: date,
) -> Dict[str, Any]:
    """
    Phase 5: Aggregate symbol-level factors to portfolio-level - PARALLEL.

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
    logger.info(f"{V2_LOG_PREFIX} Phase 5: Factor aggregation for {len(portfolio_ids)} portfolios (parallel, max {MAX_PORTFOLIO_CONCURRENCY})")

    # Use semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(MAX_PORTFOLIO_CONCURRENCY)

    # Create tasks for all portfolios
    tasks = [
        _process_single_portfolio_factors(pid, target_date, semaphore)
        for pid in portfolio_ids
    ]

    # Run all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result)[:100])
        elif result.get("status") == "calculated":
            calculated += 1
        elif result.get("status") == "skipped":
            skipped += 1
        elif result.get("status") == "failed":
            failed += 1
            if result.get("error"):
                errors.append(result["error"])

    logger.info(
        f"{V2_LOG_PREFIX} Phase 5 complete: calculated={calculated}, skipped={skipped}, failed={failed}"
    )

    return {
        "calculated": calculated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }




async def _process_single_portfolio_correlations(
    portfolio_id: UUID,
    target_date: date,
    unified_cache: SymbolCacheService,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Process correlations for a single portfolio (helper for parallel execution)."""
    from app.services.correlation_service import CorrelationService

    async with semaphore:
        try:
            async with get_async_session() as db:
                correlation_service = CorrelationService(db, price_cache=unified_cache._price_cache)
                result = await correlation_service.calculate_portfolio_correlations(
                    portfolio_id=portfolio_id,
                    calculation_date=target_date
                )

                if result is None:
                    return {"status": "skipped", "portfolio_id": portfolio_id}
                else:
                    await db.commit()
                    return {"status": "calculated", "portfolio_id": portfolio_id}

        except Exception as e:
            return {
                "status": "failed",
                "portfolio_id": portfolio_id,
                "error": f"Correlation failed for {portfolio_id}: {str(e)[:100]}"
            }


async def _run_correlations_for_all_portfolios(
    portfolio_ids: List[UUID],
    target_date: date,
    unified_cache: SymbolCacheService,
) -> Dict[str, Any]:
    """
    Phase 4: Calculate position correlations for all portfolios - PARALLEL.

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
    logger.info(f"{V2_LOG_PREFIX} Phase 4: Correlations for {len(portfolio_ids)} portfolios (parallel, max {MAX_PORTFOLIO_CONCURRENCY})")

    # Use semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(MAX_PORTFOLIO_CONCURRENCY)

    # Create tasks for all portfolios
    tasks = [
        _process_single_portfolio_correlations(pid, target_date, unified_cache, semaphore)
        for pid in portfolio_ids
    ]

    # Run all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result)[:100])
        elif result.get("status") == "calculated":
            calculated += 1
        elif result.get("status") == "skipped":
            skipped += 1
        elif result.get("status") == "failed":
            failed += 1
            if result.get("error"):
                errors.append(result["error"])

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
# PHASE 3 HELPER: SNAPSHOT ANALYTICS (BETA, VOLATILITY, CONCENTRATION)
# =============================================================================

async def _process_single_portfolio_analytics(
    portfolio_id: UUID,
    target_date: date,
    unified_cache: SymbolCacheService,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Process analytics for a single portfolio (helper for parallel execution)."""
    from app.calculations.market_beta import (
        calculate_portfolio_market_beta,
        calculate_portfolio_provider_beta,
    )
    from app.calculations.volatility_analytics import calculate_portfolio_volatility_batch
    from app.calculations.sector_analysis import calculate_concentration_metrics
    from app.models.snapshots import PortfolioSnapshot
    from sqlalchemy import select, and_
    from decimal import Decimal

    async with semaphore:
        try:
            async with get_async_session() as db:
                # Get existing snapshot for this date
                snapshot_stmt = select(PortfolioSnapshot).where(
                    and_(
                        PortfolioSnapshot.portfolio_id == portfolio_id,
                        PortfolioSnapshot.snapshot_date == target_date
                    )
                )
                result = await db.execute(snapshot_stmt)
                snapshot = result.scalar_one_or_none()

                if not snapshot:
                    return {"status": "skipped", "portfolio_id": portfolio_id}

                updates_made = False

                # 1. Calculate Market Beta (90D)
                try:
                    beta_result = await calculate_portfolio_market_beta(
                        db=db,
                        portfolio_id=portfolio_id,
                        calculation_date=target_date,
                        persist=False,
                        price_cache=unified_cache._price_cache
                    )

                    if beta_result and beta_result.get('success'):
                        portfolio_beta = beta_result.get('portfolio_beta') or beta_result.get('market_beta')
                        if portfolio_beta is not None:
                            snapshot.beta_calculated_90d = Decimal(str(portfolio_beta))
                            updates_made = True

                        r_squared = beta_result.get('r_squared')
                        if r_squared is not None:
                            snapshot.beta_calculated_90d_r_squared = Decimal(str(r_squared))

                        observations = beta_result.get('observations')
                        if observations is not None:
                            snapshot.beta_calculated_90d_observations = observations

                except Exception as e:
                    logger.warning(f"Market beta failed for {portfolio_id}: {e}")

                # 2. Calculate Provider Beta (1Y)
                try:
                    provider_result = await calculate_portfolio_provider_beta(
                        db=db,
                        portfolio_id=portfolio_id,
                        calculation_date=target_date
                    )

                    if provider_result and provider_result.get('success'):
                        provider_beta = provider_result.get('portfolio_beta')
                        if provider_beta is not None:
                            snapshot.beta_provider_1y = Decimal(str(provider_beta))
                            updates_made = True

                except Exception as e:
                    logger.warning(f"Provider beta failed for {portfolio_id}: {e}")

                # 3. Calculate Volatility
                try:
                    vol_result = await calculate_portfolio_volatility_batch(
                        db=db,
                        portfolio_id=portfolio_id,
                        calculation_date=target_date,
                        price_cache=unified_cache._price_cache
                    )

                    if vol_result and vol_result.get('success'):
                        portfolio_vol = vol_result.get('portfolio_volatility', {})

                        vol_21d = portfolio_vol.get('realized_volatility_21d')
                        if vol_21d is not None:
                            snapshot.realized_volatility_21d = Decimal(str(vol_21d))
                            updates_made = True

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

                except Exception as e:
                    logger.warning(f"Volatility failed for {portfolio_id}: {e}")

                # 4. Calculate Concentration Metrics (if not already set)
                if snapshot.hhi is None:
                    try:
                        conc_result = await calculate_concentration_metrics(
                            db=db,
                            portfolio_id=portfolio_id
                        )

                        if conc_result and conc_result.get('success'):
                            hhi = conc_result.get('hhi')
                            if hhi is not None:
                                snapshot.hhi = Decimal(str(hhi))
                                updates_made = True

                            eff_num = conc_result.get('effective_num_positions')
                            if eff_num is not None:
                                snapshot.effective_num_positions = Decimal(str(eff_num))

                            top_3 = conc_result.get('top_3_concentration')
                            if top_3 is not None:
                                snapshot.top_3_concentration = Decimal(str(top_3))

                            top_10 = conc_result.get('top_10_concentration')
                            if top_10 is not None:
                                snapshot.top_10_concentration = Decimal(str(top_10))

                    except Exception as e:
                        logger.warning(f"Concentration metrics failed for {portfolio_id}: {e}")

                # Commit if any updates were made
                if updates_made:
                    await db.commit()
                    return {"status": "updated", "portfolio_id": portfolio_id}
                else:
                    return {"status": "skipped", "portfolio_id": portfolio_id}

        except Exception as e:
            return {
                "status": "failed",
                "portfolio_id": portfolio_id,
                "error": f"Snapshot analytics failed for {portfolio_id}: {str(e)[:100]}"
            }


async def _run_snapshot_analytics(
    portfolio_ids: List[UUID],
    target_date: date,
    unified_cache: SymbolCacheService,
) -> Dict[str, Any]:
    """
    Update snapshots with risk analytics (Phase 3 Step 2) - PARALLEL.

    After base snapshots are created with P&L data, this step
    calculates and updates the deferred risk analytics fields:
    - Market Beta (90D) via OLS regression
    - Provider Beta (1Y) from company profiles
    - Volatility metrics (21d, 63d, expected, trend)
    - Concentration metrics (HHI, effective positions, top 3/10)

    Args:
        portfolio_ids: List of portfolio IDs to process
        target_date: Calculation date
        unified_cache: V2 unified cache with prices and factors

    Returns:
        Dict with update results
    """
    logger.info(f"{V2_LOG_PREFIX} Phase 3 analytics: Snapshot analytics for {len(portfolio_ids)} portfolios (parallel, max {MAX_PORTFOLIO_CONCURRENCY})")

    # Use semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(MAX_PORTFOLIO_CONCURRENCY)

    # Create tasks for all portfolios
    tasks = [
        _process_single_portfolio_analytics(pid, target_date, unified_cache, semaphore)
        for pid in portfolio_ids
    ]

    # Run all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    updated = 0
    skipped = 0
    failed = 0
    errors = []

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result)[:100])
        elif result.get("status") == "updated":
            updated += 1
        elif result.get("status") == "skipped":
            skipped += 1
        elif result.get("status") == "failed":
            failed += 1
            if result.get("error"):
                errors.append(result["error"])

    logger.info(
        f"{V2_LOG_PREFIX} Phase 3 analytics complete: updated={updated}, skipped={skipped}, failed={failed}"
    )

    return {
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }


# =============================================================================
# PHASE 5: STRESS TESTS
# =============================================================================

async def _process_single_portfolio_stress_test(
    portfolio_id: UUID,
    target_date: date,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Process stress tests for a single portfolio (helper for parallel execution)."""
    from app.calculations.stress_testing import (
        run_comprehensive_stress_test,
        save_stress_test_results
    )

    async with semaphore:
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
                    return {"status": "skipped", "portfolio_id": portfolio_id}

                # Check if stress test was skipped
                stress_test_data = stress_results.get('stress_test_results', {})
                if stress_test_data.get('skipped'):
                    return {"status": "skipped", "portfolio_id": portfolio_id}

                # Save results to database
                scenarios_tested = stress_results.get('config_metadata', {}).get('scenarios_tested', 0)
                if scenarios_tested > 0:
                    saved_count = await save_stress_test_results(
                        db=db,
                        portfolio_id=portfolio_id,
                        stress_test_results=stress_results
                    )
                    if saved_count > 0:
                        return {"status": "calculated", "portfolio_id": portfolio_id}

                return {"status": "skipped", "portfolio_id": portfolio_id}

        except Exception as e:
            return {
                "status": "failed",
                "portfolio_id": portfolio_id,
                "error": f"Stress test failed for {portfolio_id}: {str(e)[:100]}"
            }


async def _run_stress_tests_for_all_portfolios(
    portfolio_ids: List[UUID],
    target_date: date,
) -> Dict[str, Any]:
    """
    Phase 5: Calculate stress tests for all portfolios - PARALLEL.

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
    logger.info(f"{V2_LOG_PREFIX} Phase 5: Stress tests for {len(portfolio_ids)} portfolios (parallel, max {MAX_PORTFOLIO_CONCURRENCY})")

    # Use semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(MAX_PORTFOLIO_CONCURRENCY)

    # Create tasks for all portfolios
    tasks = [
        _process_single_portfolio_stress_test(pid, target_date, semaphore)
        for pid in portfolio_ids
    ]

    # Run all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    calculated = 0
    skipped = 0
    failed = 0
    errors = []

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result)[:100])
        elif result.get("status") == "calculated":
            calculated += 1
        elif result.get("status") == "skipped":
            skipped += 1
        elif result.get("status") == "failed":
            failed += 1
            if result.get("error"):
                errors.append(result["error"])

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

    IMPORTANT: Uses calc_date from error_summary (US Eastern date that was processed),
    NOT completed_at.date() which is a UTC date. This prevents timezone issues where
    a batch completing at 9:30 PM ET on Jan 13 shows as Jan 14 in UTC.

    Returns:
        Date of last successful portfolio refresh, or None if never run
    """
    import sys

    try:
        print(f"{V2_LOG_PREFIX}   -> Opening database session...")
        sys.stdout.flush()

        # Add timeout to prevent hanging on database connection issues
        async with asyncio.timeout(30):  # 30 second timeout
            async with get_async_session() as db:
                print(f"{V2_LOG_PREFIX}   -> Executing query...")
                sys.stdout.flush()

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

                print(f"{V2_LOG_PREFIX}   -> Query complete, processing result...")
                sys.stdout.flush()

                if last_run:
                    # Use calc_date from error_summary (US Eastern date that was processed)
                    # This avoids UTC vs ET timezone issues
                    error_summary = last_run.error_summary or {}
                    calc_date_str = error_summary.get("calc_date")
                    if calc_date_str:
                        return date.fromisoformat(calc_date_str)

                    # Fallback to completed_at.date() for backwards compatibility
                    # (old runs without calc_date in error_summary)
                    if last_run.completed_at:
                        return last_run.completed_at.date()

        return None

    except asyncio.TimeoutError:
        print(f"{V2_LOG_PREFIX}   -> ERROR: Database query timed out after 30s")
        sys.stdout.flush()
        logger.error(f"{V2_LOG_PREFIX} get_last_portfolio_refresh_date timed out")
        return None
    except Exception as e:
        print(f"{V2_LOG_PREFIX}   -> ERROR: {e}")
        sys.stdout.flush()
        logger.error(f"{V2_LOG_PREFIX} get_last_portfolio_refresh_date failed: {e}")
        return None


# =============================================================================
# SCOPED PORTFOLIO PROCESSING (FOR ONBOARDING)
# =============================================================================

async def run_portfolio_refresh_for_portfolio(
    portfolio_id: UUID,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Run portfolio refresh phases for a single portfolio.

    Used during onboarding after symbol processing is complete.
    Runs Phase 4 (P&L), Phase 5 (factor aggregation), Phase 6 (stress tests).

    Leverages V2 caches for fast execution:
    - symbol_cache._price_cache for P&L calculations
    - symbol_cache._factor_cache for factor aggregation

    Args:
        portfolio_id: Portfolio to refresh
        target_date: Calculation date (defaults to most recent trading day)

    Returns:
        Dict with processing results
    """
    import time
    start_time = time.time()

    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    logger.info(
        f"{V2_LOG_PREFIX} [ONBOARDING] Refreshing portfolio {portfolio_id} for {target_date}"
    )

    result = {
        "success": True,
        "portfolio_id": str(portfolio_id),
        "target_date": target_date.isoformat(),
        "phases": {},
        "errors": [],
    }

    try:
        # Ensure cache is initialized
        if not symbol_cache._initialized:
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Initializing symbol cache...")
            await symbol_cache.initialize_async(target_date)

        # Phase 4: P&L calculations using price cache
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 4: P&L calculations...")
        phase_start = time.time()
        try:
            phase_4_result = await _run_phase_4_for_portfolio(portfolio_id, target_date)
            result["phases"]["phase_4_pnl"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_4_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 4 complete")
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 4 error: {e}", exc_info=True)
            result["phases"]["phase_4_pnl"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            result["errors"].append(f"Phase 4: {e}")

        # Phase 5: Factor aggregation using factor cache
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 5: Factor aggregation...")
        phase_start = time.time()
        try:
            phase_5_result = await _run_phase_5_for_portfolio(portfolio_id, target_date)
            result["phases"]["phase_5_factors"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_5_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 5 complete")
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 5 error: {e}", exc_info=True)
            result["phases"]["phase_5_factors"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            result["errors"].append(f"Phase 5: {e}")

        # Phase 6: Stress tests
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 6: Stress tests...")
        phase_start = time.time()
        try:
            phase_6_result = await _run_phase_6_for_portfolio(portfolio_id, target_date)
            result["phases"]["phase_6_stress"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_6_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 6 complete")
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 6 error: {e}", exc_info=True)
            result["phases"]["phase_6_stress"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            result["errors"].append(f"Phase 6: {e}")

        # Determine overall success
        result["success"] = all(
            p.get("success", False) for p in result["phases"].values()
        )

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Unexpected error: {e}", exc_info=True)
        result["success"] = False
        result["errors"].append(str(e))

    result["duration_seconds"] = round(time.time() - start_time, 2)
    logger.info(
        f"{V2_LOG_PREFIX} [ONBOARDING] Portfolio refresh complete: "
        f"success={result['success']}, duration={result['duration_seconds']}s"
    )

    return result


async def _run_phase_4_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """
    Run P&L calculations for a single portfolio using price cache.

    Uses existing pnl_calculator.calculate_all_portfolios_pnl() with
    portfolio_ids=[portfolio_id] to scope to single portfolio.

    Args:
        portfolio_id: Portfolio to calculate
        target_date: Calculation date

    Returns:
        Dict with calculation results
    """
    result = await pnl_calculator.calculate_all_portfolios_pnl(
        calculation_date=target_date,
        db=None,  # Let it create its own session
        portfolio_ids=[str(portfolio_id)],  # Single portfolio
        price_cache=symbol_cache._price_cache,  # Use V2 cache
    )

    return {
        "snapshots_created": result.get("snapshots_created", 0),
        "positions_updated": result.get("positions_updated", 0),
    }


async def _run_phase_5_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """
    Run factor aggregation for a single portfolio using factor cache.

    Uses existing get_portfolio_factor_exposures() and store_portfolio_factor_exposures()
    to aggregate symbol-level factors to portfolio-level.

    Args:
        portfolio_id: Portfolio to aggregate
        target_date: Calculation date

    Returns:
        Dict with aggregation results
    """
    from app.services.portfolio_factor_service import (
        get_portfolio_factor_exposures,
        store_portfolio_factor_exposures
    )

    factors_stored = 0

    async with get_async_session() as db:
        # Get Ridge factors (aggregated from symbol-level)
        ridge_result = await get_portfolio_factor_exposures(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=target_date,
            use_delta_adjusted=False,
            include_ridge=True,
            include_spread=False,
            include_ols=False
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
            factors_stored += len(ridge_betas)

        # Get Spread factors (aggregated from symbol-level)
        spread_result = await get_portfolio_factor_exposures(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=target_date,
            use_delta_adjusted=False,
            include_ridge=False,
            include_spread=True,
            include_ols=False
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
            factors_stored += len(spread_betas)

        # Get OLS factors (Market Beta 90D, IR Beta, Provider Beta 1Y)
        ols_result = await get_portfolio_factor_exposures(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=target_date,
            use_delta_adjusted=False,
            include_ridge=False,
            include_spread=False,
            include_ols=True
        )

        ols_betas = ols_result.get('ols_betas', {})

        if ols_betas:
            await store_portfolio_factor_exposures(
                db=db,
                portfolio_id=portfolio_id,
                portfolio_betas=ols_betas,
                calculation_date=target_date,
                portfolio_equity=portfolio_equity
            )
            factors_stored += len(ols_betas)

        # Commit transaction
        if factors_stored > 0:
            await db.commit()

    return {
        "factors_stored": factors_stored,
        "ridge_count": len(ridge_betas),
        "spread_count": len(spread_betas),
        "ols_count": len(ols_betas),
    }


async def _run_phase_6_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """
    Run stress tests for a single portfolio.

    Uses existing run_comprehensive_stress_test() and save_stress_test_results().

    Args:
        portfolio_id: Portfolio to test
        target_date: Calculation date

    Returns:
        Dict with stress test results
    """
    from app.calculations.stress_testing import (
        run_comprehensive_stress_test,
        save_stress_test_results
    )

    scenarios_saved = 0

    async with get_async_session() as db:
        # Run comprehensive stress test
        stress_results = await run_comprehensive_stress_test(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=target_date
        )

        # Check if results were returned
        if not stress_results:
            return {"scenarios_saved": 0, "skipped": True, "reason": "no_results"}

        # Check if stress test was skipped
        stress_test_data = stress_results.get('stress_test_results', {})
        if stress_test_data.get('skipped'):
            reason = stress_test_data.get('reason', 'unknown')
            return {"scenarios_saved": 0, "skipped": True, "reason": reason}

        # Save results to database
        scenarios_tested = stress_results.get('config_metadata', {}).get('scenarios_tested', 0)
        if scenarios_tested > 0:
            scenarios_saved = await save_stress_test_results(
                db=db,
                portfolio_id=portfolio_id,
                stress_test_results=stress_results
            )

    return {
        "scenarios_saved": scenarios_saved,
        "skipped": False,
    }
