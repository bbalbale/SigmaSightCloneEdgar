# 12: Operational Toggles

## Overview

Single master switch to control V2 batch architecture activation, with comprehensive logging to validate each step is working correctly.

---

## Master Switch

```python
# Environment variable (requires redeploy to change)
BATCH_V2_ENABLED = os.getenv("BATCH_V2_ENABLED", "false").lower() == "true"
```

**When `BATCH_V2_ENABLED=false` (default):**
- Symbol Batch Cron: Runs legacy `batch_orchestrator.run_daily_batch_with_backfill()`
- Portfolio Refresh Cron: Does not run (legacy handles it)
- User Onboarding: Uses legacy batch trigger with progress polling

**When `BATCH_V2_ENABLED=true`:**
- Symbol Batch Cron: Runs new `symbol_batch_runner.run()`
- Portfolio Refresh Cron: Runs new `portfolio_refresh_runner.run()`
- User Onboarding: Uses instant snapshot with cached prices

---

## Implementation

```python
# backend/app/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # V2 Batch Architecture
    batch_v2_enabled: bool = Field(
        default=False,
        description="Enable V2 batch architecture (two-cron, instant onboarding)"
    )

settings = Settings()
```

### Cron Entry Point

```python
# scripts/batch_processing/run_batch.py

async def main():
    """Main entry point for daily batch processing."""
    from app.config import settings

    if settings.batch_v2_enabled:
        logger.info("BATCH_V2_ENABLED=true, running V2 symbol batch")
        from app.batch.v2.symbol_batch_runner import run_symbol_batch
        await run_symbol_batch()
    else:
        logger.info("BATCH_V2_ENABLED=false, running legacy batch")
        from app.batch.batch_orchestrator import batch_orchestrator
        await batch_orchestrator.run_daily_batch_with_backfill()
```

### Portfolio Refresh Entry Point

```python
# scripts/batch_processing/run_portfolio_refresh.py

async def main():
    """Portfolio refresh - only runs in V2 mode."""
    from app.config import settings

    if not settings.batch_v2_enabled:
        logger.warning("BATCH_V2_ENABLED=false, portfolio refresh skipped")
        return {"status": "skipped", "reason": "v2_disabled"}

    logger.info("Running V2 portfolio refresh")
    from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh
    return await run_portfolio_refresh()
```

### Onboarding Switch

```python
# backend/app/services/portfolio_service.py

async def create_portfolio_with_csv(
    db: AsyncSession,
    user_id: UUID,
    csv_data: UploadFile,
    portfolio_name: str
) -> CreatePortfolioResponse:
    """Create portfolio from CSV."""
    from app.config import settings

    if settings.batch_v2_enabled:
        # V2: Instant snapshot with cached prices
        logger.info(f"V2 onboarding for user {user_id}")
        return await _create_portfolio_v2(db, user_id, csv_data, portfolio_name)
    else:
        # Legacy: Trigger batch and poll for completion
        logger.info(f"Legacy onboarding for user {user_id}")
        return await _create_portfolio_legacy(db, user_id, csv_data, portfolio_name)
```

---

## Logging Strategy

### Step-by-Step Logging

Every significant step logs with consistent format for easy parsing:

```python
# Structured logging format
logger.info(
    "V2_BATCH_STEP",
    extra={
        "step": "symbol_prices",
        "status": "started|completed|failed",
        "duration_ms": 1234,
        "symbols_processed": 500,
        "errors": 0
    }
)
```

### Log Examples

**Symbol Batch Run:**
```
2026-01-11 21:00:00 INFO V2_BATCH_STEP step=symbol_batch_start batch_date=2026-01-10
2026-01-11 21:00:05 INFO V2_BATCH_STEP step=symbol_prices status=started symbols=500
2026-01-11 21:05:00 INFO V2_BATCH_STEP step=symbol_prices status=completed duration_ms=300000 symbols=500 errors=0
2026-01-11 21:05:01 INFO V2_BATCH_STEP step=symbol_factors status=started symbols=500
2026-01-11 21:12:00 INFO V2_BATCH_STEP step=symbol_factors status=completed duration_ms=420000 symbols=500 errors=0
2026-01-11 21:12:01 INFO V2_BATCH_STEP step=symbol_batch_complete duration_ms=720000 success=true
```

**Portfolio Refresh Run:**
```
2026-01-11 21:30:00 INFO V2_BATCH_STEP step=portfolio_refresh_start batch_date=2026-01-10
2026-01-11 21:30:00 INFO V2_BATCH_STEP step=symbol_batch_check status=verified
2026-01-11 21:30:01 INFO V2_BATCH_STEP step=portfolios_found count=150
2026-01-11 21:30:02 INFO V2_BATCH_STEP step=portfolio_snapshot portfolio_id=abc-123 status=created
...
2026-01-11 21:35:00 INFO V2_BATCH_STEP step=portfolio_refresh_complete duration_ms=300000 success=150 failed=0
```

**User Onboarding:**
```
2026-01-11 14:23:45 INFO V2_ONBOARDING step=start user_id=user-123 symbols=15
2026-01-11 14:23:45 INFO V2_ONBOARDING step=symbol_check known=14 unknown=1
2026-01-11 14:23:46 INFO V2_ONBOARDING step=portfolio_created portfolio_id=port-456
2026-01-11 14:23:46 INFO V2_ONBOARDING step=snapshot_created date=2026-01-10 positions=14
2026-01-11 14:23:47 INFO V2_ONBOARDING step=analytics_cached portfolio_id=port-456
2026-01-11 14:23:47 INFO V2_ONBOARDING step=complete duration_ms=2100 status=partial pending_symbols=1
```

---

## Validation Metrics

Track these metrics to validate V2 is working:

| Metric | Expected Value | Alert Threshold |
|--------|----------------|-----------------|
| `v2.symbol_batch.duration_seconds` | ~900 (15 min) | > 1800 (30 min) |
| `v2.symbol_batch.symbols_processed` | ~500 | < 400 |
| `v2.symbol_batch.errors` | 0 | > 10 |
| `v2.portfolio_refresh.duration_seconds` | ~300-900 | > 1800 |
| `v2.portfolio_refresh.portfolios_processed` | All active | < 90% of active |
| `v2.onboarding.duration_seconds` | < 5 | > 10 |
| `v2.onboarding.success_rate` | > 99% | < 95% |

---

## Rollback Procedure

If V2 shows problems:

1. Set `BATCH_V2_ENABLED=false` in Railway dashboard
2. Redeploy service (1-2 minutes)
3. Next cron run uses legacy batch
4. User onboarding reverts to legacy batch trigger

**Rollback time**: ~3 minutes

---

## Rollout Plan

| Phase | Duration | Config | Validation |
|-------|----------|--------|------------|
| 1. Deploy code | Day 1 | `BATCH_V2_ENABLED=false` | Verify no regressions |
| 2. Enable V2 batch | Day 2-3 | `BATCH_V2_ENABLED=true` | Monitor cron logs |
| 3. Monitor week | Day 4-10 | Stay enabled | Check all metrics |
| 4. Remove legacy | Week 3+ | Delete legacy code | Full V2 |

---

## Fallback Behavior

If V2 encounters critical errors during execution:

```python
async def run_symbol_batch():
    """Run V2 symbol batch with fallback."""
    try:
        result = await _run_symbol_batch_internal()
        if result["success"]:
            return result

        # Batch failed but didn't crash
        logger.error("V2 symbol batch failed, NOT falling back to legacy")
        await send_alert("V2 symbol batch failed - manual intervention required")
        return result

    except Exception as e:
        # Unexpected crash
        logger.error(f"V2 symbol batch crashed: {e}")
        await send_alert(f"V2 symbol batch crashed: {e}")

        # Do NOT auto-fallback - could cause duplicate processing
        # Ops team should decide whether to manually run legacy
        raise
```

**Rationale**: No automatic fallback to legacy during cron runs. If V2 fails:
1. Alert ops team
2. Manual decision on whether to run legacy
3. Prevents duplicate data or partial state corruption

---

## Monitoring Dashboard

Create Railway/Grafana dashboard showing:

1. **Batch Status Panel**
   - Symbol batch: last run time, duration, status
   - Portfolio refresh: last run time, portfolios processed, failures

2. **Onboarding Panel**
   - Onboardings last 24h: count, avg duration, success rate
   - Unknown symbols queued: count, processing time

3. **Cache Health Panel**
   - Cache hit rate
   - Cache invalidations last 24h

4. **Alerts Panel**
   - Symbol batch overdue (not started by 9:15 PM ET)
   - Portfolio refresh overdue (not started by 9:45 PM ET)
   - Onboarding failures > 5%
