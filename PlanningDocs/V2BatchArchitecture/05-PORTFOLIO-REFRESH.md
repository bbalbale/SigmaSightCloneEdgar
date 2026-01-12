# 05: Portfolio Daily Refresh (Cron Job 2)

## Overview

Second daily cron job that runs AFTER symbol batch completes. Creates snapshots and updates market values for all portfolios that need them.

**Trigger**: 9:30 PM ET (30 min after symbol batch starts)
**Prerequisite**: Symbol batch must have completed successfully
**Duration**: ~5-15 min depending on portfolio count

---

## Job Specification

```python
# scripts/batch_processing/run_portfolio_refresh.py

async def run_portfolio_refresh():
    """
    Cron Job 2: Portfolio Daily Refresh

    Runs at 9:30 PM ET, after symbol batch completes.
    """
    today = get_effective_trading_date()

    # Step 1: Check symbol batch completion
    if not await is_symbol_batch_complete(today):
        logger.error(f"Symbol batch not complete for {today}, aborting")
        # Alert ops team
        await send_alert("Portfolio refresh aborted - symbol batch incomplete")
        return {"status": "aborted", "reason": "symbol_batch_incomplete"}

    # Step 2: Find portfolios needing today's snapshot
    portfolios = await get_portfolios_without_snapshot(today)
    logger.info(f"Found {len(portfolios)} portfolios needing snapshots")

    if not portfolios:
        return {"status": "complete", "portfolios_processed": 0}

    # Step 3: Process each portfolio
    success_count = 0
    fail_count = 0

    for portfolio in portfolios:
        try:
            # Create snapshot using today's prices (from symbol batch)
            await create_portfolio_snapshot(portfolio.id, today)

            # Update position market values
            await update_position_market_values(portfolio.id, today)

            # Invalidate analytics cache
            await invalidate_portfolio_cache(portfolio.id)

            success_count += 1
        except Exception as e:
            logger.error(f"Failed to process portfolio {portfolio.id}: {e}")
            fail_count += 1

    return {
        "status": "complete",
        "portfolios_processed": success_count,
        "portfolios_failed": fail_count,
        "snapshot_date": today.isoformat()
    }
```

---

## Portfolio Query (Replaces Watermark)

```python
async def get_portfolios_without_snapshot(target_date: date) -> List[Portfolio]:
    """
    Find portfolios that need a snapshot for target_date.

    This REPLACES the complex watermark calculation.
    Each portfolio is independent - no more "minimum date" dragging.
    """
    query = """
        SELECT p.id, p.name, p.user_id
        FROM portfolios p
        WHERE p.deleted_at IS NULL

        -- Has at least one active position
        AND EXISTS (
            SELECT 1 FROM positions pos
            WHERE pos.portfolio_id = p.id
            AND pos.exit_date IS NULL
            AND pos.deleted_at IS NULL
        )

        -- Does NOT have a snapshot for target_date
        AND NOT EXISTS (
            SELECT 1 FROM portfolio_snapshots ps
            WHERE ps.portfolio_id = p.id
            AND ps.snapshot_date = :target_date
        )
    """

    result = await db.execute(text(query), {"target_date": target_date})
    return result.all()
```

**Key benefit**: New portfolios automatically get picked up. No special handling needed.

---

## Symbol Batch Completion Check

```python
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

## Snapshot Creation

```python
async def create_portfolio_snapshot(
    portfolio_id: UUID,
    snapshot_date: date
) -> PortfolioSnapshot:
    """
    Create a snapshot for a portfolio using cached prices.

    Uses prices from symbol_prices_daily (populated by symbol batch).
    NEVER fetches live prices.
    """
    # Get all active positions
    positions = await get_active_positions(portfolio_id)

    total_value = Decimal('0')
    total_cost = Decimal('0')

    for position in positions:
        # Get price from cache (symbol_prices_daily)
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
    Get price from symbol_prices_daily.

    Returns the price for target_date, or None if not found.
    """
    result = await db.execute(
        select(SymbolPricesDaily.close_price)
        .where(
            SymbolPricesDaily.symbol == symbol,
            SymbolPricesDaily.price_date == target_date
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

---

## Failure Handling

| Scenario | Action |
|----------|--------|
| Symbol batch not complete | Abort, alert, retry next day |
| Single portfolio fails | Log, continue with others, alert if >10% fail |
| Price not found for symbol | Log warning, skip position, mark snapshot as partial |
| DB connection error | Retry 3x with backoff, then fail |

---

## Telemetry

```python
# At end of job
record_metric("portfolio_refresh.duration_seconds", duration)
record_metric("portfolio_refresh.portfolios_processed", success_count)
record_metric("portfolio_refresh.portfolios_failed", fail_count)
record_metric("portfolio_refresh.portfolios_skipped", skip_count)
```

---

## Relationship to Onboarding

This job is the "catch-all" for portfolios. But onboarding doesn't wait for it:

- **User onboards at 2 PM**: Snapshot created immediately using yesterday's prices
- **Nightly cron at 9:30 PM**: Sees portfolio already has a snapshot, skips it
- **Next day at 9:30 PM**: Creates new snapshot with new prices

The query `get_portfolios_without_snapshot(today)` naturally handles this - if a portfolio already has today's snapshot (from onboarding), it's not in the result set.
