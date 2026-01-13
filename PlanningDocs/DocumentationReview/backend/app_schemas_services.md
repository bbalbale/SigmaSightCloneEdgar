# App Schemas and Services Documentation

This document covers: `schemas/` and `services/`

---

## Directory: `schemas/` - Pydantic Request/Response Schemas

### Base & Common

#### `__init__.py`
Exports all Pydantic schema classes for package-level imports. Used by API endpoints.

#### `base.py`
Provides base Pydantic schema classes with common configuration (ORM support, UUID/datetime JSON encoding). Inherited by all other schemas.

### Authentication

#### `auth.py`
Defines user authentication schemas: `CurrentUser`, `UserLogin`, `UserRegister`, `Token`, `TokenResponse`, `UserMeResponse` with subscription tier. Used by auth endpoints.

### Data & Analytics

#### `data.py`
Provides agent-optimized data response schemas: `PortfolioSummaryResponse`, `HistoricalPricesResponse`, `QuotesResponse`, `DataQualityResponse`. Used by data endpoints.

#### `analytics.py`
Defines portfolio analytics schemas: `PortfolioOverviewResponse`, `CorrelationMatrixResponse`, `StressTestResponse`, sector exposure, volatility metrics. Used by analytics endpoints.

#### `correlations.py`
Provides correlation analysis schemas: `PositionFilterConfig`, `CorrelationCalculationResponse`, `CorrelationMatrixResponse`. Used by analytics endpoints.

#### `factors.py`
Defines factor exposure schemas: `FactorDefinitionResponse`, `FactorExposureResponse`, `PositionFactorExposureResponse`. Used by factor analytics.

#### `market_risk.py`
Defines market risk schemas: `MarketRiskScenarioResponse`, `InterestRateScenarioResponse`, `PositionInterestRateBetaResponse`. Used by stress testing.

#### `stress_testing.py`
Defines comprehensive stress test schemas: scenario definitions, factor correlations, impact calculations. Used by stress test endpoints.

### Portfolio & Position Management

#### `portfolios.py`
Defines portfolio CRUD schemas: `PortfolioCreateRequest`, `PortfolioResponse`, `PortfolioListResponse`. Used by portfolio endpoints.

#### `position_schemas.py`
Defines position CRUD schemas: `CreatePositionRequest`, `UpdatePositionRequest`, `PositionResponse`. Used by position endpoints.

#### `target_prices.py`
Provides target price schemas: `TargetPriceCreate`, `TargetPriceResponse`, `PortfolioTargetPriceSummary`. Used by target price endpoints.

### Tagging

#### `tag_schemas.py`
Defines tag management schemas: `CreateTagRequest`, `UpdateTagRequest`, `TagResponse`. Used by tag endpoints.

#### `position_tag_schemas.py`
Provides position-tag relationship schemas: `AssignTagsToPositionRequest`, `PositionTagResponse`. Used by position tagging.

### Financial Data

#### `fundamentals.py`
Comprehensive financial statement schemas: `IncomeStatementResponse`, `BalanceSheetResponse`, `CashFlowResponse`. Used by fundamentals endpoints.

#### `equity_change_schemas.py`
Provides equity flow schemas: `EquityChangeCreateRequest`, `EquityChangeResponse`. Used by equity management.

### Other

#### `equity_search.py`
Provides equity search schemas: `EquitySearchItem`, `EquitySearchFiltersResponse`. Used by search endpoint.

#### `history.py`
Provides export history tracking schemas. Used by audit features.

#### `modeling.py`
Provides modeling session schemas for what-if analysis. Used by portfolio modeling.

---

## Directory: `services/` - Business Logic Layer

### Market Data Services

#### `market_data_service.py`
Fetches market data from multiple providers (YFinance primary, FMP secondary, Polygon for options, FRED for macro) with unified fallback chain. 100+ methods. Used throughout the application.

#### `company_profile_service.py`
Fetches and caches company profile data (53 fields) with automatic Railway cron sync. Used by sector classification and valuation.

#### `yahooquery_service.py`
YahooQuery API wrapper for company profiles, fundamentals, and quotes as secondary provider. Used as market data fallback.

#### `rate_limiter.py`
Rate limiter for external APIs with exponential backoff and retry logic. Used by all API calls.

### Portfolio Analytics Services

#### `portfolio_analytics_service.py`
Calculates portfolio-level analytics: exposures, P&L metrics, position counts, leverage ratios. Used by analytics endpoints.

#### `portfolio_data_service.py`
Aggregates portfolio data from snapshots, positions, and market data. Used by data endpoints.

#### `portfolio_exposure_service.py`
Calculates long/short/gross/net exposures and leverage ratios. Used by analytics overview.

#### `portfolio_factor_service.py`
Calculates portfolio-level factor exposures (5 factors) with equity-weighted aggregation. Used by factor endpoints.

#### `correlation_service.py`
Calculates pairwise and portfolio-level correlations with clustering. Used by analytics endpoints.

#### `risk_metrics_service.py`
Calculates risk metrics: volatility (HAR forecasting), drawdown, concentration (HHI), sector exposure. Used by risk endpoints.

#### `stress_test_service.py`
Executes comprehensive stress test scenarios with 50+ predefined scenarios. Used by stress test endpoint.

### Position & Tag Services

#### `position_service.py`
Core position management: CRUD, bulk operations, symbol validation, duplicate detection. Used by position endpoints.

#### `tag_service.py`
Manages user-scoped tag lifecycle: create, archive/restore, usage counting. Used by tag endpoints.

#### `position_tag_service.py`
Handles position-to-tag relationships: assign/remove, bulk operations. Used by position tagging endpoints.

#### `target_price_service.py`
Manages target prices: CRUD, CSV import/export, portfolio aggregation. Used by target price endpoints.

### Financial Data Services

#### `fundamentals_service.py`
Fetches and aggregates financial statement data from yahooquery. Used by fundamentals endpoints.

#### `equity_change_service.py`
Manages portfolio equity contributions/withdrawals. Used by equity flow endpoints.

### AI & Agent Services

#### `analytical_reasoning_service.py`
High-level analytical reasoning using OpenAI Responses API with tool integration. Used by AI chat.

#### `ai_metrics_service.py`
Tracks AI agent usage: message count, API costs, performance metrics. Used by subscription enforcement.

### Batch & Admin Services

#### `batch_trigger_service.py`
Manually triggers batch processing phases. Used by admin batch endpoints.

#### `batch_history_service.py`
Tracks batch execution history for audit and debugging. Used by batch monitoring.

#### `background_job_tracker.py`
Tracks long-running background jobs for status polling. Used by batch status endpoint.

#### `admin_fix_service.py`
Administrative maintenance services for data corrections. Used by admin operations.

### Utility Services

#### `symbol_validator.py`
Validates stock symbols against market data availability. Used by position creation.

#### `symbol_utils.py`
Utility functions for symbol normalization and synthetic detection. Used by all symbol queries.

#### `csv_parser_service.py`
Parses CSV imports for positions and target prices. Used by import endpoints.

#### `onboarding_service.py`
New user onboarding: default portfolio, starter tags. Used by registration flow.

#### `usage_service.py`
Manages user subscription tier enforcement. Used by feature gating.

---

## Summary Statistics

**Schemas**: 19 files covering all request/response models

**Services**: 45+ files organized by functional domain:
- Market Data: 5 services
- Portfolio Analytics: 7 services
- Position/Tag Management: 4 services
- Financial Data: 2 services
- AI/Agent: 2 services
- Batch/Admin: 4 services
- Utility: 6+ services
