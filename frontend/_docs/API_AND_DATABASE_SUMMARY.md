# SigmaSight API and Database Summary

**Generated**: September 29, 2025
**Status**: Production-Ready APIs with Complete Database Schema
**Latest Updates**: Added investment_class fields to positions API, implemented 3-column investment class display

---

## Part I: API Endpoints Summary

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication Required
All endpoints except `/auth/login` and `/auth/register` require JWT Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## 📍 API Endpoints by Category

### 🔐 Authentication Endpoints (5 endpoints)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/auth/login` | ✅ Ready | Login with email/password, returns JWT |
| POST | `/auth/register` | ✅ Ready | Register new user |
| GET | `/auth/me` | ✅ Ready | Get current user info |
| POST | `/auth/refresh` | ✅ Ready | Refresh JWT token |
| POST | `/auth/logout` | ✅ Ready | Clear auth cookie |

### 📊 Data Endpoints (11 endpoints)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/data/portfolios` | ✅ Ready | List user portfolios |
| GET | `/data/portfolio/{id}/complete` | ✅ Ready | Full portfolio snapshot |
| GET | `/data/portfolio/{id}/data-quality` | ✅ Ready | Data quality metrics |
| GET | `/data/positions/details` | ✅ Ready | Position details with P&L, investment_class, and options data |
| GET | `/data/positions/top/{id}` | ✅ Ready | Top positions by various metrics |
| GET | `/data/prices/historical/{id}` | ✅ Ready | Historical price data |
| GET | `/data/prices/quotes` | ✅ Ready | Real-time market quotes |
| GET | `/data/factors/etf-prices` | ✅ Ready | Factor ETF prices |
| GET | `/data/test-demo` | ✅ Ready | Test endpoint |
| GET | `/data/demo/{portfolio_type}` | ✅ Ready | Demo data (no auth) |

### 📈 Analytics Endpoints (7 endpoints)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/analytics/portfolio/{id}/overview` | ✅ Ready | Portfolio metrics overview |
| GET | `/analytics/portfolio/{id}/correlation-matrix` | ✅ Ready | Position correlations |
| GET | `/analytics/portfolio/{id}/diversification-score` | ✅ Ready | Portfolio diversification |
| GET | `/analytics/portfolio/{id}/factor-exposures` | ✅ Ready | Portfolio factor betas |
| GET | `/analytics/portfolio/{id}/positions/factor-exposures` | ✅ Ready | Position-level factors |
| GET | `/analytics/portfolio/{id}/stress-test` | ✅ Ready | Stress test scenarios |
| GET | `/analytics/portfolio/{id}/risk-metrics` | ⚠️ Deprecated | Legacy risk metrics |

### 💬 Chat Endpoints (6 endpoints - SSE Streaming)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/chat/conversations` | ✅ Ready | Create conversation |
| GET | `/chat/conversations/{id}` | ✅ Ready | Get conversation |
| GET | `/chat/conversations` | ✅ Ready | List conversations |
| PUT | `/chat/conversations/{id}/mode` | ✅ Ready | Change agent mode |
| DELETE | `/chat/conversations/{id}` | ✅ Ready | Delete conversation |
| POST | `/chat/send` | ✅ Ready | Send message (SSE stream) |

### 🎯 Target Prices Endpoints (10 endpoints)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/target-prices/{portfolio_id}` | ✅ Ready | Create target price |
| GET | `/target-prices/{portfolio_id}` | ✅ Ready | List portfolio targets |
| GET | `/target-prices/{portfolio_id}/summary` | ✅ Ready | Portfolio summary |
| GET | `/target-prices/target/{id}` | ✅ Ready | Get specific target |
| PUT | `/target-prices/target/{id}` | ✅ Ready | Update target price |
| DELETE | `/target-prices/target/{id}` | ✅ Ready | Delete target price |
| POST | `/target-prices/{portfolio_id}/bulk` | ✅ Ready | Bulk create |
| PUT | `/target-prices/{portfolio_id}/bulk-update` | ✅ Ready | Bulk update |
| POST | `/target-prices/{portfolio_id}/import-csv` | ✅ Ready | Import from CSV |
| POST | `/target-prices/{portfolio_id}/export` | ✅ Ready | Export to CSV/JSON |

### 🎯 Strategy Endpoints (12 endpoints) - **Frontend: 100% Complete** ✅
| Method | Endpoint | Status | Description | Frontend Method |
|--------|----------|--------|-------------|-----------------|
| POST | `/strategies/` | ✅ Ready | Create new strategy | `strategiesApi.create()` |
| GET | `/strategies/` | ✅ Ready | List all strategies | `strategiesApi.listByPortfolio()` |
| GET | `/strategies/{id}` | ✅ Ready | Get strategy details | `strategiesApi.get()` |
| PATCH | `/strategies/{id}` | ✅ Ready | Update strategy | `strategiesApi.update()` |
| DELETE | `/strategies/{id}` | ✅ Ready | Delete strategy | `strategiesApi.delete()` |
| POST | `/strategies/{id}/positions` | ✅ Ready | Add positions to strategy | `strategiesApi.addPositions()` |
| DELETE | `/strategies/{id}/positions` | ✅ Ready | Remove positions from strategy | `strategiesApi.removePositions()` |
| POST | `/strategies/{id}/tags` | ✅ Ready | Assign tags to strategy | `strategiesApi.addStrategyTags()` |
| DELETE | `/strategies/{id}/tags` | ✅ Ready | Remove tags from strategy | `strategiesApi.removeStrategyTags()` |
| GET | `/strategies/detect/{portfolio_id}` | ✅ Ready | Auto-detect strategies | `strategiesApi.detect()` |
| POST | `/strategies/combine` | ✅ Ready | Combine positions into strategy | `strategiesApi.combine()` |
| GET | `/data/portfolios/{id}/strategies` | ✅ Ready | Get portfolio strategies | `strategiesApi.listByPortfolio()` |

**Frontend Service**: `src/services/strategiesApi.ts` (12/12 methods implemented)

**New Strategy Fields (2025-10-01)**:
- `direction` (String): LONG, SHORT, LC, LP, SC, SP, NEUTRAL - automatically calculated from positions
- `primary_investment_class` (String): PUBLIC, OPTIONS, PRIVATE - automatically calculated from positions
- **Purpose**: Enable filtering strategies by investment class and direction for 3-column portfolio layout
- **See**: `STRATEGY_CATEGORIZATION_IMPLEMENTATION.md` for deployment guide

### 🏷️ Tag Endpoints (10 endpoints) - **Frontend: 100% Complete** ✅
| Method | Endpoint | Status | Description | Frontend Method |
|--------|----------|--------|-------------|-----------------|
| POST | `/tags/` | ✅ Ready | Create new tag | `tagsApi.create()` |
| GET | `/tags/` | ✅ Ready | List user tags | `tagsApi.list()` |
| GET | `/tags/{id}` | ✅ Ready | Get tag details | `tagsApi.get()` |
| PATCH | `/tags/{id}` | ✅ Ready | Update tag | `tagsApi.update()` |
| DELETE | `/tags/{id}` | ✅ Ready | Archive/delete tag | `tagsApi.delete()` |
| POST | `/tags/{id}/restore` | ✅ Ready | Restore archived tag | `tagsApi.restore()` |
| POST | `/tags/defaults` | ✅ Ready | Create/get default tags (idempotent) | `tagsApi.defaults()` |
| POST | `/tags/reorder` | ✅ Ready | Reorder tag display | `tagsApi.reorder()` |
| GET | `/tags/{id}/strategies` | ✅ Ready | Get strategies using tag | `tagsApi.getStrategies()` |
| POST | `/tags/batch-update` | ✅ Ready | Batch update tags | `tagsApi.batchUpdate()` |

**Frontend Service**: `src/services/tagsApi.ts` (10/10 methods implemented)

### ⚙️ Admin Endpoints (5 endpoints - Not Registered in Router)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/admin/batch/jobs/status` | ⚠️ Exists | Batch job status |
| GET | `/admin/batch/jobs/summary` | ⚠️ Exists | Job statistics |
| DELETE | `/admin/batch/jobs/{id}/cancel` | ⚠️ Exists | Cancel job |
| GET | `/admin/batch/data-quality` | ⚠️ Exists | Data quality status |
| POST | `/admin/batch/data-quality/refresh` | ⚠️ Exists | Refresh market data |

### 📋 Summary Statistics
- **Total Endpoints**: 66
- **Production Ready**: 61 (92.4%)
- **Admin (Not Registered)**: 5 (7.6%)
- **Categories**: 8 (Auth, Data, Analytics, Chat, Target Prices, Strategies, Tags, Admin)

---

## Part I-B: Frontend Integration Status

### 🎨 Frontend Services Implementation

| Service | File | Methods | Status | Notes |
|---------|------|---------|--------|-------|
| **Strategies** | `src/services/strategiesApi.ts` | 12/12 | ✅ 100% | All CRUD + tag management + combine |
| **Tags** | `src/services/tagsApi.ts` | 10/10 | ✅ 100% | Full tag lifecycle + bulk operations |
| **Analytics** | `src/services/analyticsApi.ts` | 5/5 | ✅ 100% | Portfolio analytics endpoints |
| **Portfolio** | `src/services/portfolioService.ts` | 1/1 | ✅ 100% | Load portfolio data (composite) |
| **Auth** | `src/services/authManager.ts` | - | ✅ 100% | JWT token management |

### 🧩 Frontend Components Implementation

| Component | File | Purpose | Status | Notes |
|-----------|------|---------|--------|-------|
| **StrategyCard** | `src/components/strategies/StrategyCard.tsx` | Wrapper for position cards | ✅ Complete | Follows SelectablePositionCard pattern |
| **StrategyPositionList** | `src/components/strategies/StrategyPositionList.tsx` | List container | ✅ Complete | Manages expansion state, renders cards |
| **PortfolioStrategiesView** | `src/components/portfolio/PortfolioStrategiesView.tsx` | 3-column layout (NEW) | ✅ Complete | Strategy view matching position layout |
| **TagBadge** | `src/components/organize/TagBadge.tsx` | Tag display | ✅ Complete | Drag-drop support, color customization |
| **useStrategies** | `src/hooks/useStrategies.ts` | React hook | ✅ Complete | Fetch strategies, tag management methods |
| **useTags** | `src/hooks/useTags.ts` | React hook | ✅ Complete | Tag CRUD operations |
| **useStrategyFiltering** | `src/hooks/useStrategyFiltering.ts` | Filter hook (NEW) | ✅ Complete | Filter strategies by inv. class & direction |

### 📦 Type Definitions

| File | Exports | Status | Notes |
|------|---------|--------|-------|
| `src/types/strategies.ts` | 25+ types | ✅ Complete | StrategyType, StrategyDetail, TagItem, UI props, etc. **NEW**: direction & primary_investment_class fields |
| `src/types/analytics.ts` | Factor types | ✅ Complete | FactorExposure, analytics data |

### 🚧 Integration Status (Portfolio Page)

| Feature | Status | Notes |
|---------|--------|-------|
| **Strategy display components** | ✅ Complete | StrategyCard, StrategyPositionList, PortfolioStrategiesView ready |
| **Strategy categorization** | ✅ Complete | direction & primary_investment_class fields implemented (NEW) |
| **Strategy filtering** | ✅ Complete | useStrategyFiltering hook filters by inv. class & direction |
| **Portfolio page integration** | ⏸️ Ready for integration | Non-breaking hybrid approach (view toggle) |
| **Tag filtering UI** | 🔄 Partial | FilterBar exists but doesn't filter yet |
| **Tag management modal** | ❌ Not Started | Needs implementation |
| **Organize page** | ✅ Complete | Uses strategies and tags successfully |

**Recommendation**: Implement hybrid approach (add strategy view alongside position view) to avoid breaking changes. See `strategyuicomponents.md` for detailed risk analysis.

---

## Part II: Database Schema - ASCII Diagram

### 🗄️ Database Overview
- **Type**: PostgreSQL (via Docker)
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Primary Keys**: UUID for all tables

### 📊 Core Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIGMASIGHT DATABASE SCHEMA                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     USERS       │       │   PORTFOLIOS    │       │   POSITIONS     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (UUID)    PK │───┐   │ id (UUID)    PK │───┐   │ id (UUID)    PK │
│ email           │   │   │ user_id      FK │   │   │ portfolio_id FK │
│ hashed_password │   └──<│ name            │   └──<│ symbol          │
│ full_name       │       │ description     │       │ position_type   │
│ is_active       │       │ currency        │       │ quantity        │
│ is_admin        │       │ created_at      │       │ cost_basis      │
│ created_at      │       │ updated_at      │       │ created_at      │
│ updated_at      │       │ cash_balance    │       │ updated_at      │
└─────────────────┘       │ equity_balance  │       │ investment_class│
                          └─────────────────┘       └─────────────────┘
                                    │                        │
                                    │                        │
                    ┌───────────────┴────────────────────────┴──────────┐
                    │                                                    │
                    ▼                                                    ▼
        ┌─────────────────────┐                           ┌──────────────────────┐
        │ PORTFOLIO_SNAPSHOTS │                           │  MARKET_DATA_CACHE   │
        ├─────────────────────┤                           ├──────────────────────┤
        │ id (UUID)        PK │                           │ id (UUID)         PK │
        │ portfolio_id     FK │                           │ symbol               │
        │ snapshot_date       │                           │ date                 │
        │ total_value         │                           │ open                 │
        │ daily_return        │                           │ high                 │
        │ cumulative_return   │                           │ low                  │
        │ created_at          │                           │ close                │
        └─────────────────────┘                           │ volume               │
                                                          │ adjusted_close       │
                                                          │ created_at           │
                                                          └──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CALCULATION RESULTS TABLES                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   POSITION_GREEKS    │  │  FACTOR_EXPOSURES    │  │ CORRELATION_CALCS    │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ id (UUID)         PK │  │ id (UUID)         PK │  │ id (UUID)         PK │
│ position_id       FK │  │ portfolio_id      FK │  │ portfolio_id      FK │
│ calculation_date     │  │ factor_id         FK │  │ calculation_date     │
│ delta                │  │ calculation_date     │  │ lookback_days        │
│ gamma                │  │ exposure_value       │  │ created_at           │
│ theta                │  │ beta                 │  └──────────────────────┘
│ vega                 │  │ created_at           │            │
│ rho                  │  └──────────────────────┘            │
│ created_at           │                                       ▼
└──────────────────────┘            ┌──────────────────────────────────┐
                                    │   PAIRWISE_CORRELATIONS          │
┌──────────────────────┐            ├──────────────────────────────────┤
│ POSITION_FACTOR_EXP  │            │ id (UUID)                     PK │
├──────────────────────┤            │ correlation_calc_id           FK │
│ id (UUID)         PK │            │ symbol1                          │
│ position_id       FK │            │ symbol2                          │
│ factor_id         FK │            │ correlation_value                │
│ calculation_date     │            │ overlap_days                     │
│ exposure_value       │            └──────────────────────────────────┘
│ created_at           │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          STRESS TEST & RISK TABLES                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  STRESS_SCENARIOS    │  │  STRESS_TEST_RESULTS │  │    BATCH_JOBS        │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ id (UUID)         PK │  │ id (UUID)         PK │  │ id (UUID)         PK │
│ scenario_id          │  │ portfolio_id      FK │  │ job_name             │
│ name                 │  │ scenario_id       FK │  │ status               │
│ description          │  │ calculation_date     │  │ portfolio_id      FK │
│ category             │  │ correlated_pnl       │  │ started_at           │
│ market_shock         │  │ independent_pnl      │  │ completed_at         │
│ created_at           │  │ created_at           │  │ error_message        │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            TARGET PRICE TABLES                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────┐         ┌────────────────────────────┐
│  PORTFOLIO_TARGET_PRICES   │         │   FACTOR_DEFINITIONS       │
├────────────────────────────┤         ├────────────────────────────┤
│ id (UUID)               PK │         │ id (UUID)               PK │
│ portfolio_id            FK │         │ name                       │
│ position_id             FK │         │ etf_symbol                 │
│ symbol                     │         │ description                │
│ position_type              │         │ is_active                  │
│ target_price_eoy           │         │ created_at                 │
│ target_price_next_year     │         └────────────────────────────┘
│ downside_target_price      │
│ current_price              │         ┌────────────────────────────┐
│ expected_return_eoy        │         │    ECONOMIC_DATA           │
│ expected_return_next_year  │         ├────────────────────────────┤
│ downside_return            │         │ id (UUID)               PK │
│ position_weight            │         │ indicator                  │
│ contribution_to_portfolio  │         │ date                       │
│ contribution_to_risk       │         │ value                      │
│ price_updated_at           │         │ source                     │
│ created_by              FK │         │ created_at                 │
│ created_at                 │         └────────────────────────────┘
│ updated_at                 │
└────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          STRATEGY & TAGGING TABLES                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────┐         ┌────────────────────────────┐
│       STRATEGIES           │         │     STRATEGY_LEGS          │
├────────────────────────────┤         ├────────────────────────────┤
│ id (UUID)               PK │         │ id (UUID)               PK │
│ portfolio_id            FK │───┐     │ strategy_id             FK │
│ strategy_type              │   │     │ position_id             FK │
│ name                       │   └────<│ created_at                 │
│ description                │         └────────────────────────────┘
│ is_synthetic               │
│ net_exposure               │         ┌────────────────────────────┐
│ total_cost_basis           │         │       TAGS_V2              │
│ created_at                 │         ├────────────────────────────┤
│ updated_at                 │         │ id (UUID)               PK │
│ closed_at                  │         │ user_id                 FK │
│ created_by              FK │         │ name                       │
└────────────────────────────┘         │ color                      │
                                       │ description                │
┌────────────────────────────┐         │ display_order              │
│    STRATEGY_TAGS           │         │ usage_count                │
├────────────────────────────┤         │ is_archived                │
│ id (UUID)               PK │         │ archived_at                │
│ strategy_id             FK │         │ archived_by             FK │
│ tag_id                  FK │         │ created_at                 │
│ assigned_at                │         │ updated_at                 │
│ assigned_by             FK │         └────────────────────────────┘
└────────────────────────────┘

┌────────────────────────────┐         ┌────────────────────────────┐
│   STRATEGY_METRICS         │         │   OPTION_CONTRACTS         │
├────────────────────────────┤         ├────────────────────────────┤
│ id (UUID)               PK │         │ id (UUID)               PK │
│ strategy_id             FK │         │ position_id             FK │
│ calculation_date           │         │ underlying_symbol          │
│ net_delta                  │         │ strike_price               │
│ net_gamma                  │         │ expiry_date                │
│ net_theta                  │         │ option_type                │
│ net_vega                   │         │ contract_size               │
│ total_pnl                  │         │ created_at                 │
│ max_profit                 │         └────────────────────────────┘
│ max_loss                   │
│ break_even_points          │
│ created_at                 │
└────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            AGENT/CHAT TABLES                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────┐         ┌────────────────────────────┐
│   agent.CONVERSATIONS      │         │  agent.MESSAGES            │
├────────────────────────────┤         ├────────────────────────────┤
│ id (UUID)               PK │         │ id (UUID)               PK │
│ user_id                 FK │───┐     │ conversation_id         FK │
│ portfolio_id            FK │   │     │ role                       │
│ mode                       │   └────<│ content                    │
│ provider                   │         │ tool_calls                 │
│ provider_thread_id         │         │ created_at                 │
│ created_at                 │         └────────────────────────────┘
└────────────────────────────┘

```

### 🔑 Key Relationships

#### Primary Relationships:
1. **Users → Portfolios**: One-to-Many (1 user has multiple portfolios)
2. **Portfolios → Positions**: One-to-Many (1 portfolio has multiple positions)
3. **Portfolios → Strategies**: One-to-Many (trading strategies per portfolio)
4. **Strategies → Positions**: Many-to-Many via strategy_legs (positions in strategies)
5. **Users → Tags**: One-to-Many (user-scoped tagging system)
6. **Strategies → Tags**: Many-to-Many via strategy_tags (tag assignments)
7. **Portfolios → Portfolio Snapshots**: One-to-Many (historical snapshots)
8. **Positions → Greeks/Factors**: One-to-Many (calculation results)
9. **Portfolios → Target Prices**: One-to-Many (price targets per position)
10. **Users → Conversations**: One-to-Many (chat threads)
11. **Conversations → Messages**: One-to-Many (chat history)

#### Investment Classification:
- **Position.investment_class**: Database field (PUBLIC/OPTIONS/PRIVATE)
  - PUBLIC: Regular equities, ETFs
  - OPTIONS: Options contracts (LC, LP, SC, SP position types)
  - PRIVATE: Private/alternative investments
- **Position.investment_subtype**: Optional categorization within investment class
- **API Response**: `/data/positions/details` now includes:
  - investment_class: String field for position categorization
  - investment_subtype: Optional subtype classification
  - strike_price: For options contracts
  - expiration_date: For options contracts
  - underlying_symbol: For options contracts

#### Position Types:
- LONG: Long equity position
- SHORT: Short equity position
- LC: Long Call option
- LP: Long Put option
- SC: Short Call option (covered/naked)
- SP: Short Put option

#### Portfolio Snapshots & Equity Balance:
- **PortfolioSnapshot Table**: Daily historical snapshots of portfolio state
  - Captures complete portfolio metrics on each trading day
  - Includes valuations, exposures, P&L, Greeks, and position counts
- **equity_balance Field**: Tracks the capital account over time
  - Formula: `starting_equity_balance + realized_pnl`
  - Represents actual capital (starting balance + realized gains/losses)
  - Updated daily during batch processing BEFORE snapshot creation
  - Stored in both `portfolios.equity_balance` (current) and `portfolio_snapshots.equity_balance` (historical)
  - NOT the same as market value or unrealized P&L
  - Used for historical tracking of capital account changes

### 📈 Batch Processing Tables

#### Calculation Engines (8 total, 7 functional):
1. **Market Data Update**: Populates market_data_cache
2. **Position Greeks**: Calculates options Greeks
3. **Factor Exposures**: Portfolio & position-level factor betas
4. **Correlation Matrix**: Pairwise position correlations
5. **Stress Testing**: Scenario-based portfolio impacts
6. **Portfolio Aggregation**: Daily snapshots and returns
7. **Data Quality**: Validation and completeness checks
8. **Risk Metrics**: (Partially implemented)

### 🔐 Security Features

1. **Authentication**:
   - JWT tokens with 30-day expiration
   - HTTP-only cookies for web clients
   - Password hashing with bcrypt

2. **Data Access**:
   - Row-level security via user_id/portfolio_id
   - Portfolio ownership validation
   - Audit trails with created_at/updated_at

3. **API Security**:
   - CORS configuration
   - Rate limiting on external API calls
   - Bearer token validation

### 💾 Data Volume (Demo Environment)

- **Users**: 3 demo users
- **Portfolios**: 3 (HNW, Retail, Institutional)
- **Positions**: 63 total across portfolios
- **Market Data**: ~90 days historical for each symbol
- **Calculations**: Daily batch processing results

### 🚀 Performance Optimizations

1. **Database**:
   - UUID primary keys with indexes
   - Async SQLAlchemy 2.0 operations
   - Connection pooling
   - Optimized joins for complex queries

2. **Caching**:
   - Market data caching to reduce API calls
   - Factor ETF price caching
   - Calculation result persistence

3. **Batch Processing**:
   - Sequential engine execution
   - Graceful degradation on failures
   - Parallel position processing where possible

---

## Part III: Frontend Services Architecture

### Service Layer Overview
The frontend uses a layered service architecture to interact with the backend API. All API calls should go through the service layer rather than being made directly from components. Services are located in `/src/services/` and provide:
- Centralized API endpoint management
- Consistent error handling
- Request retry and deduplication
- Authentication token management
- Type-safe responses

### Frontend Services and API Endpoints

| Service | Purpose | API Endpoints Used | Used By |
|---------|---------|-------------------|----------|
| **apiClient.ts** | Base HTTP client with proxy support | All endpoints (infrastructure) | All services |
| **authManager.ts** | JWT token management & authentication | `/auth/login`, `/auth/me` | portfolioService, components |
| **portfolioService.ts** | Main portfolio data fetching | `/analytics/portfolio/{id}/overview`<br>`/data/positions/details`<br>`/analytics/portfolio/{id}/factor-exposures` | usePortfolioData hook |
| **portfolioResolver.ts** | Dynamic portfolio ID resolution | `/data/portfolios`<br>`/data/portfolio/{id}/complete` | portfolioService |
| **analyticsApi.ts** | Analytics & calculations | `/analytics/portfolio/{id}/overview`<br>`/analytics/portfolio/{id}/correlation-matrix`<br>`/analytics/portfolio/{id}/factor-exposures`<br>`/analytics/portfolio/{id}/stress-test` | Dashboard, Analytics pages |
| **portfolioApi.ts** | Portfolio CRUD operations | `/data/portfolios`<br>`/data/portfolio/{id}/complete`<br>`/data/portfolio/{id}/data-quality` | Portfolio management |
| **positionApiService.ts** | Position details & operations | `/data/positions/details` | Position components |
| **strategiesApi.ts** | Strategy management | `/strategies/`<br>`/data/portfolios/{id}/strategies`<br>`/strategies/combine`<br>`/strategies/detect/{id}` | StrategyList component |
| **tagsApi.ts** | Tag management | `/tags/`<br>`/tags/defaults`<br>`/tags/{id}/strategies` | TagEditor component |
| **chatService.ts** | Chat conversation management | `/chat/conversations`<br>`/chat/send`<br>`/chat/conversations/{id}/mode` | ChatInterface component |
| **chatAuthService.ts** | Chat auth & streaming | `/auth/login`<br>`/auth/logout`<br>`/auth/me`<br>`/chat/send` | Chat components |
| **requestManager.ts** | Request retry & deduplication | N/A (infrastructure) | All services |

### Service Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         Components/Pages                         │
│  (PortfolioPage, ChatInterface, StrategyList, TagEditor, etc.)  │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                          Custom Hooks                           │
│           (usePortfolioData, useFetchStreaming, etc.)          │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                        Service Layer                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│ │Feature APIs │ │   Auth       │ │    Infrastructure        │ │
│ │analyticsApi │ │authManager   │ │    apiClient             │ │
│ │portfolioApi │ │chatAuthService│ │    requestManager        │ │
│ │strategiesApi│ └──────────────┘ └──────────────────────────┘ │
│ │tagsApi      │                                                │
│ └──────────────┘                                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                     Next.js API Proxy                           │
│                    (/api/proxy/[...path])                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                    Backend API (FastAPI)                        │
│                    http://localhost:8000                        │
└─────────────────────────────────────────────────────────────────┘
```

### Centralized Configuration

The frontend uses centralized API configuration in `/src/config/api.ts`:

- **API_ENDPOINTS**: Organized mapping of all backend endpoints
- **REQUEST_CONFIGS**: Preset configurations for different operation types
  - STANDARD: Normal requests with caching
  - REALTIME: Short timeout, no caching
  - CALCULATION: Long timeout for complex operations
  - AUTH: Authentication-specific settings
- **API_CONFIG**: Environment-based settings (timeouts, retries, cache TTL)

### Service Usage Patterns

#### 1. Through Custom Hooks (Recommended)
```typescript
// usePortfolioData hook uses portfolioService internally
const { positions, publicPositions, optionsPositions } = usePortfolioData()
```

#### 2. Direct Service Usage in Components
```typescript
// Components import and use services directly
import strategiesApi from '@/services/strategiesApi'
const strategies = await strategiesApi.listByPortfolio({ portfolioId })
```

#### 3. Proxy Routing
All API calls route through Next.js proxy at `/api/proxy/` to handle CORS during development.

### Best Practices

1. **Always use services** - Don't make direct fetch() calls to backend
2. **Use appropriate service** - Each service has a specific domain responsibility
3. **Handle errors gracefully** - Services provide consistent error handling
4. **Leverage request manager** - Automatic retry and deduplication
5. **Type safety** - Services provide TypeScript interfaces for responses

---

## Recent Updates & Fixes



## Notes

- **Database Location**: PostgreSQL via Docker (`docker-compose up -d`)
- **Migrations**: Managed via Alembic (`uv run alembic upgrade head`)
- **Demo Data**: Pre-seeded with `scripts/seed_database.py`
- **Admin Endpoints**: Implemented but require manual router registration
- **Testing**: Frontend API test page at `/dev/api-test` validates all endpoints

