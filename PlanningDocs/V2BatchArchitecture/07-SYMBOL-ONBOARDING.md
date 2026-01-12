# 07: Symbol Onboarding

## Purpose

Handle symbols not yet in `symbol_universe` when a user uploads a portfolio. These need historical data fetched and factors calculated before analytics can include them.

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
        .where(SymbolUniverse.status == 'active')
    )
    known_set = {row[0] for row in known_symbols.all()}

    # Identify unknown symbols
    unknown_symbols = symbols_from_csv - known_set

    if unknown_symbols:
        # Validate they exist in market data (YFinance check)
        valid, invalid = await validate_symbols(unknown_symbols)

        if invalid:
            raise CSVValidationError(f"Invalid symbols: {', '.join(invalid)}")

        # Queue valid unknown symbols for onboarding
        for symbol in valid:
            await queue_symbol_onboarding(symbol)

    # Create portfolio (positions reference symbols)
    portfolio = await create_portfolio(...)

    return {
        "portfolio_id": str(portfolio.id),
        "status": "pending" if unknown_symbols else "ready",
        "pending_symbols": list(unknown_symbols) if unknown_symbols else None
    }
```

---

## Onboarding Queue

```python
async def queue_symbol_onboarding(
    symbol: str,
    requested_by: Optional[UUID] = None,
    priority: str = "high"
) -> None:
    """Add symbol to onboarding queue."""
    async with AsyncSessionLocal() as db:
        # Check if already queued (dedupe)
        existing = await db.execute(
            select(SymbolOnboardingQueue)
            .where(
                SymbolOnboardingQueue.symbol == symbol,
                SymbolOnboardingQueue.status.in_(['pending', 'processing'])
            )
        )
        if existing.scalar_one_or_none():
            return  # Already queued

        # Add to queue
        job = SymbolOnboardingQueue(
            symbol=symbol,
            status='pending',
            requested_by=requested_by,
            priority=priority
        )
        db.add(job)
        await db.commit()
```

---

## Onboarding Worker

```python
class SymbolOnboardingRunner:
    """
    Process symbols in the onboarding queue.

    Phases:
    1. Fetch 1 year historical prices
    2. Calculate all factor betas
    3. Add to symbol_universe as active
    """

    async def process_queue(self) -> Dict[str, Any]:
        """Process all pending symbols in queue."""
        async with AsyncSessionLocal() as db:
            # Get pending jobs (high priority first)
            pending = await db.execute(
                select(SymbolOnboardingQueue)
                .where(SymbolOnboardingQueue.status == 'pending')
                .order_by(
                    SymbolOnboardingQueue.priority.desc(),
                    SymbolOnboardingQueue.created_at
                )
                .limit(10)  # Process in batches
            )

            results = {'processed': 0, 'failed': 0}

            for job in pending.scalars():
                try:
                    await self._process_symbol(db, job)
                    results['processed'] += 1
                except Exception as e:
                    job.status = 'failed'
                    job.error_message = str(e)
                    results['failed'] += 1

                await db.commit()

            return results

    async def _process_symbol(
        self,
        db: AsyncSession,
        job: SymbolOnboardingQueue
    ) -> None:
        """Process a single symbol."""
        symbol = job.symbol

        # Mark as processing
        job.status = 'processing'
        job.started_at = utc_now()
        await db.commit()

        # Phase 1: Fetch 1 year of prices
        prices = await yfinance_fetch_history(symbol, period="1y")
        await bulk_insert_symbol_prices(db, symbol, prices)

        # Phase 2: Calculate factor betas
        await calculate_symbol_factors(db, symbol)

        # Phase 3: Add to universe
        universe_entry = SymbolUniverse(
            symbol=symbol,
            status='active',
            added_source='onboarding',
            last_price_date=date.today(),
            last_factor_date=date.today()
        )
        db.add(universe_entry)

        # Mark complete
        job.status = 'completed'
        job.completed_at = utc_now()

        # Phase 4: Update affected portfolio snapshots
        await update_portfolios_with_new_symbol(db, symbol)
```

---

## Update Portfolio Snapshots (Fix for Partial Onboarding)

When a symbol completes onboarding, we need to update any portfolio snapshots that excluded it:

```python
async def update_portfolios_with_new_symbol(db: AsyncSession, symbol: str) -> int:
    """
    Find portfolios that have positions in this symbol but excluded it
    from their snapshot, and update them.

    Called after symbol onboarding completes.
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
            # Recalculate snapshot to include new symbol
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
    """
    Recalculate a snapshot to include a newly onboarded symbol.
    """
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

    # Get price for the symbol
    price = await get_cached_price_for_date(db, new_symbol, price_date)

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

## Concurrency & Rate Limiting

```python
# Max concurrent onboarding jobs
MAX_CONCURRENT = 3

# Max queue depth before rejecting
MAX_QUEUE_DEPTH = 50

async def queue_symbol_onboarding(symbol: str, ...):
    # Check queue depth
    queue_depth = await db.execute(
        select(func.count(SymbolOnboardingQueue.id))
        .where(SymbolOnboardingQueue.status.in_(['pending', 'processing']))
    )
    if queue_depth.scalar() > MAX_QUEUE_DEPTH:
        raise QueueFullError("Symbol onboarding queue is full, try again later")

    # ... add to queue ...
```

---

## Progress Tracking

Reuse Phase 7.x `batch_run_tracker` for individual symbol onboarding:

```python
async def _process_symbol(self, db, job):
    symbol = job.symbol

    # Track as mini-batch
    batch_run_tracker.start(CurrentBatchRun(
        batch_run_id=f"symbol_onboard_{symbol}",
        started_at=utc_now(),
        triggered_by="symbol_onboarding"
    ))

    try:
        batch_run_tracker.start_phase("prices", "Fetching Prices", 1, "symbol")
        await yfinance_fetch_history(symbol, ...)
        batch_run_tracker.complete_phase("prices", success=True)

        batch_run_tracker.start_phase("factors", "Calculating Factors", 1, "symbol")
        await calculate_symbol_factors(...)
        batch_run_tracker.complete_phase("factors", success=True)

        batch_run_tracker.complete(success=True)
    except Exception as e:
        batch_run_tracker.complete(success=False)
        raise
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

    # Check universe
    universe = await db.execute(
        select(SymbolUniverse)
        .where(SymbolUniverse.symbol == symbol.upper())
    )
    entry = universe.scalar_one_or_none()

    if entry and entry.status == 'active':
        return SymbolStatusResponse(
            symbol=symbol,
            status="ready",
            message="Symbol data available"
        )

    # Check queue
    queue = await db.execute(
        select(SymbolOnboardingQueue)
        .where(SymbolOnboardingQueue.symbol == symbol.upper())
        .order_by(SymbolOnboardingQueue.created_at.desc())
        .limit(1)
    )
    job = queue.scalar_one_or_none()

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
| YFinance timeout | Retry 3x, then fail |
| No price data | Mark failed, continue others |
| Factor calc fails | Use defaults, mark partial |
| Queue full | Return 503, suggest retry |
