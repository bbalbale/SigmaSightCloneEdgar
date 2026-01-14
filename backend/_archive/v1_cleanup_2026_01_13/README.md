# V1/V2 Cleanup Archive - 2026-01-13

**Purpose**: Backup of files before removing BATCH_V2_ENABLED flag and V1 fallback code.

## Why This Cleanup Was Done

1. V2 batch architecture is stable and production-validated
2. V1 fallback code was causing confusion for AI coding agents
3. Rolling back to V1 is not realistic due to architecture changes
4. Cleaner codebase with single code path

## Archived Files

| File | Original Location | Changes Made |
|------|-------------------|--------------|
| `config.py` | `app/config.py` | Removed BATCH_V2_ENABLED setting |
| `railway_daily_batch.py` | `scripts/automation/` | Removed V1 fallback, kept V2 only |
| `main.py` | `app/main.py` | Removed V2 conditional checks |
| `scheduler_config.py` | `app/batch/` | Removed V1/V2 conditional logic |
| `portfolios.py` | `app/api/v1/` | Removed V2 conditional |
| `health.py` | `app/api/v1/` | Removed V2 status reporting |
| `onboarding_status.py` | `app/api/v1/` | Removed V1/V2 mode logic |
| `run_symbol_batch.py` | `scripts/batch_processing/` | Removed V2 guard |
| `run_portfolio_refresh.py` | `scripts/batch_processing/` | Removed V2 guard |
| `test_v2_batch.py` | `scripts/railway/` | Obsolete test script (checked for V2 mode in health responses) |

## Reference

These files contain the pre-cleanup versions with BATCH_V2_ENABLED checks.
After cleanup, the codebase assumes V2 is always enabled (the only mode).
