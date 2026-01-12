"""
V2 Portfolio Refresh Runner

Runs at 9:30 PM ET (30 minutes after symbol batch) to refresh all portfolios:
1. Wait for symbol batch completion
2. Wait for pending symbol onboarding
3. Create snapshots for all portfolios using cached data
4. Calculate portfolio-level analytics

Key Design Decisions:
- Runs AFTER symbol batch to leverage cached prices and factors
- Uses existing PnLCalculator for snapshot creation
- Uses PriceCache for fast price lookups (300x faster than DB)
- Writes to existing tables (PortfolioSnapshot, etc.)

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
from app.cache.price_cache import PriceCache

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
    errors: List[str] = None
    duration_seconds: float = 0.0
    waited_for_symbol_batch: bool = False
    waited_for_onboarding: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "target_date": self.target_date.isoformat(),
            "portfolios_processed": self.portfolios_processed,
            "snapshots_created": self.snapshots_created,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "waited_for_symbol_batch": self.waited_for_symbol_batch,
            "waited_for_onboarding": self.waited_for_onboarding,
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

    # Determine target date
    if target_date is None:
        target_date = get_most_recent_trading_day()

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

        # Step 3: Load price cache for fast lookups
        price_cache = await _load_price_cache(target_date)

        # Step 4: Process all portfolios
        refresh_result = await _refresh_all_portfolios(target_date, price_cache)

        result.portfolios_processed = refresh_result.get("portfolios_processed", 0)
        result.snapshots_created = refresh_result.get("snapshots_created", 0)
        result.errors = refresh_result.get("errors", [])
        result.success = refresh_result.get("success", False)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        # Step 5: Record completion
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
# PRICE CACHE
# =============================================================================

async def _load_price_cache(target_date: date) -> PriceCache:
    """
    Load price cache from market_data_cache for fast lookups.

    The PriceCache provides 300x faster price lookups compared to DB queries.

    Args:
        target_date: Date to load prices for

    Returns:
        Initialized PriceCache
    """
    from app.models.market_data import MarketDataCache

    logger.info(f"{V2_LOG_PREFIX} Loading price cache for {target_date}")

    price_cache = PriceCache()

    async with get_async_session() as db:
        # Load prices for target date and previous trading days (for P&L calculation)
        start_date = target_date - timedelta(days=10)  # Lookback for previous prices

        result = await db.execute(
            select(MarketDataCache)
            .where(
                and_(
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= target_date,
                    MarketDataCache.close > 0,
                )
            )
        )
        records = result.scalars().all()

        for record in records:
            price_cache.set_price(record.symbol, record.date, record.close)

    stats = price_cache.get_stats()
    logger.info(
        f"{V2_LOG_PREFIX} Price cache loaded: {stats.get('cached_prices', 0)} entries"
    )

    return price_cache


# =============================================================================
# PORTFOLIO PROCESSING
# =============================================================================

async def _refresh_all_portfolios(
    target_date: date,
    price_cache: PriceCache,
) -> Dict[str, Any]:
    """
    Refresh all active portfolios using existing PnLCalculator.

    Args:
        target_date: Date to refresh
        price_cache: Pre-loaded price cache

    Returns:
        Dict with processing results
    """
    logger.info(f"{V2_LOG_PREFIX} Refreshing all portfolios for {target_date}")

    # Use existing PnLCalculator
    result = await pnl_calculator.calculate_all_portfolios_pnl(
        calculation_date=target_date,
        db=None,  # Let it create its own session
        portfolio_ids=None,  # Process all portfolios
        price_cache=price_cache,
    )

    return result


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
