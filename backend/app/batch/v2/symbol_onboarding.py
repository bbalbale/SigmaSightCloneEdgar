"""
V2 Symbol Onboarding Queue (In-Memory)

Instant onboarding for new symbols when positions are added:
1. Check if symbol is already known (in symbol_universe)
2. If new, enqueue for processing
3. Fetch prices and calculate factors
4. Mark as processed in symbol_universe

Design Decision: In-memory queue (not database-backed)
- Jobs are short-lived (< 1 minute typically)
- If Railway restarts mid-job, user simply retries
- symbol_universe table tracks which symbols have been processed
- Simpler implementation, no migration needed

Reference: PlanningDocs/V2BatchArchitecture/07-SYMBOL-ONBOARDING.md
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now
from app.core.trading_calendar import get_most_recent_trading_day
from app.database import get_async_session, AsyncSessionLocal
from app.models.symbol_analytics import SymbolUniverse
from app.batch.batch_run_tracker import (
    batch_run_tracker,
    BatchJobType,
    BatchJob,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

V2_LOG_PREFIX = "[V2_ONBOARDING]"

# Processing limits
MAX_QUEUE_SIZE = 50  # Maximum pending jobs
MAX_CONCURRENT_PROCESSING = 3  # Parallel symbol processing


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class OnboardingJob:
    """Represents a symbol onboarding job."""
    symbol: str
    portfolio_id: UUID
    user_id: UUID
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "portfolio_id": str(self.portfolio_id),
            "user_id": str(self.user_id),
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


# =============================================================================
# SYMBOL ONBOARDING QUEUE
# =============================================================================

class SymbolOnboardingQueue:
    """
    In-memory queue for symbol onboarding jobs.

    Thread-safe queue that processes new symbols:
    - Deduplicates symbols (won't queue same symbol twice)
    - Checks symbol_universe for already-processed symbols
    - Processes symbols concurrently with configurable limit
    - Automatically starts background worker
    """

    def __init__(self):
        self._pending: Dict[str, OnboardingJob] = {}
        self._processing: Dict[str, OnboardingJob] = {}
        self._completed: Dict[str, OnboardingJob] = {}
        self._failed: Dict[str, OnboardingJob] = {}
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def enqueue(
        self,
        symbol: str,
        portfolio_id: UUID,
        user_id: UUID,
    ) -> Optional[str]:
        """
        Enqueue a symbol for onboarding.

        Args:
            symbol: Symbol to onboard
            portfolio_id: Portfolio requesting the symbol
            user_id: User requesting the symbol

        Returns:
            Job ID if enqueued, None if already known or queued
        """
        symbol = symbol.upper().strip()

        async with self._lock:
            # Check if already queued or processing
            if symbol in self._pending or symbol in self._processing:
                logger.debug(f"{V2_LOG_PREFIX} Symbol {symbol} already in queue")
                return None

            # Check if already known in universe
            if await self._is_symbol_known(symbol):
                logger.debug(f"{V2_LOG_PREFIX} Symbol {symbol} already in universe")
                return None

            # Check queue size limit
            if len(self._pending) >= MAX_QUEUE_SIZE:
                logger.warning(
                    f"{V2_LOG_PREFIX} Queue full ({MAX_QUEUE_SIZE}), rejecting {symbol}"
                )
                return None

            # Create job
            job = OnboardingJob(
                symbol=symbol,
                portfolio_id=portfolio_id,
                user_id=user_id,
            )
            self._pending[symbol] = job

            logger.info(f"{V2_LOG_PREFIX} Enqueued {symbol} (job_id={job.job_id})")

            # Start worker if not running
            self._ensure_worker_running()

            return job.job_id

    async def enqueue_batch(
        self,
        symbols: List[str],
        portfolio_id: UUID,
        user_id: UUID,
    ) -> List[str]:
        """
        Enqueue multiple symbols for onboarding.

        Args:
            symbols: List of symbols to onboard
            portfolio_id: Portfolio requesting the symbols
            user_id: User requesting the symbols

        Returns:
            List of job IDs for successfully enqueued symbols
        """
        job_ids = []
        for symbol in symbols:
            job_id = await self.enqueue(symbol, portfolio_id, user_id)
            if job_id:
                job_ids.append(job_id)
        return job_ids

    async def get_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job by ID."""
        async with self._lock:
            # Check all queues
            for symbol, job in self._pending.items():
                if job.job_id == job_id:
                    return job.to_dict()

            for symbol, job in self._processing.items():
                if job.job_id == job_id:
                    return job.to_dict()

            for symbol, job in self._completed.items():
                if job.job_id == job_id:
                    return job.to_dict()

            for symbol, job in self._failed.items():
                if job.job_id == job_id:
                    return job.to_dict()

        return None

    async def get_pending_count(self) -> int:
        """Get count of pending jobs."""
        async with self._lock:
            return len(self._pending)

    async def get_processing_count(self) -> int:
        """Get count of currently processing jobs."""
        async with self._lock:
            return len(self._processing)

    async def get_queue_status(self) -> Dict:
        """Get full queue status."""
        async with self._lock:
            return {
                "pending": len(self._pending),
                "processing": len(self._processing),
                "completed": len(self._completed),
                "failed": len(self._failed),
                "pending_symbols": list(self._pending.keys()),
                "processing_symbols": list(self._processing.keys()),
            }

    async def is_symbol_queued_or_processing(self, symbol: str) -> bool:
        """Check if symbol is queued or being processed."""
        symbol = symbol.upper().strip()
        async with self._lock:
            return symbol in self._pending or symbol in self._processing

    # =========================================================================
    # BACKGROUND WORKER
    # =========================================================================

    def _ensure_worker_running(self):
        """Ensure background worker is running."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info(f"{V2_LOG_PREFIX} Started background worker")

    async def _worker_loop(self):
        """Background worker that processes queued symbols."""
        logger.info(f"{V2_LOG_PREFIX} Worker loop started")

        while not self._shutdown:
            try:
                # Process next batch of symbols
                await self._process_batch()

                # Sleep before next iteration
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"{V2_LOG_PREFIX} Worker error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Backoff on error

        logger.info(f"{V2_LOG_PREFIX} Worker loop stopped")

    async def _process_batch(self):
        """Process a batch of pending symbols concurrently."""
        # Get symbols to process (up to max concurrent)
        symbols_to_process = []

        async with self._lock:
            available_slots = MAX_CONCURRENT_PROCESSING - len(self._processing)
            if available_slots <= 0:
                return

            for symbol, job in list(self._pending.items()):
                if len(symbols_to_process) >= available_slots:
                    break

                # Move to processing
                job.status = "processing"
                job.started_at = utc_now()
                self._processing[symbol] = job
                del self._pending[symbol]
                symbols_to_process.append(symbol)

        if not symbols_to_process:
            return

        # Process symbols concurrently
        tasks = [
            self._process_symbol(symbol)
            for symbol in symbols_to_process
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_symbol(self, symbol: str):
        """Process a single symbol."""
        logger.info(f"{V2_LOG_PREFIX} Processing {symbol}")

        try:
            # Get calculation date
            calc_date = get_most_recent_trading_day()

            # Fetch prices for symbol
            await self._fetch_symbol_prices(symbol, calc_date)

            # Calculate factors for symbol
            await self._calculate_symbol_factors(symbol, calc_date)

            # Mark as known in universe
            await self._mark_symbol_known(symbol)

            # Move to completed
            async with self._lock:
                if symbol in self._processing:
                    job = self._processing[symbol]
                    job.status = "completed"
                    job.completed_at = utc_now()
                    self._completed[symbol] = job
                    del self._processing[symbol]

            logger.info(f"{V2_LOG_PREFIX} Completed {symbol}")

        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Failed {symbol}: {e}", exc_info=True)

            # Move to failed
            async with self._lock:
                if symbol in self._processing:
                    job = self._processing[symbol]
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = utc_now()
                    self._failed[symbol] = job
                    del self._processing[symbol]

    # =========================================================================
    # SYMBOL PROCESSING
    # =========================================================================

    async def _is_symbol_known(self, symbol: str) -> bool:
        """Check if symbol is already in symbol_universe."""
        async with get_async_session() as db:
            result = await db.execute(
                select(SymbolUniverse.symbol).where(
                    SymbolUniverse.symbol == symbol
                )
            )
            return result.scalar_one_or_none() is not None

    async def _mark_symbol_known(self, symbol: str):
        """Add symbol to symbol_universe."""
        async with get_async_session() as db:
            # Check if already exists
            result = await db.execute(
                select(SymbolUniverse).where(SymbolUniverse.symbol == symbol)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update last_seen_date
                existing.last_seen_date = date.today()
                existing.is_active = True
            else:
                # Create new entry
                new_entry = SymbolUniverse(
                    symbol=symbol,
                    asset_type='equity',
                    first_seen_date=date.today(),
                    last_seen_date=date.today(),
                    is_active=True,
                )
                db.add(new_entry)

            await db.commit()

    async def _fetch_symbol_prices(self, symbol: str, calc_date: date):
        """Fetch historical prices for symbol."""
        from app.batch.market_data_collector import market_data_collector

        # Use scoped_only=True to only fetch this symbol
        await market_data_collector.collect_daily_market_data(
            calculation_date=calc_date,
            lookback_days=365,
            db=None,
            portfolio_ids=None,
            skip_company_profiles=False,
            scoped_only=True,  # Only fetch this symbol + factor ETFs
        )

    async def _calculate_symbol_factors(self, symbol: str, calc_date: date):
        """Calculate factors for symbol."""
        from app.calculations.symbol_factors import calculate_universe_factors

        # Calculate factors for just this symbol
        await calculate_universe_factors(
            calculation_date=calc_date,
            regularization_alpha=1.0,
            calculate_ridge=True,
            calculate_spread=True,
            price_cache=None,
            symbols=[symbol],  # Just this symbol
        )

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def shutdown(self):
        """Shutdown the queue worker."""
        logger.info(f"{V2_LOG_PREFIX} Shutting down...")
        self._shutdown = True

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info(f"{V2_LOG_PREFIX} Shutdown complete")

    def clear_completed(self):
        """Clear completed jobs (memory cleanup)."""
        self._completed.clear()
        self._failed.clear()


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

symbol_onboarding_queue = SymbolOnboardingQueue()
