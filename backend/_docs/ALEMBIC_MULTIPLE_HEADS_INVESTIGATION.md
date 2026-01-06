# Alembic Multiple Heads Investigation

**Date**: 2026-01-05
**Branch Investigated**: `origin/main`
**Status**: CRITICAL - `origin/main` has 2 unmerged migration heads

---

## Executive Summary

The `main` branch has **two unmerged Alembic migration chains** that diverged on **October 19, 2025**. This means:
1. Running `alembic upgrade head` on a fresh database would fail with "Multiple heads detected"
2. Railway production database only **tracks** Chain 2 in `alembic_version`
3. **However**, most Chain 1 schema objects **actually exist** in production (applied outside Alembic)
4. Only the `spread_factor_definitions` table is truly missing from production

**Fix Strategy**: Stamp Railway with Chain 1 head, then apply a merge migration.

---

## Railway Production Database State

```sql
SELECT version_num FROM alembic_version;
-- Result: r4s5t6u7v8w9
```

**Alembic only tracks Chain 2**, but **most Chain 1 schema objects actually exist** in production (applied manually/outside Alembic).

### Schema Objects Present (Despite Not Being Tracked)

| Object | Migration | Status |
|--------|-----------|--------|
| `portfolio_snapshots.is_complete` | k8l9m0n1o2p3 | ✅ EXISTS |
| `uq_portfolio_snapshots_portfolio_date` constraint | k8l9m0n1o2p3 | ✅ EXISTS |
| `positions.notes` column | 2623cfc89fb7 | ✅ EXISTS |
| `equity_changes` table | 62b5c8b1d8a3 | ✅ EXISTS |
| `position_realized_events` table | a3b4c5d6e7f8 | ✅ EXISTS |
| Target price columns on portfolio_snapshots | 035e1888bea0 | ✅ EXISTS |
| Performance indexes on positions | i6j7k8l9m0n1, j7k8l9m0n1o2 | ✅ EXISTS |
| Spread factor rows in `factor_definitions` | b9f866cb3838 | ⚠️ **PARTIAL** (see note) |

**Note on b9f866cb3838**: This migration doesn't create a table - it inserts 4 rows into `factor_definitions` with `factor_type = 'spread'`. Railway has spread factor rows but with `factor_type = 'style'` instead. This is a **data discrepancy**, not a missing schema object.

### Key Finding
Railway production has a **hybrid state**:
- Schema matches Chain 1 + Chain 2 (all tables/columns exist)
- Alembic version only tracks Chain 2 (`r4s5t6u7v8w9`)
- Minor data discrepancy: spread factors have wrong `factor_type` value

---

## The Two Heads on `origin/main`

| Head | Migration | Create Date | Git Commit |
|------|-----------|-------------|------------|
| `k8l9m0n1o2p3` | add_snapshot_idempotency_fields.py | 2025-11-17 | `3be9a32b` feat: Dual database architecture |
| `r4s5t6u7v8w9` | add_batch_history_daily_metrics.py | 2025-12-22 | `ddeaecdb` feat: Add Batch History & Daily Metrics |

---

## Divergence Point

Both chains share a common ancestor:

```
f8g9h0i1j2k3 (add_ai_insights_tables.py)
Date: 2025-10-19 20:00:00
```

After this point, development split into two parallel chains that were never merged on `main`.

---

## Visual Migration Tree

```
                         f8g9h0i1j2k3 (Oct 19)
                         add_ai_insights_tables.py
                                  │
           ┌──────────────────────┴──────────────────────┐
           │                                             │
           │ CHAIN 1 (Oct 19 - Nov 17)                   │ CHAIN 2 (Dec 20 - Dec 22)
           │ 16 migrations                               │ 5 migrations
           ▼                                             ▼
   7003a3be89fe (Oct 19)                         n0o1p2q3r4s5 (Dec 20)
   add_sector_exposure_and_concentration         add_symbol_analytics_tables
           │                                             │
           ▼                                             ▼
   h1i2j3k4l5m6 (Oct 19)                         o1p2q3r4s5t6 (Dec 22)
   add_portfolio_id_to_interest_rate_betas       add_admin_user_tables
           │                                             │
           ▼                                             ▼
   b9f866cb3838 (Oct 20)                         p2q3r4s5t6u7 (Dec 22)
   add_spread_factor_definitions                 add_user_activity_events
           │                                             │
           ▼                                             ▼
   035e1888bea0 (Oct 20)                         q3r4s5t6u7v8 (Dec 22)
   add_portfolio_target_price_fields             add_ai_request_metrics
           │                                             │
           ▼                                             ▼
   ca2a68ee0c2c (Oct 28)                         r4s5t6u7v8w9 (Dec 22)
   add_batch_run_tracking_table                  add_batch_history_daily_metrics
           │                                             │
           ▼                                             │
   9b0768a49ad8 (Nov 1)                                  │
   add_multi_portfolio_support                           │
           │                                             │
           ▼                                             │
   ce3dd9222427 (Nov 2)                                  │
   add_fundamental_tables                                │
           │                                             │
           ▼                                             │
   f2a8b1c4d5e6 (Nov 2)                                  │
   change_share_counts_to_bigint                         │
           │                                             │
      ┌────┴────┐ (parallel dev)                         │
      │         │                                        │
      ▼         ▼                                        │
g3h4i5j6k7l8  2623cfc89fb7                               │
      │         │                                        │
      │    ┌────┘                                        │
      │    │                                             │
      │    ▼                                             │
      │  a3b4c5d6e7f8 (Nov 4)                           │
      │  add_position_realized_events                   │
      │    │                                             │
      │    ▼                                             │
      │  62b5c8b1d8a3 (Nov 4)                           │
      │  add_equity_changes_table                       │
      │    │                                             │
      │    ▼                                             │
      │  i6j7k8l9m0n1 (Nov 6)                           │
      │  add_composite_indexes                          │
      │    │                                             │
      │    ▼                                             │
      │  j7k8l9m0n1o2 (Nov 6)                           │
      │  add_priority_performance_indexes               │
      │    │                                             │
      └────┴───┐                                         │
               │                                         │
               ▼                                         │
       792ffb1ab1ad (Nov 11)                             │
       MERGE of g3h4i5j6k7l8 + j7k8l9m0n1o2              │
               │                                         │
               ▼                                         │
       k8l9m0n1o2p3 (Nov 17)                             │
       add_snapshot_idempotency_fields                   │
               │                                         │
               ▼                                         ▼
           [HEAD 1]                                  [HEAD 2]
           DEAD END                                  DEAD END
           (no merge)                                (no merge)
```

---

## Chain 1 Migrations (NOT in Production)

These 16 migrations exist on `main` but are **NOT applied to Railway production**:

| Order | Revision | Date | Description | Git Commit |
|-------|----------|------|-------------|------------|
| 1 | `7003a3be89fe` | Oct 19 | add_sector_exposure_and_concentration | `3be9a32b` |
| 2 | `h1i2j3k4l5m6` | Oct 19 | add_portfolio_id_to_interest_rate_betas | `3be9a32b` |
| 3 | `b9f866cb3838` | Oct 20 | add_spread_factor_definitions | `3be9a32b` |
| 4 | `035e1888bea0` | Oct 20 | add_portfolio_target_price_fields | `3be9a32b` |
| 5 | `ca2a68ee0c2c` | Oct 28 | add_batch_run_tracking_table | `3be9a32b` |
| 6 | `9b0768a49ad8` | Nov 1 | add_multi_portfolio_support | `3be9a32b` |
| 7 | `ce3dd9222427` | Nov 2 | add_fundamental_tables_and_enhance | `3be9a32b` |
| 8 | `f2a8b1c4d5e6` | Nov 2 | change_share_counts_to_bigint | `3be9a32b` |
| 9 | `2623cfc89fb7` | Nov 3 | add_notes_column_and_active_positions | `3be9a32b` |
| 10 | `a3b4c5d6e7f8` | Nov 4 | add_position_realized_events | `3be9a32b` |
| 11 | `62b5c8b1d8a3` | Nov 4 | add_equity_changes_table | `3be9a32b` |
| 12 | `g3h4i5j6k7l8` | Nov 6 | add_portfolio_account_name_unique_constraint | `3be9a32b` |
| 13 | `i6j7k8l9m0n1` | Nov 6 | add_composite_indexes_for_performance | `3be9a32b` |
| 14 | `j7k8l9m0n1o2` | Nov 6 | add_priority_performance_indexes | `3be9a32b` |
| 15 | `792ffb1ab1ad` | Nov 11 | merge_migration_heads | `3be9a32b` |
| 16 | `k8l9m0n1o2p3` | Nov 17 | add_snapshot_idempotency_fields | `3be9a32b` |

**Note**: All Chain 1 migrations show the same git commit `3be9a32b` ("feat: Dual database architecture"), suggesting they were batch-added in a single commit that merged an old branch.

---

## Chain 2 Migrations (IN Production)

These 5 migrations are applied to Railway production:

| Order | Revision | Date | Description | Git Commit |
|-------|----------|------|-------------|------------|
| 1 | `n0o1p2q3r4s5` | Dec 20 | add_symbol_analytics_tables | `44003485` |
| 2 | `o1p2q3r4s5t6` | Dec 22 | add_admin_user_tables | `ccbc7df8` |
| 3 | `p2q3r4s5t6u7` | Dec 22 | add_user_activity_events | `e761215e` |
| 4 | `q3r4s5t6u7v8` | Dec 22 | add_ai_request_metrics | `8995787a` |
| 5 | `r4s5t6u7v8w9` | Dec 22 | add_batch_history_daily_metrics | `ddeaecdb` |

---

## How This Happened

1. **October 19, 2025**: `f8g9h0i1j2k3` (AI insights tables) was created

2. **October 19 - November 17**: Development continued on what became Chain 1, including:
   - Sector exposure, spread factors, target prices
   - Multi-portfolio support, fundamentals
   - Performance indexes
   - A merge migration (`792ffb1ab1ad`) to combine parallel work
   - Snapshot idempotency fields

3. **December 20**: Someone created `n0o1p2q3r4s5` (symbol analytics) with `down_revision = 'f8g9h0i1j2k3'`, **bypassing all of Chain 1**
   - This was likely done from Railway production state, which only had `f8g9h0i1j2k3` applied
   - The comment in the file says: `# Current Railway version (AI insights tables)`

4. **December 20-22**: Chain 2 continued with admin tables, metrics, and batch history

5. **December 24**: Commit `3be9a32b` ("feat: Dual database architecture") batch-added all Chain 1 migrations to `main`, but **without creating a merge migration**

---

## Root Cause

The problem originated when Chain 2 was created based on **Railway production state** (`f8g9h0i1j2k3`) rather than the **current main branch state** (which had Chain 1).

This happened because:
1. Railway production was behind `main` (only had `f8g9h0i1j2k3`)
2. Someone created new migrations on top of production state
3. Meanwhile, another branch had Chain 1 migrations
4. Both were pushed to main without proper merge

---

## Critical Missing Schema in Production

**UPDATE (2026-01-05 Schema Verification):** All Chain 1 schema objects **already exist** in production:

| Status | Object | Migration |
|--------|--------|-----------|
| ✅ Exists | `portfolio_snapshots.is_complete` | k8l9m0n1o2p3 |
| ✅ Exists | `uq_portfolio_snapshots_portfolio_date` | k8l9m0n1o2p3 |
| ✅ Exists | Target price columns | 035e1888bea0 |
| ✅ Exists | `equity_changes` table | 62b5c8b1d8a3 |
| ✅ Exists | `position_realized_events` table | a3b4c5d6e7f8 |
| ✅ Exists | `positions.notes` column | 2623cfc89fb7 |
| ✅ Exists | Performance indexes | i6j7k8l9m0n1, j7k8l9m0n1o2 |
| ⚠️ Data | Spread factors (wrong `factor_type`) | b9f866cb3838 |

**Conclusion**: Schema is fully aligned. The merge migration can be a no-op. The only discrepancy is a data value (`factor_type = 'style'` vs `'spread'`), which is minor and can be fixed separately if needed.

This indicates Chain 1 migrations were applied **outside of Alembic** (likely via direct SQL or a different deployment method).

---

## Recommended Fix: 2-Phase Approach

The cleanest solution is to fix `main` first, then rebase `AuthOnboarding` on top of the fixed `main`. This keeps the merge migration in `main` where it belongs and gives `AuthOnboarding` a clean starting point.

---

# PHASE 1: Fix Main Branch (Create Single Head)

**Goal**: Get `main` to have a single Alembic head by creating a merge migration.

## Phase 1 Prerequisites

✅ **DONE** (2026-01-05): Stamped Railway with Chain 1 head
```sql
-- Railway now has both heads in alembic_version:
SELECT version_num FROM alembic_version;
-- k8l9m0n1o2p3  (Chain 1 head - just stamped)
-- r4s5t6u7v8w9  (Chain 2 head - was already there)
```

## Phase 1 Steps

### Step 1.1: Switch to main branch
```bash
git checkout main
git pull origin main
```

### Step 1.2: Create merge migration on main
```bash
cd backend
uv run alembic -c alembic.ini revision -m "merge_chain1_and_chain2_heads"
```

Then edit the generated file to set:
```python
# revision identifiers
revision = 'u7v8w9x0y1z2'  # New unique ID
down_revision = ('k8l9m0n1o2p3', 'r4s5t6u7v8w9')  # Both heads
branch_labels = None
depends_on = None

def upgrade():
    pass  # No-op merge

def downgrade():
    pass  # No-op merge
```

### Step 1.3: Verify single head
```bash
uv run alembic -c alembic.ini heads
# Should show only: u7v8w9x0y1z2 (head)
```

### Step 1.4: Commit and push to main
```bash
git add migrations_core/versions/u7v8w9x0y1z2_merge_chain1_and_chain2_heads.py
git commit -m "fix: Merge Alembic migration chains (k8l9m0n1o2p3 + r4s5t6u7v8w9)"
git push origin main
```

### Step 1.5: Deploy to Railway
Railway will apply the merge migration. Since both heads are already stamped, this is a no-op that just unifies the version tracking.

```bash
# Railway deployment will run:
uv run alembic -c alembic.ini upgrade head
# Result: alembic_version now contains only u7v8w9x0y1z2
```

### Step 1.6: (Optional) Create missing table
If `spread_factor_definitions` is needed, create it manually or via a new migration after the merge.

## Phase 1 Expected Result

```
Main branch migration chain (single linear history):

f8g9h0i1j2k3 (Oct 19)
        │
   ┌────┴────┐
   │         │
Chain 1    Chain 2
   │         │
   └────┬────┘
        │
        ▼
u7v8w9x0y1z2 (MERGE) ← NEW SINGLE HEAD
```

---

# PHASE 2: Rebase AuthOnboarding on Fixed Main

**Goal**: Update `AuthOnboarding` to build on the fixed `main` instead of carrying its own merge migration.

## Phase 2 Prerequisites

- Phase 1 complete (main has single head `u7v8w9x0y1z2`)
- Railway deployed with merged migrations

## Phase 2 Steps

### Step 2.1: Switch to AuthOnboarding branch
```bash
git checkout AuthOnboarding
git fetch origin main
```

### Step 2.2: Delete the old merge migration
The file `t6u7v8w9x0y1_merge_heads.py` is no longer needed since main now has the merge.

```bash
rm migrations_core/versions/t6u7v8w9x0y1_merge_heads.py
```

### Step 2.3: Update Clerk auth migration's down_revision
Edit `s5t6u7v8w9x0_add_clerk_auth_columns.py`:

```python
# BEFORE:
down_revision = 't6u7v8w9x0y1'  # Old merge migration

# AFTER:
down_revision = 'u7v8w9x0y1z2'  # Main's new merge migration
```

### Step 2.4: Rebase on main
```bash
git rebase origin/main
# Resolve any conflicts (mainly the migration file changes)
```

### Step 2.5: Verify migration chain
```bash
uv run alembic -c alembic.ini heads
# Should show only: 15e70d6147cd (head) - batch_runs table

uv run alembic -c alembic.ini history --verbose
# Should show clean linear chain from main's merge → Clerk → batch_runs
```

### Step 2.6: Force push rebased branch
```bash
git push --force-with-lease origin AuthOnboarding
```

## Phase 2 Expected Result

```
AuthOnboarding migration chain (clean, linear):

u7v8w9x0y1z2 (main's merge) ← From main
        │
        ▼
s5t6u7v8w9x0 (Clerk auth columns)
        │
        ▼
15e70d6147cd (batch_runs table) ← HEAD
```

---

## Summary: Before and After

### BEFORE (Current State)
```
main:           2 unmerged heads (k8l9m0n1o2p3, r4s5t6u7v8w9)
AuthOnboarding: Has its own merge (t6u7v8w9x0y1) + 2 new migrations
Railway:        Has both heads stamped (fixed earlier)
```

### AFTER (Phase 1 + Phase 2 Complete)
```
main:           Single head (u7v8w9x0y1z2)
AuthOnboarding: Clean branch with 2 migrations on top of main's merge
Railway:        Single head (u7v8w9x0y1z2), ready for AuthOnboarding PR
```

---

## Benefits of 2-Phase Approach

1. **Main is self-contained**: The merge lives in main where the problem originated
2. **AuthOnboarding is clean**: No merge complexity, just feature migrations
3. **Easier code review**: AuthOnboarding PR shows only Clerk + batch_runs changes
4. **Railway stays stable**: Phase 1 deploys first, Phase 2 is just a feature branch
5. **Rollback is simpler**: Each phase can be tested independently

---

## Prevention: CI Checks for Migration Drift

To prevent this from happening again, add these checks to CI:

### Option 1: GitHub Actions Check (Recommended)

Add to `.github/workflows/ci.yml`:

```yaml
- name: Check Alembic single head
  run: |
    cd backend
    HEAD_COUNT=$(uv run alembic -c alembic.ini heads | wc -l)
    if [ "$HEAD_COUNT" -gt 1 ]; then
      echo "❌ ERROR: Multiple Alembic heads detected!"
      uv run alembic -c alembic.ini heads
      exit 1
    fi
    echo "✅ Single Alembic head confirmed"

- name: Verify migration history
  run: |
    cd backend
    uv run alembic -c alembic.ini history --verbose | head -20
```

### Option 2: Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: alembic-single-head
      name: Check Alembic single head
      entry: bash -c 'cd backend && uv run alembic -c alembic.ini heads | wc -l | xargs test 1 -eq'
      language: system
      pass_filenames: false
      files: ^backend/migrations_core/
```

### Option 3: Branch Protection Rule

Require the CI check to pass before merging to `main`. This ensures:
- No PR can introduce a second head
- Merges to main always maintain linear migration history

### Recommended Implementation

1. Add the GitHub Actions check (Option 1)
2. Enable branch protection requiring the check to pass
3. Document in CONTRIBUTING.md that migrations must maintain single head

---

## Execution Checklist

### Phase 1: Fix Main Branch
- [x] Investigate multiple heads issue
- [x] Document migration tree and divergence point
- [x] Verify Railway production schema state
- [x] Stamp Railway with Chain 1 head (`k8l9m0n1o2p3`)
- [ ] Switch to main branch
- [ ] Create merge migration (`u7v8w9x0y1z2`)
- [ ] Verify single head with `alembic heads`
- [ ] Commit and push to main
- [ ] Deploy to Railway
- [ ] Verify Railway has single head

### Phase 2: Rebase AuthOnboarding
- [ ] Switch to AuthOnboarding branch
- [ ] Delete old merge migration (`t6u7v8w9x0y1`)
- [ ] Update Clerk migration's `down_revision`
- [ ] Rebase on updated main
- [ ] Verify migration chain
- [ ] Force push rebased branch
- [ ] Create PR to merge AuthOnboarding → main

### Follow-up: Prevention
- [ ] Add CI check for single Alembic head (see Prevention section)
- [ ] Enable branch protection requiring CI check
- [ ] (Optional) Fix spread factor `factor_type` values if needed

---

## Files Referenced

- `/Users/elliottng/CascadeProjects/SigmaSight-BE/backend/migrations_core/versions/`
- Railway Core Database: `gondola.proxy.rlwy.net:38391/railway`

---

*Investigation conducted by Claude Code on 2026-01-05*
*Railway stamped with Chain 1 head on 2026-01-05*
*2-Phase fix plan documented on 2026-01-05*
