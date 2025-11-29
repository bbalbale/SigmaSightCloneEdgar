# P&L CALCULATION AUDIT - Complete System Analysis
**Date**: November 3, 2025
**Purpose**: Document where P&L fields are calculated and identify discrepancies

---

## Executive Summary

**The Problem**: Equity balance calculations are fundamentally broken across 3 demo portfolios. Individual Investor portfolio shows incorrect values:
- **Position Entry Values**: $484,860
- **Position Market Values**: $465,225
- **Position.unrealized_pnl (stored)**: +$84,966 ❌ **WRONG**
- **Correct unrealized P&L**: -$19,635 ✅
- **Expected Equity**: $484,860 + (-$19,635) = $465,225
- **Actual Equity (shown)**: $485,000 ❌ **STUCK AT INITIAL VALUE**

**Root Cause**: Multiple calculation locations using different formulas, and missing integration between:
1. Position market value updates (Phase 2.5)
2. Position unrealized P&L updates (NOT HAPPENING in Phase 2.5!)
3. Daily P&L calculation (pnl_calculator.py)
4. Equity rollforward (pnl_calculator.py)

---

## Part 1: Database Field Definitions

### Position Model Fields
```python
class Position:
    quantity: Decimal          # Signed quantity (negative for shorts)
    entry_price: Decimal       # Price paid when entering position
    entry_date: date           # Date position was opened
    last_price: Decimal        # Most recent market price
    market_value: Decimal      # Current market value (quantity × last_price × multiplier)
    unrealized_pnl: Decimal    # Cumulative P&L without sale: (last_price - entry_price) × quantity × multiplier
    realized_pnl: Decimal      # P&L locked in from sales (NOT IMPLEMENTED YET)
```

### Portfolio Model Fields
```python
class Portfolio:
    equity_balance: Decimal    # STATIC initial capital (never changes from user input)
```

### PortfolioSnapshot Model Fields
```python
class PortfolioSnapshot:
    snapshot_date: date
    equity_balance: Decimal    # ROLLING balance (changes daily with P&L)
    daily_pnl: Decimal         # Daily change in portfolio value
    cumulative_pnl: Decimal    # Total P&L since inception
    daily_return: Decimal      # daily_pnl / previous_equity
    long_value: Decimal        # Sum of long position market values
    short_value: Decimal       # Sum of short position market values (negative)
```

---

## Part 2: CORRECT Calculation Formulas

### 2.1 Position-Level Calculations (CUMULATIVE)

**Position.market_value** (signed):
```python
multiplier = 100 if is_options_position(position) else 1
market_value = quantity × last_price × multiplier

# Examples:
# - LONG 100 AAPL @ $150: 100 × 150 × 1 = $15,000
# - SHORT 100 AAPL @ $150: -100 × 150 × 1 = -$15,000
# - LONG 10 call contracts @ $5: 10 × 5 × 100 = $5,000
```

**Position.unrealized_pnl** (cumulative, since entry):
```python
cost_basis = quantity × entry_price × multiplier
unrealized_pnl = market_value - cost_basis

# Examples:
# - Bought 100 AAPL @ $140, now $150:
#   cost_basis = 100 × 140 = $14,000
#   market_value = 100 × 150 = $15,000
#   unrealized_pnl = $15,000 - $14,000 = +$1,000 ✅
#
# - Shorted 100 AAPL @ $140, now $150:
#   cost_basis = -100 × 140 = -$14,000
#   market_value = -100 × 150 = -$15,000
#   unrealized_pnl = -$15,000 - (-$14,000) = -$1,000 ✅ (loss on short)
```

**Position.realized_pnl** (cumulative, from sales):
```python
# NOT YET IMPLEMENTED - future enhancement
# When position sold:
realized_pnl = (sale_price - entry_price) × sold_quantity × multiplier
```

### 2.2 Daily P&L Calculation (for Snapshots)

**Daily P&L** (change from yesterday):
```python
# Step 1: Get yesterday's market value from market_data_cache
previous_price = get_cached_price(symbol, previous_trading_day)

# Step 2: Calculate yesterday's value
previous_value = quantity × previous_price × multiplier

# Step 3: Calculate today's value
current_value = quantity × current_price × multiplier

# Step 4: Daily P&L is the change
daily_pnl = current_value - previous_value

# CRITICAL: On Day 1 (no previous price):
# previous_price should equal current_price → daily_pnl = $0
# BUT equity should start at entry_cost value, NOT static Portfolio.equity_balance!
```

**Portfolio Daily P&L**:
```python
portfolio_daily_pnl = sum(position.daily_pnl for all positions)
```

### 2.3 Equity Rollforward

**Equity Balance** (capital account):
```python
# Day 0 (initial):
equity_balance = sum(position.quantity × position.entry_price × multiplier)
# This is the total capital deployed at entry, NOT Portfolio.equity_balance!

# Day N (subsequent days):
new_equity = previous_snapshot.equity_balance + portfolio_daily_pnl

# Example for Individual Investor:
# Day 0: equity = $484,860 (sum of entry costs)
# Day 1: prices change, daily_pnl = -$19,635
# Day 1: equity = $484,860 + (-$19,635) = $465,225 ✅
```

### 2.4 Cash Calculation

**Cash/Margin**:
```python
equity_balance = [from snapshot or sum of entry costs]
total_market_value = sum(position.market_value for all positions)

cash_or_margin = equity_balance - total_market_value

# Positive = Cash (buying power)
# Negative = Margin (leverage)
# Zero = Fully invested (100% invested, no leverage)

# Example for Individual Investor (100% invested):
# equity_balance = $465,225
# total_market_value = $465,225
# cash = $465,225 - $465,225 = $0 ✅
```

---

## Part 3: CURRENT STATE - Where Fields Are Set

### 3.1 Position.unrealized_pnl

**✅ CORRECT LOCATIONS**:

1. **app/calculations/market_data.py:489** (update_position_market_values)
   ```python
   market_value_data = await calculate_position_market_value(position, current_price)
   position.unrealized_pnl = market_value_data["unrealized_pnl"]
   # where unrealized_pnl = exposure - cost_basis (CORRECT ✅)
   ```
   **Used by**: Position update workflows

2. **scripts/data_operations/sync_position_prices.py:57**
   ```python
   new_unrealized_pnl = (new_price - position.entry_price) * position.quantity
   position.unrealized_pnl = new_unrealized_pnl
   ```
   **Status**: CORRECT ✅ (but missing multiplier for options)

3. **scripts/analysis/update_position_prices.py:18**
   ```python
   if pos.entry_price and pos.entry_price > 0:
       pos.unrealized_pnl = (pos.last_price - pos.entry_price) * pos.quantity
   ```
   **Status**: CORRECT ✅ (but missing multiplier for options)

**❌ MISSING LOCATION (THE BUG!)**:

4. **app/batch/batch_orchestrator_v3.py:380-381** (Phase 2.5)
   ```python
   position.last_price = current_price
   position.market_value = market_value
   # ❌ DOES NOT UPDATE position.unrealized_pnl!
   ```
   **Status**: ❌ **CRITICAL BUG** - Phase 2.5 updates market_value but NOT unrealized_pnl!

**📊 CALCULATED ON-THE-FLY (not stored)**:

5. **app/api/v1/data.py:668-672** (positions API endpoint)
   ```python
   if position.position_type.value == "SHORT":
       unrealized_pnl = cost_basis - abs(market_value)
   else:
       unrealized_pnl = market_value - cost_basis
   ```
   **Status**: CORRECT ✅ (calculated for API response, not stored in database)

### 3.2 Position.market_value

**✅ CORRECT LOCATIONS**:

1. **app/batch/batch_orchestrator_v3.py:377-381** (Phase 2.5)
   ```python
   multiplier = Decimal('100') if position.position_type.name in ['CALL', 'PUT', 'LC', 'LP', 'SC', 'SP'] else Decimal('1')
   market_value = position.quantity * current_price * multiplier
   position.last_price = current_price
   position.market_value = market_value
   ```
   **Status**: CORRECT ✅ (but missing unrealized_pnl update!)

2. **app/calculations/market_data.py:488** (update_position_market_values)
   ```python
   market_value_data = await calculate_position_market_value(position, current_price)
   position.market_value = market_value_data["market_value"]
   ```
   **Status**: CORRECT ✅

3. **scripts/data_operations/sync_position_prices.py:56**
   ```python
   new_market_value = position.quantity * new_price
   position.market_value = new_market_value
   ```
   **Status**: ⚠️ MISSING multiplier for options (should be × 100 for options)

4. **scripts/analysis/update_position_prices.py:16**
   ```python
   pos.market_value = pos.quantity * pos.last_price
   ```
   **Status**: ⚠️ MISSING multiplier for options

### 3.3 Position.realized_pnl

**Status**: ❌ **NOT IMPLEMENTED**
- Field exists in database schema
- Seeded with $0 in demo data
- NOT updated anywhere in codebase
- Future enhancement for buy/sell transactions

---

## Part 4: DISCREPANCIES & BUGS

### Bug #1: Phase 2.5 Does Not Update unrealized_pnl ❌ **CRITICAL**

**Location**: `app/batch/batch_orchestrator_v3.py:380-381`

**What it does**:
```python
position.last_price = current_price
position.market_value = market_value
# ❌ MISSING: position.unrealized_pnl update!
```

**What it SHOULD do**:
```python
position.last_price = current_price
position.market_value = market_value

# Calculate unrealized P&L
cost_basis = position.quantity * position.entry_price * multiplier
position.unrealized_pnl = market_value - cost_basis
```

**Impact**: Position.unrealized_pnl fields contain stale data, causing incorrect P&L reporting.

---

### Bug #2: pnl_calculator.py Day 1 Logic is Wrong ❌ **CRITICAL**

**Location**: `app/batch/pnl_calculator.py:314-319`

**Current code**:
```python
# CRITICAL FIX (2025-11-03): If no previous price, use current price (no change on Day 1)
if not previous_price:
    previous_price = current_price
    logger.debug(f"      {position.symbol}: No previous price, using current (P&L=0)")
```

**Problem**:
- On Day 1, daily P&L = $0 ✅ (correct)
- BUT equity starts at Portfolio.equity_balance ($485,000) ❌ (wrong!)
- SHOULD start at sum of entry costs ($484,860) ✅

**Original buggy code** (even worse):
```python
# If no previous price, use entry price
if not previous_price:
    previous_price = position.entry_price  # ❌ WRONG!
```

**This calculated**:
```python
daily_pnl = (current_price - entry_price) × quantity
# This gives CUMULATIVE P&L on Day 1, not daily P&L!
# Inflated equity by $85,602 on Day 1
```

**What it SHOULD do**:
```python
# On Day 1 (no previous snapshot):
# - Daily P&L = $0 (no price change to compare)
# - Equity should be initialized to sum of entry costs, NOT Portfolio.equity_balance!

# In calculate_portfolio_pnl():
if previous_snapshot is None:
    # Day 1 initialization
    # Calculate initial equity from position entry costs
    initial_equity = sum(
        position.quantity × position.entry_price × multiplier
        for all positions
    )
    daily_pnl = Decimal('0')  # No change on Day 1
    new_equity = initial_equity  # Start at entry cost
else:
    # Day N (subsequent days)
    previous_equity = previous_snapshot.equity_balance
    daily_pnl = [calculate from price changes]
    new_equity = previous_equity + daily_pnl
```

---

### Bug #3: Portfolio.equity_balance vs PortfolioSnapshot.equity_balance Confusion ❌

**The Issue**:
- `Portfolio.equity_balance` = STATIC initial capital (never changes)
- `PortfolioSnapshot.equity_balance` = ROLLING balance (changes daily)

**Current Problem**:
- `pnl_calculator.py:167` uses `Portfolio.equity_balance` as fallback
- This is the WRONG fallback - it's static initial capital, not actual entry cost

**Example**:
```
Portfolio.equity_balance = $485,000 (user input, static)
Sum of position entry costs = $484,860 (actual capital deployed)
Difference = $140 (this is cash, not invested!)
```

**Fix**: On Day 1, equity should initialize to sum of entry costs, NOT Portfolio.equity_balance

---

### Bug #4: Snapshot.long_value vs Equity Relationship ⚠️

**Current Behavior**:
- Snapshot stores `long_value` (sum of long position market values)
- Equity rollforward uses previous equity + daily P&L

**Issue**: These can diverge because:
- `long_value` = market value snapshot
- `equity` = capital account (entry cost + accumulated P&L)
- For 100% invested portfolio: equity ≈ long_value (but they measure different things!)

**Example**:
```
Entry costs: $484,860
Market value: $465,225
P&L: -$19,635

Snapshot.long_value = $465,225 ✅ (market value)
Snapshot.equity_balance = $484,860 + (-$19,635) = $465,225 ✅ (capital account)
Cash = $465,225 - $465,225 = $0 ✅ (100% invested)
```

---

## Part 5: THE FIX - Step-by-Step Plan

### Phase 1: Fix Position Field Updates (High Priority)

**1.1 Update Phase 2.5 to set unrealized_pnl**

**File**: `app/batch/batch_orchestrator_v3.py:380-381`

**Change**:
```python
# Before:
position.last_price = current_price
position.market_value = market_value

# After:
position.last_price = current_price
position.market_value = market_value

# Calculate unrealized P&L (cumulative since entry)
cost_basis = position.quantity * position.entry_price * multiplier
position.unrealized_pnl = market_value - cost_basis
```

**1.2 Add multiplier to sync scripts**

**Files**:
- `scripts/data_operations/sync_position_prices.py:56-57`
- `scripts/analysis/update_position_prices.py:16-18`

**Change**: Add multiplier logic for options (100x)

---

### Phase 2: Fix Equity Rollforward (Critical)

**2.1 Fix Day 1 Initialization**

**File**: `app/batch/pnl_calculator.py:calculate_portfolio_pnl()`

**Change**: Around lines 162-185
```python
# Get most recent snapshot
previous_snapshot = None
previous_equity = None

prev_query = select(PortfolioSnapshot).where(
    and_(
        PortfolioSnapshot.portfolio_id == portfolio_id,
        PortfolioSnapshot.snapshot_date < calculation_date
    )
).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

prev_result = await db.execute(prev_query)
previous_snapshot = prev_result.scalar_one_or_none()

if previous_snapshot:
    # Day N: Use previous snapshot equity
    previous_equity = previous_snapshot.equity_balance
    logger.debug(f"    Previous equity ({previous_snapshot.snapshot_date}): ${previous_equity:,.2f}")
else:
    # Day 1: Calculate initial equity from position entry costs
    positions_query = select(Position).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.entry_date <= calculation_date,
            Position.deleted_at.is_(None)
        )
    )
    positions_result = await db.execute(positions_query)
    positions = positions_result.scalars().all()

    # Sum up entry costs (actual capital deployed)
    previous_equity = Decimal('0')
    for pos in positions:
        multiplier = Decimal('100') if pos.position_type.name in ['CALL', 'PUT', 'LC', 'LP', 'SC', 'SP'] else Decimal('1')
        entry_cost = pos.quantity * pos.entry_price * multiplier
        previous_equity += entry_cost

    logger.info(f"    Day 1 initialization: equity = ${previous_equity:,.2f} (sum of entry costs)")
```

**2.2 Fix Day 1 P&L Calculation**

**File**: `app/batch/pnl_calculator.py:_calculate_position_pnl()`

**Change**: Around lines 314-319
```python
# Previous price lookup with proper Day 1 handling
if previous_date:
    previous_price = await self._get_cached_price(db, position.symbol, previous_date)

if not previous_price:
    # Day 1 or missing data: use current price for zero change
    previous_price = current_price
    logger.debug(f"      {position.symbol}: No previous price, using current (P&L=0)")
```

**Status**: This part is already correct ✅

---

### Phase 3: Add Cash/Margin Display (Enhancement)

**3.1 Calculate Cash/Margin**

**File**: Create new function in `app/calculations/portfolio.py`

```python
def calculate_cash_margin(
    equity_balance: Decimal,
    total_market_value: Decimal
) -> Dict[str, Decimal]:
    """
    Calculate cash or margin from equity and market value

    Cash/Margin = Equity - Market Value
    - Positive = Cash (buying power)
    - Negative = Margin (leverage)
    - Zero = Fully invested
    """
    cash_margin = equity_balance - total_market_value

    return {
        "equity_balance": equity_balance,
        "total_market_value": total_market_value,
        "cash_margin": cash_margin,
        "is_cash": cash_margin > 0,
        "is_margin": cash_margin < 0,
        "is_fully_invested": abs(cash_margin) < Decimal('0.01'),  # Within $0.01
        "leverage_ratio": abs(total_market_value / equity_balance) if equity_balance > 0 else Decimal('0')
    }
```

**3.2 Add to Portfolio Overview API**

**File**: `app/services/portfolio_analytics_service.py`

Add cash_margin field to overview response

---

### Phase 4: Implement Realized P&L (Future Enhancement)

**When to implement**: After buy/sell transaction system is integrated

**Requirements**:
1. Track Position.realized_pnl on sales
2. Separate unrealized vs realized P&L in snapshots
3. Update equity rollforward to include realized P&L

**Formula**:
```python
# On position sale:
sale_proceeds = sale_quantity × sale_price × multiplier
cost_basis_sold = sale_quantity × entry_price × multiplier
realized_pnl_on_sale = sale_proceeds - cost_basis_sold

# Accumulate:
position.realized_pnl += realized_pnl_on_sale

# Adjust unrealized:
position.quantity -= sale_quantity  # Reduce quantity
# unrealized_pnl will recalculate based on remaining quantity
```

---

## Part 6: Verification Steps

### 6.1 After Phase 1 Fix (Position Fields)

**Run**:
```bash
python scripts/analysis/reset_all_portfolios.py  # Reset to clean state
python scripts/analysis/run_batch_now.py         # Run batch with fixes
python scripts/analysis/check_actual_position_pnl.py  # Verify position P&L
```

**Expected**:
```
Position.unrealized_pnl totals should match:
  AAPL: (150 - 140) × 100 × 1 = +$1,000
  Individual Portfolio Total: -$19,635 ✅
```

### 6.2 After Phase 2 Fix (Equity Rollforward)

**Run**:
```bash
python scripts/analysis/check_snapshot_equity_history.py
```

**Expected**:
```
Day 1 (2024-09-03):
  Equity Balance: $484,860 (sum of entry costs, not $485,000!)
  Daily P&L: $0
  Cumulative P&L: $0

Day N (2024-10-29):
  Equity Balance: $465,225 (after accumulated P&L)
  Daily P&L: [varies]
  Cumulative P&L: -$19,635
```

### 6.3 After Phase 3 (Cash/Margin)

**Check API**:
```bash
GET /api/v1/analytics/portfolio/{id}/overview
```

**Expected**:
```json
{
  "equity_balance": 465225.45,
  "total_market_value": 465225.45,
  "cash_margin": 0.00,
  "is_fully_invested": true
}
```

---

## Part 7: Manual Calculation Walkthrough

### Individual Investor Portfolio - Expected Values

**Entry Costs** (Day 0):
```
Sum of (quantity × entry_price × multiplier) = $484,860
```

**Current Market Values** (Day N):
```
Sum of (quantity × last_price × multiplier) = $465,225
```

**Unrealized P&L** (Cumulative):
```
$465,225 - $484,860 = -$19,635 ✅
```

**Equity Balance** (Day N):
```
Initial Equity + Cumulative P&L
= $484,860 + (-$19,635)
= $465,225 ✅
```

**Cash/Margin**:
```
Equity - Market Value
= $465,225 - $465,225
= $0 ✅ (100% invested, no leverage)
```

**Daily P&L** (Day N vs Day N-1):
```
Change in market value from yesterday
= Sum of [(today_price - yesterday_price) × quantity × multiplier]
= [varies by day]
```

---

## Conclusion

**Root Cause**: Three systemic issues:
1. ❌ Phase 2.5 updates `market_value` but NOT `unrealized_pnl`
2. ❌ Day 1 equity initialization uses static `Portfolio.equity_balance` instead of sum of entry costs
3. ❌ Missing cash/margin visibility

**Fix Complexity**: Medium
- Phase 1: Single line addition to Phase 2.5 ✅
- Phase 2: Refactor Day 1 initialization logic (~30 lines) ⚠️
- Phase 3: Add cash/margin calculation (new function) ✅

**Testing**: All 3 demo portfolios after each phase

**Timeline**:
- Phase 1: 30 minutes
- Phase 2: 1-2 hours (careful testing needed)
- Phase 3: 30 minutes
- **Total**: ~3 hours to fix completely

---

**END OF AUDIT**
