# 09: Railway Constraints

## Overview

Railway-specific configuration and constraints for V2 batch architecture.

---

## Resource Limits

| Resource | Limit | Our Usage |
|----------|-------|-----------|
| Memory | 8 GB | ~200 MB peak (cache + processing) |
| CPU | 8 vCPU | Burst during batch |
| Cron timeout | 30 min | Target: 15 min symbol, 10 min portfolio |
| Concurrent tasks | 10 recommended | 5 for API calls |

---

## Cron Configuration

```yaml
# railway.json
{
  "crons": [
    {
      "name": "symbol-batch",
      "schedule": "0 2 * * 1-5",
      "command": "python scripts/batch_processing/run_symbol_batch.py"
    },
    {
      "name": "portfolio-refresh",
      "schedule": "30 2 * * 1-5",
      "command": "python scripts/batch_processing/run_portfolio_refresh.py"
    }
  ]
}
```

**Note**: Times in UTC.
- 2:00 AM UTC = 9:00 PM ET (EST) / 10:00 PM ET (EDT)
- 2:30 AM UTC = 9:30 PM ET (EST) / 10:30 PM ET (EDT)

---

## Async + Windows Event Loop Fix

**Problem**: Railway runs on Linux, but local development on Windows can have asyncio issues. The default Windows event loop (`ProactorEventLoop`) has compatibility issues with some async libraries.

**Fix**: Set event loop policy at script entry point.

```python
# scripts/batch_processing/run_symbol_batch.py

import sys
import asyncio

# Windows asyncio fix - must be before any async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvloop  # Only on Linux/Mac

async def main():
    # ... batch logic ...
    pass

if __name__ == "__main__":
    # Use uvloop on Linux (Railway), default on Windows
    if sys.platform != "win32":
        uvloop.install()

    asyncio.run(main())
```

**Alternative - use `anyio` for cross-platform compatibility:**

```python
# If using anyio (already in our deps via httpx)
import anyio

async def main():
    # ... batch logic ...
    pass

if __name__ == "__main__":
    anyio.run(main)
```

---

## Environment Variables

```bash
# Railway environment variables for V2

# Master switch
BATCH_V2_ENABLED=true

# Batch timing (optional overrides)
SYMBOL_BATCH_TIMEOUT_SECONDS=1500  # 25 min abort
PORTFOLIO_REFRESH_TIMEOUT_SECONDS=900  # 15 min abort

# Concurrency limits
PRICE_FETCH_CONCURRENCY=5
FACTOR_CALC_CONCURRENCY=10
PORTFOLIO_REFRESH_CONCURRENCY=10

# Alerting (if configured)
ALERT_WEBHOOK_URL=https://...  # Slack/Discord webhook
```

---

## Timeout Handling

```python
import asyncio
from app.config import settings

async def run_symbol_batch():
    """Run symbol batch with timeout."""
    timeout = settings.symbol_batch_timeout_seconds or 1500  # 25 min default

    try:
        await asyncio.wait_for(
            _run_symbol_batch_internal(),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Symbol batch timed out after {timeout}s")
        await send_alert(f"Symbol batch timed out after {timeout}s")
        raise
```

---

## Batch Timing Thresholds

| Metric | Target | Warning | Abort |
|--------|--------|---------|-------|
| Symbol batch duration | 15 min | 20 min | 25 min |
| Portfolio refresh duration | 10 min | 15 min | 20 min |
| Symbol onboarding (single) | 10 sec | 30 sec | 60 sec |

```python
# Logging with timing alerts
async def run_symbol_batch():
    start = time.time()

    result = await _run_symbol_batch_internal()

    duration = time.time() - start
    duration_min = duration / 60

    if duration_min > 20:
        logger.warning(f"Symbol batch took {duration_min:.1f} min (warning threshold)")
    elif duration_min > 25:
        logger.error(f"Symbol batch took {duration_min:.1f} min (exceeded abort threshold)")

    logger.info(f"V2_BATCH_STEP step=symbol_batch_complete duration_seconds={duration:.0f}")
```

---

## Deployment Checklist

Before enabling V2 on Railway:

- [ ] Set `BATCH_V2_ENABLED=false` initially
- [ ] Deploy code with both V1 and V2 paths
- [ ] Verify cron schedules in Railway dashboard
- [ ] Check timezone (Railway uses UTC)
- [ ] Set `BATCH_V2_ENABLED=true` to enable
- [ ] Monitor first batch run in logs
- [ ] Verify admin dashboard shows correct status

---

## Rollback

If V2 has issues:

1. Set `BATCH_V2_ENABLED=false` in Railway dashboard
2. Redeploy (automatic on env var change)
3. Next cron run uses legacy batch
4. Time to rollback: ~2-3 minutes

---

## Local Development vs Railway

| Aspect | Local (Windows) | Railway (Linux) |
|--------|-----------------|-----------------|
| Event loop | WindowsSelectorEventLoopPolicy | uvloop |
| Cron | Manual trigger | Railway cron |
| Database | Local PostgreSQL | Railway PostgreSQL |
| Cache | In-memory (lost on restart) | In-memory (lost on deploy) |

**Testing locally:**

```bash
# Run symbol batch manually
cd backend
python scripts/batch_processing/run_symbol_batch.py

# Run portfolio refresh manually
python scripts/batch_processing/run_portfolio_refresh.py
```
