# ⚠️ DESTRUCTIVE SCRIPTS - EXTREME CAUTION REQUIRED

## 🔴 WARNING: ALL SCRIPTS IN THIS DIRECTORY WILL DELETE DATA!

**These scripts will PERMANENTLY DELETE portfolio, position, and market data from the database.**

Do NOT run these scripts unless you:
1. ✅ Want to completely reset your database
2. ✅ Have backed up any data you want to keep
3. ✅ Understand all data will be lost
4. ✅ Are in a development/test environment

---

## 🚨 Scripts in This Directory

### `DANGEROUS_reseed_july_2025_complete.py`
**What it does:**
- Deletes ALL portfolio, position, market data, and agent data
- Reseeds 3 demo portfolios with July 1, 2025 entry dates
- Runs historical batch processing for July 1 - October 28, 2025
- Takes 60-100 minutes to complete

**Safety:**
- ✅ Requires two confirmations
- ✅ Interactive prompt: "yes/no"
- ✅ Text confirmation: "DELETE ALL MY DATA"

**When to use:**
- Recreating historical data from July onwards
- Testing historical batch processing
- Fresh start with specific entry dates

---

### `DANGEROUS_reseed_with_v3_backfill.py`
**What it does:**
- Truncates ALL portfolio, position, and market data tables
- Reseeds 3 demo portfolios with July 1, 2025 entry dates
- Runs V3 batch orchestrator with automatic backfill
- Takes 30-40 minutes to complete

**Safety:**
- ✅ Requires two confirmations
- ✅ Interactive prompt: "yes/no"
- ✅ Text confirmation: "DELETE ALL MY DATA"

**When to use:**
- Faster historical data recreation using V3
- Testing V3 batch orchestrator backfill
- Fresh start with automatic date detection

**Note:** This version PRESERVES market_data_cache (commented out on line 71)

---

### `DANGEROUS_railway_reset_database.py`
**What it does:**
- Automatically calls `reset_and_seed.py reset --confirm`
- Drops ALL database tables completely
- Recreates schema from scratch
- Reseeds demo data
- Bypasses normal safety prompts (auto-confirms)

**Safety:**
- ⚠️ Originally had NO confirmation (hence "DANGEROUS")
- ✅ Now requires interactive confirmation at script level

**When to use:**
- Railway deployment resets only
- NEVER on production
- NEVER when you want to preserve data

---

## ✅ Safe Alternative: Daily Batch Processing

**For daily operations, use this SAFE script instead:**
```bash
# This is SAFE - only updates calculations, doesn't delete data
python scripts/batch_processing/run_batch.py
```

This script:
- ✅ Fetches latest market data
- ✅ Updates position prices
- ✅ Calculates analytics and risk metrics
- ✅ Creates snapshots
- ❌ Does NOT delete any existing data

---

## 🛡️ Safety Features (All Scripts Now Have)

1. **Double Confirmation Required:**
   - First: "yes/no" prompt
   - Second: Must type "DELETE ALL MY DATA" exactly

2. **Clear Warnings:**
   - Scripts print what will be deleted
   - Estimated time displayed
   - Can be cancelled at any prompt

3. **DANGEROUS Prefix:**
   - All scripts named with DANGEROUS_ prefix
   - Isolated in this separate directory
   - Obvious warning when listing files

---

## 📋 Recommended Workflow

### If You Must Reset Database:

1. **Backup First (if needed):**
   ```bash
   docker exec backend-postgres-1 pg_dump -U sigmasight sigmasight_db > backup_$(date +%Y%m%d).sql
   ```

2. **Choose Appropriate Script:**
   - Need historical data? → `DANGEROUS_reseed_with_v3_backfill.py`
   - Testing V2 loop? → `DANGEROUS_reseed_july_2025_complete.py`
   - Railway reset? → `DANGEROUS_railway_reset_database.py`

3. **Run Script:**
   ```bash
   cd backend
   python scripts/DANGEROUS_DESTRUCTIVE_SCRIPTS/DANGEROUS_reseed_with_v3_backfill.py
   ```

4. **Follow Prompts:**
   - First prompt: Type "yes"
   - Second prompt: Type exactly "DELETE ALL MY DATA"

5. **Wait for Completion:**
   - V3 backfill: ~30-40 minutes
   - V2 loop: ~60-100 minutes

---

## 🚫 When NOT to Use These Scripts

- ❌ For daily operations (use `batch_processing/run_batch.py`)
- ❌ When you want to preserve existing data
- ❌ In production environments
- ❌ When you haven't backed up important data
- ❌ When unsure - ask first!

---

## 🔄 Alternative: Safe Seeding

If you just want to ADD demo data without deleting:

```bash
# SAFE - Only adds data, doesn't delete
python scripts/database/reset_and_seed.py seed
```

This will:
- ✅ Add demo portfolios if they don't exist
- ✅ Preserve existing data
- ❌ Won't delete anything

---

## ❓ Questions?

**Confused about which script to use?**
- For daily operations: `batch_processing/run_batch.py` ✅
- For fresh local dev setup: `database/reset_and_seed.py reset --confirm`
- For production: NEVER run these scripts

**Need to preserve data but update calculations?**
- Use: `batch_processing/run_batch.py` ✅

**Accidentally ran a dangerous script?**
- If data is gone, restore from backup
- Consider implementing automated daily backups going forward

---

**Last Updated:** 2025-11-01
**Maintainer:** SigmaSight Team

**Remember:** These scripts exist for specific testing and development scenarios. 99% of the time, you should be using `batch_processing/run_batch.py` for daily operations.
