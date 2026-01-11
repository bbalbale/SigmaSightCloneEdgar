# Code Review Request: Phase 7.3.1 Persistent Log Storage

**Date**: January 11, 2026
**Author**: Claude Opus 4.5
**Branch**: `main` (direct commit pending review)
**Related Docs**:
- `TESTSCOTTY_PROGRESS.md` (Section A13, A14)
- `TESTSCOTTY_BATCH_STATUS_UI.md`

---

## Summary

This PR enhances the Phase 7.3 Batch Status UI with **persistent log storage** to the database. Previously, logs were only stored in-memory with a 5-minute TTL. Now logs are persisted to PostgreSQL at each phase completion, surviving service restarts and enabling log retrieval hours or days later.

### Problem Solved

During long batch runs (25+ minutes):
1. In-memory logs were lost after TTL expiry or service restart
2. Users couldn't download logs if they waited too long after completion
3. Crash recovery was impossible - no way to see what happened before crash

### Solution

1. **Persist logs to database** at each phase completion
2. **Extend TTL to 2 hours** for in-memory cache
3. **Database fallback** when retrieving logs (in-memory first, then DB)

---

## Files Changed

### 1. `backend/app/models/admin.py`

**Changes**: Added 2 new columns to `BatchRunHistory` model

```python
# Portfolio tracking (for onboarding batches)
portfolio_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

# Activity log for persistent storage (Phase 7.3 enhancement)
# Stores full activity log as JSONB array, written at each phase completion
# Format: [{"timestamp": "ISO8601", "message": "...", "level": "info|warning|error"}, ...]
activity_log: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
```

**Rationale**:
- `portfolio_id` enables lookup of logs by portfolio (for download endpoint)
- `activity_log` stores the complete log as JSONB for efficient storage and retrieval
- Index on `portfolio_id` for fast queries

**Review Focus**:
- Is JSONB the right choice vs a separate log entries table?
- Any concerns about log size (up to 5000 entries)?

---

### 2. `backend/migrations_core/versions/s5t6u7v8w9x0_add_activity_log_to_batch_history.py`

**Changes**: Alembic migration to add the new columns

```python
def upgrade() -> None:
    op.add_column('batch_run_history',
        sa.Column('activity_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('batch_run_history',
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('ix_batch_run_history_portfolio_id', 'batch_run_history', ['portfolio_id'])
```

**Rationale**: Standard Alembic migration pattern with rollback support.

**Review Focus**:
- Migration naming convention correct?
- Any concerns about running on production data?

---

### 3. `backend/app/batch/batch_run_tracker.py`

**Changes**:

#### 3a. TTL Increase (line 36)
```python
# Before
COMPLETED_RUN_TTL_SECONDS = 300  # 5 minutes

# After
COMPLETED_RUN_TTL_SECONDS = 7200  # 2 hours
```

**Rationale**: Users may stay on completion screen for extended periods. 2 hours gives ample time to download logs.

#### 3b. New `persist_logs_to_db()` method (lines 371-429)
```python
async def persist_logs_to_db(self) -> None:
    """
    Persist current activity logs to database for crash recovery.
    Called at each phase completion to ensure logs are saved even if
    a later phase fails or the service crashes.
    """
    # ... updates BatchRunHistory.activity_log via SQL UPDATE
```

**Rationale**:
- Async method to avoid blocking batch processing
- Uses UPDATE (not INSERT) since BatchRunHistory record already exists
- Graceful failure - logs warning but doesn't fail the batch

**Review Focus**:
- Is the UPDATE approach correct? (vs INSERT or upsert)
- Any race condition concerns with concurrent writes?

#### 3c. Updated `complete_phase()` to persist logs (lines 462-472)
```python
# Phase 7.3: Persist logs to database after each phase completion
import asyncio
try:
    loop = asyncio.get_running_loop()
    asyncio.create_task(self.persist_logs_to_db())
except RuntimeError:
    asyncio.run(self.persist_logs_to_db())
```

**Rationale**:
- Fires async task to persist logs without blocking phase completion
- Handles both async context (batch orchestrator) and sync context (tests)

**Review Focus**:
- Is `create_task` the right pattern here? Should we await instead?
- Any concerns about task not completing before process exit?

#### 3d. New `get_full_activity_log_async()` method (lines 303-351)
```python
async def get_full_activity_log_async(self, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get complete activity log with database fallback.
    Falls back to database if logs not in memory (after TTL or restart).
    """
    # First try in-memory
    in_memory_logs = self.get_full_activity_log(portfolio_id)
    if in_memory_logs:
        return in_memory_logs

    # Fall back to database
    # ... queries BatchRunHistory.activity_log
```

**Rationale**:
- Preserves backward compatibility (sync method still exists)
- In-memory first for performance, DB fallback for durability
- Only queries DB when necessary

**Review Focus**:
- Is the fallback order correct?
- Any concerns about querying DB on every request if no in-memory logs?

---

### 4. `backend/app/api/v1/onboarding_status.py`

**Changes**: Updated log download endpoint to use async method

```python
# Before
activity_log = batch_run_tracker.get_full_activity_log(portfolio_id=portfolio_id)

# After
activity_log = await batch_run_tracker.get_full_activity_log_async(portfolio_id=portfolio_id)

# Also added handling for when status_data is None but logs exist in DB
if status_data is None:
    if activity_log:
        # Logs found in database - create minimal status for response
        status_data = {...}
```

**Rationale**:
- Use async version for database fallback
- Handle case where in-memory status expired but DB logs exist

**Review Focus**:
- Is the minimal status_data correct for DB-only case?
- Any security concerns with returning logs without full status?

---

## Documentation Changes

### 5. `backend/_docs/TESTSCOTTY_PROGRESS.md`

**Changes**:
- Added Section A13: Phase 1.5 Factor Coverage Diagnostic Guide
- Added Section A14: Phase 7.5 Risk Assessment (deferred)
- Added "Known Issues" section with Clerk token expiration issue

---

## Testing Notes

### Manual Testing Steps

1. **Apply migration**:
   ```bash
   railway run alembic -c alembic.ini upgrade head
   ```

2. **Trigger batch for test portfolio**:
   - Upload CSV via onboarding flow
   - Wait for batch to complete (or fail at any phase)

3. **Verify logs persisted**:
   ```bash
   railway run python -c "
   import asyncio
   from app.database import get_async_session
   from app.models.admin import BatchRunHistory
   from sqlalchemy import select

   async def check():
       async with get_async_session() as db:
           result = await db.execute(
               select(BatchRunHistory)
               .order_by(BatchRunHistory.started_at.desc())
               .limit(1)
           )
           row = result.scalar_one_or_none()
           if row:
               print(f'Batch: {row.batch_run_id}')
               print(f'Portfolio: {row.portfolio_id}')
               print(f'Log entries: {len(row.activity_log) if row.activity_log else 0}')

   asyncio.run(check())
   "
   ```

4. **Test log download after TTL expiry**:
   - Wait 2+ hours (or restart Railway service)
   - Try to download logs via UI
   - Should retrieve from database

### Edge Cases to Verify

- [ ] Batch completes successfully - logs persisted
- [ ] Batch fails mid-phase - logs up to failure persisted
- [ ] Service restarts during batch - partial logs available
- [ ] Download logs after 2+ hours - DB fallback works
- [ ] Multiple portfolios running - correct logs returned per portfolio

---

## Deployment Checklist

- [ ] Code review approved
- [ ] Migration tested locally
- [ ] Migration applied to Railway: `railway run alembic -c alembic.ini upgrade head`
- [ ] Deploy code to Railway
- [ ] Verify batch processing still works
- [ ] Verify log download works (both in-memory and DB fallback)

---

## Rollback Plan

If issues arise:

1. **Revert code**:
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Migration is backward-compatible** (nullable columns) - no DB rollback needed

3. **TTL change is safe** - just reverts to shorter cache time

---

## Code Review Fixes Applied (January 11, 2026)

Based on code review feedback, the following fixes were implemented:

### Fix 1: DB Fallback Status - RESOLVED ✅

**Problem**: When in-memory status expired but logs existed in DB, we hardcoded `status: "completed"` with 100% progress. This could misrepresent failed or partial runs.

**Solution**: Added `get_batch_status_from_db_async()` method that fetches actual `BatchRunHistory` record including:
- `status` (completed, failed, partial, running)
- `started_at` / `completed_at` timestamps
- `total_jobs`, `completed_jobs`, `failed_jobs`

Now the download endpoint uses actual DB status instead of assuming success.

### Fix 2: Race Condition Prevention - RESOLVED ✅

**Problem**: Fire-and-forget `create_task(persist_logs_to_db())` could cause race conditions where a slower earlier task overwrites newer logs with fewer entries.

**Solution**: Made UPDATE conditional using PostgreSQL `jsonb_array_length()`:
```sql
UPDATE batch_run_history
SET activity_log = :new_logs
WHERE batch_run_id = :id
  AND (activity_log IS NULL
       OR jsonb_array_length(COALESCE(activity_log, '[]'::jsonb)) <= :new_count)
```

Older writes with fewer entries are now safely rejected.

### Fix 3: Batch Run ID Selection - DOCUMENTED

**Problem**: DB fallback returns most recent run for a portfolio, which may not be the expected run after retries.

**Status**: Documented as future enhancement. Would require API contract change to add optional `batch_run_id` query parameter to download endpoint. Current behavior (most recent) is acceptable for MVP.

---

## Questions for Reviewers

1. **JSONB vs separate table**: Is storing logs as JSONB in `BatchRunHistory` the right approach? Alternative would be a separate `batch_run_logs` table with one row per entry.

2. **Fire-and-forget persistence**: The `create_task(persist_logs_to_db())` pattern doesn't await completion. Is this acceptable, or should we await to ensure logs are saved? **Note**: Now protected by conditional UPDATE.

3. **TTL of 2 hours**: Is this too long? Could lead to memory growth if many batches run. Should we add a max completed runs limit?

4. **Error handling**: Currently logs warning and continues if persistence fails. Should we retry? Store in a fallback location?

---

## Phase 7.3.2: Admin Batch Log Download (January 11, 2026)

### Summary

Added ability for admins to download activity logs for any batch run directly from the Admin Dashboard. This complements the user-facing log download (which is portfolio-scoped) by providing full administrative access to all batch run logs.

### Problem Solved

1. Admins needed to SSH into Railway or run database queries to view batch logs
2. No easy way to debug failed batch runs from the admin UI
3. Support tickets required manual log extraction

### Solution

1. **New backend endpoint** for admin log download
2. **Frontend download buttons** in the Run Details card
3. **Support for TXT and JSON formats**

---

### Files Changed

#### 1. `backend/app/api/v1/endpoints/admin_batch.py`

**Changes**: Added new endpoint `GET /api/v1/admin/batch/history/{batch_run_id}/logs`

```python
@router.get("/history/{batch_run_id}/logs")
async def get_batch_run_logs(
    batch_run_id: str,
    format: str = Query("json", description="Output format: 'json' or 'txt'"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Download activity logs for a specific batch run.
    Supports JSON and TXT formats for download.
    """
```

**Features**:
- Admin authentication required (`get_current_admin` dependency)
- Supports `?format=txt` or `?format=json` query parameter
- Returns `Content-Disposition` header for file download
- TXT format includes header with batch metadata
- JSON format includes full structured data

**Review Focus**:
- Is admin-only authentication sufficient, or should we add role-based access?
- Should we limit log size in response (currently returns full log)?

---

#### 2. `frontend/src/services/adminApiService.ts`

**Changes**: Added two new methods

```typescript
/**
 * Download batch run activity logs
 * Triggers browser file download
 */
async downloadBatchLogs(batchRunId: string, format: 'json' | 'txt' = 'txt'): Promise<void> {
  // Fetches blob, creates object URL, triggers download
}

/**
 * Get batch run log entry count (without downloading)
 */
async getBatchLogCount(batchRunId: string): Promise<number> {
  // Returns just the count for UI display
}
```

**Implementation Details**:
- Uses raw `fetch()` instead of `adminFetch()` to handle blob response
- Creates temporary `<a>` element to trigger download
- Extracts filename from `Content-Disposition` header
- Cleans up object URL after download

**Review Focus**:
- Is blob download the right pattern for this use case?
- Should we add progress indication for large log files?

---

#### 3. `frontend/app/admin/batch/page.tsx`

**Changes**: Added Download Logs section to Run Details card

```tsx
{/* Download Logs Section */}
<div className="pt-4 border-t border-slate-700">
  <p className="text-xs text-slate-500 uppercase mb-3">Activity Logs</p>
  <div className="flex gap-2">
    <Button onClick={() => downloadLogs('txt')}>
      <FileText /> TXT
    </Button>
    <Button onClick={() => downloadLogs('json')}>
      <Download /> JSON
    </Button>
  </div>
</div>
```

**UI Details**:
- Appears at bottom of Run Details card when a run is selected
- Two buttons: TXT (human-readable) and JSON (machine-readable)
- Loading spinner during download
- Error handling with toast/alert

**Review Focus**:
- Is button placement intuitive?
- Should we show log entry count before downloading?

---

### Testing Notes

#### Manual Testing Steps

1. **Navigate to Admin Batch History**:
   - Login at `/admin/login`
   - Go to `/admin/batch`

2. **Select a batch run** from the Recent Runs list

3. **Click TXT or JSON download button**:
   - Verify file downloads with correct filename
   - Verify TXT format is human-readable with header
   - Verify JSON format includes all metadata

4. **Test edge cases**:
   - Batch run with no logs (should show "No activity log entries available")
   - Very large log file (5000+ entries)
   - Failed batch run (should still have partial logs)

#### API Testing

```bash
# Test TXT format
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/history/batch_20260111_140711/logs?format=txt"

# Test JSON format
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/history/batch_20260111_140711/logs?format=json"
```

---

### Security Considerations

1. **Admin-only access**: Endpoint requires `get_current_admin` authentication
2. **No user data exposure**: Logs contain batch processing info, not user PII
3. **Rate limiting**: Consider adding rate limits for large log downloads

---

### Deployment Notes

- No database migration required (uses existing `activity_log` column)
- Backend and frontend must be deployed together
- Existing batch runs without `activity_log` will show "No activity log entries available"
