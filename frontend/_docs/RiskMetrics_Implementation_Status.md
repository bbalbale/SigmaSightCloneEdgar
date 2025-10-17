# Risk Metrics Implementation Status

**Branch:** `RiskMetricsLocal`
**Last Updated:** 2025-10-17 (Session 1)
**Status:** Phase 0 Database Schema Complete - Calculation Scripts In Progress

---

## Progress Summary

### ✅ Phase 0: Market Beta Single-Factor Model (30% Complete)

**Completed:**
- ✅ **Migration 0:** `position_market_betas` table created
  - Full OLS regression statistics (beta, alpha, r², std_error, p_value)
  - Historical tracking via `calc_date`
  - 3 performance indexes
  - File: `backend/alembic/versions/a1b2c3d4e5f6_create_position_market_betas.py`

- ✅ **Migration 1:** Portfolio snapshots beta columns added
  - `market_beta_weighted`, `market_beta_r_squared`, `market_beta_observations`, `market_beta_direct`
  - Performance index added
  - File: `backend/alembic/versions/b2c3d4e5f6g7_add_market_beta_to_snapshots.py`

- ✅ **PositionMarketBeta Model:** SQLAlchemy model created
  - Added to `backend/app/models/market_data.py`
  - Relationships configured in Portfolio and Position models

**In Progress:**
- 🔄 **market_beta.py calculation script** - Not started yet
- 🔄 **Constants update** - Need to add REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
- 🔄 **Batch orchestrator integration** - Need to add market beta calculation step
- 🔄 **Migration execution** - Migrations created but not yet applied to database
- 🔄 **Testing & validation** - Cannot test until calculation scripts are complete

**Remaining Tasks:**
1. Create `backend/app/calculations/market_beta.py` with:
   - `fetch_returns_for_beta()` - Fetch price data and calculate returns
   - `calculate_position_market_beta()` - Single-factor OLS regression
   - `persist_position_beta()` - Save to position_market_betas table
   - `calculate_portfolio_market_beta()` - Aggregate position betas

2. Update `backend/app/constants/factors.py`:
   - Add `REGRESSION_WINDOW_DAYS = 90`
   - Add `MIN_REGRESSION_DAYS = 30`
   - Add `BETA_CAP_LIMIT = 5.0`

3. Update `backend/app/batch/batch_orchestrator_v2.py`:
   - Add market beta calculation step after portfolio aggregation
   - Integrate with snapshot creation

4. Create `backend/app/calculations/snapshots.py` updates:
   - Add market beta fields to snapshot creation

5. Run migrations:
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

6. Test implementation:
   - Verify NVDA beta = 1.7 to 2.2 (not -3)
   - Confirm R² > 0.3 for high-beta stocks
   - No VIF warnings in logs

---

### ⏸️ Phase 1: Benchmark Weights & Sector Analysis (0% Complete)

**Not Started:**
- Migration 2: `benchmarks_sector_weights` table
- Migration 3: Sector & concentration columns in portfolio_snapshots
- BenchmarkSectorWeight model
- `seed_benchmark_weights.py` script (FMP API integration)
- `update_benchmark_weights.py` script
- `sector_analysis.py` calculation module

---

### ⏸️ Phase 2: Volatility Analytics (0% Complete)

**Not Started:**
- Migration 4: Volatility columns in portfolio_snapshots
- Migration 5: `position_volatility` table
- Portfolio returns calculation (CRITICAL FIX)
- Volatility calculation with 21d/63d trading day windows
- HAR model forecasting

---

## Files Modified (Committed)

### Alembic Migrations
1. `backend/alembic/versions/a1b2c3d4e5f6_create_position_market_betas.py` (NEW)
2. `backend/alembic/versions/b2c3d4e5f6g7_add_market_beta_to_snapshots.py` (NEW)

### Database Models
3. `backend/app/models/market_data.py` (MODIFIED)
   - Added `PositionMarketBeta` class

4. `backend/app/models/users.py` (MODIFIED)
   - Added `position_market_betas` relationship to Portfolio model

5. `backend/app/models/positions.py` (MODIFIED)
   - Added `market_betas` relationship to Position model

---

## Next Session Priorities

### Immediate (Phase 0 Completion)
1. **Create market_beta.py** - Core calculation logic (~400 lines)
2. **Update constants.py** - Add regression constants
3. **Update batch orchestrator** - Integrate market beta calculation
4. **Run migrations** - Apply database schema changes
5. **Test & validate** - Verify beta calculations are correct

### After Phase 0
6. **Phase 1 Database** - Create benchmark and sector migrations
7. **Phase 1 Scripts** - FMP API integration for S&P 500 data
8. **Phase 2 Fix** - Implement correct portfolio volatility calculation

---

## Estimated Completion

- **Phase 0 Complete:** ~2-3 hours remaining
- **Phase 1 Complete:** ~3-4 hours
- **Phase 2 Complete:** ~4-5 hours
- **Testing & Validation:** ~2-3 hours

**Total Remaining:** ~11-15 hours of implementation work

---

## Critical Notes

### ⚠️ Portfolio Volatility Calculation (Phase 2)
**MUST FIX:** Current approach is mathematically incorrect!

**Wrong (current):**
```python
portfolio_vol = Σ(position_vol[i] * position_weight[i])  # Ignores correlations
```

**Correct (Phase 2):**
```python
# Step 1: Compute portfolio returns
portfolio_returns[date] = Σ(position_weight[i] * position_return[i][date])

# Step 2: Calculate volatility from portfolio returns
realized_vol_21d = sqrt(252) * std(portfolio_returns[-21:])
```

### ✅ Benchmark Data Source (Phase 1)
**Solved:** Using FMP API for S&P 500 sector weights
- Endpoint: `/api/v3/sp500_constituent`
- Storage: `benchmarks_sector_weights` table
- Updates: Weekly/monthly via `update_benchmark_weights.py`

---

## Git Information

**Branch:** `RiskMetricsLocal`
**Latest Commit:** `1d8c009a` - "feat(risk-metrics): Phase 0 database schema - market beta single-factor model"
**Parent Branch:** `FrontendLocal`
**Remote:** `origin/RiskMetricsLocal`

**To Continue Work:**
```bash
git checkout RiskMetricsLocal
git pull origin RiskMetricsLocal
```

---

## References

- **Execution Plan:** `frontend/_docs/RiskMetricsExecution.md`
- **Alembic Guide:** `frontend/_docs/RiskMetricsAlembicMigrations.md`
- **Planning Doc:** `frontend/_docs/RiskMetricsPlanning.md`
- **Testing Guide:** `frontend/_docs/RiskMetricsTesting.md` (pending)

---

**Session Notes:**
- Database schema foundation is solid and ready for calculations
- All migrations follow proper Alembic patterns with up/down support
- Model relationships configured correctly for bidirectional access
- Ready to implement calculation logic in next session
