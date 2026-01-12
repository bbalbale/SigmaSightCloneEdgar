# Architecture V2 Plan - Phase 7.x Reconciliation Edits

**Purpose**: This document contains specific edits to `ARCHITECTURE_V2_IMPLEMENTATION_PLAN.md` to reconcile with the Phase 7.x work already deployed.

**Core Change**: Phase 7.x infrastructure is REPURPOSED, not deprecated. The onboarding UI is REFACTORED to be conditional, not removed.

---

## Edit 1: Replace Section 10.7 (Frontend Changes)

**Location**: Section 10.7 (lines ~1499-1531)

**DELETE this content:**
```markdown
### 10.7 Frontend Changes (Suggested)

**Current frontend (waiting state):**
...
**New frontend (instant):**
...
```

**REPLACE WITH:**

```markdown
### 10.7 Frontend Changes (Conditional Flow)

The frontend onboarding flow becomes **conditional** based on symbol readiness:

#### 10.7.1 Fast Path (99% of users - all symbols known)

When all symbols are in the universe, skip the progress screen entirely:

```typescript
// In CSV upload handler or create-portfolio response handler
const response = await createPortfolio(csvData)

if (response.status === 'ready') {
  // No progress screen needed - go straight to dashboard
  router.push(`/dashboard/${response.portfolio_id}`)
  toast.success('Portfolio created with full analytics!')
} else if (response.status === 'pending') {
  // Some symbols need loading - show progress
  router.push(`/onboarding/progress/${response.portfolio_id}`)
}
```

#### 10.7.2 Slow Path (rare - unknown symbols)

When some symbols need onboarding, show a **simplified** progress screen:

```tsx
// OnboardingProgress.tsx - Refactored for V2
export function OnboardingProgress({ portfolioId }: Props) {
  const { data, isLoading } = useOnboardingStatus(portfolioId)

  // Fast path: Ready - redirect immediately
  if (data?.status === 'ready') {
    router.push(`/dashboard/${portfolioId}`)
    return null
  }

  // Error state
  if (data?.status === 'error') {
    return <OnboardingError message={data.message} />
  }

  // Pending state: Show simplified symbol loading progress
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <Card className="w-full max-w-md p-8">
        <h2 className="text-xl font-semibold mb-4">
          Setting up your portfolio...
        </h2>

        {/* Simplified progress - not 9 phases */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-500" />
            <span>Portfolio created</span>
          </div>

          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-500" />
            <span>Positions imported</span>
          </div>

          {data?.pending_symbols?.length > 0 && (
            <div className="flex items-center gap-3">
              <Loader2 className="animate-spin text-blue-500" />
              <span>
                Loading data for {data.pending_symbols.length} new symbol(s)...
              </span>
            </div>
          )}

          {data?.pending_symbols?.length === 0 && (
            <div className="flex items-center gap-3">
              <Loader2 className="animate-spin text-blue-500" />
              <span>Computing analytics...</span>
            </div>
          )}
        </div>

        {/* Estimated time - only shown for pending symbols */}
        {data?.estimated_seconds_remaining && (
          <p className="text-sm text-muted-foreground mt-4">
            Estimated time: {data.estimated_seconds_remaining} seconds
          </p>
        )}

        {/* Show pending symbols if any */}
        {data?.pending_symbols?.length > 0 && (
          <div className="mt-4 p-3 bg-muted rounded-md">
            <p className="text-sm font-medium">New symbols being processed:</p>
            <p className="text-sm text-muted-foreground">
              {data.pending_symbols.join(', ')}
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}
```

#### 10.7.3 What Changes in the UI

| Aspect | Phase 7.6 (Current) | V2 (New) |
|--------|---------------------|----------|
| Progress visualization | 9-phase tracker | 3-step checklist |
| Activity log | Detailed, scrolling | Removed (too fast) |
| Estimated time | 15-30 minutes | 30-60 seconds max |
| Polling frequency | 2 seconds | 5 seconds |
| Default flow | Always show progress | Skip if ready |

#### 10.7.4 Reusing Phase 7.6 Components

The Phase 7.6 `OnboardingProgress.tsx` is **refactored**, not deleted:

1. **Keep**: Card layout, loading states, error handling, routing logic
2. **Remove**: 9-phase progress bars, activity log, phase-by-phase details
3. **Add**: Conditional redirect for fast path, pending symbols display
```

---

## Edit 2: Replace Section 10.9 (Deprecations)

**Location**: Section 10.9 (lines ~1543-1569)

**DELETE this content:**
```markdown
### 10.9 Deprecations

The following will be deprecated/simplified:

1. **Phase 7.1-7.4 Progress Tracking FOR ONBOARDING** - No longer needed
...
```

**REPLACE WITH:**

```markdown
### 10.9 Phase 7.x Reuse Strategy

The Phase 7.x infrastructure is **REPURPOSED**, not deprecated. Here's the detailed breakdown:

#### 10.9.1 Infrastructure That Gets REUSED

| Component | Current Use | V2 Use | Location |
|-----------|-------------|--------|----------|
| `batch_run_tracker.py` | Onboarding progress | Daily symbol batch | Backend |
| `BatchActivityLogHandler` | Onboarding logs | Symbol batch logs | Backend |
| `PhaseProgress` dataclass | 9 onboarding phases | 6 symbol batch phases | Backend |
| `CompletedRunStatus` | 60s TTL for onboarding | 60s TTL for symbol batch | Backend |
| Admin batch status endpoint | Onboarding monitoring | Symbol batch monitoring | API |

#### 10.9.2 Frontend Components - Refactor Plan

| Component | Action | Details |
|-----------|--------|---------|
| `OnboardingProgress.tsx` | **REFACTOR** | Remove 9-phase UI, add conditional redirect, simplify to 3-step checklist |
| `useOnboardingStatus.ts` | **SIMPLIFY** | Change status enum, reduce polling frequency |
| `OnboardingComplete.tsx` | **DELETE** | Merged into conditional OnboardingProgress |
| `OnboardingError.tsx` | **KEEP** | Still needed for error states |
| `progress/page.tsx` | **SIMPLIFY** | Remove phase routing, single component |

#### 10.9.3 Backend Changes - What Moves Where

**FROM onboarding flow TO symbol batch:**
```python
# These calls MOVE from onboarding.py to symbol_batch_runner.py:
batch_run_tracker.start(...)
batch_run_tracker.start_phase(...)
batch_run_tracker.update_phase_progress(...)
batch_run_tracker.complete_phase(...)
batch_run_tracker.add_activity(...)
batch_run_tracker.complete(...)
```

**REMOVED from onboarding flow:**
```python
# These are no longer called during onboarding:
batch_run_tracker.set_portfolio_id(...)  # Onboarding doesn't track phases
batch_orchestrator.run_daily_batch_sequence(...)  # Onboarding doesn't run batch
```

#### 10.9.4 Status Response Changes

**Current (Phase 7.x):**
```typescript
interface OnboardingStatusResponse {
  status: 'not_started' | 'running' | 'completed' | 'partial' | 'failed'
  current_phase: string
  phases: PhaseProgress[]
  activity_log: ActivityEntry[]
  estimated_remaining_seconds: number
}
```

**V2 (Simplified):**
```typescript
interface OnboardingStatusResponse {
  status: 'ready' | 'pending' | 'error'
  portfolio_id: string
  analytics_available: boolean
  pending_symbols: string[] | null
  estimated_seconds_remaining: number | null  // Max 120 seconds
  message: string
}
```

#### 10.9.5 What We're NOT Deprecating

To be clear, the following are **KEPT**:

1. **`batch_run_tracker.py`** - Core tracking infrastructure, reused for symbol batch
2. **Phase tracking dataclasses** - `PhaseProgress`, `ActivityLogEntry`, `CompletedRunStatus`
3. **Admin visibility** - Admins can still monitor batch progress
4. **Activity logging** - Moves to symbol batch monitoring
5. **Error handling patterns** - Still used for symbol onboarding failures
```

---

## Edit 3: Update Section 11.2 (Compatibility Matrix)

**Location**: Section 11.2 (lines ~1592-1603)

**DELETE this content:**
```markdown
### 11.2 Compatibility Matrix

| Phase 7.x Feature | Onboarding | Symbol Batch | Portfolio Batch |
|-------------------|------------|--------------|-----------------|
| Activity Log | ❌ DEPRECATED | ✅ REUSE | ✅ KEEP |
...
```

**REPLACE WITH:**

```markdown
### 11.2 Compatibility Matrix (Updated)

| Phase 7.x Feature | Onboarding | Symbol Batch | Admin Ops |
|-------------------|------------|--------------|-----------|
| `batch_run_tracker` | ⚠️ NOT USED | ✅ REUSE | ✅ KEEP |
| Activity Log | ⚠️ NOT USED | ✅ REUSE | ✅ KEEP |
| Phase Progress | ⚠️ NOT USED | ✅ REUSE (6 phases) | ✅ KEEP |
| Completed Status TTL | ⚠️ NOT USED | ✅ KEEP (60s) | ✅ KEEP |
| 9-Phase Tracking | ⚠️ NOT USED | ⚠️ REPLACE (6 phases) | ✅ KEEP |
| Progress UI | ⚠️ REFACTOR | N/A (admin only) | ✅ KEEP |

**Legend:**
- ✅ REUSE/KEEP: Used as-is or with minor modifications
- ⚠️ NOT USED: Not called in this flow, but code remains
- ⚠️ REFACTOR: Code modified but not deleted
- ⚠️ REPLACE: Different phase structure

**Key Insight**: The Phase 7.x code is NOT deleted. It's simply not called during user onboarding because onboarding no longer runs batch phases. The infrastructure remains for symbol batch and admin operations.
```

---

## Edit 4: Update Section 11.4 (What Gets Deprecated)

**Location**: Section 11.4 (lines ~1624-1649)

**DELETE the entire section and REPLACE WITH:**

```markdown
### 11.4 Onboarding Flow Changes (Not Deprecation)

**Current onboarding flow** (15-30 minutes, uses Phase 7.x):
```
User uploads CSV
  → Create portfolio
  → Redirect to /onboarding/progress/{id}
  → Poll status every 2 seconds
  → Show 9-phase progress for 15-30 minutes
  → Redirect to dashboard when complete
```

**V2 onboarding flow** (< 5 seconds, Phase 7.x not invoked):
```
User uploads CSV
  → Create portfolio
  → Check symbol readiness
  → If all ready: Redirect directly to dashboard (skip progress screen)
  → If pending: Redirect to simplified progress screen
    → Poll status every 5 seconds
    → Show "Loading N symbols..." for 30-60 seconds max
    → Redirect to dashboard when complete
```

**What changes:**
1. **No batch phases run** - Symbol data is pre-computed
2. **Progress screen is conditional** - Skipped for 99% of users
3. **Simplified progress UI** - 3-step checklist, not 9-phase tracker
4. **Faster polling** - 5 seconds, not 2 seconds (less urgent)
5. **Shorter timeout** - 120 seconds max, not unlimited

**What stays the same:**
1. **Backend tracking infrastructure** - Reused for symbol batch
2. **Error handling** - Same patterns for failures
3. **Admin monitoring** - Same endpoints, different use case
```

---

## Edit 5: Update Appendix A (File Reference)

**Location**: Appendix A - "Current Files to Modify" table (lines ~2139-2156)

**ADD these rows to the table:**

```markdown
| `OnboardingProgress.tsx` | REFACTOR | Remove 9-phase UI, add conditional redirect, simplify to 3-step |
| `useOnboardingStatus.ts` | SIMPLIFY | Change status enum to ready/pending/error, 5s polling |
| `OnboardingComplete.tsx` | DELETE | Functionality merged into OnboardingProgress |
| `progress/page.tsx` | SIMPLIFY | Remove phase-based routing |
```

**UPDATE these existing rows:**

```markdown
# Change FROM:
| `onboarding_status.py` | SIMPLIFY | Remove 9-phase tracking, use simple ready/pending/error status |

# Change TO:
| `onboarding_status.py` | SIMPLIFY | New response schema (ready/pending/error), remove phase details |
```

---

## Edit 6: Add New Section 10.10 (Migration Path for Phase 7.6 Code)

**Location**: After Section 10.9, before Section 11

**ADD this new section:**

```markdown
### 10.10 Migration Path for Phase 7.6 Code

This section provides a concrete migration path for the Phase 7.6 unified progress screen.

#### 10.10.1 Files to Modify

| File | Lines of Code | Action | Effort |
|------|---------------|--------|--------|
| `OnboardingProgress.tsx` | ~270 | Refactor | Medium |
| `useOnboardingStatus.ts` | ~80 | Simplify | Low |
| `OnboardingComplete.tsx` | ~50 | Delete | Trivial |
| `OnboardingError.tsx` | ~40 | Keep | None |
| `progress/page.tsx` | ~30 | Simplify | Low |

#### 10.10.2 OnboardingProgress.tsx Refactor Steps

1. **Keep**:
   - Card/container layout
   - Loading spinner components
   - Error state rendering
   - Router navigation logic
   - Toast notifications

2. **Remove**:
   - `PhaseProgressBar` component usage
   - `ActivityLog` component usage
   - 9-phase iteration logic
   - `PHASE_ORDER` constant usage
   - Detailed phase descriptions

3. **Add**:
   - Conditional redirect check at component mount
   - `pending_symbols` display
   - Simplified 3-step checklist
   - Reduced polling interval (5s)

4. **Refactor**:
   - Status type from `'running' | 'completed' | 'partial' | 'failed'` to `'ready' | 'pending' | 'error'`
   - Remove phase-based progress calculation
   - Simplify estimated time display

#### 10.10.3 useOnboardingStatus.ts Changes

```typescript
// BEFORE (Phase 7.6)
interface OnboardingStatus {
  status: 'not_started' | 'running' | 'completed' | 'partial' | 'failed'
  portfolio_id: string
  current_phase?: string
  phases?: PhaseProgress[]
  activity_log?: ActivityEntry[]
}

const POLL_INTERVAL = 2000  // 2 seconds
const TERMINAL_STATES = ['completed', 'partial', 'failed']

// AFTER (V2)
interface OnboardingStatus {
  status: 'ready' | 'pending' | 'error'
  portfolio_id: string
  analytics_available: boolean
  pending_symbols: string[] | null
  estimated_seconds_remaining: number | null
  message: string
}

const POLL_INTERVAL = 5000  // 5 seconds
const TERMINAL_STATES = ['ready', 'error']
const MAX_POLL_TIME = 120000  // 2 minutes max
```

#### 10.10.4 Backward Compatibility During Migration

During the V2 migration (Weeks 1-4), the old onboarding flow continues to work. The frontend changes happen in Week 5 alongside the backend onboarding changes.

**Week 1-4**: Old frontend + old backend (Phase 7.6 flow)
**Week 5**: New frontend + new backend (V2 flow)
**Week 6**: Cleanup, remove dead code

This ensures no broken state during migration.
```

---

## Summary of Edits

| Section | Change Type | Key Message |
|---------|-------------|-------------|
| 10.7 | REPLACE | Frontend is conditional, not deprecated |
| 10.9 | REPLACE | "Reuse Strategy" not "Deprecations" |
| 10.10 | ADD NEW | Concrete migration path for Phase 7.6 |
| 11.2 | REPLACE | Updated compatibility matrix |
| 11.4 | REPLACE | "Flow Changes" not "What Gets Deprecated" |
| Appendix A | UPDATE | Add frontend files to modification list |

---

## How to Apply These Edits

1. Open `ARCHITECTURE_V2_IMPLEMENTATION_PLAN.md`
2. Find each section by line number or heading
3. Replace the content as specified above
4. Review the full document for consistency
5. Update the "Last Updated" date at the top

After applying these edits, the V2 plan will properly acknowledge the Phase 7.x work and provide a clear migration path that reuses the infrastructure rather than discarding it.

---

## Edit 7: Add New Section 4.5 (Unknown Symbol Handling)

**Location**: After Section 4.4, before Section 5

**ADD this new section:**

```markdown
### 4.5 Unknown Symbol Handling (Reusing Existing Infrastructure)

This section describes how V2 handles symbols not yet in `symbol_universe`, leveraging existing code rather than building new infrastructure.

#### 4.5.1 Existing Infrastructure We Reuse

| Component | Location | What It Does | How V2 Uses It |
|-----------|----------|--------------|----------------|
| `symbol_validator.py` | `app/services/` | Validates symbols against YFinance with 12-hour cache | Called during portfolio creation to validate unknown symbols |
| `validate_symbol()` | `symbol_validator.py:73` | Single symbol validation with caching | Per-symbol validation at creation time |
| `validate_symbols()` | `symbol_validator.py:116` | Batch validation with concurrency control | Validate all unknown symbols in one call |
| `market_data_collector.py` | `app/batch/` | Fetches historical prices, calculates factors | Mini-batch for unknown symbols only |
| `batch_run_tracker.py` | `app/batch/` | Phase tracking, activity logging | Track symbol onboarding progress |
| Phase 7.x UI | `OnboardingProgress.tsx` | Progress display, polling | Show symbol loading progress |

#### 4.5.2 Detection Flow (During Portfolio Creation)

```python
# In onboarding_service.py - MODIFIED create_portfolio_with_csv()

async def create_portfolio_with_csv(...):
    # ... existing validation ...

    # NEW: After CSV parsing, check symbol_universe
    symbols_from_csv = {pos.symbol for pos in csv_result.positions}

    # Query symbol_universe for known symbols
    known_symbols = await db.execute(
        select(SymbolUniverse.symbol)
        .where(SymbolUniverse.symbol.in_(symbols_from_csv))
        .where(SymbolUniverse.status == 'active')
    )
    known_set = {row[0] for row in known_symbols.all()}

    unknown_symbols = symbols_from_csv - known_set

    # NEW: Validate unknown symbols against YFinance (EXISTING CODE)
    if unknown_symbols:
        from app.services.symbol_validator import validate_symbols
        valid_unknown, invalid_unknown = await validate_symbols(
            unknown_symbols,
            treat_synthetic_as_valid=True
        )

        if invalid_unknown:
            # Return error - these symbols don't exist in market data
            raise CSVValidationError(
                code="ERR_SYMBOL_INVALID",
                message=f"Invalid symbols: {', '.join(invalid_unknown)}",
                details={"invalid_symbols": list(invalid_unknown)}
            )

    # ... create portfolio and positions ...

    # NEW: Return status indicating if symbol onboarding needed
    return {
        "portfolio_id": str(portfolio.id),
        "status": "pending" if unknown_symbols else "ready",
        "pending_symbols": list(unknown_symbols) if unknown_symbols else None,
        # ... other fields ...
    }
```

#### 4.5.3 Symbol Onboarding Mini-Batch

When unknown symbols are detected, trigger a mini-batch that runs only the necessary phases:

```python
# NEW FILE: app/batch/symbol_onboarding.py

from app.batch.batch_run_tracker import batch_run_tracker
from app.batch.market_data_collector import market_data_collector
from app.services.symbol_validator import validate_symbol

class SymbolOnboardingRunner:
    """
    Runs a mini-batch for unknown symbols only.

    Reuses existing infrastructure:
    - batch_run_tracker for progress tracking
    - market_data_collector for price fetching
    - symbol_factors for factor calculation
    """

    async def onboard_symbols(
        self,
        symbols: List[str],
        portfolio_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Onboard new symbols with Phase 7.x progress tracking.

        Phases:
        1. Validate symbols (already done at creation, but double-check)
        2. Fetch 1 year historical prices
        3. Calculate factor betas
        4. Add to symbol_universe
        """
        batch_run_id = f"symbol_onboard_{portfolio_id}_{utc_now().isoformat()}"

        # Start tracking (EXISTING INFRASTRUCTURE)
        batch_run_tracker.start(CurrentBatchRun(
            batch_run_id=batch_run_id,
            started_at=utc_now(),
            triggered_by="symbol_onboarding",
            portfolio_id=portfolio_id
        ))

        try:
            # Phase 1: Fetch Historical Prices (EXISTING CODE)
            batch_run_tracker.start_phase(
                "prices",
                "Fetching Historical Prices",
                len(symbols),
                "symbols"
            )
            batch_run_tracker.add_activity(
                f"Fetching 1-year price history for {len(symbols)} symbol(s)",
                "info"
            )

            for i, symbol in enumerate(symbols):
                await market_data_collector.fetch_symbol_history(
                    db=db,
                    symbol=symbol,
                    lookback_days=365
                )
                batch_run_tracker.update_phase_progress("prices", i + 1)

            batch_run_tracker.complete_phase("prices", success=True)

            # Phase 2: Calculate Factor Betas (EXISTING CODE)
            batch_run_tracker.start_phase(
                "factors",
                "Calculating Factor Exposures",
                len(symbols),
                "symbols"
            )

            from app.calculations.symbol_factors import calculate_symbol_factors
            for i, symbol in enumerate(symbols):
                await calculate_symbol_factors(db, symbol)
                batch_run_tracker.update_phase_progress("factors", i + 1)

            batch_run_tracker.complete_phase("factors", success=True)

            # Phase 3: Add to Symbol Universe
            batch_run_tracker.start_phase(
                "universe",
                "Registering Symbols",
                len(symbols),
                "symbols"
            )

            for i, symbol in enumerate(symbols):
                await self._add_to_universe(db, symbol)
                batch_run_tracker.update_phase_progress("universe", i + 1)

            batch_run_tracker.complete_phase("universe", success=True)

            # Complete
            batch_run_tracker.add_activity(
                f"Successfully onboarded {len(symbols)} symbol(s)",
                "info"
            )
            batch_run_tracker.complete(success=True)

            return {"success": True, "symbols_onboarded": len(symbols)}

        except Exception as e:
            batch_run_tracker.add_activity(f"Error: {str(e)}", "error")
            batch_run_tracker.complete(success=False)
            raise

    async def _add_to_universe(self, db: AsyncSession, symbol: str):
        """Add symbol to universe with 'active' status."""
        from app.models.symbol_universe import SymbolUniverse

        universe_entry = SymbolUniverse(
            symbol=symbol,
            status='active',
            added_source='onboarding',
            first_seen_at=utc_now()
        )
        db.add(universe_entry)
        await db.flush()
```

#### 4.5.4 Triggering Symbol Onboarding

The symbol onboarding is triggered automatically after portfolio creation:

```python
# In portfolios.py - MODIFIED /calculate endpoint

@router.post("/{portfolio_id}/calculate")
async def trigger_calculations(
    portfolio_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check for pending symbols
    pending = await get_pending_symbols_for_portfolio(db, portfolio_id)

    if pending:
        # Run symbol onboarding first (uses Phase 7.x tracking)
        background_tasks.add_task(
            symbol_onboarding_runner.onboard_symbols,
            symbols=pending,
            portfolio_id=str(portfolio_id),
            db=db
        )
        return {
            "status": "pending",
            "message": f"Onboarding {len(pending)} new symbol(s)",
            "pending_symbols": pending,
            "poll_url": f"/api/v1/onboarding/status/{portfolio_id}"
        }

    # All symbols known - compute analytics immediately
    analytics = await compute_portfolio_analytics(db, portfolio_id)
    return {
        "status": "ready",
        "message": "Analytics computed",
        "analytics_available": True
    }
```

#### 4.5.5 Progress Polling (Reuses Phase 7.x Endpoint)

The existing `/api/v1/onboarding/status/{portfolio_id}` endpoint works as-is:

```python
# In onboarding_status.py - MINOR MODIFICATION

@router.get("/status/{portfolio_id}")
async def get_onboarding_status(portfolio_id: UUID, ...):
    # EXISTING: Get status from batch_run_tracker
    status = batch_run_tracker.get_onboarding_status(str(portfolio_id))

    if status:
        # Symbol onboarding in progress - return Phase 7.x format
        # Frontend will show simplified progress (not full 9 phases)
        return status

    # NEW: Check if portfolio has pending symbols
    pending = await get_pending_symbols_for_portfolio(db, portfolio_id)

    if pending:
        return OnboardingStatusResponse(
            portfolio_id=str(portfolio_id),
            status="pending",
            pending_symbols=pending,
            estimated_seconds_remaining=len(pending) * 30,
            message=f"Waiting to process {len(pending)} symbol(s)"
        )

    # All done
    return OnboardingStatusResponse(
        portfolio_id=str(portfolio_id),
        status="ready",
        analytics_available=True,
        message="Portfolio analytics are ready!"
    )
```

#### 4.5.6 Frontend Display (Reuses Phase 7.x Components)

The frontend uses the same `OnboardingProgress.tsx` component, but with simplified display:

```typescript
// useOnboardingStatus.ts - handles both old and new response formats

export function useOnboardingStatus(portfolioId: string) {
  const { data, isLoading } = useQuery({
    queryKey: ['onboarding-status', portfolioId],
    queryFn: () => onboardingService.getStatus(portfolioId),
    refetchInterval: (data) => {
      // Stop polling when ready or error
      if (data?.status === 'ready' || data?.status === 'error') {
        return false
      }
      return 5000  // 5 second polling for symbol onboarding
    }
  })

  return {
    status: data?.status,
    pendingSymbols: data?.pending_symbols,
    estimatedSeconds: data?.estimated_seconds_remaining,
    // Phase 7.x fields (if available - for backward compatibility)
    phases: data?.phases,
    activityLog: data?.activity_log,
    isLoading
  }
}
```

#### 4.5.7 Estimated Timeline for Symbol Onboarding

| Symbols | Phase 1 (Prices) | Phase 2 (Factors) | Phase 3 (Universe) | Total |
|---------|------------------|-------------------|---------------------|-------|
| 1 | ~3-5 sec | ~2-3 sec | <1 sec | ~8-10 sec |
| 5 | ~10-15 sec | ~5-8 sec | <1 sec | ~20-25 sec |
| 10 | ~20-30 sec | ~10-15 sec | <1 sec | ~35-50 sec |
| 20 | ~40-60 sec | ~20-30 sec | ~1 sec | ~65-95 sec |

**Maximum expected wait**: ~2 minutes for 20 unknown symbols

#### 4.5.8 Error Handling

| Error | When | User Sees | Backend Action |
|-------|------|-----------|----------------|
| Invalid symbol | CSV upload | "Invalid symbols: XYZ" | Reject upload |
| YFinance timeout | Symbol onboarding | "Loading data..." (retry) | Retry 3 times |
| No price data | Symbol onboarding | "Symbol XYZ unavailable" | Mark as failed, continue |
| Factor calc fails | Symbol onboarding | "Partial data for XYZ" | Use defaults, continue |

#### 4.5.9 Key Design Decisions

1. **Validate at upload, not batch**: Call `validate_symbols()` during CSV upload to catch invalid symbols early
2. **Reuse market_data_collector**: Don't rebuild price fetching - use existing code
3. **Reuse batch_run_tracker**: Don't rebuild progress tracking - use Phase 7.x infrastructure
4. **Simplified UI for symbol onboarding**: Show 3 phases (prices, factors, register) not 9
5. **Same polling endpoint**: `/api/v1/onboarding/status/{portfolio_id}` handles both flows
```

---

## Edit 8: Update Section 5.1 (Migration Timeline)

**Location**: Section 5.1 (Week-by-week breakdown)

**ADD to Week 2:**

```markdown
### Week 2: Symbol Batch Runner + Symbol Onboarding

**Symbol Batch Runner** (daily cron):
- [ ] Create `symbol_batch_runner.py`
- [ ] Integrate with `batch_run_tracker` for Phase 7.x tracking
- [ ] 6-phase processing for all symbols in universe

**Symbol Onboarding** (on-demand for new symbols):
- [ ] Create `symbol_onboarding.py` using existing infrastructure
- [ ] Modify `create_portfolio_with_csv()` to check `symbol_universe`
- [ ] Call `validate_symbols()` for unknown symbols at upload time
- [ ] Trigger mini-batch for valid unknown symbols
- [ ] Reuse `batch_run_tracker` for progress (3 phases)

**Validation Changes**:
- [ ] Move YFinance validation earlier (CSV upload, not Phase 1)
- [ ] Return `pending_symbols` in portfolio creation response
- [ ] Update `/calculate` endpoint to handle pending symbols
```

---

## Summary of New Edits

| Edit | Section | Purpose |
|------|---------|---------|
| Edit 7 | 4.5 (NEW) | Complete unknown symbol handling using existing infrastructure |
| Edit 8 | 5.1 | Add symbol onboarding to Week 2 migration timeline |

## Key Takeaways

1. **No new validation code needed** - `symbol_validator.py` already exists and validates against YFinance
2. **No new tracking code needed** - `batch_run_tracker.py` (Phase 7.x) handles progress
3. **No new price fetching code needed** - `market_data_collector.py` already fetches historical prices
4. **No new UI components needed** - `OnboardingProgress.tsx` (Phase 7.6) handles progress display
5. **Move validation earlier** - Call `validate_symbols()` at CSV upload, not buried in Phase 1
6. **Simplified progress** - Symbol onboarding shows 3 phases instead of 9, completes in <2 minutes
