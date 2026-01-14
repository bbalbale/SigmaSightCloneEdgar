# 23-DEPRECATE-OLD-ARCHITECTURE

**V1 Code Path Cleanup Plan**

**Date**: 2026-01-13
**Status**: Planning
**Reference Branch**: `BatchProcessUpdate` (pre-V2 architecture baseline)

---

## 1. Executive Summary

The SigmaSight batch processing system now runs a **dual architecture**:

1. **V2 (Nightly Automation)**: `symbol_batch_runner` + `portfolio_refresh_runner` - handles the nightly Railway cron
2. **batch_orchestrator (On-Demand)**: Admin API, user calculate endpoint, manual batch triggers

**Key Decision**: Both systems are needed. V2 handles automated nightly processing, while batch_orchestrator handles on-demand/admin operations.

This document outlines the plan to:
1. **Clean up obsolete V1-specific scripts** that are no longer used
2. **Remove the V1 fallback path** from `railway_daily_batch.py` (V2 is now stable)
3. **Update documentation** to clarify the dual architecture
4. **Archive old debugging/testing scripts** related to V1-only flows

**What We Are NOT Doing**:
- NOT archiving `batch_orchestrator.py` - still needed for admin/on-demand processing
- NOT archiving `analytics_runner.py` - still used by batch_orchestrator
- NOT removing `BATCH_V2_ENABLED` flag entirely - useful for emergency rollback

---

## 2. Architecture Overview (Current State)

### V2 Nightly Batch (Railway Cron)
When `BATCH_V2_ENABLED=true` (production default):

| Component | Purpose |
|-----------|---------|
| `app/batch/v2/symbol_batch_runner.py` | Universe-level market data + factor calculations |
| `app/batch/v2/portfolio_refresh_runner.py` | Portfolio-level P&L + analytics refresh |
| `app/batch/v2/symbol_onboarding.py` | Instant onboarding for new symbols |

**Entry Point**: `scripts/automation/railway_daily_batch.py` → `run_v2_batch()`

### batch_orchestrator (On-Demand Processing)
Still actively used for:

| Use Case | File | Method |
|----------|------|--------|
| Admin batch endpoint | `app/api/v1/endpoints/admin_batch.py` | `batch_orchestrator.run_daily_batch_with_backfill()` |
| User calculate endpoint | `app/api/v1/portfolios.py` | Portfolio calculation triggers |
| Batch trigger service | `app/services/batch_trigger_service.py` | On-demand batch coordination |
| APScheduler jobs | `app/batch/scheduler_config.py` | Background job scheduling |

### Key Shared Components (DO NOT ARCHIVE)
| File | Used By |
|------|---------|
| `batch_orchestrator.py` | Admin API, scheduler, on-demand triggers |
| `analytics_runner.py` | batch_orchestrator (Phase 6) |
| `market_data_collector.py` | V2 symbol_batch_runner, symbol_onboarding |
| `fundamentals_collector.py` | V2 symbol_batch_runner |
| `pnl_calculator.py` | V2 portfolio_refresh_runner, batch_orchestrator |
| `batch_run_tracker.py` | Both V2 and batch_orchestrator |

---

## 3. Files to Clean Up

### 3.1 Scripts to Archive (No Longer Needed)
These scripts were used during V1 development/debugging and are obsolete now that V2 is stable:

**ARCHIVE to `_archive/v1_scripts/`:**

| Script | Reason |
|--------|--------|
| `scripts/railway/_archive_manual_batch_railway.py` | Already prefixed as archive |
| `scripts/test_phase_1_5_integration.py` | Tests V1-specific phase 1.5 |
| `scripts/test_phase_5_6_integration.py` | Tests V1-specific phases |

**REVIEW (may need updates):**

| Script | Current State | Recommendation |
|--------|--------------|----------------|
| `scripts/batch_processing/run_batch.py` | Uses batch_orchestrator | KEEP - useful for local testing |
| `scripts/manual_catchup_batch.py` | Uses batch_orchestrator | KEEP - useful for manual recovery |
| `scripts/run_batch_now.py` | Uses batch_orchestrator | KEEP - useful for on-demand runs |
| `scripts/maintenance/run_phase3_only.py` | Uses V1 phases | Archive (V2 handles this differently) |

### 3.2 Batch Module Files (DO NOT ARCHIVE)

All files in `app/batch/` are still in use:

| File | Status | Reason |
|------|--------|--------|
| `batch_orchestrator.py` | **KEEP** | Used by admin API, scheduler, on-demand |
| `analytics_runner.py` | **KEEP** | Used by batch_orchestrator |
| `market_data_collector.py` | **KEEP** | Used by V2 symbol_batch_runner |
| `fundamentals_collector.py` | **KEEP** | Used by V2 symbol_batch_runner |
| `pnl_calculator.py` | **KEEP** | Used by V2 and batch_orchestrator |
| `batch_run_tracker.py` | **KEEP** | Used by both |
| `scheduler_config.py` | **KEEP** | APScheduler configuration |

### 3.3 Documentation Updates

**Documentation to Archive** (already done in Phase 1):

| Document | Location |
|----------|----------|
| V1 debugging sessions | `_archive/v1_docs/` |
| V1 testing progress | `_archive/v1_docs/` |
| V1 9-phase architecture docs | `_archive/v1_docs/` |

---

## 4. Code Modifications (Optional Future Work)

These are optional cleanup items - the current dual architecture works correctly.

### 4.1 Railway Daily Batch Script (OPTIONAL)

**File**: `scripts/automation/railway_daily_batch.py`

**Current State**: V2 guard redirects to V2 when enabled, V1 fallback exists

**Optional Cleanup**:
- Remove V1 fallback code (lines 216-276) - only if confident V2 won't need rollback
- Keep `BATCH_V2_ENABLED` flag for emergency rollback capability

### 4.2 Documentation Updates

**Files to Update**:
- `backend/CLAUDE.md` - Clarify dual architecture (V2 nightly + batch_orchestrator on-demand)
- `CLAUDE.md` (root) - Same

**Key Message**: Both systems are actively used - V2 is NOT replacing batch_orchestrator

---

## 5. Current Production Architecture

### 5.1 V2 Nightly Batch Components

| File | Purpose |
|------|---------|
| `app/batch/v2/symbol_batch_runner.py` | Universe-level batch (market data, factors) |
| `app/batch/v2/portfolio_refresh_runner.py` | Portfolio-level batch (P&L, analytics) |
| `app/batch/v2/symbol_onboarding.py` | Instant onboarding for new symbols |

### 5.2 batch_orchestrator On-Demand Components

| File | Purpose |
|------|---------|
| `app/batch/batch_orchestrator.py` | On-demand batch processing |
| `app/batch/analytics_runner.py` | Analytics phase (used by batch_orchestrator) |
| `app/api/v1/endpoints/admin_batch.py` | Admin batch API |
| `app/services/batch_trigger_service.py` | Batch coordination service |

### 5.3 Shared Components (Both V2 and batch_orchestrator)

| Component | Reason |
|-----------|--------|
| `app/batch/pnl_calculator.py` | Core P&L calculation logic |
| `app/batch/batch_run_tracker.py` | Batch run tracking |
| `app/batch/market_data_collector.py` | Market data fetching |
| `app/batch/fundamentals_collector.py` | Fundamentals fetching |

---

## 6. Configuration (Keep As-Is)

### 6.1 Environment Variables

**KEEP (for V2 nightly batch + emergency rollback)**:
```bash
BATCH_V2_ENABLED=true                    # Enables V2 nightly batch
SYMBOL_BATCH_TIMEOUT_SECONDS=1500        # V2 symbol batch timeout
PORTFOLIO_REFRESH_TIMEOUT_SECONDS=900    # V2 portfolio refresh timeout
MAX_PORTFOLIO_CONCURRENCY=10             # V2 parallel portfolio processing
MAX_BACKFILL_DATES=30                    # Max dates to backfill
```

### 6.2 Railway Cron Configuration

**Current (V2)**:
```
Symbol Batch: 0 2 * * 1-5 (9 PM ET)
Portfolio Refresh: 0 2 30 * * 1-5 (9:30 PM ET)
```

**No changes needed** - already V2 configuration.

---

## 7. Summary: Dual Architecture

### Key Takeaways

1. **V2 handles nightly automated batch** via Railway cron
   - Entry point: `scripts/automation/railway_daily_batch.py` → `run_v2_batch()`
   - Components: `symbol_batch_runner.py`, `portfolio_refresh_runner.py`

2. **batch_orchestrator handles on-demand processing**
   - Admin API: `POST /api/v1/admin/batch/run`
   - User calculate: `POST /api/v1/portfolios/{id}/calculate`
   - Manual scripts: `run_batch.py`, `manual_catchup_batch.py`

3. **Shared components used by both**:
   - `pnl_calculator.py`, `market_data_collector.py`, `fundamentals_collector.py`
   - `batch_run_tracker.py`

### What NOT to Do

- **DO NOT** archive `batch_orchestrator.py` - still needed for admin/on-demand
- **DO NOT** archive `analytics_runner.py` - still used by batch_orchestrator
- **DO NOT** remove `BATCH_V2_ENABLED` flag - needed for emergency rollback

---

## 8. Completed Actions (Phase 1)

✅ **Done on 2026-01-13**:
1. Created archive directories: `_archive/v1_batch/`, `_archive/v1_scripts/`, `_archive/v1_docs/`
2. Verified V2 is working in production (`BATCH_V2_ENABLED=True`)
3. Created backup tag `v1-batch-architecture-backup` pointing to BatchProcessUpdate branch
4. Added README files to archive directories
5. Corrected this plan to reflect dual architecture reality

---

## 9. Rollback Plan

### If V2 Nightly Batch Has Issues

1. **Immediate**: Set `BATCH_V2_ENABLED=false` in Railway dashboard
2. **Effect**: Railway cron will use batch_orchestrator instead of V2 runners
3. **Rollback time**: ~3 minutes (environment variable change + redeploy)

### Reference

- `BatchProcessUpdate` branch: Contains pre-V2 code for reference
- `v1-batch-architecture-backup` tag: Points to BatchProcessUpdate for quick access

---

## 10. Appendix: Entry Points Reference

### A. V2 Entry Points (Nightly Cron)

```python
# Symbol Batch (Phase 1)
from app.batch.v2.symbol_batch_runner import run_symbol_batch
await run_symbol_batch(target_date=None, backfill=True)

# Portfolio Refresh (Phase 2)
from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh
await run_portfolio_refresh(target_date=None, backfill=True)

# Instant Onboarding
from app.batch.v2.symbol_onboarding import onboard_portfolio_symbols
await onboard_portfolio_symbols(portfolio_id, symbols)
```

### B. batch_orchestrator Entry Points (On-Demand)

```python
# Full batch processing
from app.batch.batch_orchestrator import batch_orchestrator
await batch_orchestrator.run_daily_batch_with_backfill(
    start_date=None,
    end_date=None,
    portfolio_ids=None,
    force_rerun=False,
)

# Used by admin API and user calculate endpoints
```

---

## 11. Sign-Off

| Role | Name | Date | Approval |
|------|------|------|----------|
| Developer | | 2026-01-13 | Plan corrected |
| Reviewer | | | |
| Product Owner | | | |

---

**Status**: Plan corrected to reflect dual architecture. No major code changes needed - both V2 and batch_orchestrator remain active and serve different purposes.
