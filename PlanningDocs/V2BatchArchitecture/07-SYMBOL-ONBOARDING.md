# 07: Symbol Onboarding

## Purpose

Handle symbols not yet in `symbol_universe` when a user uploads a portfolio. These need historical data fetched and factors calculated before analytics can include them.

---

## Design: In-Memory Queue

Symbol onboarding uses an **in-memory queue** instead of a database table because:
- Jobs are transient (complete in seconds, then stale)
- Single Railway instance (no multi-worker coordination needed)
- If server restarts, user can simply retry (rare edge case)
- Simpler implementation, no migration needed

---

## In-Memory Queue Structure

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
import asyncio

@dataclass
class OnboardingJob:
    symbol: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    requested_by: Optional[UUID]
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None

class SymbolOnboardingQueue:
    """
    In-memory queue for symbol onboarding jobs.

    Thread-safe via asyncio.Lock.
    """

    def __init__(self, max_queue_depth: int = 50, max_concurrent: int = 3):
        self._jobs: Dict[str, OnboardingJob] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.max_queue_depth = max_queue_depth

    async def enqueue(self, symbol: str, requested_by: Optional[UUID] = None) -> bool:
        """
        Add symbol to queue. Returns False if already queued or queue full.
        """
        symbol = symbol.upper()

        async with self._lock:
            # Already in queue?
            if symbol in self._jobs:
                return False

            # Queue full?
            pending_count = sum(1 for j in self._jobs.values()
                              if j.status in ('pending', 'processing'))
            if pending_count >= self.max_queue_depth:
                raise QueueFullError(f"Queue full ({self.max_queue_depth} max)")

            # Add to queue
            self._jobs[symbol] = OnboardingJob(
                symbol=symbol,
                status='pending',
                requested_by=requested_by
            )
            return True

    async def get_pending(self) -> list[str]:
        """Get all pending symbols."""
        async with self._lock:
            return [s for s, j in self._jobs.items() if j.status == 'pending']

    async def mark_processing(self, symbol: str) -> None:
        """Mark symbol as processing."""
        async with self._lock:
            if symbol in self._jobs:
                self._jobs[symbol].status = 'processing'
                self._jobs[symbol].started_at = datetime.utcnow()

    async def mark_completed(self, symbol: str) -> None:
        """Mark symbol as completed and remove from queue."""
        async with self._lock:
            if symbol in self._jobs:
                del self._jobs[symbol]  # Clean up - no stale data

    async def mark_failed(self, symbol: str, error: str) -> None:
        """Mark symbol as failed."""
        async with self._lock:
            if symbol in self._jobs:
                self._jobs[symbol].status = 'failed'
                self._jobs[symbol].error_message = error

    async def get_status(self, symbol: str) -> Optional[OnboardingJob]:
        """Get job status for a symbol."""
        async with self._lock:
            return self._jobs.get(symbol.upper())

    def queue_depth(self) -> int:
        """Current queue depth."""
        return sum(1 for j in self._jobs.values()
                  if j.status in ('pending', 'processing'))


# Global singleton
symbol_onboarding_queue = SymbolOnboardingQueue()
```

---

## Detection Flow

When user uploads portfolio CSV:

```python
async def create_portfolio_with_csv(...):
    # Parse CSV and extract symbols
    symbols_from_csv = {pos.symbol for pos in csv_positions}

    # Query symbol_universe for known symbols
    known_symbols = await db.execute(
        select(SymbolUniverse.symbol)
        .where(SymbolUniverse.symbol.in_(symbols_from_csv))
        .where(SymbolUniverse.is_active == True)
    )
    known_set = {row[0] for row in known_symbols.all()}

    # Identify unknown symbols
    unknown_symbols = symbols_from_csv - known_set

    if unknown_symbols:
        # Validate they exist in market data (YFinance check)
        valid, invalid = await validate_symbols(unknown_symbols)

        if invalid:
            raise CSVValidationError(f"Invalid symbols: {', '.join(invalid)}")

        # Queue valid unknown symbols for onboarding (in-memory)
        for symbol in valid:
            await symbol_onboarding_queue.enqueue(symbol, requested_by=user_id)

        # Start processing in background
        asyncio.create_task(process_onboarding_queue())

    # Create portfolio (positions reference symbols)
    portfolio = await create_portfolio(...)

    return {
        "portfolio_id": str(portfolio.id),
        "status": "pending" if unknown_symbols else "ready",
        "pending_symbols": list(unknown_symbols) if unknown_symbols else None
    }
```

---

## Onboarding Worker

```python
async def process_onboarding_queue() -> Dict[str, Any]:
    """
    Process all pending symbols in the in-memory queue.

    Called as background task after symbols are queued.
    """
    pending = await symbol_onboarding_queue.get_pending()

    if not pending:
        return {'processed': 0, 'failed': 0}

    results = {'processed': 0, 'failed': 0}

    async def process_one(symbol: str):
        async with symbol_onboarding_queue._semaphore:  # Limit concurrency
            try:
                await _process_symbol(symbol)
                results['processed'] += 1
            except Exception as e:
                logger.error(f"Failed to onboard {symbol}: {e}")
                await symbol_onboarding_queue.mark_failed(symbol, str(e))
                results['failed'] += 1

    # Process all pending symbols with concurrency limit
    await asyncio.gather(*[process_one(s) for s in pending])

    return results


async def _process_symbol(symbol: str) -> None:
    """Process a single symbol."""
    await symbol_onboarding_queue.mark_processing(symbol)

    async with get_async_session() as db:
        # Phase 1: Fetch 1 year of prices → market_data_cache
        prices = await yfinance_fetch_history(symbol, period="1y")
        await bulk_upsert_market_data(db, symbol, prices)

        # Phase 2: Calculate factor betas → symbol_factor_exposures
        await calculate_symbol_factors(db, symbol)

        # Phase 3: Add to universe (or update if exists)
        universe_entry = SymbolUniverse(
            symbol=symbol,
            is_active=True
        )
        db.add(universe_entry)
        await db.commit()

        # Phase 4: Update affected portfolio snapshots
        await update_portfolios_with_new_symbol(db, symbol)

        # Phase 5: Add to in-memory cache
        await symbol_cache.add_symbol(db, symbol)

    # Clean up from queue
    await symbol_onboarding_queue.mark_completed(symbol)

    logger.info(f"V2_ONBOARDING symbol={symbol} status=completed")
```

---

## Update Portfolio Snapshots

When a symbol completes onboarding, update any portfolio snapshots that excluded it:

```python
async def update_portfolios_with_new_symbol(db: AsyncSession, symbol: str) -> int:
    """
    Find portfolios that have positions in this symbol but excluded it
    from their snapshot, and update them.
    """
    # Find portfolios with positions in this symbol
    portfolios_with_symbol = await db.execute(
        select(Position.portfolio_id)
        .where(
            Position.symbol == symbol.upper(),
            Position.exit_date.is_(None),
            Position.deleted_at.is_(None)
        )
        .distinct()
    )
    portfolio_ids = [row[0] for row in portfolios_with_symbol.all()]

    if not portfolio_ids:
        return 0

    updated_count = 0
    latest_price_date = await get_latest_price_date(db)

    for portfolio_id in portfolio_ids:
        # Get the most recent snapshot for this portfolio
        latest_snapshot = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot = latest_snapshot.scalar_one_or_none()

        if snapshot:
            await recalculate_snapshot_with_symbol(
                db, snapshot, symbol, latest_price_date
            )
            updated_count += 1

    logger.info(f"Updated {updated_count} portfolio snapshots with new symbol {symbol}")
    return updated_count


async def recalculate_snapshot_with_symbol(
    db: AsyncSession,
    snapshot: PortfolioSnapshot,
    new_symbol: str,
    price_date: date
) -> None:
    """Recalculate a snapshot to include a newly onboarded symbol."""
    # Get the position for this symbol
    position = await db.execute(
        select(Position)
        .where(
            Position.portfolio_id == snapshot.portfolio_id,
            Position.symbol == new_symbol.upper(),
            Position.exit_date.is_(None)
        )
    )
    pos = position.scalar_one_or_none()

    if not pos:
        return

    # Get price for the symbol from cache
    price = symbol_cache.get_latest_price(new_symbol)

    if not price:
        return

    # Calculate additional value from this position
    additional_value = pos.quantity * price
    additional_cost = pos.quantity * pos.entry_price

    # Update snapshot totals
    snapshot.total_value += additional_value
    snapshot.total_cost += additional_cost
    snapshot.total_pnl = snapshot.total_value - snapshot.total_cost
    snapshot.pnl_percent = (
        (snapshot.total_pnl / snapshot.total_cost * 100)
        if snapshot.total_cost else Decimal('0')
    )
    snapshot.position_count += 1

    # Update position market value
    pos.market_value = additional_value
    pos.last_price = price
    pos.last_price_date = price_date

    await db.commit()
    logger.info(f"Added {new_symbol} to snapshot for portfolio {snapshot.portfolio_id}")
```

---

## Status Endpoint

```python
@router.get("/symbols/{symbol}/status")
async def get_symbol_status(
    symbol: str,
    db: AsyncSession = Depends(get_db)
) -> SymbolStatusResponse:
    """Check if symbol is ready for analytics."""

    # Check universe first
    universe = await db.execute(
        select(SymbolUniverse)
        .where(SymbolUniverse.symbol == symbol.upper())
    )
    entry = universe.scalar_one_or_none()

    if entry and entry.is_active:
        return SymbolStatusResponse(
            symbol=symbol,
            status="ready",
            message="Symbol data available"
        )

    # Check in-memory queue
    job = await symbol_onboarding_queue.get_status(symbol)

    if job:
        if job.status == 'processing':
            return SymbolStatusResponse(
                symbol=symbol,
                status="processing",
                message="Loading data...",
                estimated_seconds=30
            )
        elif job.status == 'pending':
            return SymbolStatusResponse(
                symbol=symbol,
                status="pending",
                message="Queued for processing",
                estimated_seconds=60
            )
        elif job.status == 'failed':
            return SymbolStatusResponse(
                symbol=symbol,
                status="error",
                message=job.error_message
            )

    return SymbolStatusResponse(
        symbol=symbol,
        status="unknown",
        message="Symbol not found"
    )
```

---

## Timeline Estimates

| Symbols | Fetch Prices | Calculate Factors | Total |
|---------|--------------|-------------------|-------|
| 1 | ~3-5 sec | ~2-3 sec | ~8-10 sec |
| 5 | ~10-15 sec | ~5-8 sec | ~20-25 sec |
| 10 | ~20-30 sec | ~10-15 sec | ~35-50 sec |
| 20 | ~40-60 sec | ~20-30 sec | ~65-95 sec |

Max expected: ~2 minutes for 20 unknown symbols.

---

## Error Handling

| Error | Action |
|-------|--------|
| Invalid symbol (YFinance) | Reject at CSV upload |
| YFinance timeout | Retry 3x, then mark failed |
| No price data | Mark failed, continue others |
| Factor calc fails | Use defaults, mark partial |
| Queue full | Return 503, suggest retry |
| Server restart | Queue lost, user retries on next action |

---

## Trade-offs: In-Memory vs Database Queue

| Aspect | In-Memory (Chosen) | Database |
|--------|-------------------|----------|
| Survives restart | No (user retries) | Yes |
| Multi-worker safe | No (single instance) | Yes |
| Stale data | Never | Yes (completed jobs linger) |
| Complexity | Simple | More complex |
| Migration needed | No | Yes |
