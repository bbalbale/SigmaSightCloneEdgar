# App Smaller Directories Documentation

This document covers: `auth/`, `cache/`, `clients/`, `config/`, `constants/`

---

## Directory: `auth/`

### `__init__.py`
Empty module initialization file for the auth package. Provides import namespace for `from app.auth import ...`.

---

## Directory: `cache/`

### `__init__.py`
Package initialization that exports PriceCache for public API consumption. Used via `from app.cache import PriceCache`.

### `price_cache.py`
Implements in-memory price caching (bulk load vs N+1 queries) with support for single-date and multi-date ranges, achieving 300-10,000x speedup for batch processing. Used by `symbol_cache.py` and batch processing workflows.

### `symbol_cache.py`
Provides V2-compatible symbol cache with cold start support, DB fallback during initialization, and health check endpoints for Kubernetes/Railway readiness probes. Used by app startup, price lookups, and health check endpoints.

---

## Directory: `clients/`

### `__init__.py`
Package initialization that exports all market data provider classes and factory. Enables `from app.clients import MarketDataFactory, FMPClient, YFinanceClient, YahooQueryClient`.

### `base.py`
Abstract base class defining the MarketDataProvider interface with methods for stock prices, fund holdings, API key validation, and provider information. Inherited by all concrete provider implementations.

### `factory.py`
Factory pattern implementation for creating, managing, and validating market data provider clients (YFinance primary, FMP secondary, YahooQuery fallback, Polygon for options). Used by market_data_service, batch_orchestrator, and calculations.

### `yfinance_client.py`
YFinance API client as **primary provider** for stock prices, historical prices (batch download optimized), company profiles, and options chains. Used by MarketDataFactory and throughout the application.

### `fmp_client.py`
Financial Modeling Prep (FMP) API client as **secondary provider** with rate limiting, quota tracking (250 calls/day), and retry logic. Used as fallback when YFinance unavailable.

### `yahooquery_client.py`
YahooQuery API client wrapping synchronous library for historical prices, fund holdings, financial statements, and analyst estimates. Used as fallback for mutual funds and symbols failing on YFinance.

### `tradefeeds_client.py`
TradeFeeds API client (backup provider) with aggressive rate limiting to avoid CAPTCHA protection and credit usage tracking. Used as emergency fallback.

---

## Directory: `config/`

Configuration is primarily handled in `app/config.py` (root level). This subdirectory may contain supplementary configuration files if present.

---

## Directory: `constants/`

### `__init__.py`
Package initialization that re-exports all constants from submodules. Enables `from app.constants import FACTOR_ETFS, REGRESSION_WINDOW_DAYS`.

### `factors.py`
Defines factor calculation parameters (90-day regression window, 30-day minimum), ETF symbols for 8-factor model (SPY, VTV, VUG, MTUM, QUAL, IWM, USMV, TLT), spread factors, and beta caps. Used by factor calculations, batch orchestrator, and risk metrics service.

### `portfolio.py`
Defines portfolio calculation constants including position multipliers (100 for options, 1 for stocks), decimal precision (4dp Greeks, 2dp monetary), position type enums, tag filtering modes, and batch job timing. Used by portfolio calculations, models, tagging, and batch scheduling.

---

## Summary Usage Map

| Module | Primary Consumer | Secondary Consumers |
|--------|-----------------|---------------------|
| `cache/price_cache.py` | symbol_cache.py | batch processing |
| `cache/symbol_cache.py` | app startup, health checks | analytics endpoints |
| `clients/factory.py` | market_data_service, batch_orchestrator | data endpoints, calculations |
| `clients/yfinance_client.py` | factory (primary) | all market data operations |
| `clients/fmp_client.py` | factory (secondary) | fallback provider |
| `clients/yahooquery_client.py` | factory (fallback) | fund holdings, historical data |
| `constants/factors.py` | factor calculations, APScheduler | risk metrics, interpretations |
| `constants/portfolio.py` | portfolio calculations, batch jobs | position tagging, analytics |
