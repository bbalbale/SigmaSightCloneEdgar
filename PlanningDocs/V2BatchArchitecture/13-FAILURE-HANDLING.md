# 13: Failure Handling

## Overview

Graceful degradation strategy for V2 batch architecture. Failures are retried with fallbacks, surfaced on admin page, and users can fix data issues from command center.

---

## Symbol Price Fetch Failures

**Strategy**: Cascading fallback with retry

```python
PRICE_PROVIDER_CHAIN = [
    "yfinance",
    "yahooquery",
    "fmp",
    "polygon"
]

async def fetch_symbol_price(symbol: str, date: date) -> Optional[Decimal]:
    """Fetch price with cascading fallback."""
    for provider in PRICE_PROVIDER_CHAIN:
        try:
            price = await fetch_from_provider(provider, symbol, date)
            if price:
                logger.info(f"Price for {symbol} fetched from {provider}")
                return price
        except Exception as e:
            logger.warning(f"{provider} failed for {symbol}: {e}")
            continue

    # All providers failed
    logger.error(f"All providers failed for {symbol}")
    await record_symbol_failure(symbol, date, "all_providers_exhausted")
    return None
```

**Batch completion logic**:
```python
async def run_symbol_batch():
    results = await fetch_all_symbol_prices()

    failed_symbols = [s for s in results if not s.success]

    if failed_symbols:
        # Record for admin visibility
        await record_batch_failures(
            batch_type="symbol_prices",
            failed_items=failed_symbols,
            total_items=len(results)
        )

    # Batch completes even with partial failures
    # Portfolio refresh will skip symbols without prices
    return {
        "status": "complete_with_warnings" if failed_symbols else "complete",
        "symbols_success": len(results) - len(failed_symbols),
        "symbols_failed": len(failed_symbols),
        "failed_symbols": [s.symbol for s in failed_symbols]
    }
```

---

## Portfolio Refresh Failures

**Strategy**: Retry once, skip private portfolios

```python
async def refresh_portfolio(portfolio: Portfolio, target_date: date) -> RefreshResult:
    """Refresh single portfolio with retry."""

    # Skip private portfolios (no market data available)
    if portfolio.is_private:
        logger.info(f"Skipping private portfolio {portfolio.id}")
        return RefreshResult(status="skipped", reason="private_portfolio")

    # First attempt
    try:
        await create_portfolio_snapshot(portfolio.id, target_date)
        return RefreshResult(status="success")
    except Exception as e:
        logger.warning(f"First attempt failed for {portfolio.id}: {e}")

    # Retry once
    try:
        await asyncio.sleep(1)  # Brief backoff
        await create_portfolio_snapshot(portfolio.id, target_date)
        return RefreshResult(status="success_on_retry")
    except Exception as e:
        logger.error(f"Retry failed for {portfolio.id}: {e}")
        await record_portfolio_failure(portfolio.id, target_date, str(e))
        return RefreshResult(status="failed", error=str(e))


async def run_portfolio_refresh():
    portfolios = await get_portfolios_without_snapshot(target_date)

    results = []
    for portfolio in portfolios:
        result = await refresh_portfolio(portfolio, target_date)
        results.append(result)

    failed = [r for r in results if r.status == "failed"]

    if failed:
        await record_batch_failures(
            batch_type="portfolio_refresh",
            failed_items=failed,
            total_items=len(results)
        )

    return {
        "status": "complete",
        "portfolios_success": len([r for r in results if "success" in r.status]),
        "portfolios_skipped": len([r for r in results if r.status == "skipped"]),
        "portfolios_failed": len(failed)
    }
```

---

## Admin Page: Failure Visibility

### Batch Status Panel

```typescript
// Admin dashboard component
interface BatchStatus {
  lastRun: Date;
  status: 'success' | 'complete_with_warnings' | 'failed';
  symbolsProcessed: number;
  symbolsFailed: number;
  failedSymbols: string[];
  portfoliosProcessed: number;
  portfoliosFailed: number;
  failedPortfolioIds: string[];
}
```

**Display**:
```
┌─────────────────────────────────────────────────────────┐
│ BATCH STATUS                                             │
├─────────────────────────────────────────────────────────┤
│ Symbol Batch (Jan 10, 2026 9:15 PM)                     │
│ Status: ⚠️ Complete with warnings                        │
│ Symbols: 497/500 success                                │
│ Failed: XYZ, ABC, DEF                                   │
├─────────────────────────────────────────────────────────┤
│ Portfolio Refresh (Jan 10, 2026 9:45 PM)                │
│ Status: ✅ Complete                                      │
│ Portfolios: 148/150 success                             │
│ Skipped (private): 5                                    │
│ Failed: 2 [View Details]                                │
└─────────────────────────────────────────────────────────┘
```

### Market Data Cache Status

```typescript
interface MarketDataStatus {
  latestPriceDate: Date;
  symbolCount: number;
  staleness: 'current' | 'stale_1d' | 'stale_2d+';
  lastRefreshAttempt: Date;
  lastRefreshStatus: 'success' | 'partial' | 'failed';
}
```

**Display**:
```
┌─────────────────────────────────────────────────────────┐
│ MARKET DATA CACHE                                        │
├─────────────────────────────────────────────────────────┤
│ Latest Price Date: January 10, 2026                     │
│ Symbols in Cache: 500                                   │
│ Status: ✅ Current                                       │
│                                                         │
│ If stale:                                               │
│ Status: ⚠️ Data is 2 days old (last: Jan 8, 2026)       │
│ [Trigger Manual Refresh]                                │
└─────────────────────────────────────────────────────────┘
```

---

## Admin API Endpoints

```python
@router.get("/admin/batch/status")
async def get_batch_status(db: AsyncSession = Depends(get_db)) -> BatchStatusResponse:
    """Get current batch status for admin dashboard."""

    # Latest symbol batch
    symbol_batch = await db.execute(
        select(BatchRunTracking)
        .where(BatchRunTracking.batch_type == 'symbol_batch')
        .order_by(BatchRunTracking.created_at.desc())
        .limit(1)
    )

    # Latest portfolio refresh
    portfolio_refresh = await db.execute(
        select(BatchRunTracking)
        .where(BatchRunTracking.batch_type == 'portfolio_refresh')
        .order_by(BatchRunTracking.created_at.desc())
        .limit(1)
    )

    # Market data staleness
    latest_price_date = await db.execute(
        select(func.max(SymbolPricesDaily.price_date))
    )

    return BatchStatusResponse(
        symbol_batch=symbol_batch.scalar_one_or_none(),
        portfolio_refresh=portfolio_refresh.scalar_one_or_none(),
        latest_price_date=latest_price_date.scalar(),
        staleness=calculate_staleness(latest_price_date.scalar())
    )


@router.get("/admin/batch/failures")
async def get_batch_failures(
    batch_type: Optional[str] = None,
    since: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
) -> List[BatchFailure]:
    """Get detailed failure records for admin review."""
    query = select(BatchFailureLog)

    if batch_type:
        query = query.where(BatchFailureLog.batch_type == batch_type)
    if since:
        query = query.where(BatchFailureLog.created_at >= since)

    query = query.order_by(BatchFailureLog.created_at.desc()).limit(100)

    result = await db.execute(query)
    return result.scalars().all()
```

---

## Unknown Symbol Handling (User-Facing)

**Command Center Page**: User can view and fix positions with unavailable data.

### Position Status Display

```typescript
interface PositionWithStatus {
  id: string;
  symbol: string;
  quantity: number;
  dataStatus: 'available' | 'unavailable' | 'pending';
  lastPriceDate?: Date;
  errorMessage?: string;
}

// Command center shows:
// ┌─────────────────────────────────────────────────────────┐
// │ AAPL    100 shares    $15,234.00    ✅ Data current     │
// │ GOOGL   50 shares     $8,750.00     ✅ Data current     │
// │ XYZ     25 shares     —             ⚠️ Data unavailable │
// │                                      [Edit] [Remove]    │
// └─────────────────────────────────────────────────────────┘
```

### User Actions

**Option 1: Edit Position** (fix the symbol)
```typescript
// User clicks Edit on unavailable position
// Modal shows:
// "Symbol XYZ not found. Did you mean:"
// - XYZ.TO (Toronto Stock Exchange)
// - XYZA (Alternative ticker)
// - [Enter correct symbol manually]
```

**Option 2: Keep As-Is**
- Position remains in portfolio
- Excluded from analytics calculations
- Shows "Data unavailable" in all views
- User understands this won't affect portfolio metrics

**Option 3: Remove Position**
- Delete position entirely
- Portfolio recalculates without it

### Frontend Implementation

```typescript
// Command center position row
function PositionRow({ position }: { position: PositionWithStatus }) {
  if (position.dataStatus === 'unavailable') {
    return (
      <tr className="bg-yellow-50">
        <td>{position.symbol}</td>
        <td>{position.quantity}</td>
        <td>—</td>
        <td>
          <Badge variant="warning">Data unavailable</Badge>
        </td>
        <td>
          <Button size="sm" onClick={() => openEditModal(position)}>
            Edit
          </Button>
          <Button size="sm" variant="ghost" onClick={() => removePosition(position.id)}>
            Remove
          </Button>
        </td>
      </tr>
    );
  }
  // ... normal position display
}
```

---

## Database: Failure Logging

```sql
-- New table for failure tracking
CREATE TABLE batch_failure_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_type VARCHAR(50) NOT NULL,  -- 'symbol_prices', 'portfolio_refresh', 'symbol_onboarding'
    batch_date DATE NOT NULL,
    item_id VARCHAR(100) NOT NULL,    -- symbol or portfolio_id
    error_type VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_batch_failure_type_date ON batch_failure_log(batch_type, batch_date);
CREATE INDEX idx_batch_failure_unresolved ON batch_failure_log(resolved_at) WHERE resolved_at IS NULL;
```

---

## Summary

| Failure Type | Retry Strategy | User Impact | Admin Visibility |
|--------------|----------------|-------------|------------------|
| Symbol price fetch | 4-provider cascade | None (uses last known) | Failed symbols listed |
| Portfolio refresh | 1 retry, skip private | Stale data indicator | Failed portfolios listed |
| Symbol onboarding | 3 retries with backoff | "Data unavailable" badge | Queue status shown |
| Unknown symbol | No retry (invalid) | Edit/remove on command center | Logged for review |
