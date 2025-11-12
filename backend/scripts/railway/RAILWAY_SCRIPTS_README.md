# Railway Production Scripts

Scripts designed to run **on Railway's servers** (not locally) to avoid async driver conflicts.

## Why These Scripts?

Running `railway run python <script>` executes the script **locally** but connects to Railway's database. This causes issues because:
- Local environment uses `psycopg2` (sync driver)
- Railway's async code requires `asyncpg` (async driver)
- Result: `InvalidRequestError: The asyncio extension requires an async driver`

These Railway-specific scripts are designed to be executed **on the Railway server itself** where the correct async drivers are available.

## Quick Start - All-in-One Fix

### Complete Data Fix (`fix_railway_data.py`) ⭐ **RECOMMENDED**

Runs all three steps in one command: clears calculations, seeds portfolios, and runs batch processing.

**Usage:**
```bash
railway run --service SigmaSight-BE python scripts/railway/fix_railway_data.py
```

**What it does (in order):**
1. Clears all old calculation data
2. Seeds portfolios with corrected June 30, 2025 data
3. Runs batch processing to calculate P&L and analytics

**Estimated time:** 10-20 minutes

**Use this when:**
- Railway production has empty portfolios or wrong data
- You want to completely reset and fix everything
- You don't want to run individual steps

---

## Individual Scripts

### 1. Clear Calculations (`clear_calculations_railway.py`)

Clears all calculated data (snapshots, P&L, Greeks, factors, correlations) **WITHOUT** touching the market data cache.

**Usage:**
```bash
railway run --service SigmaSight-BE python scripts/railway/clear_calculations_railway.py
```

**What it clears:**
- ✅ Portfolio snapshots
- ✅ Position Greeks
- ✅ Position factor exposures
- ✅ Correlation calculations
- ❌ Market data cache (historical_prices) - **preserved**

**When to use:**
- After fixing seed data
- Before re-running batch processing
- When calculations are incorrect

---

### 2. Seed Portfolios (`seed_portfolios_railway.py`)

Seeds all 5 demo portfolios with corrected June 30, 2025 market data.

**Usage:**
```bash
railway run --service SigmaSight-BE python scripts/railway/seed_portfolios_railway.py
```

**What it does:**
1. Creates demo users (if they don't exist)
2. Seeds 5 portfolios with corrected position data:
   - Demo Individual Investor (16 positions)
   - Demo High Net Worth (39 positions)
   - Demo Hedge Fund Style (30 positions)
   - Demo Family Office Public Growth (12 positions)
   - Demo Family Office Private Opportunities (9 positions)

**Smart seeding:**
- Won't duplicate existing positions
- Only adds missing positions
- Updates equity_balance if changed

**When to use:**
- After updating seed_demo_portfolios.py
- When Railway database has empty portfolios
- To add missing positions

---

### 3. Run Batch Processing (`run_batch_railway.py`)

Runs batch processing for all portfolios to calculate P&L and analytics.

**Usage:**
```bash
railway run --service SigmaSight-BE python scripts/railway/run_batch_railway.py
```

**What it does:**
- **Phase 1**: Collects market data (1-year lookback)
- **Phase 2**: Calculates P&L and portfolio snapshots
- **Phase 2.5**: Updates position market values
- **Phase 3**: Calculates risk analytics (betas, factors, correlations)

**When to use:**
- After seeding portfolios
- After clearing calculations
- When P&L or analytics are incorrect

---

## Typical Workflow

### Problem: Empty portfolios or wrong data on Railway

```bash
# Step 1: Clear old calculations
railway run --service SigmaSight-BE python scripts/railway/clear_calculations_railway.py

# Step 2: Seed correct position data
railway run --service SigmaSight-BE python scripts/railway/seed_portfolios_railway.py

# Step 3: Run batch processing to calculate P&L and analytics
railway run --service SigmaSight-BE python scripts/railway/run_batch_railway.py
```

### Problem: Incorrect P&L calculations

```bash
# Step 1: Clear calculations
railway run --service SigmaSight-BE python scripts/railway/clear_calculations_railway.py

# Step 2: Re-run batch (skips seeding since positions are correct)
railway run --service SigmaSight-BE python scripts/railway/run_batch_railway.py
```

---

## Comparison with Local Scripts

| Script | Local Version | Railway Version |
|--------|---------------|-----------------|
| Clear Calculations | `scripts/database/clear_calculation_data.py` | `scripts/railway/clear_calculations_railway.py` |
| Seed Portfolios | `scripts/database/reset_and_seed.py` | `scripts/railway/seed_portfolios_railway.py` |
| Run Batch | `scripts/run_batch_calculations.py` | `scripts/railway/run_batch_railway.py` |

**Key Differences:**
- Local scripts work with local database (psycopg2)
- Railway scripts work on Railway server (asyncpg)
- Railway scripts are simpler (no reset/full wipe functionality)
- Railway scripts preserve market data cache

---

## Troubleshooting

### "The asyncio extension requires an async driver"

**Problem:** You're running a local script against Railway database.

**Solution:** Use the Railway-specific scripts in this directory instead.

### "No module named 'app'"

**Problem:** Script can't find the app module.

**Solution:** Ensure you're running from the correct service:
```bash
railway run --service SigmaSight-BE python scripts/railway/<script>.py
```

### "Portfolio already exists"

**Not an error!** The seeding script is smart - it won't duplicate data, only adds missing positions.

### Batch processing takes too long

**Expected behavior.** Batch processing can take 5-15 minutes depending on:
- Number of portfolios
- Market data availability
- API rate limits

Monitor progress in Railway logs:
```bash
railway logs --service SigmaSight-BE
```

---

## Important Notes

1. **Market Data Cache is Preserved**
   - Clearing calculations does NOT delete historical_prices
   - This saves API calls when re-running batch processing

2. **Idempotent Operations**
   - All scripts can be run multiple times safely
   - Seeding won't duplicate positions
   - Clearing removes all calculations (safe to re-clear)

3. **No Reset Functionality**
   - Railway scripts don't have "reset" mode (unlike local scripts)
   - Use separate clear + seed steps instead
   - This prevents accidental data loss

4. **Execution Location**
   - `railway run` executes **on Railway's servers**
   - Scripts use Railway's async drivers (asyncpg)
   - Database connection is local to Railway

---

## See Also

- **Backend CLAUDE.md**: Complete backend architecture reference
- **API_REFERENCE_V1.4.6.md**: API endpoint documentation
- **corrected_seed_data.txt**: Source of truth for position data
- **seed_demo_portfolios.py**: Main seeding logic
