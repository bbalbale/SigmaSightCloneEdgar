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

## Questions for Reviewers

1. **JSONB vs separate table**: Is storing logs as JSONB in `BatchRunHistory` the right approach? Alternative would be a separate `batch_run_logs` table with one row per entry.

2. **Fire-and-forget persistence**: The `create_task(persist_logs_to_db())` pattern doesn't await completion. Is this acceptable, or should we await to ensure logs are saved?

3. **TTL of 2 hours**: Is this too long? Could lead to memory growth if many batches run. Should we add a max completed runs limit?

4. **Error handling**: Currently logs warning and continues if persistence fails. Should we retry? Store in a fallback location?
