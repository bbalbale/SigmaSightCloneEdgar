# App Calculations Directory Documentation

This document describes all files in `backend/app/calculations/`.

---

## Overview

The calculations directory contains 18+ Python modules implementing 8+ quantitative calculation engines for portfolio risk analytics, valuation, and Greeks calculations. Used primarily by the batch orchestrator (Phase 1-6) for daily portfolio processing.

---

## Core Calculation Engines

### `__init__.py`
Module entry point exporting public API for market data and portfolio calculations. Exports: `calculate_position_market_value`, `calculate_daily_pnl`, `calculate_portfolio_exposures`, `create_portfolio_snapshot`.

### `market_data.py`
Position valuation and daily P&L calculations with database integration. Used by `pnl_calculator.py` (Phase 2), `analytics_runner.py` (Phase 6), and all factor modules for price fetching and returns calculation.

### `greeks.py`
Options Greeks calculation using the mibian library with real/mock calculation fallback. Used by `analytics_runner.py` (Phase 6) and batch processing for Greeks calculations on options positions.

### `portfolio.py`
Portfolio aggregation of position-level metrics with 60-second TTL caching. Used by `snapshots.py`, `analytics_runner.py`, and stress testing modules in Phase 2/6 for portfolio-level aggregations.

### `snapshots.py`
Portfolio snapshot generation for daily portfolio state tracking using insert-first idempotency pattern. Used by `pnl_calculator.py` (Phase 2) for creating daily snapshots.

---

## Beta & Factor Calculation Engines

### `market_beta.py`
Single-factor OLS regression model calculating position and portfolio market beta against SPY. Used by `analytics_runner.py` (Phase 6), `market_risk.py`, and stress testing modules.

### `interest_rate_beta.py`
Interest rate sensitivity calculation via OLS regression against TLT (20+ Year Treasury ETF). Used by `analytics_runner.py` (Phase 6), `stress_testing.py`, and IR integration modules.

### `factors.py`
Multi-factor exposure analysis (7-factor model) with ETF proxies, ridge regression, and multicollinearity diagnostics. Used by `analytics_runner.py` (Phase 6) as fallback when symbol-level factors insufficient.

### `factors_ridge.py`
Ridge regression factor analysis for 6 non-market factors (Value, Growth, Momentum, Quality, Size, Low Volatility) addressing multicollinearity. Used by `analytics_runner.py` (Phase 6) and `symbol_factors.py`.

### `factors_spread.py`
Long-short spread factor betas using 4 factors (Growth-Value, Momentum, Size, Quality spreads) with 180-day OLS regression. Used by `analytics_runner.py` (Phase 6) and `symbol_factors.py`.

### `symbol_factors.py`
Symbol-level factor calculations (Phase 1.5) - pre-computes factor betas once per symbol eliminating redundant calculations across portfolios. Used by `batch_orchestrator.py` (Phase 1.5).

---

## Risk Analysis & Stress Testing

### `market_risk.py`
Market risk scenarios implementation using factor-based approach and interest rate scenarios with FRED treasury data. Used by `analytics_runner.py` (Phase 6) and `stress_testing.py`.

### `stress_testing.py`
Comprehensive stress testing framework with factor correlation modeling and predefined scenarios from JSON configuration. Used by `analytics_runner.py` (Phase 6).

### `stress_testing_ir_integration.py`
Interest rate beta integration for stress testing - fetches IR betas and calculates shock impacts. Used by `stress_testing.py` for IR scenarios.

### `volatility_analytics.py`
Realized volatility and HAR (Heterogeneous Autoregressive) forecasting using 21d/63d windows and historical percentiles. Used by `analytics_runner.py` (Phase 6) for Phase 3 risk metrics.

### `sector_analysis.py`
Sector exposure analysis vs S&P 500 benchmark and concentration metrics (HHI). Used by `analytics_runner.py` (Phase 6) for sector exposure calculations.

---

## Utility & Support Modules

### `factor_utils.py`
Shared utilities for factor analysis including factor name normalization, multicollinearity diagnostics, and default data structures. Used by all factor modules for common operations.

### `regression_utils.py`
Standardized OLS regression wrapper with statistical classification and diagnostics. Used by `market_beta.py`, `interest_rate_beta.py`, and factor modules for consistent regression handling.

### `factor_interpretation.py`
User-friendly interpretation conversion for spread factor betas to plain English explanations. Used by `portfolio_factor_service.py` and analytics endpoints.

---

## Batch Processing Integration

```
batch_orchestrator
├── Phase 1: market_data_collector
│   └── market_data.py (fetch prices)
├── Phase 1.5: symbol_factors.py
│   ├── factors_ridge.py
│   └── factors_spread.py
├── Phase 2: pnl_calculator
│   ├── market_data.py
│   └── snapshots.py
└── Phase 6: analytics_runner
    ├── market_beta.py
    ├── interest_rate_beta.py
    ├── factors.py (fallback)
    ├── factors_ridge.py
    ├── factors_spread.py
    ├── symbol_factors.py (load pre-computed)
    ├── sector_analysis.py
    ├── volatility_analytics.py
    ├── market_risk.py
    └── stress_testing.py
        └── stress_testing_ir_integration.py
```

---

## Summary Table

| File | Primary Dependencies | Used By |
|------|----------------------|---------|
| `market_data.py` | SQLAlchemy, market_data_service | All modules, pnl_calculator |
| `greeks.py` | mibian | analytics_runner |
| `portfolio.py` | pandas, Decimal | snapshots, analytics_runner |
| `snapshots.py` | market_data.py, trading_calendar | pnl_calculator |
| `market_beta.py` | regression_utils | analytics_runner, stress_testing |
| `interest_rate_beta.py` | regression_utils | analytics_runner, stress_testing |
| `factors.py` | statsmodels, factor_utils | analytics_runner |
| `factors_ridge.py` | sklearn, factor_utils | analytics_runner, symbol_factors |
| `factors_spread.py` | statsmodels, factor_utils | analytics_runner, symbol_factors |
| `symbol_factors.py` | factors_ridge, factors_spread | batch_orchestrator |
| `volatility_analytics.py` | sklearn, pandas | analytics_runner |
| `sector_analysis.py` | market_data.py | analytics_runner |
| `market_risk.py` | fredapi, statsmodels | stress_testing, analytics_runner |
| `stress_testing.py` | factors.py, market_risk.py | analytics_runner |
| `stress_testing_ir_integration.py` | interest_rate_beta | stress_testing |
| `factor_utils.py` | numpy, pandas | All factor modules |
| `regression_utils.py` | statsmodels, numpy | All beta modules |
| `factor_interpretation.py` | None | portfolio_factor_service |

---

## Key Design Patterns

1. **Position-First Caching**: Beta calculations check cache first, only compute uncached positions
2. **Symbol-Level Pre-Computation**: Factor betas computed once per symbol in Phase 1.5, aggregated at portfolio level in Phase 6
3. **Graceful Degradation**: All calculations handle missing data with fallbacks
4. **TTL Caching**: Portfolio aggregations use 60-second in-memory LRU cache with time-based expiration
