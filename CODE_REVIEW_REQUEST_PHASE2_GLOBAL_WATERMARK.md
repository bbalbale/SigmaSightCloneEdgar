# Code Review Request: Phase 2 Global Watermark Bug Fix

**Date**: January 8, 2026
**Author**: Claude Opus 4.5
**Reviewer**: Advanced AI Coding Agent
**Branch**: main (uncommitted changes)

---

## Summary

This PR implements Phase 2 of the Testscotty batch processing debug plan: **Fix Global Watermark Bug**. The goal is to ensure the cron job processes ALL portfolios that are behind, not just check global MAX snapshot date.

## Problem Statement

The previous `_get_last_batch_run_date()` function used a **global MAX** query:

```python
# BEFORE (buggy)
query = select(PortfolioSnapshot.snapshot_date).order_by(
    desc(PortfolioSnapshot.snapshot_date)
).limit(1)  # Gets MAX across ALL portfolios
```

**Impact**: If Portfolio A was at Jan 7 but Portfolios B-L were at Jan 5, the cron saw `last_run_date = Jan 7` and thought "all caught up", leaving 11 portfolios permanently behind.

**Evidence from Railway (Jan 8, 2026)**:
- 11 portfolios stuck at Jan 5 snapshots
- 1 portfolio (Tech Growth) at Jan 6
- 1 portfolio (Testscotty) at Jan 7
- Global MAX = Jan 7, so cron skipped processing

## Solution: Hybrid Approach

Implemented two-part fix:

### 1. Minimum Watermark Strategy (Step 1)

Changed `_get_last_batch_run_date()` to use MIN of per-portfolio MAX dates:

```python
# AFTER (fixed)
# Subquery: Get MAX snapshot date for each portfolio
subquery = (
    select(
        PortfolioSnapshot.portfolio_id,
        func.max(PortfolioSnapshot.snapshot_date).label('max_date')
    )
    .group_by(PortfolioSnapshot.portfolio_id)
    .subquery()
)

# Main query: Get the MIN of those max dates (most lagging portfolio)
query = select(func.min(subquery.c.max_date))
```

**Result**: Date range calculation now based on the "slowest" portfolio.

### 2. Per-Date Portfolio Filtering (Step 2)

Added filtering in `_execute_batch_phases()` to avoid reprocessing portfolios that already have snapshots:

```python
# For each date, get portfolios that already have snapshots
portfolios_with_snapshot = await self._get_portfolios_with_snapshot(filter_db, calc_date)

# Filter to only portfolios needing this date
all_portfolios = await self._get_all_active_portfolio_ids(filter_db)
portfolios_to_process = [p for p in all_portfolios if p not in portfolios_with_snapshot]

if not portfolios_to_process:
    logger.debug(f"Skipping {calc_date}: all portfolios already have snapshots")
    continue
```

**Result**: Efficient processing - only touches portfolios that actually need updates.

---

## Files Changed

| File | Changes |
|------|---------|
| `backend/app/batch/batch_orchestrator.py` | Added `func` import; modified `_get_last_batch_run_date()` for MIN of MAX; added `_get_portfolios_with_snapshot()` helper; added `_get_all_active_portfolio_ids()` helper; added per-date filtering in `_execute_batch_phases()` |

---

## Key Code Changes

### 1. Import Addition (line 41)

```python
from sqlalchemy import select, and_, desc, func  # Added func
```

### 2. `_get_last_batch_run_date()` (lines 1688-1743)

- Changed from global MAX to MIN of per-portfolio MAX
- Added detailed docstring explaining the strategy
- Preserved fallback logic for first run (no snapshots)

### 3. Helper Methods (lines 1754-1788)

```python
async def _get_portfolios_with_snapshot(self, db, snapshot_date) -> set:
    """Get portfolio IDs that already have a snapshot for the given date."""

async def _get_all_active_portfolio_ids(self, db) -> List[str]:
    """Get all active (non-deleted) portfolio IDs."""
```

### 4. Per-Date Filtering in `_execute_batch_phases()` (lines 528-586)

- Only applies in cron mode (`scoped_only=False`)
- Single-portfolio mode (`scoped_only=True`) bypasses filtering
- Tracks `dates_skipped` for logging
- Logs which portfolios already have snapshots

---

## Key Review Points

### 1. MIN of MAX Query Correctness (lines 1710-1721)

```python
subquery = (
    select(
        PortfolioSnapshot.portfolio_id,
        func.max(PortfolioSnapshot.snapshot_date).label('max_date')
    )
    .group_by(PortfolioSnapshot.portfolio_id)
    .subquery()
)
query = select(func.min(subquery.c.max_date))
```

**Question**: Is the subquery approach correct for SQLAlchemy 2.0 async? Should we use `.cte()` instead of `.subquery()`?

### 2. Per-Date Filtering Session Management (lines 536-545)

```python
async with AsyncSessionLocal() as filter_db:
    portfolios_with_snapshot = await self._get_portfolios_with_snapshot(filter_db, calc_date)
    # ... filtering logic ...
```

**Question**: Is opening a separate session (`filter_db`) for filtering correct, or should we reuse the outer session? The filtering happens before the main processing session is opened.

### 3. Scoped Mode Bypass (lines 531-533)

```python
if scoped_only:
    portfolios_to_process = portfolio_ids  # Use directly, no filtering
```

**Question**: Is it correct to bypass filtering entirely in scoped mode? The rationale is that single-portfolio batches (onboarding) should always process that one portfolio.

### 4. Progress Tracking for Skipped Dates (lines 549-551)

```python
if not portfolios_to_process:
    dates_skipped += 1
    progress["completed"] += 1  # Count as completed (no work needed)
    continue
```

**Question**: Should skipped dates count as "completed" in progress tracking? The alternative is to not count them at all, but that could make progress percentages confusing.

### 5. Edge Case: New Portfolio with No Snapshots

If a new portfolio has no snapshots yet, the MIN of MAX query will not include it (it has no MAX to contribute). Is this correct?

**Answer**: Yes - new portfolios without any snapshots are handled by onboarding (scoped mode), not the cron job. The cron job processes existing portfolios that need catch-up.

---

## Example Scenario

**Before (Bug)**:
```
Portfolios: A (Jan 7), B (Jan 5), C (Jan 5)
Global MAX = Jan 7
Cron: "All caught up!" → Skips B and C forever
```

**After (Fixed)**:
```
Portfolios: A (Jan 7), B (Jan 5), C (Jan 5)
MIN of MAX = Jan 5
Date range: Jan 6, 7, 8

Jan 6: A already has it → Process B, C only
Jan 7: A already has it → Process B, C only
Jan 8: None have it → Process A, B, C

Result: All portfolios now have Jan 6, 7, 8
```

---

## Testing Checklist

- [ ] Cron job correctly identifies lagging portfolios
- [ ] Lagging portfolios get backfilled without reprocessing current ones
- [ ] Single-portfolio mode (onboarding) still works correctly
- [ ] Progress tracking accurately reflects work done
- [ ] Logs show "System watermark (most lagging portfolio): YYYY-MM-DD"
- [ ] Logs show "Skipping {date}: all portfolios already have snapshots" when applicable
- [ ] Logs show "Processing {date}: N portfolios need updates (M already have snapshots)"

---

## Expected Performance Impact

| Scenario | Before | After | Impact |
|----------|--------|-------|--------|
| All portfolios current | Quick (no work) | Quick (no work) | Same |
| 1 portfolio behind | Process ALL for that date | Process 1 for that date | **~15x faster** |
| 11 portfolios behind | Process ALL for all dates | Process only behind portfolios | **~15x faster** |

The filtering ensures we never reprocess portfolios that are already up-to-date.

---

## Rollback Plan

If issues arise:
1. Revert `_get_last_batch_run_date()` to original global MAX query
2. Remove per-date filtering logic from `_execute_batch_phases()`
3. Remove helper methods `_get_portfolios_with_snapshot()` and `_get_all_active_portfolio_ids()`

Changes are isolated to `batch_orchestrator.py` and don't affect the data model.

---

## Related Documentation

- `backend/_docs/TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md` - Phase 2 detailed plan
- `backend/_docs/TESTSCOTTY_PROGRESS.md` - Progress tracking

---

## Questions for Reviewer

1. **Query correctness**: Is the MIN of MAX subquery pattern correct for async SQLAlchemy?

2. **Session management**: Should filtering use a separate session or reuse an existing one?

3. **Edge cases**: What happens if ALL portfolios are new (no snapshots)? Should we handle this explicitly?

4. **Logging verbosity**: Is the logging level appropriate? Should per-date filtering info be DEBUG instead of INFO?

5. **Performance**: Should we cache the `_get_all_active_portfolio_ids()` result instead of querying it for each date?

---

## Code Review Fixes Applied

### Code Review #1 Findings (Approved with optimization)
- **Finding**: Cache `_get_all_active_portfolio_ids()` outside the loop
- **Fix**: ✅ Implemented - cached before the date loop

### Code Review #2 Findings

**Finding #1: Deleted portfolios affecting watermark**
> The subquery queries every PortfolioSnapshot row regardless of whether the owning portfolio is active. Any soft-deleted or archived portfolio with an old snapshot immediately drives the "minimum watermark" back to that stale date.

**Fix**: ✅ Added join to Portfolio table with filter:
```python
subquery_base = (
    select(...)
    .join(Portfolio, Portfolio.id == PortfolioSnapshot.portfolio_id)
    .where(Portfolio.deleted_at.is_(None))  # Only active portfolios
)
```

**Finding #2: Watermark ignores caller's scope**
> The new watermark logic ignores the caller's scope (portfolio_ids). If an admin runs a manual backfill for a small subset, _get_last_batch_run_date() still bases the date range on the most-lagging portfolio in the entire system.

**Fix**: ✅ Added `portfolio_ids` parameter to `_get_last_batch_run_date()`:
```python
async def _get_last_batch_run_date(
    self,
    db: AsyncSession,
    portfolio_ids: Optional[List[str]] = None  # NEW: scope to specific portfolios
) -> Optional[date]:
    ...
    if portfolio_ids:
        portfolio_uuids = [UUID(pid) if isinstance(pid, str) else pid for pid in portfolio_ids]
        subquery_base = subquery_base.where(PortfolioSnapshot.portfolio_id.in_(portfolio_uuids))
```

And updated the call site:
```python
last_run_date = await self._get_last_batch_run_date(db, portfolio_ids=portfolio_ids)
```

### Code Review #3 Findings

**Finding: Invalid portfolio IDs crash the batch**
> `_get_last_batch_run_date()` converts every element of `portfolio_ids` to a UUID without validation. If the caller passes an invalid portfolio ID, this raises `ValueError` and aborts the batch.

**Fix**: ✅ Added try/except wrapper matching `_normalize_portfolio_ids()` pattern:
```python
portfolio_uuids = []
for pid in portfolio_ids:
    if isinstance(pid, UUID):
        portfolio_uuids.append(pid)
    else:
        try:
            portfolio_uuids.append(UUID(str(pid)))
        except (TypeError, ValueError):
            logger.warning(f"Invalid portfolio ID '{pid}' in watermark query, skipping")

if portfolio_uuids:
    subquery_base = subquery_base.where(PortfolioSnapshot.portfolio_id.in_(portfolio_uuids))
```

Now invalid IDs are logged and skipped, allowing the batch to continue with valid IDs.

### Code Review #4 Findings (Idempotency Gap)

**Finding: Partial runs leave portfolios with incomplete analytics**
> The per-date skip check only considers snapshot existence, not phase completion. If the process crashes after Phase 3 (snapshot creation) but before Phases 4-6 complete, the portfolio remains with stale analytics and no mechanism to self-heal.

**Fix**: Added `force_rerun` mode to bypass snapshot existence checks:

```python
# In run_daily_batch_with_backfill()
async def run_daily_batch_with_backfill(
    self,
    ...
    force_rerun: bool = False,  # NEW: Bypass snapshot checks
) -> Dict[str, Any]:
```

**Per-date filtering bypass:**
```python
if scoped_only or force_rerun:
    if force_rerun and not scoped_only:
        # Force rerun in cron mode: process all active portfolios
        logger.info(f"FORCE_RERUN: Processing {calc_date} for {len(portfolios_to_process)} portfolios")
```

**Admin endpoint updated:**
```
POST /api/v1/admin/batch/run?force_rerun=true&start_date=2026-01-05&end_date=2026-01-08
```

**Follow-up**: Per-phase completion tracking (self-healing) planned for future implementation.

---

Please review and provide feedback on the implementation approach, query correctness, and any edge cases that should be addressed.
