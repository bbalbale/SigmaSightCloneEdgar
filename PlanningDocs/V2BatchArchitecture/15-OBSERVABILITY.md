# 15: Observability

## Overview

Structured logging plus admin dashboard for V2 batch observability. No external monitoring services for now - just logs and admin APIs.

---

## Structured Logging

All V2 components use consistent log format for easy parsing:

```python
# Log format for batch operations
logger.info(
    "V2_BATCH_STEP",
    extra={
        "step": "symbol_prices",
        "status": "completed",
        "duration_ms": 300000,
        "items_processed": 500,
        "items_failed": 3
    }
)

# Log format for onboarding
logger.info(
    "V2_ONBOARDING",
    extra={
        "step": "portfolio_created",
        "user_id": "user-123",
        "portfolio_id": "port-456",
        "duration_ms": 2100
    }
)
```

### Log Events

**Symbol Batch:**
```
V2_BATCH_STEP step=symbol_batch_start batch_date=2026-01-10
V2_BATCH_STEP step=symbol_prices status=completed duration_ms=300000 symbols=500 failed=3
V2_BATCH_STEP step=symbol_factors status=completed duration_ms=420000 symbols=500 failed=0
V2_BATCH_STEP step=cache_refresh status=completed symbols=500
V2_BATCH_STEP step=symbol_batch_complete duration_ms=720000 success=true
```

**Portfolio Refresh:**
```
V2_BATCH_STEP step=portfolio_refresh_start batch_date=2026-01-10
V2_BATCH_STEP step=symbol_batch_check status=verified
V2_BATCH_STEP step=portfolios_query count=150
V2_BATCH_STEP step=portfolio_snapshot portfolio_id=abc-123 status=created
V2_BATCH_STEP step=portfolio_refresh_complete duration_ms=300000 success=148 failed=2 skipped=5
```

**Symbol Onboarding:**
```
V2_ONBOARDING step=queued symbol=XYZ user_id=user-123
V2_ONBOARDING step=processing symbol=XYZ
V2_ONBOARDING step=prices_fetched symbol=XYZ duration_ms=3000
V2_ONBOARDING step=factors_calculated symbol=XYZ duration_ms=2000
V2_ONBOARDING step=cache_add symbol=XYZ
V2_ONBOARDING step=complete symbol=XYZ duration_ms=5500
```

---

## Admin APIs

### Existing Endpoints (keep as-is)

| Endpoint | Purpose |
|----------|---------|
| `POST /admin/batch/run` | Trigger batch manually |
| `GET /admin/batch/run/current` | Current batch status |
| `GET /admin/batch/data-quality` | Data quality metrics |

### New Endpoints

#### 1. Batch History

```python
@router.get("/admin/batch/history")
async def get_batch_history(
    limit: int = 10,
    batch_type: Optional[str] = None,  # 'symbol_batch' | 'portfolio_refresh'
    db: AsyncSession = Depends(get_db)
) -> List[BatchRunSummary]:
    """Get history of recent batch runs."""
    query = select(BatchRunTracking).order_by(
        BatchRunTracking.created_at.desc()
    ).limit(limit)

    if batch_type:
        query = query.where(BatchRunTracking.batch_type == batch_type)

    result = await db.execute(query)
    return [BatchRunSummary.from_orm(r) for r in result.scalars()]


class BatchRunSummary(BaseModel):
    id: str
    batch_type: str  # 'symbol_batch' | 'portfolio_refresh'
    batch_date: date
    status: str  # 'completed' | 'completed_with_warnings' | 'failed'
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    items_processed: int
    items_failed: int
    error_message: Optional[str]
```

#### 2. Cache Status

```python
@router.get("/admin/cache/status")
async def get_cache_status() -> CacheStatusResponse:
    """Get in-memory cache status."""
    return CacheStatusResponse(
        symbols_cached=symbol_cache.symbols_in_cache(),
        latest_price_date=symbol_cache.get_latest_price_date(),
        last_refresh=symbol_cache._last_refresh,
        memory_estimate_mb=round(symbol_cache.symbols_in_cache() * 350 / 1_000_000, 2)
    )


class CacheStatusResponse(BaseModel):
    symbols_cached: int
    latest_price_date: Optional[date]
    last_refresh: Optional[date]
    memory_estimate_mb: float
```

#### 3. Onboarding Queue Status

```python
@router.get("/admin/onboarding/queue")
async def get_onboarding_queue() -> OnboardingQueueStatus:
    """Get symbol onboarding queue status from in-memory queue."""
    from app.batch.symbol_onboarding import symbol_onboarding_queue

    # Get all jobs from in-memory queue
    jobs = symbol_onboarding_queue._jobs

    pending = [j for j in jobs.values() if j.status == 'pending']
    processing = [j for j in jobs.values() if j.status == 'processing']
    failed = [j for j in jobs.values() if j.status == 'failed']

    return OnboardingQueueStatus(
        pending_count=len(pending),
        processing_count=len(processing),
        failed_count=len(failed),
        pending_symbols=[
            {"symbol": j.symbol, "queued_at": j.started_at}
            for j in pending[:20]
        ]
    )


class OnboardingQueueStatus(BaseModel):
    pending_count: int
    processing_count: int
    failed_count: int
    pending_symbols: List[dict]
```

**Note**: Onboarding queue is in-memory, so completed jobs are removed immediately (no stale data). Failed jobs remain until server restart or manual clear.

#### 4. Data Freshness (from freshness doc)

```python
@router.get("/admin/data/freshness")
async def get_data_freshness(
    db: AsyncSession = Depends(get_db)
) -> DataFreshnessResponse:
    """Get market data freshness status."""
    latest_price_date = await get_latest_price_date(db)
    staleness_days = calculate_staleness_days(latest_price_date)

    return DataFreshnessResponse(
        latest_price_date=latest_price_date,
        trading_days_stale=staleness_days,
        status="current" if staleness_days == 0 else f"stale_{staleness_days}d",
        alert_level="none" if staleness_days == 0 else "warning" if staleness_days == 1 else "critical"
    )
```

#### 5. Batch Failures (from failure doc)

```python
@router.get("/admin/batch/failures")
async def get_batch_failures(
    batch_type: Optional[str] = None,
    since: Optional[date] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> List[BatchFailure]:
    """Get recent batch failures."""
    query = select(BatchFailureLog).order_by(
        BatchFailureLog.created_at.desc()
    ).limit(limit)

    if batch_type:
        query = query.where(BatchFailureLog.batch_type == batch_type)
    if since:
        query = query.where(BatchFailureLog.created_at >= since)

    result = await db.execute(query)
    return result.scalars().all()
```

---

## Frontend Admin Page Updates

### Current Admin Page Structure

```
/admin
├── Batch Processing (existing)
│   ├── Trigger Batch button
│   ├── Current batch status
│   └── Data quality metrics
```

### New Admin Page Structure

```
/admin
├── System Status (NEW - top summary cards)
│   ├── Data Freshness card
│   ├── Cache Status card
│   └── Onboarding Queue card
│
├── Batch Processing (enhanced)
│   ├── Symbol Batch panel
│   │   ├── Last run status/time/duration
│   │   ├── Symbols processed/failed
│   │   └── Failed symbols list (if any)
│   ├── Portfolio Refresh panel
│   │   ├── Last run status/time/duration
│   │   ├── Portfolios processed/failed/skipped
│   │   └── Failed portfolios list (if any)
│   ├── Batch History table
│   └── Trigger Batch button
│
├── Failures (NEW)
│   ├── Filter by type/date
│   └── Failure list with details
│
└── Data Quality (existing, keep)
```

### Component Mockups

#### System Status Cards

```typescript
// Top of admin page - 3 summary cards

function SystemStatusCards() {
  const { data: freshness } = useQuery('freshness', fetchFreshness);
  const { data: cache } = useQuery('cache', fetchCacheStatus);
  const { data: queue } = useQuery('queue', fetchQueueStatus);

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {/* Data Freshness */}
      <Card>
        <CardHeader>Data Freshness</CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatDate(freshness?.latest_price_date)}
          </div>
          <Badge variant={freshness?.alert_level === 'none' ? 'success' : 'warning'}>
            {freshness?.status}
          </Badge>
        </CardContent>
      </Card>

      {/* Cache Status */}
      <Card>
        <CardHeader>Symbol Cache</CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {cache?.symbols_cached} symbols
          </div>
          <div className="text-sm text-muted">
            {cache?.memory_estimate_mb} MB
          </div>
        </CardContent>
      </Card>

      {/* Onboarding Queue */}
      <Card>
        <CardHeader>Onboarding Queue</CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {queue?.pending_count + queue?.processing_count} pending
          </div>
          <div className="text-sm text-muted">
            {queue?.completed_today} completed today
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

#### Batch Status Panels

```typescript
function BatchStatusPanels() {
  const { data: history } = useQuery('batchHistory', fetchBatchHistory);

  const lastSymbolBatch = history?.find(h => h.batch_type === 'symbol_batch');
  const lastPortfolioRefresh = history?.find(h => h.batch_type === 'portfolio_refresh');

  return (
    <div className="grid grid-cols-2 gap-4 mb-6">
      {/* Symbol Batch */}
      <Card>
        <CardHeader>
          Symbol Batch
          <StatusBadge status={lastSymbolBatch?.status} />
        </CardHeader>
        <CardContent>
          <div>Last run: {formatDateTime(lastSymbolBatch?.completed_at)}</div>
          <div>Duration: {lastSymbolBatch?.duration_seconds}s</div>
          <div>Symbols: {lastSymbolBatch?.items_processed} processed</div>
          {lastSymbolBatch?.items_failed > 0 && (
            <div className="text-red-500">
              {lastSymbolBatch.items_failed} failed
              <Button size="sm" variant="link">View</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Portfolio Refresh */}
      <Card>
        <CardHeader>
          Portfolio Refresh
          <StatusBadge status={lastPortfolioRefresh?.status} />
        </CardHeader>
        <CardContent>
          <div>Last run: {formatDateTime(lastPortfolioRefresh?.completed_at)}</div>
          <div>Duration: {lastPortfolioRefresh?.duration_seconds}s</div>
          <div>Portfolios: {lastPortfolioRefresh?.items_processed} processed</div>
          {lastPortfolioRefresh?.items_failed > 0 && (
            <div className="text-red-500">
              {lastPortfolioRefresh.items_failed} failed
              <Button size="sm" variant="link">View</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

#### Batch History Table

```typescript
function BatchHistoryTable() {
  const { data: history } = useQuery('batchHistory', () => fetchBatchHistory(10));

  return (
    <Card>
      <CardHeader>Batch History</CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Type</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Processed</TableHead>
            <TableHead>Failed</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {history?.map(run => (
            <TableRow key={run.id}>
              <TableCell>{run.batch_type}</TableCell>
              <TableCell>{formatDate(run.batch_date)}</TableCell>
              <TableCell><StatusBadge status={run.status} /></TableCell>
              <TableCell>{run.duration_seconds}s</TableCell>
              <TableCell>{run.items_processed}</TableCell>
              <TableCell className={run.items_failed > 0 ? 'text-red-500' : ''}>
                {run.items_failed}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
```

---

## API Summary

| Endpoint | Purpose | New? |
|----------|---------|------|
| `GET /admin/batch/run/current` | Current batch status | Existing |
| `GET /admin/batch/history` | Last N batch runs | New |
| `GET /admin/cache/status` | In-memory cache status | New |
| `GET /admin/onboarding/queue` | Symbol onboarding queue | New |
| `GET /admin/data/freshness` | Market data freshness | New |
| `GET /admin/batch/failures` | Recent failures | New |
| `POST /admin/batch/run` | Trigger batch | Existing |
| `GET /admin/batch/data-quality` | Data quality metrics | Existing |

---

## Frontend Changes Summary

| File | Changes |
|------|---------|
| `frontend/app/admin/page.tsx` | Add SystemStatusCards, BatchStatusPanels, BatchHistoryTable |
| `frontend/src/services/adminApi.ts` | Add fetchBatchHistory, fetchCacheStatus, fetchQueueStatus, fetchFreshness, fetchFailures |
| `frontend/src/components/admin/SystemStatusCards.tsx` | New component |
| `frontend/src/components/admin/BatchStatusPanels.tsx` | New component |
| `frontend/src/components/admin/BatchHistoryTable.tsx` | New component |
| `frontend/src/components/admin/FailuresPanel.tsx` | New component |
