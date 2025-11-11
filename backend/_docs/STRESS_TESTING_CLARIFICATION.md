# Stress Testing System Clarification

**Date**: November 6, 2025
**Issue**: Confusion about stress scenario configuration

## How Stress Testing Actually Works

### ✅ CORRECT: JSON Config File

The stress testing system reads scenarios from:
```
backend/app/config/stress_scenarios.json
```

**This file contains 19 active scenarios**:
- **Base Cases** (4): Market Rally/Decline 5%, Rates Up/Down 50bp
- **Market Risk** (4): Market Rally/Decline 10%, Crash 35%, Rally 25%
- **Interest Rate Risk** (5): Rates ±25bp, ±50bp, ±100bp, Spike 300bp
- **Factor Rotations** (4): Value Rotation 20%, Growth Rally 15%, Small Cap 10%, Flight to Quality 12%
- **Volatility Risk** (2): VIX Spike 150%, Liquidity Crisis
- **Historical Replays** (3, inactive): 2008 Financial Crisis, COVID-19, Dot-com (marked as `"active": false`)

**Total Active**: 19 scenarios
**Total Inactive** (optional historical replays): 3 scenarios

### ❌ INCORRECT: Database StressTestScenario Table

During the previous session, I mistakenly created a seed script (`seed_stress_scenarios_safe.py`) that populated the `stress_test_scenarios` database table with 18 scenarios.

**Problem**: The stress testing code (`app/calculations/stress_testing.py`) does NOT read from this database table. It reads from the JSON file.

**Evidence**:
- Line 29 of `stress_testing.py`: `DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "stress_scenarios.json"`
- The `load_stress_scenarios()` function reads the JSON file, not the database

### What I Did Wrong

1. Created `seed_stress_scenarios_safe.py` with 18 "historical" scenarios (like "2008 Financial Crisis")
2. These scenarios used a different schema (`shock_config` with nested dicts)
3. Populated the database table that ISN'T used by stress testing
4. The JSON config file was already correct and didn't need changes

### Current Status

**JSON Config File**: ✅ Correct, has 19 active scenarios matching best practices
**Database Table**: ⚠️ Populated with 18 incorrect scenarios (not used, can be ignored or deleted)
**Stress Testing Code**: ✅ Working correctly, reads from JSON file

## Resolution

**No action needed** - the stress testing system is configured correctly via the JSON file.

If you want to clean up the incorrect database scenarios:
```python
# Optional cleanup script
from app.database import AsyncSessionLocal
from app.models.market_data import StressTestScenario
from sqlalchemy import select

async def cleanup():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(StressTestScenario))
        scenarios = result.scalars().all()
        for s in scenarios:
            await db.delete(s)
        await db.commit()
        print(f"Deleted {len(scenarios)} unused stress test scenarios from database")
```

## Stress Testing Error Investigation

If you're getting errors in stress testing, it's NOT because of scenario configuration (the JSON is correct).

**Possible causes**:
1. **Missing factor exposures** - Stress testing requires portfolio-level factor exposures in the `factor_exposures` table
2. **Missing Market Beta** - Market Beta must be saved as a factor exposure (see `market_beta.py` lines 399-450)
3. **Calculation date mismatch** - Factor exposures must exist for the calculation date being stress-tested

**To diagnose**, check what error message you're seeing during stress testing.
