# 17: API Contract Changes

## Overview

V2 is a **backend implementation change only**. API response formats stay the same. The frontend works unchanged - everything just gets faster.

---

## Principle: No Breaking Changes

| Endpoint | Response Format | Behavior Change |
|----------|-----------------|-----------------|
| `POST /portfolios` | **Same** | Faster (computes snapshot inline) |
| `POST /portfolios/{id}/calculate` | **Same** | No-op (returns success immediately) |
| `GET /onboarding/status/{id}` | **Same** | Always returns "completed" instantly |
| `GET /analytics/*` | **Same** | Reads from cache instead of DB |

---

## Endpoint Details

### `POST /api/v1/portfolios` (or `/onboarding/create-portfolio`)

**Response format**: Unchanged

```json
{
    "portfolio_id": "uuid-123"
}
```

**Behavior change**:
- V1: Creates portfolio, returns ID. Frontend must call `/calculate` next.
- V2: Creates portfolio + instant snapshot, returns ID. Snapshot already computed.

**Frontend impact**: None. Works exactly as before, just faster.

---

### `POST /api/v1/portfolios/{id}/calculate`

**Response format**: Unchanged

```json
{
    "status": "started"
}
```

**Behavior change**:
- V1: Triggers full 9-phase batch processing (15-20 min).
- V2: **No-op**. Returns success immediately. Does nothing because snapshot was already created during `POST /portfolios`.

**Frontend impact**: None. Frontend can continue calling this - it just returns instantly. Eventually can be removed as optional cleanup.

---

### `GET /api/v1/onboarding/status/{portfolio_id}`

**Response format**: Unchanged (same structure)

```json
{
    "status": "completed",
    "current_phase": "complete",
    "progress_percent": 100,
    "phases": { ... }
}
```

**Behavior change**:
- V1: Returns phase progress over 15-20 minutes.
- V2: Always returns "completed" immediately (because snapshot was created inline).

**Frontend impact**: None. Progress page will show 100% complete instantly. Eventually can remove polling as optional cleanup.

---

### `GET /api/v1/analytics/*` (all analytics endpoints)

**Response format**: Unchanged for all endpoints:
- `/analytics/portfolio/{id}/overview`
- `/analytics/portfolio/{id}/correlation-matrix`
- `/analytics/portfolio/{id}/factor-exposures`
- `/analytics/portfolio/{id}/positions/factor-exposures`
- `/analytics/portfolio/{id}/stress-test`
- `/analytics/portfolio/{id}/volatility`
- `/analytics/portfolio/{id}/sector-exposure`
- `/analytics/portfolio/{id}/concentration`

**Behavior change**:
- V1: Reads from database tables.
- V2: Reads from in-memory cache (faster).

**Frontend impact**: None. Same data, just faster.

---

## Unknown Symbols (Edge Case)

When a portfolio contains symbols not in the universe (~1% of cases):

**V2 Behavior**:
1. `POST /portfolios` creates portfolio + snapshot for known symbols only
2. Unknown symbols queued for background processing
3. Dashboard shows positions - unknown symbols show "Loading..." or placeholder values
4. Background job completes in 30-60 seconds
5. Next page refresh shows full data

**Frontend impact**: Minimal. Could optionally show a toast "Loading data for X new symbols..." but not required. The experience degrades gracefully.

---

## Optional Frontend Cleanup (Not Required)

After V2 is stable, frontend could optionally:

1. **Remove `/calculate` call** - No longer needed
2. **Skip progress page** - Redirect directly to dashboard
3. **Remove polling logic** - Status is always "completed"

These are performance optimizations, not requirements. V2 works with current frontend unchanged.

---

## Summary

| Aspect | V1 | V2 |
|--------|----|----|
| API response formats | Current | **Same** |
| Onboarding time | 15-20 min | < 5 sec |
| Frontend changes required | N/A | **None** |
| Breaking changes | N/A | **None** |

**V2 is transparent to the frontend.** Everything works the same, just faster.
