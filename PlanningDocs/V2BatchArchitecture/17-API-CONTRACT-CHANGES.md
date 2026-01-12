# 17: API Contract Changes

## Overview

V2 instant onboarding introduces **breaking API contract changes**. This document maps old endpoints to new behavior for frontend migration.

---

## Onboarding Endpoints

### `POST /api/v1/portfolios` (or `/onboarding/create-portfolio`)

**Current (V1) Response:**
```json
{
    "portfolio_id": "uuid-123"
}
```

**V2 Response (BREAKING CHANGE):**
```json
{
    "portfolio_id": "uuid-123",
    "status": "ready" | "partial",
    "pending_symbols": ["XYZ", "ABC"] | null,
    "snapshot_date": "2026-01-10"
}
```

**Frontend Migration:**
- Handle new `status` field
- Use `pending_symbols` to show loading indicators
- Display `snapshot_date` in confirmation

---

### `POST /api/v1/portfolios/{id}/calculate` (DEPRECATED)

**Current (V1):** Triggers full 9-phase batch processing. Required after portfolio creation.

**V2:** **DO NOT CALL.** Endpoint will be deprecated/removed.

**Reason:** V2 creates portfolio snapshot inline during `POST /portfolios`. No separate calculation trigger needed.

**Frontend Migration:**
```typescript
// BEFORE (V1)
const portfolio = await createPortfolio(file);
await triggerCalculations(portfolio.id);  // REMOVE THIS LINE

// AFTER (V2)
const response = await createPortfolio(file);
// Analytics are already computed - go to dashboard
```

---

### `GET /api/v1/onboarding/status/{portfolio_id}`

**Current (V1) Response:**
```json
{
    "status": "running" | "completed" | "failed",
    "current_phase": "phase_2",
    "progress_percent": 45,
    "phases": {
        "phase_1": {"status": "completed", "progress": 100},
        "phase_1_5": {"status": "completed", "progress": 100},
        "phase_2": {"status": "running", "progress": 45},
        ...
    },
    "activity_log": [
        {"timestamp": "...", "message": "Fetching market data..."},
        ...
    ]
}
```

**V2 Response (SIMPLIFIED):**
```json
{
    "status": "ready" | "partial",
    "pending_symbols": [
        {"symbol": "XYZ", "status": "processing"},
        {"symbol": "ABC", "status": "pending"}
    ]
}
```

**Changes:**
- No more 9-phase tracking
- No more activity log
- Only tracks symbol onboarding (rare case)
- Most users get `status: "ready"` immediately

**Frontend Migration:**
- Remove phase progress UI
- Remove activity log display
- Only show symbol status when `status === "partial"`

---

## Summary: Frontend Must Remove

| Current Frontend Behavior | V2 Action |
|---------------------------|-----------|
| Call `triggerCalculations()` after upload | **REMOVE** - no longer needed |
| Redirect to `/onboarding/progress` | **CHANGE** - redirect to dashboard |
| Poll `/onboarding/status` for 15-20 min | **CHANGE** - only poll if `status === "partial"` |
| Display 9-phase progress bars | **REMOVE** - not applicable |
| Display activity log | **REMOVE** - not applicable |
| Show "Estimated time: 15-20 minutes" | **REMOVE** - instant for most users |

---

## Summary: Frontend Must Add

| New Behavior | Implementation |
|--------------|----------------|
| Handle new `status` field in response | Check `ready` vs `partial` |
| Show toast for partial status | "Loading data for N symbols..." |
| Allow dashboard access immediately | Always redirect to dashboard |
| Optional: Symbol loading indicators | Show pending symbols on dashboard |

---

## API Contract Matrix

| Endpoint | V1 Behavior | V2 Behavior | Breaking? |
|----------|-------------|-------------|-----------|
| `POST /portfolios` | Returns `portfolio_id` only | Returns `portfolio_id`, `status`, `pending_symbols`, `snapshot_date` | Yes - response shape |
| `POST /portfolios/{id}/calculate` | Triggers batch | **DEPRECATED** - do not call | Yes - removal |
| `GET /onboarding/status/{id}` | 9-phase progress | Simple `ready`/`partial` status | Yes - response shape |
| `GET /analytics/*` | Reads from stored rows | Computes from cache (see doc 18) | No - same response |

---

## Migration Sequence

### Phase 1: Backend Deploys V2 Endpoints

1. Update `POST /portfolios` to return new response shape
2. Keep `POST /calculate` functional but log deprecation warnings
3. Simplify `GET /onboarding/status` response

### Phase 2: Frontend Migrates

1. Update `createPortfolio()` return type handling
2. Remove `triggerCalculations()` call
3. Update redirect logic based on `status`
4. Replace progress page with simple symbol status (or remove)

### Phase 3: Cleanup

1. Remove `POST /calculate` endpoint
2. Remove phase tracking from `onboarding_status.py`
3. Remove frontend progress components

---

## Response Type Definitions

### V2 CreatePortfolioResponse

```typescript
interface CreatePortfolioResponse {
    portfolio_id: string;
    status: 'ready' | 'partial';
    pending_symbols: string[] | null;
    snapshot_date: string;  // ISO date
}
```

### V2 OnboardingStatusResponse

```typescript
interface OnboardingStatusResponse {
    status: 'ready' | 'partial';
    pending_symbols: PendingSymbol[];
}

interface PendingSymbol {
    symbol: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    error_message?: string;
}
```

---

## Backend Implementation Notes

### `portfolios.py`

```python
@router.post("/portfolios")
async def create_portfolio(...) -> CreatePortfolioResponse:
    # Create portfolio and positions
    portfolio = await create_portfolio_record(...)

    # Check symbol universe
    known, unknown = await check_symbol_universe(symbols)

    # Create instant snapshot (using cached prices)
    snapshot = await create_portfolio_snapshot(
        portfolio.id,
        symbols_to_include=known
    )

    # Queue unknown symbols (in-memory queue)
    if unknown:
        for symbol in unknown:
            await symbol_onboarding_queue.enqueue(symbol)
        asyncio.create_task(process_onboarding_queue())

    # Return V2 response
    return CreatePortfolioResponse(
        portfolio_id=str(portfolio.id),
        status="ready" if not unknown else "partial",
        pending_symbols=list(unknown) if unknown else None,
        snapshot_date=snapshot.snapshot_date.isoformat()
    )
```

### `onboarding_status.py`

```python
@router.get("/onboarding/status/{portfolio_id}")
async def get_onboarding_status(portfolio_id: UUID) -> OnboardingStatusResponse:
    # Get positions in this portfolio
    positions = await get_positions(portfolio_id)
    symbols = [p.symbol for p in positions]

    # Check in-memory queue for pending symbols
    pending_symbols = []
    for symbol in symbols:
        job = await symbol_onboarding_queue.get_status(symbol)
        if job and job.status in ('pending', 'processing'):
            pending_symbols.append(PendingSymbol(
                symbol=symbol,
                status=job.status,
                error_message=job.error_message
            ))

    return OnboardingStatusResponse(
        status="ready" if not pending_symbols else "partial",
        pending_symbols=pending_symbols
    )
```
