# Railway Database Initial Seeding Guide

## Overview

This guide explains how to seed your Railway PostgreSQL database for the first time after deployment.

## Prerequisites

✅ Backend successfully deployed to Railway (migrations completed)
✅ Railway CLI installed locally (`brew install railway` or similar)
✅ Logged into Railway CLI (`railway login`)
✅ Linked to your Railway project (`railway link`)

## Quick Start (Recommended)

Run the automated seeding script via SSH:

```bash
railway ssh bash scripts/railway_initial_seed.sh
```

This **single command** will:
1. ✅ Check for existing data
2. ✅ Seed demo accounts and portfolios (3 accounts, 63 positions)
3. ✅ Validate database setup
4. ✅ Verify portfolio IDs are deterministic
5. ✅ Seed target prices (105 records)
6. ✅ Run batch processing to populate all calculations

**Expected Time:** 2-5 minutes

## What Gets Created

### Demo Accounts
```
Email: demo_individual@sigmasight.com
Email: demo_hnw@sigmasight.com
Email: demo_hedgefundstyle@sigmasight.com
Password (all): demo12345
```

### Portfolios (Deterministic IDs)
```
Individual Investor: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
High Net Worth: e23ab931-a033-edfe-ed4f-9d02474780b4
Hedge Fund Style: fcd71196-e93e-f000-5a74-31a9eead3118
```

### Data Seeded
- **63 positions** across 3 portfolios
- **8 factor definitions** (Market Beta, Momentum, Value, Growth, Quality, Size, Low Volatility, Short Interest)
- **18 stress test scenarios** across 5 categories
- **105 target price records** (35 symbols × 3 portfolios)
- **Security master data** (sector/industry classifications)
- **Initial price cache** (current market prices)
- **Calculation data** (factor exposures, correlations, snapshots, market risk scenarios)

## Alternative: Manual Step-by-Step

If you prefer to run commands manually:

### 1. Check for Existing Data
```bash
railway ssh uv run python scripts/database/check_database_content.py
```

### 2. Seed Database
```bash
railway ssh uv run python scripts/database/seed_database.py
```

### 3. Validate Setup
```bash
railway ssh uv run python scripts/validation/verify_setup.py
```

### 4. Verify Portfolio IDs
```bash
railway ssh uv run python scripts/list_portfolios.py
```

### 5. Seed Target Prices (Optional)
```bash
railway ssh uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv --execute
```

### 6. Run Batch Processing
```bash
railway ssh uv run python scripts/batch_processing/run_batch_with_reports.py
```

## Verify Deployment

After seeding completes, test your API:

### 1. Health Check
```bash
curl https://sigmasight-be-production.up.railway.app/health
```
Expected: `{"status":"healthy"}`

### 2. Test Login
```bash
curl -X POST https://sigmasight-be-production.up.railway.app/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_individual@sigmasight.com","password":"demo12345"}'
```

### 3. View API Documentation
Open in browser: https://sigmasight-be-production.up.railway.app/docs

### 4. Test Data Endpoint
```bash
# First, get a token from step 2 above, then:
curl -X GET https://sigmasight-be-production.up.railway.app/api/v1/data/portfolio/1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe/complete \
  -H 'Authorization: Bearer YOUR_TOKEN_HERE'
```

## Troubleshooting

### Script Fails with "command not found"
- Make sure you're running from the Railway container: `railway ssh`
- Try using the full path: `bash /app/scripts/railway_initial_seed.sh`

### "Existing data found" Warning
- The script will wait 5 seconds before proceeding
- Press `Ctrl+C` to cancel if you don't want to overwrite existing data
- Or let it continue to re-seed (useful for resetting to known state)

### Batch Processing Errors
- Some errors are expected (e.g., missing options data for Greeks)
- Check Railway logs: `railway logs --lines 100`
- Look for "✓ Batch processing completed" or "⚠ encountered errors"

### API Returns Empty Data
- Verify batch processing completed successfully
- Check Railway logs for calculation engine errors
- Re-run batch processing: `railway ssh uv run python scripts/batch_processing/run_batch_with_reports.py`

## View Logs

Watch the seeding process in real-time:

```bash
# In a separate terminal
railway logs

# Or filter for errors only
railway logs --filter "@level:error"
```

## Resetting the Database

To completely reset and re-seed:

```bash
# Option 1: Use the seeding script (recommended)
railway ssh bash scripts/railway_initial_seed.sh

# Option 2: Manual reset (DESTRUCTIVE)
railway ssh uv run python scripts/database/reset_and_seed.py reset --confirm
```

## Interactive Session

For debugging or exploration:

```bash
# Open interactive shell
railway ssh

# Once inside:
uv run python scripts/database/check_database_content.py
uv run python scripts/list_portfolios.py
uv run python -c "from app.database import AsyncSessionLocal; print('DB connected!')"

# Exit when done
exit
```

## Next Steps

Once seeding is complete:
1. Test API endpoints via Swagger UI: `/docs`
2. Test authentication flow with demo accounts
3. Explore calculation data in the database
4. Connect your frontend to the Railway backend
5. For daily operations, see: `_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`

## Related Documentation

- **Initial Setup Guide**: `_guides/BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`
- **Daily Operations**: `_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`
- **API Reference**: `_docs/reference/API_REFERENCE_V1.4.6.md`
- **Deterministic IDs**: `SETUP_DETERMINISTIC_IDS.md`

---

**Last Updated**: October 4, 2025
**Version**: 1.0 - Initial Railway seeding automation
