# SigmaSight Risk Metrics — Execution Plan
**Owner:** Analytics Platform  
**Created:** 2025-10-16  
**Status:** Ready to Implement (Phase 0 → Phase 2)  
**Context:** Current 7‑factor regression is unstable due to extreme multicollinearity (e.g., Market VIF >> 10). We will shift to a simpler, investor‑oriented risk framework: rock‑solid Market Beta, Sector Exposure, Concentration, and Volatility (realized + forecast). Multi‑factor “style” betas are deferred behind an Advanced toggle.

---

## Goals (What “Good” Looks Like)
1. **Accurate, explainable Market Beta** at **position** and **portfolio** levels.
2. **Sector exposure vs S&P 500** with clear **over/underweights**.
3. **Concentration metrics** (HHI, Effective N, Top‑N) computed daily.
4. **Portfolio volatility**: 21d/63d realized vol, **30d forecast** (HAR), trend + percentile.
5. **Stress testing** driven by market beta & sector shocks; add historical scenarios.
6. **Simple first**: defer complex factor models; add later behind **Advanced** toggle.

---

## Scope & Priorities
- **Phase 0 (Foundation)**: Market Beta (position → portfolio aggregation), table schema & migrations.  
- **Phase 1 (Core)**: Sector exposure + concentration + S&P benchmark compare.  
- **Phase 2 (Volatility)**: Realized vol, HAR 30d forecast, trend, percentile.  
- **Phase 3 (Advanced—Optional)**: GARCH & vol‑of‑vol; direct portfolio beta regression; historical scenarios pack.  
- **Phase 4 (Advanced Factors—Optional)**: 3–4 long‑short factors (Market, Growth‑Value spread, Momentum spread, Size spread) with UI translation.

---

## Architecture & Files
Create focused modules; **deprecate** the monolithic 7‑factor path.

```
backend/app/calculations/
├── market_beta.py           # Phase 0: single‑factor OLS (position betas), portfolio aggregation
├── sector_analysis.py       # Phase 1: sector weights, S&P compare, concentration metrics
├── volatility_analysis.py   # Phase 2: realized vols, HAR forecast, trend, percentile
├── market_risk.py           # Use new market_beta for stress tests
└── factors.py               # Deprecated (keep for reference; remove from pipelines)
```

Orchestration (batch/cron):
```
backend/app/batch/run_daily_risk_pipeline.py
  ├─ compute_position_market_betas()
  ├─ compute_portfolio_beta_agg()
  ├─ compute_sector_and_concentration()
  └─ compute_volatility_metrics()
```

---

## Data Model (Postgres) & Migrations
All primary outputs will be snapshotted daily for charting and UX simplicity.

### 1) `portfolio_snapshots` — add risk columns
```sql
ALTER TABLE portfolio_snapshots
  ADD COLUMN market_beta_weighted NUMERIC(10,4),   -- agg from position betas (Phase 0)
  ADD COLUMN market_beta_direct NUMERIC(10,4),     -- direct regression vs SPY (Phase 3)
  ADD COLUMN sector_exposure JSONB,                -- {"Technology": {"portfolio_pct":45,"benchmark_pct":28,"diff":17}, ...}
  ADD COLUMN hhi NUMERIC(12,6),
  ADD COLUMN effective_num_positions NUMERIC(12,6),
  ADD COLUMN top_3_concentration NUMERIC(12,6),
  ADD COLUMN top_10_concentration NUMERIC(12,6),
  ADD COLUMN realized_vol_21d NUMERIC(12,6),
  ADD COLUMN realized_vol_63d NUMERIC(12,6),
  ADD COLUMN expected_vol_30d NUMERIC(12,6),       -- HAR forecast
  ADD COLUMN vol_trend VARCHAR(20),                -- 'Rising'|'Falling'|'Stable'
  ADD COLUMN vol_percentile NUMERIC(12,6);
```

**Indexes (optional, useful for charts & filters)**
```sql
CREATE INDEX IF NOT EXISTS idx_snapshots_beta ON portfolio_snapshots (portfolio_id, snapshot_date, market_beta_weighted);
CREATE INDEX IF NOT EXISTS idx_snapshots_vol ON portfolio_snapshots (portfolio_id, snapshot_date, realized_vol_21d);
```

### 2) `position_market_betas` — new (store position‑level market betas by date)
```sql
CREATE TABLE IF NOT EXISTS position_market_betas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID NOT NULL,
  position_id UUID NOT NULL,
  calc_date DATE NOT NULL,
  observations INT NOT NULL,             -- sample size used
  beta NUMERIC(12,6) NOT NULL,           -- OLS slope
  alpha NUMERIC(12,6) NULL,              -- optional intercept
  r2 NUMERIC(12,6) NULL,
  stderr NUMERIC(12,6) NULL,             -- std err of beta
  p_value NUMERIC(12,6) NULL,
  method VARCHAR(32) NOT NULL DEFAULT 'OLS_SIMPLE', -- future: 'OLS_NW', etc.
  window_days INT NOT NULL,              -- e.g., 90
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE (portfolio_id, position_id, calc_date, method, window_days)
);
CREATE INDEX IF NOT EXISTS idx_pos_betas_lookup ON position_market_betas (portfolio_id, calc_date);
```

### 3) `benchmarks_sector_weights` — S&P sector weights by date (for compare)
```sql
CREATE TABLE IF NOT EXISTS benchmarks_sector_weights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  benchmark_code VARCHAR(32) NOT NULL,    -- 'SP500'
  asof_date DATE NOT NULL,
  sector VARCHAR(64) NOT NULL,            -- GICS sector
  weight NUMERIC(12,6) NOT NULL,
  UNIQUE (benchmark_code, asof_date, sector)
);
```

---

## Calculations (Specifications)

### A) Market Beta (Phase 0)
**Level:** Position → aggregate to portfolio.  
**Inputs:** Daily log returns for position *i* and SPY (or chosen market index).  
**Window:** default **90 trading days** (min 60).  
**Pre‑processing:**  
- Sort asc by date; drop NaNs.  
- Optional: winsorize returns at 1st/99th pct or cap at ±10%.  
- Use **OLS slope** (with intercept).

**Model:** `r_i,t = α_i + β_i * r_mkt,t + ε_t`  
- Report: `beta`, `alpha`, `R²`, `stderr(beta)`, `p_value`, `n`, `window_days`.  
- Flag unreliable when: `n < 60` or `stderr(beta) > |beta|` (UI “beta unstable”).

**Portfolio aggregation (Method 1 — Phase 0):**  
`β_port_weighted = Σ( w_i * β_i )` where `w_i = equity_value_i / total_equity` (same day).

**Portfolio direct regression (Method 2 — Phase 3):**  
Compute portfolio daily returns from position weights × returns, then OLS vs market returns.

**Sanity checks (unit tests):**  
- NVDA beta on recent window ≈ 1.7–2.2.  
- Correlation sign matches beta sign.  
- Perfect tracking ETF → beta ~1.0, R² > 0.95.

### B) Sector Exposure & Concentration (Phase 1)
**Inputs:** Position‐level GICS sector, position equity value (or market value), portfolio total.  
**Sector weights:** `sector_w = Σ(value in sector) / total_value`.  
**Benchmark compare:** pull latest `SP500` weights by `asof_date` (closest prior business day).  
**Over/Underweight:** `diff = portfolio_pct − benchmark_pct` per sector.

**Concentration metrics:**  
- **HHI:** `Σ w_i^2` (use decimal weights; range (0,1]); display HHI×10,000 if desired).  
- **Effective N:** `1 / Σ w_i^2`.  
- **Top‑N:** sum of largest N weights (3, 10).

**Storage:** in `portfolio_snapshots.sector_exposure` (JSONB) and concentration columns.

**Validation:** Sectors sum to ~100%; JSON schema consistent; HHI ≤ 1; Effective N ≥ 1.

### C) Volatility (Phase 2)
**Position returns:** daily log returns; **Portfolio returns:** weight‑adjusted sum by date.  
> **Important:** Portfolio volatility **must** be computed from **portfolio returns**, not the average of position vols.

**Realized volatility:**  
- 21d: `σ_21 = sqrt(252) * std(portfolio_returns over last 21)`  
- 63d: `σ_63 = sqrt(252) * std(portfolio_returns over last 63)`

**HAR 30d Forecast (Corsi)** using portfolio returns:  
- Compute realized vol proxies:  
  - `RV_d = std(returns over 1d window)` (use realized variance via squared returns mean if preferred)  
  - `RV_w = std(returns over last 5d)`  
  - `RV_m = std(returns over last 21d)`  
- Fit OLS on training window (e.g., 126–252d):  
  `RV_{t+1} = b0 + b1*RV_d + b2*RV_w + b3*RV_m + ε`  
- Forecast **30d** target: scale daily forecast to 30d annualized.  
- Store `expected_vol_30d` + `vol_trend` (‘Rising’/’Falling’/’Stable’ based on 21d vs 63d delta) + `vol_percentile` (percentile of 21d vol vs last 252d).

**Validation:**  
- σ_21 ≤ σ_63 typically in quiet regimes; trend logic matches direction.  
- Percentile ∈ [0,1]; sufficient observations (min 63 for HAR fit).

### D) Stress Testing (Phase 1+)
**Market shocks:** ±5%, ±10%, ±20% using `β_port_weighted`.  
`P&L ≈ β_port * Shock * Equity` (first‑order).

**Sector shocks:** apply sector‑specific returns to sector buckets; hold others flat.  
**Historical packs (Phase 3):** 2008, 2020‑Mar, 2011 US downgrade, 1987 (scale to multi‑day windows).  
**Crisis correlation mode:** optionally set corr→1 to remove diversification (toggle).

---

## Pipelines & Scheduling
- **Daily cron** (after EOD data load):  
  1) `compute_position_market_betas()`  
  2) `compute_portfolio_beta_agg()`  
  3) `compute_sector_and_concentration()`  
  4) `compute_volatility_metrics()`  

- **Backfill commands** (by date range) for historical snapshots.

---

## Testing & Diagnostics
**Unit tests** (pytest):
- OLS beta regression with synthetic data (known β).  
- Sector aggregation sums to 100%; HHI/Effective N identities.  
- Volatility invariants (percentile bounds, trend sign).

**Golden cases / acceptance:**
- NVDA vs SPY (beta 1.7–2.2).  
- SPY vs SPY (beta ~1.0).  
- Portfolio with 100% single stock: portfolio β == position β; HHI==1; Effective N==1.

**Runtime diagnostics (optional):**
- Flag snapshot when `observations < 60` or `stderr(beta) > |beta|`.  
- Write lightweight CSV debug dumps per stage (`/tmp/risk_debug/`).

---

## UI/UX Notes
- **Core Risk card**: Market Beta, 21d Vol, 30d Forecast, Trend.  
- **Sector vs S&P chart**: bars for portfolio vs benchmark + diff pill.  
- **Concentration widget**: Top‑3/Top‑10, HHI, Effective N.  
- **Stress tests**: quick presets + “Tech −25%” scenario.  
- **Advanced toggle** (future): 3–4 factor betas with plain‑English tooltips.

---

## Implementation Plan (Week‑by‑Week)

### Week 1 — Phase 0 (Foundation)
- Create `market_beta.py`; compute position betas via OLS 90d (min 60).  
- New table `position_market_betas`; add beta columns to `portfolio_snapshots`.  
- Aggregation to `market_beta_weighted`; expose to `market_risk.py`.  
- Unit tests & golden cases.

### Week 2 — Phase 1 (Core Metrics)
- `sector_analysis.py`: sector weights, S&P compare, JSONB payload.  
- Concentration metrics: HHI, Effective N, Top‑3/Top‑10.  
- Fill `benchmarks_sector_weights`; wire ingestion (monthly or daily).  
- Snapshot write; charts feed.

### Week 3 — Phase 2 (Volatility)
- Portfolio returns series generation.  
- Realized vol 21d/63d; HAR 30d forecast; trend; percentile.  
- Persist to snapshots; add UI cards.

### Week 4 — Phase 3 (Advanced, Optional)
- Direct portfolio beta regression.  
- Historical scenario pack; crisis correlation mode.  
- (Optional) GARCH & vol‑of‑vol calculations (store in auxiliary table if added).

---

## Advanced Factors (Phase 4 — Optional / Advanced Toggle)
- Use **orthogonal long‑short** constructs to avoid multicollinearity:
  - Market: SPY
  - Growth‑Value spread: VUG − VTV (sign ⇒ tilt)
  - Momentum spread: MTUM − SPY
  - Size spread: IWM − SPY
- Store in `portfolio_snapshots` as separate JSONB or new table if needed.  
- UI translation layer: “Growth Tilt: Strong (+0.6)” rather than raw spread beta numbers.

---

## Open Decisions
1. **Market index:** SPY vs. other (QQQ/ACWI) selectable per portfolio? (default SPY)  
2. **Winsorization caps:** ±10% or percentile‑based?  
3. **Benchmark cadence:** Monthly S&P sector weights OK? (fallback to last known).  
4. **Minimum obs rules:** Block betas if `n<60`? Mark as “unstable”?  
5. **UI Feature flagging:** `ADVANCED_FACTORS` off by default.

---

## Rollback & Safety
- Feature flag new calculations; keep old fields until parity verified.  
- Dry‑run migrations in staging; backfill limited range; compare charts.  
- If anomalies found, revert feature flag to old displays (no downtime).

---

## Deliverables Checklist
- [ ] Alembic migration(s) created & applied.  
- [ ] `position_market_betas` populated in daily job.  
- [ ] `portfolio_snapshots` risk fields populated.  
- [ ] Sector JSONB + compare rendering in UI.  
- [ ] Volatility metrics visible with HAR forecast.  
- [ ] Stress test card hooked to new market beta.  
- [ ] Tests: unit + golden cases passing.  
- [ ] Docs in `/frontend/docs/risk-metrics.md` updated if any deviations.
