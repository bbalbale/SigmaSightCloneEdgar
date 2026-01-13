# 05: Portfolio Daily Refresh (Cron Job 2)

## Overview

Second daily cron job that runs AFTER symbol batch completes. Creates snapshots, calculates correlations, aggregates factors, and runs stress tests for all portfolios.

**Trigger**: 9:30 PM ET (30 min after symbol batch starts)
**Prerequisite**: Symbol batch must have completed successfully
**Duration**: ~5-15 min depending on portfolio count

---

## V2 Implementation (January 2026)

The V2 portfolio refresh runs 6 phases:

| Phase | Name | Description | Tables Written |
|-------|------|-------------|----------------|
| 3 | Snapshots | Create daily P&L snapshots using cached prices | `portfolio_snapshots` |
| 4 | Correlations | Calculate position-to-position correlations | `correlation_calculations`, `pairwise_correlations` |
| 5 | Factor Aggregation | Aggregate symbol factors to portfolio level | `factor_exposures` |
| 6 | Stress Tests | Run stress scenarios using portfolio factors | `stress_test_results` |

### Data Flow

```
Symbol Batch (Cron Job 1)
    │
    ├─► market_data_cache (prices)
    └─► symbol_factor_exposures (symbol-level factors)
            │
            ▼
Portfolio Refresh (Cron Job 2)
    │
    ├─► Phase 3: PriceCache → portfolio_snapshots
    ├─► Phase 4: PriceCache → correlation_calculations, pairwise_correlations
    ├─► Phase 5: symbol_factor_exposures → factor_exposures (aggregated)
    └─► Phase 6: factor_exposures → stress_test_results
```

### Key Dependencies

- **Unified V2 Cache**: `SymbolCacheService` provides both price and factor data in ONE cache
  - `_price_cache`: PriceCache for 300x faster price lookups
  - `_factor_cache`: In-memory symbol factor data for fast aggregation
  - DB fallback if cache miss
- **Phase 4 (Correlations)**: Uses unified cache's `_price_cache` for price lookups (300x faster)
- **Phase 5 (Factor Aggregation)**: Reads from `symbol_factor_exposures`, writes to `factor_exposures`
- **Phase 6 (Stress Tests)**: Reads from `factor_exposures` (portfolio-level factors)

---

## Job Specification

```python
# scripts/batch_processing/run_portfolio_refresh.py

async def run_portfolio_refresh():
    """
    Cron Job 2: Portfolio Daily Refresh

    Runs at 9:30 PM ET. Waits for symbol batch if needed.
    Backfills any missed days.
    """
    today = get_effective_trading_date()

    # Step 1: Wait for symbol batch completion (up to 60 min)
    symbol_batch_ready = await wait_for_symbol_batch(today, max_wait_minutes=60)
    if not symbol_batch_ready:
        logger.error(f"Symbol batch not complete after 60 min, aborting")
        await send_alert("Portfolio refresh aborted - symbol batch incomplete after 60 min wait")
        return {"status": "aborted", "reason": "symbol_batch_timeout"}

    # Step 2: Find portfolios needing snapshots (including missed days)
    portfolios_with_gaps = await get_portfolios_needing_snapshots(today)
    logger.info(f"Found {len(portfolios_with_gaps)} portfolios needing snapshots")

    if not portfolios_with_gaps:
        return {"status": "complete", "portfolios_processed": 0}

    # Step 3: Process each portfolio (backfill all missing dates)
    success_count = 0
    fail_count = 0
    snapshots_created = 0

    for portfolio, missing_dates in portfolios_with_gaps:
        try:
            for snapshot_date in missing_dates:
                # Only create snapshot if we have price data for that date
                if await has_price_data_for_date(snapshot_date):
                    await create_portfolio_snapshot(portfolio.id, snapshot_date)
                    snapshots_created += 1
                else:
                    logger.warning(f"No price data for {snapshot_date}, skipping")

            # Update position market values to latest
            await update_position_market_values(portfolio.id, today)

            success_count += 1
        except Exception as e:
            logger.error(f"Failed to process portfolio {portfolio.id}: {e}")
            fail_count += 1

    return {
        "status": "complete",
        "portfolios_processed": success_count,
        "portfolios_failed": fail_count,
        "snapshots_created": snapshots_created,
        "target_date": today.isoformat()
    }
```

---

## Wait for Symbol Batch (Fix for Timing Dependency)

Instead of aborting immediately if symbol batch isn't complete, we wait and retry:

```python
async def wait_for_symbol_batch(target_date: date, max_wait_minutes: int = 60) -> bool:
    """
    Wait for symbol batch to complete, checking every 5 minutes.

    Returns True if batch completed, False if timeout.
    """
    check_interval = 300  # 5 minutes
    max_attempts = max_wait_minutes // 5

    for attempt in range(max_attempts):
        if await is_symbol_batch_complete(target_date):
            logger.info(f"Symbol batch complete (attempt {attempt + 1})")
            return True

        logger.info(f"Symbol batch not complete, waiting 5 min (attempt {attempt + 1}/{max_attempts})")
        await asyncio.sleep(check_interval)

    return False


async def is_symbol_batch_complete(target_date: date) -> bool:
    """
    Check if symbol batch completed successfully for target_date.

    Uses batch_run_tracking table (already exists).
    """
    result = await db.execute(
        select(BatchRunTracking)
        .where(
            BatchRunTracking.batch_type == 'symbol_batch',
            BatchRunTracking.target_date == target_date,
            BatchRunTracking.status == 'completed'
        )
    )
    return result.scalar_one_or_none() is not None
```

---

## Backfill Missing Days (Fix for Missed Day Gap)

Instead of only checking for today's snapshot, we find all missing dates:

```python
async def get_portfolios_needing_snapshots(
    target_date: date
) -> List[Tuple[Portfolio, List[date]]]:
    """
    Find portfolios with missing snapshots, including missed days.

    Returns list of (portfolio, [missing_dates]) tuples.
    Handles the case where cron failed for multiple days.
    """
    result = []

    # Get all active portfolios
    portfolios = await get_active_portfolios()

    for portfolio in portfolios:
        # Get the last snapshot date for this portfolio
        last_snapshot = await get_last_snapshot_date(portfolio.id)

        if last_snapshot is None:
            # New portfolio, needs snapshot for today only
            # (onboarding should have created initial snapshot)
            missing_dates = [target_date]
        else:
            # Find all trading days between last snapshot and today
            missing_dates = get_trading_days_between(
                start_date=last_snapshot + timedelta(days=1),
                end_date=target_date
            )

        if missing_dates:
            result.append((portfolio, missing_dates))

    return result


async def get_last_snapshot_date(portfolio_id: UUID) -> Optional[date]:
    """Get the most recent snapshot date for a portfolio."""
    result = await db.execute(
        select(func.max(PortfolioSnapshot.snapshot_date))
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
    )
    return result.scalar()


def get_trading_days_between(start_date: date, end_date: date) -> List[date]:
    """
    Get all trading days between start and end (inclusive).

    Excludes weekends and US market holidays.
    """
    import holidays
    us_holidays = holidays.NYSE()

    trading_days = []
    current = start_date

    while current <= end_date:
        # Skip weekends
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        # Skip holidays
        if current in us_holidays:
            current += timedelta(days=1)
            continue

        trading_days.append(current)
        current += timedelta(days=1)

    return trading_days


async def has_price_data_for_date(target_date: date) -> bool:
    """Check if we have price data for a given date."""
    result = await db.execute(
        select(func.count(MarketDataCache.id))
        .where(MarketDataCache.date == target_date)
    )
    count = result.scalar()
    return count > 0
```

---

## Portfolio Query (Original - Still Used)

```python
async def get_active_portfolios() -> List[Portfolio]:
    """
    Get all active portfolios with at least one active position.
    """
    query = """
        SELECT p.id, p.name, p.user_id
        FROM portfolios p
        WHERE p.deleted_at IS NULL
        AND EXISTS (
            SELECT 1 FROM positions pos
            WHERE pos.portfolio_id = p.id
            AND pos.exit_date IS NULL
            AND pos.deleted_at IS NULL
        )
    """
    result = await db.execute(text(query))
    return result.all()
```

---

## Snapshot Creation

```python
async def create_portfolio_snapshot(
    portfolio_id: UUID,
    snapshot_date: date
) -> PortfolioSnapshot:
    """
    Create a snapshot for a portfolio using cached prices.

    Uses prices from market_data_cache (populated by symbol batch).
    NEVER fetches live prices.
    """
    # Check if snapshot already exists (idempotent)
    existing = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"Snapshot already exists for {portfolio_id} on {snapshot_date}")
        return existing.scalar_one()

    # Get all active positions
    positions = await get_active_positions(portfolio_id)

    total_value = Decimal('0')
    total_cost = Decimal('0')

    for position in positions:
        # Get price from cache (market_data_cache)
        price = await get_cached_price(position.symbol, snapshot_date)

        if price:
            market_value = position.quantity * price
            total_value += market_value
            total_cost += position.quantity * position.entry_price

    # Calculate P&L
    total_pnl = total_value - total_cost
    pnl_percent = (total_pnl / total_cost * 100) if total_cost else Decimal('0')

    # Create snapshot
    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_pnl,
        pnl_percent=pnl_percent,
        position_count=len(positions)
    )

    db.add(snapshot)
    await db.commit()

    return snapshot


async def get_cached_price(symbol: str, target_date: date) -> Optional[Decimal]:
    """
    Get price from market_data_cache.

    Returns the price for target_date, or None if not found.
    """
    result = await db.execute(
        select(MarketDataCache.close_price)
        .where(
            MarketDataCache.symbol == symbol,
            MarketDataCache.date == target_date
        )
    )
    row = result.first()
    return row.close_price if row else None
```

---

## Railway Cron Configuration

```yaml
# railway.json (or Railway dashboard)
{
  "crons": [
    {
      "name": "symbol-batch",
      "schedule": "0 21 * * 1-5",  # 9:00 PM ET, Mon-Fri
      "command": "python scripts/batch_processing/run_symbol_batch.py"
    },
    {
      "name": "portfolio-refresh",
      "schedule": "30 21 * * 1-5",  # 9:30 PM ET, Mon-Fri
      "command": "python scripts/batch_processing/run_portfolio_refresh.py"
    }
  ]
}
```

**Note**: Times are in UTC on Railway. 9:00 PM ET = 01:00 UTC (EST) or 02:00 UTC (EDT).

**Note**: Portfolio refresh will wait up to 60 min for symbol batch, so even if symbol batch runs long, we don't lose the day.

---

## Race Condition Fix: Check for Missing Factors

> **See also**: [19-IMPLEMENTATION-FIXES.md](./19-IMPLEMENTATION-FIXES.md) Section 4 for full implementation details.

### Problem

When a user uploads a portfolio with a new symbol mid-day, symbol onboarding processes it. But there's a race condition:
1. User uploads at 2 PM with new symbol XYZ
2. Symbol onboarding starts processing XYZ
3. Nightly symbol batch runs at 9 PM (XYZ may not be in `symbol_universe` yet)
4. Portfolio refresh at 9:30 PM - XYZ might have prices but no factors

### Solution: Check for Missing Factors Before Creating Snapshot

```python
async def run_portfolio_refresh(target_date: date) -> Dict[str, Any]:
    # ... wait for symbol batch ...

    # NEW: Wait for pending symbol onboarding to complete
    pending_symbols = await get_pending_onboarding_symbols()
    if pending_symbols:
        logger.info(f"Waiting for {len(pending_symbols)} pending onboarding jobs")
        await wait_for_onboarding_completion(pending_symbols, max_wait_seconds=120)

    for portfolio in portfolios:
        # NEW: Check for symbols missing factors
        missing_factors = await get_symbols_missing_factors(portfolio.id, target_date)

        if missing_factors:
            logger.info(f"Portfolio {portfolio.id}: calculating factors for {len(missing_factors)} symbols")
            await calculate_factors_for_symbols(missing_factors, target_date)

        # Now all symbols have data - create snapshot
        await create_portfolio_snapshot(portfolio.id, target_date)
```

### Private Position Handling

```python
async def create_portfolio_snapshot(portfolio_id: UUID, snapshot_date: date):
    """
    Create snapshot handling all investment classes.

    - PUBLIC/OPTIONS: Use cached market prices
    - PRIVATE: Use manually-entered market_value (no factor exposures)
    """
    for position in positions:
        if position.investment_class == 'PRIVATE':
            # PRIVATE: Use manual valuation
            if position.market_value:
                total_value += position.market_value
            else:
                logger.warning(f"Private position {position.id} has no market_value")
        else:
            # PUBLIC/OPTIONS: Get from cache
            price = await get_cached_price(position.symbol, snapshot_date)
            if price:
                total_value += position.quantity * price
```

---

## Failure Handling

| Scenario | Action |
|----------|--------|
| Symbol batch not complete after 60 min | Abort, alert, portfolios backfilled next day |
| Pending symbol onboarding after 2 min | Continue anyway, symbols calculated inline |
| Missing factors for symbol | Calculate inline before snapshot |
| Single portfolio fails | Log, continue with others, alert if >10% fail |
| Price not found for symbol | Log warning, skip position, mark snapshot as partial |
| Private position no market_value | Log warning, exclude from snapshot |
| Price data missing for entire date | Skip that date, log warning |
| DB connection error | Retry 3x with backoff, then fail |

---

## Telemetry

```python
# At end of job
record_metric("portfolio_refresh.duration_seconds", duration)
record_metric("portfolio_refresh.portfolios_processed", success_count)
record_metric("portfolio_refresh.portfolios_failed", fail_count)
record_metric("portfolio_refresh.snapshots_created", snapshots_created)
record_metric("portfolio_refresh.days_backfilled", days_backfilled)
```

---

## Relationship to Onboarding

This job is the "catch-all" for portfolios. But onboarding doesn't wait for it:

- **User onboards at 2 PM**: Snapshot created immediately using yesterday's prices
- **Nightly cron at 9:30 PM**: Sees portfolio already has today's snapshot, skips it
- **Next day at 9:30 PM**: Creates new snapshot with new prices

The backfill logic handles edge cases:
- If cron fails Monday and Tuesday, Wednesday's run creates Mon + Tue + Wed snapshots
- Only creates snapshots for dates where we have price data
