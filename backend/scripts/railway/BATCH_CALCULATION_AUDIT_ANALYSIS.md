# Batch Calculation Audit - Gap Analysis

**Date:** 2025-10-06
**Purpose:** Identify calculation results tables NOT covered by existing audit scripts

---

## Batch Orchestration Overview

The batch orchestrator runs **8 calculation engines** sequentially per portfolio:

1. **market_data_update** - Syncs market prices (252 days for factor analysis)
2. **position_values_update** - Updates Position.last_price, Position.market_value
3. **portfolio_aggregation** - Calculates portfolio-level exposures (not stored, just computed)
4. **greeks_calculation** - Options Greeks (DISABLED - no options feed)
5. **factor_analysis** - 7-factor exposure analysis
6. **market_risk_scenarios** - Market beta and risk scenarios
7. **stress_testing** - Comprehensive stress tests
8. **portfolio_snapshot** - Daily portfolio snapshot
9. **position_correlations** - Position correlation matrix

---

## Database Tables Populated by Batch Jobs

### ✅ Already Audited by Existing Scripts

| Table | Populated By | Audited By |
|-------|-------------|------------|
| `market_data_cache` | market_data_update | audit_railway_market_data.py |
| `company_profiles` | market_data_update | Both scripts |
| `positions` (last_price, market_value) | position_values_update | audit_railway_data.py |

---

## ❌ NOT Audited - Calculation Results Tables

### 1. Greeks Calculations
**Table:** `position_greeks`
**Populated by:** _calculate_greeks() job
**Fields:**
- delta, gamma, theta, vega, rho
- implied_volatility
- calculation_date
- underlying_price

**Status:** DISABLED (no options feed), but table exists

---

### 2. Factor Exposure Analysis
**Table:** `position_factor_exposure`
**Populated by:** _calculate_factors() job (calculate_factor_betas_hybrid)
**Fields:**
- market_beta, value_beta, growth_beta
- momentum_beta, quality_beta, size_beta, low_vol_beta
- r_squared, residual_volatility
- calculation_date

**Critical:** Needs 252 days of historical data for factor regression

---

### 3. Interest Rate Beta
**Table:** `position_interest_rate_beta`
**Populated by:** _calculate_market_risk() job
**Fields:**
- ir_beta (interest rate sensitivity)
- calculation_date

---

### 4. Stress Test Results
**Table:** `stress_test_results`
**Populated by:** _run_stress_tests() job
**Fields:**
- portfolio_id, scenario_id
- direct_pnl, correlated_pnl, correlation_effect
- factor_impacts (JSONB), calculation_metadata (JSONB)
- calculation_date

**Status:** ✅ Table EXISTS (created via migration b56aa92cde75 in Aug 2025)

---

### 5. Portfolio Snapshots
**Table:** `portfolio_snapshots`
**Populated by:** _create_snapshot() job
**Fields:**
- total_value, total_market_value, equity_balance
- total_long, total_short, net_exposure
- long_count, short_count, option_count
- net_delta, total_gamma, total_theta, total_vega
- snapshot_date

**Critical:** Only created on TRADING DAYS (skips weekends)

---

### 6. Correlation Analysis
**Tables:**
- `correlation_calculations` (summary)
- `pairwise_correlations` (individual pairs)
- `correlation_clusters` (groupings)
- `correlation_cluster_positions` (position→cluster mapping)

**Populated by:** _calculate_correlations() job (CorrelationService)
**Fields:**
- correlation_calculations: avg_correlation, top_correlations (JSONB)
- pairwise_correlations: symbol1, symbol2, correlation_coefficient, p_value
- correlation_clusters: cluster analysis metadata

---

### 7. Factor Correlation Matrix
**Table:** `factor_correlations`
**Populated by:** Factor analysis calculations
**Fields:**
- factor_1, factor_2, correlation
- calculation_date

---

### 8. Market Risk Scenarios
**Table:** `market_risk_scenarios`
**Populated by:** Scenario definitions (not batch job, but referenced)
**Fields:**
- scenario_name, scenario_type
- market_shock, volatility_shock
- parameters (JSONB)

---

## Batch Execution Metadata (Not Audited)

### 9. Batch Job Tracking
**Table:** `batch_jobs`
**Fields:**
- job_name, job_type, portfolio_id
- status, error_message
- started_at, completed_at, duration_seconds

**Purpose:** Track batch execution history and failures

---

### 10. Batch Job Schedules
**Table:** `batch_job_schedules`
**Fields:**
- schedule_name, cron_expression, enabled
- last_run, next_run

**Purpose:** Track scheduled batch runs (via APScheduler)

---

## Recommended Audit Script

### New Script: `audit_railway_calculations.py`

**Purpose:** Audit all calculation results tables populated by batch orchestration

**Sections:**

1. **Greeks Coverage** (if table has data)
   - Positions with Greeks vs without
   - Latest calculation dates
   - Data completeness

2. **Factor Exposures** ⭐ CRITICAL
   - Positions with factor betas
   - 7-factor model coverage
   - R-squared quality metrics
   - Missing factor exposures

3. **Portfolio Snapshots** ⭐ CRITICAL
   - Snapshot history (count by portfolio)
   - Date range coverage
   - Trading days vs calendar days
   - Latest snapshot metrics

4. **Correlations** ⭐ CRITICAL
   - Portfolio correlation matrices
   - Pairwise correlation count
   - Cluster analysis results
   - Missing correlation pairs

5. **Stress Tests**
   - Results count (if table exists)
   - Scenario coverage
   - Latest test dates

6. **Interest Rate Betas**
   - Positions with IR beta
   - Latest calculation dates

7. **Batch Execution Metadata**
   - Recent batch runs
   - Success/failure rates
   - Common error patterns

---

## Data Quality Indicators

### Green (Good Coverage)
- ✅ Market data: 100% coverage, 124 trading days
- ✅ Position prices: 100% current prices
- ✅ Company profiles: Well... 0% but that's expected

### Red (Missing)
- ❌ Greeks: 0% (disabled, no options feed)
- ❌ Factor exposures: Unknown (NOT AUDITED)
- ❌ Snapshots: Unknown (NOT AUDITED)
- ❌ Correlations: Unknown (NOT AUDITED)
- ❌ Stress tests: 0% (table missing)

---

## Priority for New Audit

**HIGH PRIORITY:**
1. Portfolio Snapshots - Critical for P&L tracking
2. Factor Exposures - Core risk analytics
3. Correlations - Portfolio diversification metrics

**MEDIUM PRIORITY:**
4. Interest Rate Betas - Interest rate risk
5. Batch Job Tracking - Operational health

**LOW PRIORITY:**
6. Greeks - Disabled, no options feed
7. Stress Tests - Table exists but empty (batch hasn't run)

---

## Expected Results on Railway

Based on current audit results showing 0% Greeks/Factors:

**Likely findings:**
- Portfolio snapshots: **Probably 0%** (batch not run on Railway yet)
- Factor exposures: **0%** (confirmed by existing audit)
- Correlations: **Probably 0%** (batch not run on Railway yet)
- Batch jobs: **Probably empty** (no batch execution history)

**This audit will confirm** whether batch calculations have EVER been run on Railway production database, or if only seed data + market data sync has occurred.
