# Phase 2.10 Code Review - Batch Processing Idempotency Fix

**Commit**: `0190024a`
**Status**: Foundation complete - ready for code review
**Risk Level**: HIGH - Production critical bug fix

---

## Problem Statement

**Bug**: Running batch processing multiple times on the same day causes portfolio equity to compound incorrectly, resulting in severe data corruption.

**Evidence**:
- test009 portfolio: Equity inflated from -$6.9M → $14.2M (215% inflation)
- Caused by 4 batch runs in 40 minutes applying same P&L calculation repeatedly
- Root cause: Race condition in snapshot creation allows duplicate snapshots

**Production Impact**:
- 🚨 Production blocker
- All portfolio values incorrect after multiple batch runs
- Railway cron cannot safely run automated daily batches

---

## Root Cause Analysis

**Current Flow** (BROKEN):
```python
# pnl_calculator.py::calculate_portfolio_pnl()

# Step 1: Calculate P&L
daily_pnl = calculate_pnl()

# Step 2: Update equity (HAPPENS FIRST!)
portfolio.equity_balance += daily_pnl  # ← Line 244
await db.flush()

# Step 3: Create snapshot (HAPPENS SECOND!)
snapshot = create_portfolio_snapshot()  # ← Line 260

# Problem: If two processes run simultaneously:
# - Both calculate same P&L
# - Both update equity (equity touched BEFORE idempotency check)
# - Both create snapshots (check-then-act race condition)
# - Result: equity += (pnl + pnl) instead of (pnl)
```

**Race Condition Window**:
```python
# In create_portfolio_snapshot() or similar location
existing = await db.execute(
    select(PortfolioSnapshot).where(
        portfolio_id == id,
        snapshot_date == today
    )
)
if not existing:  # ← RACE WINDOW: Two processes can both see "not existing"
    create_snapshot()
```

---

## Proposed Solution: Insert-First Pattern

**Strategy**: Insert placeholder snapshot FIRST (before any calculations), using database unique constraint for atomic enforcement.

**New Flow**:
```python
# Step 1: Insert placeholder snapshot FIRST (before P&L calculation)
try:
    placeholder = PortfolioSnapshot(
        portfolio_id=X,
        snapshot_date=today,
        is_complete=False,  # Mark as incomplete
        # ... all fields with placeholder zeros
    )
    db.add(placeholder)
    await db.flush()  # ← Database enforces uniqueness HERE
except IntegrityError:
    # Another process already owns this (portfolio, date)
    return "skipped"  # Exit before touching equity

# Step 2: Calculate P&L (safe - we own this date)
daily_pnl = calculate_pnl()
portfolio.equity_balance += daily_pnl
await db.flush()

# Step 3: Update placeholder with real values
placeholder.net_asset_value = new_equity
# ... populate all fields
placeholder.is_complete = True  # Mark complete
await db.flush()
```

**Why This Works**:
- ✅ Database unique constraint is atomic (no race condition possible)
- ✅ Second process hits IntegrityError BEFORE calculating anything
- ✅ Equity only updated if we successfully claimed the slot
- ✅ Works on first run of day (insert before calculate)

---

## Files Created (3 files, 355 lines)

### 1. `scripts/repair/dedupe_snapshots_pre_migration.py` (265 lines)

**Purpose**: Remove existing duplicate snapshots before applying unique constraint migration.

**Key Functions**:

```python
async def find_duplicate_groups(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Find all (portfolio_id, snapshot_date) pairs with count > 1.
    Uses SQL GROUP BY with HAVING clause.
    """

async def get_best_snapshot(db, portfolio_id, snapshot_date) -> PortfolioSnapshot:
    """
    Select which snapshot to keep from duplicate group.

    Logic:
    1. Prefer non-zero net_asset_value (complete calculations)
    2. If equal, prefer latest created_at timestamp

    Returns first row after ORDER BY:
        - net_asset_value DESC  (complete snapshots first)
        - created_at DESC        (latest timestamp first)
    """

async def dedupe_snapshots(dry_run: bool = False) -> Dict[str, Any]:
    """
    Main deduplication logic:
    1. Find all duplicate groups
    2. For each group, keep "best" snapshot
    3. Delete all others in group
    4. Log deletions for audit trail
    5. Verify no duplicates remain (if not dry run)
    """
```

**Features**:
- Dry-run mode (`--dry-run` flag)
- Audit logging of all deletions
- Verification step (confirms no duplicates after completion)
- Interactive confirmation for live mode
- Full error handling with rollback

**Usage**:
```bash
# Dry run (safe to test)
python scripts/repair/dedupe_snapshots_pre_migration.py --dry-run

# Live run (requires confirmation)
python scripts/repair/dedupe_snapshots_pre_migration.py
```

**CRITICAL**: Must run BEFORE migration, or migration will fail on existing duplicates.

---

### 2. `alembic/versions/k8l9m0n1o2p3_add_snapshot_idempotency_fields.py` (60 lines)

**Purpose**: Database migration to add idempotency enforcement.

**Changes**:

```python
def upgrade():
    # 1. Add is_complete flag (defaults TRUE for existing rows)
    op.add_column(
        'portfolio_snapshots',
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='true')
    )

    # 2. Add unique constraint (WILL FAIL if duplicates exist!)
    op.create_unique_constraint(
        'uq_portfolio_snapshot_date',
        'portfolio_snapshots',
        ['portfolio_id', 'snapshot_date']
    )

def downgrade():
    op.drop_constraint('uq_portfolio_snapshot_date', 'portfolio_snapshots', type_='unique')
    op.drop_column('portfolio_snapshots', 'is_complete')
```

**Design Decisions**:

1. **Why `server_default='true'`?**
   - All existing snapshots assumed complete (valid assumption)
   - Prevents breaking existing rows
   - New rows will use application default (True)

2. **Why unique constraint on `snapshot_date` not `calculation_date`?**
   - Model defines `snapshot_date` field (line 19 of snapshots.py)
   - `calculation_date` doesn't exist in schema
   - This was explicitly called out in TODO5.md warnings

3. **Migration order dependency**:
   - Revises: `j7k8l9m0n1o2` (previous migration)
   - Must run dedupe script BEFORE this migration
   - Migration includes warning comment

---

### 3. `app/models/snapshots.py` (4 lines changed)

**Changes**:

```python
# Import addition
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, UniqueConstraint, JSON, Boolean

# Field addition (after target_price_last_updated, before created_at)
# Phase 2.10: Batch idempotency flag (prevents duplicate snapshot creation on same day)
# TRUE = calculations complete, FALSE = placeholder snapshot (process crashed mid-calculation)
# Used with unique constraint on (portfolio_id, snapshot_date) for atomic idempotency
is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

**Design Decisions**:

1. **Field placement**: Between tracking fields and created_at (logical grouping)
2. **Default value**: `True` (matches migration's server_default)
3. **Nullable**: `False` (every snapshot must have completion status)
4. **Documentation**: Clear inline comments explaining purpose

---

## Code Review Checklist

### ✅ Correctness

**Dedupe Script**:
- [ ] SQL query for finding duplicates is correct (GROUP BY + HAVING)
- [ ] "Best snapshot" selection logic is sound (non-zero NAV > latest timestamp)
- [ ] DELETE query excludes the "best" snapshot correctly (`id != best_snapshot.id`)
- [ ] Verification query confirms no duplicates remain
- [ ] Error handling includes rollback on failure

**Migration**:
- [ ] Column name is correct (`snapshot_date` not `calculation_date`)
- [ ] Server default matches application default (`true` / `True`)
- [ ] Unique constraint name is descriptive and unlikely to conflict
- [ ] Downgrade properly reverses changes

**Model**:
- [ ] Import statement includes `Boolean`
- [ ] Field type is correct (`Mapped[bool]`)
- [ ] Default value matches migration
- [ ] Field is non-nullable as intended

### ⚠️ Potential Issues

1. **Migration Failure Scenario**:
   - **Issue**: If duplicates exist, migration fails with unique constraint violation
   - **Mitigation**: Dedupe script MUST run first (documented extensively)
   - **Question**: Should migration check for duplicates and fail gracefully with clear message?

2. **Existing Snapshots Assumption**:
   - **Assumption**: All existing snapshots are complete (`is_complete=TRUE`)
   - **Risk**: If any existing snapshots are actually incomplete, they'll be marked complete
   - **Likelihood**: Low (no incomplete flag existed before)

3. **Dedupe "Best Snapshot" Logic**:
   - **Current**: Prefer non-zero NAV, then latest timestamp
   - **Edge Case**: What if all snapshots in group have zero NAV?
   - **Behavior**: Would keep latest created_at (reasonable)

4. **Column Name Confusion**:
   - **Risk**: Developer might use `calculation_date` instead of `snapshot_date`
   - **Mitigation**: Migration includes warning comment, TODO5.md has explicit warnings
   - **Question**: Should we add a model-level check or comment?

5. **Transaction Safety in Dedupe Script**:
   - **Current**: Single transaction for all deletions
   - **Risk**: If deleting 1000s of duplicates, long-running transaction
   - **Question**: Should we batch deletions? (Probably not needed for 10-100 duplicates)

6. **Incomplete Snapshot Cleanup**:
   - **Missing**: No automated cleanup for `is_complete=FALSE` snapshots yet
   - **Impact**: If process crashes, incomplete snapshots block retries
   - **Status**: Planned in Task 2.10.2 Step D (not in this commit)

### 🔍 Testing Gaps

**What's NOT tested yet** (planned for Tasks 2.10.3-2.10.4):
- [ ] Dedupe script with various duplicate scenarios
- [ ] Migration rollback/upgrade cycle
- [ ] Unique constraint violation behavior (IntegrityError)
- [ ] is_complete flag updates
- [ ] Concurrent batch runs (threading/asyncio)

### 📋 Documentation

**What's documented**:
- ✅ Inline code comments
- ✅ Docstrings in dedupe script
- ✅ Migration file comments
- ✅ Model field documentation
- ✅ Commit message explains purpose

**What's NOT documented yet**:
- [ ] CLAUDE.md update (planned)
- [ ] API documentation (if adding admin endpoints)
- [ ] Operator runbook for migration deployment

---

## Deployment Sequence (CRITICAL)

**MUST follow this order**:

1. **Pre-Migration** (LOCAL):
   ```bash
   # Dry run first
   python scripts/repair/dedupe_snapshots_pre_migration.py --dry-run

   # Review results, then run for real
   python scripts/repair/dedupe_snapshots_pre_migration.py

   # Verify no duplicates
   SELECT portfolio_id, snapshot_date, COUNT(*)
   FROM portfolio_snapshots
   GROUP BY portfolio_id, snapshot_date
   HAVING COUNT(*) > 1;
   ```

2. **Migration** (LOCAL):
   ```bash
   alembic upgrade head

   # Verify constraint exists
   SELECT conname FROM pg_constraint
   WHERE conname = 'uq_portfolio_snapshot_date';
   ```

3. **Code Deployment** (NEXT COMMIT):
   - Two-phase snapshot refactoring (Task 2.10.2)
   - Insert-first pattern in PNL calculator
   - Automated cleanup for incomplete snapshots

4. **Repeat for PRODUCTION** (Railway):
   ```bash
   # Step 1: Dedupe
   railway run python scripts/repair/dedupe_snapshots_pre_migration.py

   # Step 2: Verify
   railway run "SELECT portfolio_id, snapshot_date, COUNT(*) ..."

   # Step 3: Deploy (git push triggers Railway auto-deploy)
   git push origin main
   ```

---

## Questions for Reviewer

1. **Dedupe Logic**: Is "prefer non-zero NAV, then latest timestamp" the correct heuristic for selecting best snapshot?

2. **Migration Safety**: Should the migration include a pre-check for duplicates with a clearer error message?

3. **Transaction Scope**: Is a single transaction for all deletions acceptable, or should we batch?

4. **Column Naming**: Should we add a runtime check to prevent confusion between `snapshot_date` and `calculation_date`?

5. **Incomplete Cleanup**: Should automated cleanup (Task 2.10.2 Step D) be included in this commit, or is it safe to deploy separately?

6. **Testing Strategy**: Do we need integration tests BEFORE deploying foundation, or can foundation deploy with unit tests following?

7. **Rollback Plan**: If migration succeeds but code deployment fails, what's the recovery path?

---

## Next Implementation Steps (Not in This Commit)

**Task 2.10.2: Two-Phase Snapshot Refactoring**
- [ ] Step A: Create `lock_snapshot_slot()` helper function
- [ ] Step B: Refactor `create_portfolio_snapshot()` → `populate_snapshot_data()`
- [ ] Step C: Update `pnl_calculator.py` to use insert-first pattern
- [ ] Step D: Add automated cleanup for incomplete snapshots

**Task 2.10.3-2.10.4: Testing**
- [ ] Unit tests for insert-first pattern
- [ ] Integration tests for concurrent batch runs
- [ ] Test incomplete snapshot cleanup

**Task 2.10.5: Data Repair**
- [ ] Fix test009/test011 corrupted equity values
- [ ] Replay from last known good snapshot

---

## Risk Assessment

**Overall Risk**: MEDIUM-HIGH
- Foundation code is simple (migration + model update)
- Real complexity is in PNL calculator refactoring (not yet implemented)
- Migration is reversible (downgrade available)
- Dedupe script has dry-run mode for safety

**Deployment Risk**: LOW for this commit
- No behavioral changes to running code
- Migration is additive (adds column + constraint)
- Dedupe script is manual operation (not automatic)

**Production Impact if Issues**:
- If migration fails: Can rollback, fix duplicates, retry
- If code breaks later: Unique constraint still enforces idempotency (prevents further damage)
- If incomplete snapshots accumulate: Manual cleanup possible via SQL

---

## Files Modified Summary

```
backend/scripts/repair/dedupe_snapshots_pre_migration.py     (NEW, 265 lines)
backend/alembic/versions/k8l9m0n1o2p3_add_snapshot_...py    (NEW, 60 lines)
backend/app/models/snapshots.py                              (+4 lines, -1 line)
```

**Total**: 3 files changed, 355 insertions(+), 1 deletion(-)

---

## Conclusion

**Foundation is solid** - The migration and model changes are straightforward and well-documented. The dedupe script is comprehensive with good safety features.

**Main concerns**:
1. Ensure dedupe script runs BEFORE migration (well documented)
2. Verify "best snapshot" selection logic is correct
3. Plan for incomplete snapshot cleanup (coming in next commit)

**Ready for**:
- Code review
- Local testing (run migration on dev database)
- Proceed with Task 2.10.2 (code refactoring)

**NOT ready for**:
- Production deployment (needs PNL calculator refactoring first)
- Full end-to-end testing (needs insert-first pattern implemented)
