# V2 Batch Architecture - Next Steps

## Overview

This document tracks future enhancements needed for the V2 batch architecture after the initial implementation is complete and stable.

---

## 1. Smart Company Profile Refresh (Priority: High)

### Problem

The current `_fetch_company_profiles()` function fetches ALL 53 fields for every symbol on every run. With 1250+ symbols in the universe, this is:
- Too slow (30+ minutes of API calls)
- Wasteful (most data doesn't change daily)
- Inefficient (same API cost whether data changed or not)

### Current State (V2 Initial Release)

Company profile sync is **skipped** in the V2 symbol batch to unblock the critical path (prices + factors). Profiles must be synced separately via manual trigger or existing mechanisms.

### Proposed Solution: Tiered Refresh Strategy

Split company profile data into tiers based on refresh frequency:

#### Tier 1: Daily Refresh
Fields that change with market close:
- `pe_ratio`, `forward_pe`
- `dividend_yield`
- `beta`
- `week_52_high`, `week_52_low`
- `market_cap`

**Implementation:** Fetch nightly as part of V2 symbol batch, but ONLY these fields.

#### Tier 2: Quarterly Refresh (Earnings-Driven)
Fields that change with earnings reports:
- `forward_eps`, `earnings_growth`, `revenue_growth`
- `earnings_quarterly_growth`
- `profit_margins`, `operating_margins`, `gross_margins`
- `return_on_assets`, `return_on_equity`
- `total_revenue`
- `current_year_*` estimates
- `next_year_*` estimates
- Analyst targets and recommendations

**Implementation:**
- Check `updated_at` timestamp
- Only refresh if:
  - Last update > 7 days ago, OR
  - Symbol had earnings in last 3 days (use earnings calendar)

#### Tier 3: Static/Rare Refresh
Fields that rarely change:
- `company_name`, `sector`, `industry`
- `exchange`, `country`
- `ceo`, `employees`, `website`
- `is_etf`, `is_fund`
- `description`

**Implementation:**
- Only fetch if record doesn't exist, OR
- Last update > 30 days ago, OR
- Manual trigger

### API Design

```python
async def refresh_company_profiles(
    symbols: List[str],
    tier: str = "daily",  # "daily", "quarterly", "static", "all"
    force: bool = False,  # Bypass age checks
) -> Dict[str, Any]:
    """
    Smart company profile refresh with tiered strategy.

    Args:
        symbols: Symbols to refresh
        tier: Which tier of data to refresh
        force: Force refresh even if data is fresh
    """
```

### Database Changes Needed

Add to `company_profiles` table:
- `daily_updated_at` - Last daily tier refresh
- `quarterly_updated_at` - Last quarterly tier refresh
- `static_updated_at` - Last static tier refresh

Or use a separate `company_profile_refresh_log` table to track per-symbol refresh history.

### Estimated Effort

- Design: 2-3 hours
- Implementation: 4-6 hours
- Testing: 2-3 hours

---

## 2. Symbol Universe Management (Priority: Medium)

### Problem

V2 currently processes ALL symbols from:
- Active positions (~63)
- Symbol universe table (~1200+)
- Factor ETFs (5)

This leads to 1250+ symbols, most of which may not be actively used.

### Proposed Solution

Add `priority` or `tier` to symbol_universe:
- **Tier 1 (Active):** Symbols in current positions - always process
- **Tier 2 (Watchlist):** User watchlist symbols - process daily
- **Tier 3 (Universe):** Full universe - process weekly or on-demand

### Benefits

- Faster nightly batch (only Tier 1+2)
- Full universe refresh can run on weekends
- Reduces API costs

---

## 3. Batch Progress Persistence (Priority: Low)

### Problem

If V2 batch crashes mid-run, there's no record of which symbols were processed.

### Proposed Solution

Add `symbol_batch_progress` table:
```sql
CREATE TABLE symbol_batch_progress (
    id UUID PRIMARY KEY,
    batch_run_id VARCHAR(50),
    symbol VARCHAR(20),
    calc_date DATE,
    phase VARCHAR(50),
    status VARCHAR(20),  -- pending, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

Benefits:
- Resume from where batch left off
- Per-symbol error tracking
- Better observability

---

## 4. Parallel Processing (Priority: Low)

### Current State

V2 processes symbols sequentially within each phase.

### Proposed Enhancement

Use asyncio.gather() or worker pools for:
- Phase 1: Parallel price fetches (with rate limiting)
- Phase 3: Parallel factor calculations

### Considerations

- API rate limits (YFinance, FMP)
- Database connection pool limits
- Memory usage with 1000+ concurrent tasks

---

## 5. New Company Profile Creation (Priority: High)

### Problem

When a new symbol is added to a portfolio (via position creation), the V2 daily valuation batch will skip it because no `company_profiles` record exists. The valuation batch only UPDATES existing profiles - it doesn't create new ones.

### Current State

- Daily valuation batch fetches PE, beta, 52w range, market cap for all symbols
- If a symbol has no existing profile, it's skipped (logged as "skipped - no profile")
- New symbols won't get valuation data until a profile is created

### Proposed Solution

Create a separate "New Profile Sync" step that runs:
1. **On portfolio onboarding** - When new positions are added
2. **Before daily valuation batch** - Check for symbols without profiles

```python
async def sync_missing_profiles(symbols: List[str]) -> Dict[str, Any]:
    """
    Create company_profiles for symbols that don't have one.

    Fetches static fields (sector, industry, company_name, etc.)
    only for symbols missing from company_profiles table.
    """
    # 1. Query DB for existing profile symbols
    # 2. Find symbols in input that don't have profiles
    # 3. Fetch full profile data for missing symbols only
    # 4. Insert new profiles
```

### Implementation Options

**Option A: Add to V2 Symbol Batch (Phase -1)**
- Run before Phase 0 daily valuations
- Only fetches profiles for symbols without existing records
- Pro: Automatic, no manual trigger needed
- Con: Adds time to nightly batch

**Option B: Separate Cron Job**
- Runs weekly or on-demand
- Syncs all missing profiles
- Pro: Doesn't slow down nightly batch
- Con: New symbols may wait up to a week for profiles

**Option C: On-Demand via Onboarding**
- Trigger profile sync when new positions are added
- Pro: Immediate data availability
- Con: Requires integration with position creation flow

### Recommended Approach

Start with **Option A** - add a quick "missing profiles" check to V2 batch. Since we're only fetching profiles for NEW symbols (not all 1250), it should be fast.

---

## 6. Fundamentals Collection (Priority: Medium)

### Problem

Phase 2 (fundamentals collection) is currently **skipped** in the V2 symbol batch because:
1. **Numeric overflow errors** - Income statement values for some symbols (e.g., ARWR) exceed column precision
2. **Slow execution** - Fetches full financial statements for all symbols
3. **Not critical for daily operations** - Earnings data changes quarterly, not daily

### What Phase 2 Collects

The fundamentals collector fetches and stores:
- **Income Statements** - Revenue, net income, EPS, margins (quarterly + annual)
- **Balance Sheets** - Assets, liabilities, shareholders equity
- **Cash Flow Statements** - Operating, investing, financing cash flows

These are stored in separate tables:
- `income_statements`
- `balance_sheets`
- `cash_flow_statements`

### Current State

Phase 2 is skipped in `symbol_batch_runner.py` with the message:
```
[V2_SYMBOL_BATCH] Phase 2: Fundamentals... SKIPPED (see NextSteps.md)
```

### Issues to Fix

1. **Numeric Overflow**
   - Error: `NumericValueOutOfRangeError` for income_statements
   - Cause: Column precision too small for large revenue numbers
   - Fix: Widen NUMERIC columns in migration (e.g., `NUMERIC(20,2)` → `NUMERIC(30,2)`)

2. **Performance**
   - Current: Fetches all symbols every run
   - Better: Only fetch symbols with recent earnings (earnings-driven approach exists but may need tuning)

3. **Quarterly Focus**
   - Fundamentals don't change daily - only after earnings reports
   - Should run weekly or after earnings, not nightly

### Proposed Solution

**Option A: Fix and Re-enable**
1. Create migration to widen numeric columns
2. Add better error handling for edge cases
3. Re-enable Phase 2 with earnings-driven logic

**Option B: Separate Cron Job**
1. Run fundamentals collection weekly (e.g., Sunday)
2. Trigger on-demand after earnings season
3. Remove from nightly symbol batch

### Estimated Effort

- Numeric column fix: 1-2 hours
- Performance tuning: 2-3 hours
- Testing: 2 hours

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-12 | Claude | Added fundamentals collection section (Phase 2 skipped) |
| 2026-01-12 | Claude | Added new company profile creation section |
| 2026-01-12 | Claude | Initial creation - Smart profile refresh planning |
