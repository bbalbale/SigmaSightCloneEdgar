# SigmaSight Backend API Reference V1.4.6

**Version**: 1.4.6  
**Date**: October 4, 2025  
**Status**: ✅ **PRODUCTION-READY** - Code-verified implemented endpoints  
**Purpose**: Reference documentation for all implemented API endpoints  

## Overview

This document provides comprehensive reference documentation for all **implemented and production-ready endpoints** in the SigmaSight Backend API. All endpoints have been **code-verified** to access database data through direct ORM queries or service layers and are ready for frontend integration.

### Namespace Organization
- **`/auth/`**: Authentication and user management
- **`/data/`**: Raw data endpoints optimized for LLM consumption
- **`/analytics/`**: Calculated metrics and derived analytics values
- **`/chat/`**: AI chat conversation management

### Key Design Principles
1. **Code-Verified**: All endpoints confirmed through direct code inspection
2. **Database-Backed**: Real data from PostgreSQL via SQLAlchemy ORM
3. **LLM-Optimized**: `/data/` endpoints return complete, denormalized datasets
4. **Self-Documenting**: Endpoint paths clearly convey data type and purpose

## ⚠️ Breaking Change (October 2025)

**Removed**: All `/api/v1/strategies/*` endpoints and strategy tables. The platform now uses **position-level tagging only**.

**Impact**:
- Multi-leg strategy containers and metrics are no longer supported
- SDKs or scripts calling `/strategies` routes must migrate to `/position-tags`
- `usage_count` and related analytics reflect direct position-tag assignments

**Migration Path**:
1. Use `/api/v1/position-tags` endpoints to assign tags directly to positions
2. Use `/api/v1/tags/{id}/positions` for reverse lookup instead of strategy queries
3. Remove any references to `strategy_id` columns or `Strategy*` models in integrations

---

# IMPLEMENTED ENDPOINTS ✅

This section documents all **fully implemented and production-ready endpoints** in the SigmaSight Backend API.

### Complete Endpoint List

**Total: 57 implemented endpoints** across 8 categories

Base prefix for all endpoints below: `/api/v1`

#### Authentication (5 endpoints)
- POST `/auth/login`
- POST `/auth/register`
- GET `/auth/me`
- POST `/auth/refresh`
- POST `/auth/logout`

#### Data (10 endpoints)
- GET `/data/portfolios`
- GET `/data/portfolio/{portfolio_id}/complete`
- GET `/data/portfolio/{portfolio_id}/data-quality`
- GET `/data/positions/details` (query: `portfolio_id` or `position_ids`)
- GET `/data/prices/historical/{portfolio_id}`
- GET `/data/prices/quotes` (query: `symbols`)
- GET `/data/factors/etf-prices` (query: `lookback_days`, `factors`)
- GET `/data/positions/top/{portfolio_id}` (query: `limit`, `sort_by`, `as_of_date`)
- GET `/data/test-demo`
- GET `/data/demo/{portfolio_type}` (no auth; demo only)

#### Analytics (7 endpoints)
- GET `/analytics/portfolio/{portfolio_id}/overview`
- GET `/analytics/portfolio/{portfolio_id}/correlation-matrix`
- GET `/analytics/portfolio/{portfolio_id}/diversification-score` ✨ **NEW**
- GET `/analytics/portfolio/{portfolio_id}/factor-exposures`
- GET `/analytics/portfolio/{portfolio_id}/positions/factor-exposures` (query: `limit`, `offset`, `symbols`)
- GET `/analytics/portfolio/{portfolio_id}/stress-test` (query: `scenarios`)
- GET `/analytics/portfolio/{portfolio_id}/risk-metrics` (deprecated; do not use)

#### Chat (6 endpoints)
- POST `/chat/conversations`
- GET `/chat/conversations/{conversation_id}`
- GET `/chat/conversations`
- PUT `/chat/conversations/{conversation_id}/mode`
- DELETE `/chat/conversations/{conversation_id}`
- POST `/chat/send` (SSE streaming; `text/event-stream`)

#### Target Prices (10 endpoints)
- POST `/target-prices/{portfolio_id}`
- GET `/target-prices/{portfolio_id}`
- GET `/target-prices/{portfolio_id}/summary`
- GET `/target-prices/target/{id}`
- PUT `/target-prices/target/{id}`
- DELETE `/target-prices/target/{id}`
- POST `/target-prices/{portfolio_id}/bulk`
- PUT `/target-prices/{portfolio_id}/bulk-update`
- POST `/target-prices/{portfolio_id}/import-csv`
- POST `/target-prices/{portfolio_id}/export`

#### Tag Management (8 endpoints) ✨ **NEW - October 2, 2025**
- POST `/tags/` - Create tag
- GET `/tags/` - List user tags
- GET `/tags/{id}` - Get tag details
- PATCH `/tags/{id}` - Update tag
- POST `/tags/{id}/archive` - Archive tag (soft delete)
- POST `/tags/{id}/restore` - Restore archived tag
- POST `/tags/defaults` - Create default tags (idempotent)
- GET `/tags/{id}/strategies` - Get strategies by tag (deprecated)

#### Position Tagging (5 endpoints) ✨ **NEW - October 2, 2025 - PREFERRED METHOD**
- POST `/positions/{id}/tags` - Add tags to position
- DELETE `/positions/{id}/tags` - Remove tags from position
- GET `/positions/{id}/tags` - Get position's tags
- PATCH `/positions/{id}/tags` - Replace all position tags
- GET `/tags/{id}/positions` - Get positions by tag (reverse lookup)

#### Admin Batch Processing (6 endpoints) ✨ **NEW - October 6, 2025**
- POST `/admin/batch/run` - Trigger batch processing with real-time tracking
- GET `/admin/batch/run/current` - Get current batch status (polling endpoint)
- POST `/admin/batch/trigger/market-data` - Manually trigger market data update
- POST `/admin/batch/trigger/correlations` - Manually trigger correlation calculations
- GET `/admin/batch/data-quality` - Get data quality status and metrics
- POST `/admin/batch/data-quality/refresh` - Refresh market data for quality improvement

#### Portfolio (removed in v1.2)
These placeholder endpoints were removed and are no longer exposed.
- (removed) GET `/portfolio/`
- (removed) POST `/portfolio/upload`
- (removed) GET `/portfolio/summary`

#### Positions (removed in v1.2)
These placeholder endpoints were removed and are no longer exposed.
- (removed) GET `/positions/`
- (removed) GET `/positions/{position_id}`
- (removed) PUT `/positions/{position_id}`

#### Risk (removed in v1.2)
These placeholder endpoints were removed and are no longer exposed.
- (removed) GET `/risk/metrics`
- (removed) GET `/risk/factors`
- (removed) GET `/risk/greeks`
- (removed) POST `/risk/greeks/calculate`

#### Modeling (removed in v1.2)
These placeholder endpoints were removed and are no longer exposed.
- (removed) GET `/modeling/sessions`
- (removed) POST `/modeling/sessions`
- (removed) GET `/modeling/sessions/{session_id}`

#### Administration (removed/deprecated endpoints)
Several admin batch endpoints were removed on October 6, 2025 in favor of the new real-time batch monitoring system. See Section D for currently implemented admin endpoints.

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
All data endpoints require JWT authentication via Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## B. Chat Endpoints (Implemented)

These endpoints power the conversational agent and server‑sent events (SSE) streaming. Frontend calls typically go through the Next.js proxy at `/api/proxy/...`, but the canonical backend paths are under `/api/v1/chat/...`.

### Chat Overview
- Base path: `/api/v1/chat`
- Auth: Required (Bearer token or HttpOnly cookie forwarded via proxy)
- SSE: `POST /chat/send` returns `text/event-stream`

### Create Conversation
**Endpoint**: `POST /chat/conversations`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/conversations.py`  
**Function**: `create_conversation()`  
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/conversations`  
Creates a new conversation, auto-resolving the user’s `portfolio_id` when not provided.

**Authentication**: Required (Bearer token or HttpOnly cookie via proxy)  
**OpenAPI Description**: "Create a new conversation for the current user"  
**Database Access**: Direct ORM via AsyncSession  
- Tables: `agent.conversations` (Conversation), `portfolios` (resolve portfolio_id)  
**Service Layer**: None (direct ORM in endpoint)  

**Purpose**: Establish a chat thread with portfolio context for subsequent messages.  
**Implementation Notes**: Saves conversation metadata including `portfolio_id`; logs creation with IDs.  

**Parameters**:  
- Body (ConversationCreate): `{ mode: "green|blue|indigo|violet", portfolio_id?: string }`  

**Response** (ConversationResponse):  
`{ id: "uuid", mode: "green", created_at: "ISO", provider: "openai", provider_thread_id: null }`

### Get Conversation
**Endpoint**: `GET /chat/conversations/{conversation_id}`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/conversations.py`  
**Function**: `get_conversation()`
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/conversations/{conversation_id}`  

**Authentication**: Required  
**Database Access**: Direct ORM (Conversation by id + user scope)  
**Service Layer**: None  
**Purpose**: Retrieve conversation metadata.  
**Parameters**: Path `conversation_id` (UUID)  
**Response**: ConversationResponse

### List Conversations
**Endpoint**: `GET /chat/conversations`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/conversations.py`  
**Function**: `list_conversations()`
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/conversations`  

**Authentication**: Required  
**Database Access**: Direct ORM (current user’s conversations)  
**Service Layer**: None  
**Purpose**: Paginated list for UI selector/history.  
**Parameters**: Query `limit` (int, default 10), `offset` (int, default 0)  
**Response**: `ConversationResponse[]`

### Change Conversation Mode
**Endpoint**: `PUT /chat/conversations/{conversation_id}/mode`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/conversations.py`  
**Function**: `change_conversation_mode()`
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/conversations/{conversation_id}/mode`  

**Authentication**: Required  
**Database Access**: Direct ORM (update Conversation)  
**Service Layer**: None  
**Purpose**: Switch agent mode (prompt/tooling flavor) mid-conversation.  
**Parameters**:  
- Path `conversation_id` (UUID)  
- Body (ModeChangeRequest): `{ mode: "green|blue|indigo|violet" }`  
**Response** (ModeChangeResponse): `{ id, previous_mode, new_mode, changed_at }`

### Delete Conversation
**Endpoint**: `DELETE /chat/conversations/{conversation_id}`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/conversations.py`  
**Function**: `delete_conversation()`
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/conversations/{conversation_id}`  

**Authentication**: Required  
**Database Access**: Direct ORM (delete Conversation; cascades messages)  
**Service Layer**: None  
**Purpose**: Remove conversation and associated messages.  
**Parameters**: Path `conversation_id` (UUID)  
**Response**: 204 No Content

### Send Message (SSE Streaming)
**Endpoint**: `POST /chat/send`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/chat/send.py`  
**Function**: `router.post('/chat/send')` (SSE via `StreamingResponse`)  
**Frontend Proxy Path**: `/api/proxy/api/v1/chat/send`  
**Response Type**: `text/event-stream`  
Streams standardized SSE events: `message_created`, `start`, `message` tokens, `done`, with error and heartbeat events. Frontend proxies this as `POST /api/proxy/api/v1/chat/send`.

**Authentication**: Required (Bearer or HttpOnly cookie)  
**Database Access**: Direct ORM (create ConversationMessage rows; update assistant message)  
**Service Layer**:  
- OpenAI: `app/agent/services/openai_service.py` (`openai_service`)  
- Portfolio data (optional context): `app/services/portfolio_data_service.py` (PortfolioDataService)  
**Purpose**: Stream model output and tool results as SSE for responsive chat UX.  
**Implementation Notes**: 
- Generates backend message IDs before streaming; emits `message_created` with both IDs  
- Retries with exponential backoff; can switch to fallback model before first token  
- Emits standardized `done` envelope with timing/metrics  
**Parameters**: Body (MessageSend): `{ conversation_id: UUID, text: string }`  
**Response (SSE events)**: `start`, `message` token deltas, `done` with final text and metrics; `error`/`heartbeat` as needed

---

## C. Market Data Endpoints (Implemented)

### Symbol Historical Prices
**Endpoint**: `GET /market-data/prices/{symbol}`  
**Status**: ✅ Fully Implemented  
Removed in v1.2: `backend/app/api/v1/market_data.py:get_price_data()`  
**Authentication**: Required (`Depends(get_current_user)`)  

**Data Access**:
- Service layer: `app/services/market_data_service.py` (class `MarketDataService`)
  - `get_cached_prices(db, symbols, target_date)`
    - ORM query on `app.models.market_data.MarketDataCache` (table: `market_data_cache`) via `SELECT` with `symbol IN` and `date <= target_date`
  - `update_market_data_cache(db, symbols, start_date, end_date)`
    - Inserts historical rows into `MarketDataCache` using `pg_insert ... ON CONFLICT DO NOTHING`, then `commit`
- Direct ORM in endpoint:
  - `SELECT MarketDataCache` WHERE `symbol == {symbol}`, `date BETWEEN start_date AND end_date`, `ORDER BY date DESC`; then maps rows to response

**Tables**: `market_data_cache` (model: `app.models.market_data.MarketDataCache`)

---

### Options Chain
**Endpoint**: `GET /market-data/options/{symbol}`  
**Status**: ✅ Fully Implemented  
Removed in v1.2: `backend/app/api/v1/market_data.py:get_options_chain()`  
**Authentication**: Required (`Depends(get_current_user)`)  

**Data Access**:
- Service layer: `app/services/market_data_service.py` (class `MarketDataService`)
  - `fetch_options_chain(symbol, expiration_date)`
    - Uses external provider Polygon.io:
      - `polygon_rate_limiter.acquire()` (from `app/services/rate_limiter.py`)
      - REST client: `MarketDataService.polygon_client` (`polygon.RESTClient`) calling `list_options_contracts(...)` and pagination via `_get_raw(next_url)`
    - No database access; returns parsed contracts list

**Tables**: none (external API only)

---

## A. Authentication Endpoints

### 1. Login
**Endpoint**: `POST /auth/login`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/auth.py`  
**Function**: `login()`  
**Authentication**: None required  
**OpenAPI Description**: "Authenticate user and return JWT token (in response body AND cookie)"  
**Database Access**: Direct ORM queries to `User` and `Portfolio` tables (lines 27-28, 53-55)  
**Service Layer**: Uses authentication utilities:
  - File: `app/core/auth.py`
  - Functions: `verify_password()` (line 16), `create_token_response()` (line 69)  

Authenticates a user and returns JWT token in both response body and HTTP-only cookie.

**Request Body**:
```json
{
  "email": "demo_hnw@sigmasight.com", 
  "password": "demo12345"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 2592000
}
```

### 2. Register
**Endpoint**: `POST /auth/register`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/auth.py`  
**Function**: `register()`  
**Authentication**: None required  
**OpenAPI Description**: "Register a new user (admin-only initially)"  
**Database Access**: Direct ORM queries - Creates `User` and `Portfolio` records (lines 107-124)  
**Service Layer**: Uses authentication utilities:
  - File: `app/core/auth.py`
  - Function: `get_password_hash()` (line 25)  

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "New User"
}
```

**Response**:
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "email": "newuser@example.com",
  "full_name": "New User",
  "is_active": true,
  "created_at": "2025-09-05T12:30:45Z"
}
```

### 3. Get Current User
**Endpoint**: `GET /auth/me`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/auth.py`  
**Function**: `get_current_user_info()`  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Get current authenticated user information"  
**Database Access**: Via JWT token validation in `get_current_user` dependency from `app/core/dependencies.py`  
**Service Layer**: Uses dependency injection:
  - File: `app/core/dependencies.py`
  - Function: `get_current_user()` dependency
  - Note: No direct DB queries in endpoint itself  

**Response**:
```json
{
  "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "email": "demo_hnw@sigmasight.com",
  "full_name": "Demo HNW User",
  "is_active": true,
  "created_at": "2025-08-08T12:00:00Z",
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e"
}
```  

### 4. Refresh Token
**Endpoint**: `POST /auth/refresh`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/auth.py`  
**Function**: `refresh_token()`  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Refresh JWT token (returns new token in body AND cookie)"  
**Database Access**: Direct ORM query to `Portfolio` table for consistent portfolio_id (lines 153-156)  
**Service Layer**: Uses authentication utilities:
  - File: `app/core/auth.py`
  - Function: `create_token_response()` (line 69)  

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 2592000
}
```

### 5. Logout
**Endpoint**: `POST /auth/logout`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/auth.py`  
**Function**: `logout()` (lines 186-206)  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Logout endpoint - clears auth cookie and instructs client to discard token"  
**Database Access**: None - only clears cookie  
**Service Layer**: None - cookie management only  

Clears the HTTP-only auth cookie and returns success message. Client should also discard any stored Bearer tokens.

**Response**:
```json
{
  "message": "Successfully logged out",
  "success": true
}
```

---

## B. Data Endpoints

### 6. Get Portfolios
**Endpoint**: `GET /data/portfolios`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/data.py`
**Function**: `get_user_portfolios()` (lines 34-81)
**Authentication**: Required
**OpenAPI Description**: "Get all portfolios for authenticated user"
**Database Access**: Direct ORM query to `Portfolio` table with `selectinload(Portfolio.positions)` (lines 47-52)
**Service Layer**: None - direct database access with manual calculation of total_value

Returns all portfolios for the authenticated user with real database data.

**Response** (Bare Array):
```json
[
  {
    "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
    "name": "Demo High Net Worth Investor Portfolio",
    "description": "HNW portfolio description",
    "currency": "USD",
    "created_at": "2025-08-08T12:00:00Z",
    "updated_at": "2025-09-05T10:00:00Z",
    "equity_balance": 1662126.38,
    "position_count": 21
  }
]
```

### 6. Get Complete Portfolio
**Endpoint**: `GET /data/portfolio/{portfolio_id}/complete`
**Status**: ✅ Fully Implemented (Simplified)
**File**: `app/api/v1/data.py`
**Function**: `get_portfolio_complete()` (lines 83-294)
**Authentication**: Required
**OpenAPI Description**: "Get complete portfolio data with optional sections"

**Implementation Notes**:
- **Simplified in-route implementation** - All logic built directly in endpoint
- No dedicated service layer orchestration
- Direct ORM queries for Portfolio and Position tables
- Basic aggregation and summarization
- Placeholder timeseries data (not historical)
- No attribution calculations or advanced analytics

**Database Access**: Direct ORM queries only
- `Portfolio` table for portfolio details
- `Position` table for position list
- `MarketDataCache` for current prices
- No service layer dependencies

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `sections` (query, optional): Comma-separated list of sections to include (currently not used)
- `as_of_date` (query, optional): Date for historical data (currently not implemented)

**Current Limitations**:
- Timeseries data is placeholder only
- No historical data support (as_of_date ignored)
- No cash/margin tracking
- No attribution analysis
- Simple position aggregation only

**Response** (Simplified Structure):
```json
{
  "portfolio": {
    "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
    "name": "Demo High Net Worth Investor Portfolio",
    "description": "Diversified portfolio with options strategies",
    "currency": "USD",
    "created_at": "2025-08-08T12:00:00Z",
    "updated_at": "2025-09-05T10:00:00Z"
  },
  "positions": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pnl": 1525.00,
      "cost_basis": 160.00
    }
  ],
  "summary": {
    "total_value": 1662126.38,
    "total_pnl": 125432.18,
    "positions_count": 21
  }
}
```

### 7. Get Data Quality
**Endpoint**: `GET /data/portfolio/{portfolio_id}/data-quality`
**Status**: ✅ Fully Implemented (Binary Check)
**File**: `app/api/v1/data.py`
**Function**: `get_data_quality()` (lines 295-379)
**Authentication**: Required
**OpenAPI Description**: "Get data quality metrics for portfolio"

**Implementation Notes**:
- **Binary heuristic check** - Simple pass/fail per position
- Checks if historical price data exists (150 days or 0 days)
- No overall quality scoring system
- No recommendations engine
- No detailed metric breakdowns

**Database Access**: Direct ORM queries
- `Position` table for position list
- `MarketDataCache` for price data availability check
- No service layer dependencies

**Parameters**:
- `portfolio_id` (path): Portfolio UUID

**Current Limitations**:
- No overall portfolio quality score (0-100)
- No completeness, recency, or accuracy metrics
- No specific recommendations
- No data provider coverage analysis
- Simple binary check only: has data or doesn't

**Response** (Simplified Structure):
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "positions": [
    {
      "position_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "has_price_data": true,
      "data_points": 150
    },
    {
      "position_id": "b2c3d4e5-f6g7-8901-bcde-fg2345678901",
      "symbol": "TSLA",
      "has_price_data": false,
      "data_points": 0
    }
  ]
}
```

### 8. Get Position Details
**Endpoint**: `GET /data/positions/details`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/data.py`
**Function**: `get_position_details()` (lines 433-626)
**Authentication**: Required
**OpenAPI Description**: "Get detailed position information with P&L calculations"
**Database Access**: Position, MarketDataCache tables
**Service Layer**: Direct ORM queries with P&L calculations

**Parameters**:
- `portfolio_id` (query): Portfolio UUID
- `position_type` (query, optional): Filter by position type
- `include_inactive` (query, optional): Include soft-deleted positions

**Response**:
```json
{
  "positions": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "cost_basis": 160.00,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pnl": 1525.00,
      "unrealized_pnl_percent": 9.53,
      "created_at": "2025-08-15T10:30:00Z",
      "updated_at": "2025-09-05T15:30:00Z"
    },
    {
      "id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
      "symbol": "SPY_240920C00550000",
      "position_type": "CALL",
      "quantity": 5.0,
      "cost_basis": 2.85,
      "current_price": 4.20,
      "market_value": 2100.00,
      "unrealized_pnl": 675.00,
      "unrealized_pnl_percent": 47.37,
      "created_at": "2025-08-20T14:15:00Z",
      "updated_at": "2025-09-05T15:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 21,
    "total_market_value": 1662126.38,
    "total_unrealized_pnl": 125432.18,
    "total_day_change": -8942.15,
    "long_positions": 15,
    "short_positions": 2,
    "options_positions": 4
  }
}
```

### 9. Get Historical Prices
**Endpoint**: `GET /data/prices/historical/{portfolio_id}`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/data.py`
**Function**: `get_historical_prices()` (lines 627-722)
**Authentication**: Required
**OpenAPI Description**: "Get historical price data for all symbols in portfolio"

**Database Access**: MarketDataCache table
**Service Layer**: Uses market data service:
  - File: `app/services/market_data_service.py`
  - Class: `MarketDataService`
  - Method: `get_historical_prices()`

**Parameters**:
- `portfolio_id` (path): Portfolio UUID (aggregates all portfolio symbols)
- `days` (query, optional): Number of days of history (default 30)
- `start_date` (query, optional): Start date (YYYY-MM-DD)
- `end_date` (query, optional): End date (YYYY-MM-DD)

**Response**:
```json
{
  "AAPL": [
    {
      "date": "2025-09-05",
      "open": 174.80,
      "high": 176.15,
      "low": 174.25,
      "close": 175.25,
      "volume": 58432100
    },
    {
      "date": "2025-09-04",
      "open": 173.50,
      "high": 175.20,
      "low": 173.10,
      "close": 174.65,
      "volume": 62145800
    }
  ],
  "MSFT": [
    {
      "date": "2025-09-05",
      "open": 424.50,
      "high": 426.80,
      "low": 423.90,
      "close": 425.18,
      "volume": 24785900
    }
  ]
}
```

### 10. Get Market Quotes
**Endpoint**: `GET /data/prices/quotes`
**Status**: ✅ Fully Implemented (Simulated Data)
**File**: `app/api/v1/data.py`
**Function**: `get_market_quotes()` (lines 732-807)
**Authentication**: Required
**OpenAPI Description**: "Get market quotes for symbols"

**⚠️ Implementation Notes**:
- **SIMULATED QUOTES ONLY** - Not real-time market data
- Bid/ask spreads are calculated (current_price ± 0.5%)
- All change fields return zero (no day change data)
- No 52-week high/low ranges
- No volume data
- Placeholder implementation for frontend development

**Database Access**: MarketDataCache table for current prices only
- No real-time market data integration
- No external API calls (Polygon/FMP)

**Parameters**:
- `symbols` (query): Comma-separated list of symbols

**Current Limitations**:
- Not real-time data
- No actual bid/ask from market
- No intraday statistics
- No market status indicators
- Simple price lookup with simulated spread

**Response** (Simulated Data):
```json
{
  "quotes": [
    {
      "symbol": "AAPL",
      "price": 175.25,
      "bid": 174.38,
      "ask": 176.13,
      "change": 0.00,
      "change_percent": 0.00,
      "timestamp": "2025-09-05T20:00:00Z"
    },
    {
      "symbol": "MSFT",
      "price": 425.18,
      "bid": 422.93,
      "ask": 427.43,
      "change": 0.00,
      "change_percent": 0.00,
      "timestamp": "2025-09-05T20:00:00Z"
    }
  ],
  "last_updated": "2025-09-05T20:00:00Z"
}
```

### 11. Get Factor ETF Prices
**Endpoint**: `GET /data/factors/etf-prices`
**Status**: ✅ Fully Implemented (Current Snapshots Only)
**File**: `app/api/v1/data.py`
**Function**: `get_factor_etf_prices()` (lines 813-875)
**Authentication**: Required
**OpenAPI Description**: "Get current prices for factor ETFs"

**Implementation Notes**:
- Returns **current snapshots only** (single point-in-time data)
- No historical price arrays
- Simplified map structure keyed by symbol

**Database Access**: MarketDataCache table
**Service Layer**: Uses market data service:
  - File: `app/services/market_data_service.py`
  - Class: `MarketDataService`
  - Method: `get_factor_etf_prices()`

**Parameters**:
- `lookback_days` (query, optional): Number of days (parameter accepted but not used for historical)
- `factors` (query, optional): Specific factor types to retrieve

**Response** (Current Snapshots Map):
```json
{
  "VTI": {
    "symbol": "VTI",
    "price": 268.45,
    "last_updated": "2025-09-05T20:00:00Z"
  },
  "VEA": {
    "symbol": "VEA",
    "price": 52.18,
    "last_updated": "2025-09-05T20:00:00Z"
  },
  "VWO": {
    "symbol": "VWO",
    "price": 45.32,
    "last_updated": "2025-09-05T20:00:00Z"
  }
}
```

---

## C. Analytics Endpoints

### 12. Portfolio Overview
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/overview`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/analytics/portfolio.py`  
**Function**: `get_portfolio_overview()` (lines 23-75)  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Get comprehensive portfolio overview with exposures, P&L, and position metrics"  
**Database Access**: Direct ORM queries to Portfolio, Position, and MarketDataCache tables  
**Service Layer**: `app/services/portfolio_analytics_service.py`
  - Class: `PortfolioAnalyticsService`
  - Method: `get_portfolio_overview()` (lines 26-86)
  - Uses async ORM queries with aggregations

**Purpose**: Portfolio aggregate metrics for dashboard cards (exposures, P&L, totals)
**Implementation Notes**:
- Direct ORM queries with in-route calculations (no caching)
- Returns calculated exposures (long/short/gross/net)
- Includes P&L metrics and portfolio totals
- **Note**: `realized_pnl` currently returns 0 (placeholder implementation)
- No service-level caching or batch data reuse
- **Frontend Integration**: Required for portfolio page aggregate cards at `http://localhost:3005/portfolio`

**Parameters**:
- `portfolio_id` (path): Portfolio UUID

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "total_value": 1250000.00,
  "cash_balance": 62500.00,
  "exposures": {
    "long_exposure": 1187500.00,
    "short_exposure": 0.00,
    "gross_exposure": 1187500.00,
    "net_exposure": 1187500.00,
    "long_percentage": 95.0,
    "short_percentage": 0.0,
    "gross_percentage": 95.0,
    "net_percentage": 95.0
  },
  "pnl": {
    "total_pnl": 125000.00,
    "unrealized_pnl": 87500.00,
    "realized_pnl": 37500.00
  },
  "position_count": {
    "total_positions": 21,
    "long_count": 21,
    "short_count": 0,
    "option_count": 0
  },
  "last_updated": "2025-09-05T10:30:00Z"
}
```

### 14. Correlation Matrix
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/correlation-matrix`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/analytics/portfolio.py`  
**Function**: `get_correlation_matrix()` (lines 80-147)  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Get the correlation matrix for portfolio positions"  
**Database Access**: ORM queries to CorrelationCalculation, PairwiseCorrelation, and Position tables  
**Service Layer**: `app/services/correlation_service.py`
  - Class: `CorrelationService`
  - Method: `get_matrix()` (lines 652-773)
  - Retrieves pre-calculated correlations from batch processing

**Purpose**: Returns pairwise correlations between all positions in the portfolio  
**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `lookback_days` (query, optional): Lookback period in days (30-365, default: 90)
- `min_overlap` (query, optional): Minimum overlapping data points (10-365, default: 30)

**Response Schema**: `CorrelationMatrixResponse`
```json
{
  "available": true,
  "data": {
    "matrix": {
      "AAPL": {
        "AAPL": 1.0,
        "MSFT": 0.75,
        "GOOGL": 0.62
      },
      "MSFT": {
        "AAPL": 0.75,
        "MSFT": 1.0,
        "GOOGL": 0.58
      }
    },
    "average_correlation": 0.65
  },
  "metadata": {
    "calculation_date": "2025-09-07T00:00:00",
    "lookback_days": 90,
    "positions_included": 15
  }
}
```

**Implementation Notes**: 
- Returns pre-calculated correlations from nightly batch processing

### 15. Portfolio Factor Exposures
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/factor-exposures`  
**Status**: ✅ Implemented  
**File**: `app/api/v1/analytics/portfolio.py`  
**Function**: `get_portfolio_factor_exposures()` (lines 202–232)  

**Authentication**: Required (Bearer token)  
**Database Access**: Read-only via service layer  
**Service Layer**: `app/services/factor_exposure_service.py`
  - Class: `FactorExposureService`
  - Method: `get_portfolio_exposures(portfolio_id)` (lines 52-143)
  - Reads: `factor_exposures` joined with `factor_definitions`
  - Returns available factors only (not enforcing complete set)
  - Reports completeness in metadata

**Purpose**: Return portfolio-level factor betas (and optional dollar exposures) from available factors for dashboards and reports.
**Missing Data Contract**: `200 OK` with `{ available:false, reason:"no_calculation_available" }`  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID

**Response Schema**: `PortfolioFactorExposuresResponse`
```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "calculation_date": "2025-09-05",
  "factors": [
    { "name": "Market Beta",     "beta": 0.72,  "exposure_dollar": 900000.0 },
    { "name": "Size",             "beta": 0.74,  "exposure_dollar": 925000.0 },
    { "name": "Value",            "beta": -0.15, "exposure_dollar": -187500.0 },
    { "name": "Momentum",         "beta": 0.22,  "exposure_dollar": 275000.0 },
    { "name": "Quality",          "beta": 0.82,  "exposure_dollar": 1025000.0 },
    { "name": "Low Volatility",   "beta": 0.90,  "exposure_dollar": 1125000.0 },
    { "name": "Growth",           "beta": 0.67,  "exposure_dollar": 837500.0 }
  ],
  "metadata": { "factor_model": "7-factor", "calculation_method": "ETF-proxy regression" }
}
```

### 16. Position Factor Exposures
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/positions/factor-exposures`
**Status**: ✅ Implemented
**File**: `app/api/v1/analytics/portfolio.py`
**Function**: `list_position_factor_exposures()` (lines 235–271)

**Authentication**: Required (Bearer token)
**Database Access**: Read-only via service layer
**Service Layer**: `app/services/factor_exposure_service.py`
  - Method: `list_position_exposures(portfolio_id, limit, offset, symbols=None)`
  - Reads: `position_factor_exposures` joined with `positions` and `factor_definitions`
  - Uses latest available anchor `calculation_date` for the portfolio; paginates by positions

**Purpose**: Return per-position factor betas for the latest anchor date to power position-level analytics tables.
**Missing Data Contract**: `200 OK` with `{ available:false, reason:"no_calculation_available" }`

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `limit` (query, default 50, max 200)
- `offset` (query, default 0)
- `symbols` (query, optional CSV)

**Response Schema**: `PositionFactorExposuresResponse`
```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "calculation_date": "2025-09-05",
  "total": 120,
  "limit": 50,
  "offset": 0,
  "positions": [
    {
      "position_id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
      "symbol": "AAPL",
      "exposures": {
        "Market Beta": 0.95,
        "Size": 0.10,
        "Value": -0.12,
        "Momentum": 0.18,
        "Quality": 0.22,
        "Low Volatility": 0.30,
        "Growth": 0.40
      }
    },
    {
      "position_id": "77dc7c6c-3b8e-41a2-9b9e-c2f0f8b3a111",
      "symbol": "MSFT",
      "exposures": {
        "Market Beta": 0.82,
        "Size": 0.05,
        "Value": 0.05,
        "Momentum": 0.21,
        "Quality": 0.35,
        "Low Volatility": 0.28,
        "Growth": 0.32
      }
    }
  ]
}
```
- Matrix is ordered by position weight (gross market value)
- Returns `available: false` if no calculation exists for the requested parameters
- Self-correlations are always 1.0

---

### 17. Portfolio Diversification Score
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/diversification-score`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/analytics/portfolio.py`
**Function**: `get_diversification_score()` (lines 166–202)

**Authentication**: Required (Bearer token)
**Database Access**: Read-only via service layer
**Service Layer**: `app/services/correlation_service.py`
  - Class: `CorrelationService`
  - Method: `get_weighted_correlation(portfolio_id, lookback_days, min_overlap)`
  - Reads: `correlation_calculation` and `pairwise_correlations` tables
  - Computes weighted absolute portfolio correlation (0–1) using position weights

**Purpose**: Calculate portfolio diversification using weighted correlation analysis. Returns a single diversification score (0-1) where higher values indicate more diversification.
**Missing Data Contract**: `200 OK` with `{ available:false, reason:"no_calculation_available" }`

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `lookback_days` (query, default 90, range 30-365): Lookback period for correlation calculation
- `min_overlap` (query, default 30, range 10-365): Minimum overlapping data points required

**Response Schema**: `DiversificationScoreResponse` (from `app/schemas/analytics.py:73-114`)
```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "portfolio_correlation": 0.28,
  "calculation_date": "2025-09-05",
  "duration_days": 90,
  "positions_analyzed": 15,
  "metadata": {
    "min_overlap": 30,
    "data_quality": "high"
  }
}
```

**Implementation Notes**:
- Uses pre-calculated correlations from nightly batch processing
- Score calculation: `1 - weighted_absolute_correlation`
- Weights based on position market values
- Target response time: <300ms
- Returns `available: false` if no correlation data exists

---

### 18. Portfolio Stress Test
```http
GET /api/v1/analytics/portfolio/{portfolio_id}/stress-test
```

**Purpose**: Return precomputed stress testing results across ~15 scenarios using correlated impacts.  
**Status**: ✅ Implemented (read-only; no recomputation)

**Parameters**:
- `scenarios` (query, optional CSV): Filter by scenario IDs

**Response (v1)**:
```json
{
  "available": true,
  "data": {
    "scenarios": [
      {
        "id": "market_down_10",
        "name": "Market Down 10%",
        "description": "S&P 500 falls 10%",
        "category": "market",
        "impact_type": "correlated",
        "impact": {
          "dollar_impact": -48500.0,
          "percentage_impact": -10.0,
          "new_portfolio_value": 436500.0
        },
        "severity": "moderate"
      }
    ],
    "portfolio_value": 485000.0,
    "calculation_date": "2025-09-05"
  },
  "metadata": {
    "scenarios_requested": ["market_down_10"]
  }
}
```

**Implementation Notes**:
- Read `StressTestResult` (use `correlated_pnl`) joined with `StressTestScenario`
- Baseline `portfolio_value` from `PortfolioSnapshot.total_value` on/<= anchor date
- No recomputation in v1; if no snapshot or no results, return `available=false`
- Anchor selection: if `scenarios` filter is provided, use the latest calculation_date among the filtered subset; otherwise use latest overall
- Sorting: stable by `category` (ASC), then `name` (ASC)
- `percentage_impact` reported in percentage points (e.g., -10.0 means -10%)
- `calculation_date` is date-only (YYYY-MM-DD)
- `metadata.scenarios_requested` is included only when filter param is provided
- Reason precedence: if no results → `no_results`; if results but no snapshot → `no_snapshot`

**File/Function**: `app/api/v1/analytics/portfolio.py:get_stress_test_results()` (lines 273-311)  
**Service Layer**: `app/services/stress_test_service.py:StressTestService.get_portfolio_results(...)`

**cURL Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)
PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq -r .portfolio_id)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/stress-test" | jq
```

**Missing Data Contract**:
- `200 OK` with `{ "available": false, "reason": "no_results|no_snapshot" }`

---


## D. Administration Endpoints

### Overview
These endpoints provide administrative control over batch processing operations, including triggering batch runs, monitoring progress in real-time, and assessing data quality. All endpoints require admin authentication.

**Base Path**: `/api/v1/admin/batch`
**Authentication**: Required (Admin users only)
**Status**: ✅ **Fully Implemented and Registered** (as of October 6, 2025)
**Router File**: `app/api/v1/endpoints/admin_batch.py`

### Recent Changes (October 6, 2025)
- ✅ **Added**: Real-time batch monitoring with polling support
- ✅ **Added**: New batch trigger endpoint with concurrent run prevention
- ❌ **Removed**: Deprecated scheduler control endpoints
- ❌ **Removed**: Old job history/summary endpoints (BatchJob table not used)

---

### 19. Trigger Batch Processing
**Endpoint**: `POST /admin/batch/run`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `run_batch_processing()` (lines 23-71)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Trigger batch processing with real-time tracking"
**Database Access**: None (uses in-memory tracker)
**Service Layer**: `batch_orchestrator_v2.run_daily_batch_sequence()`

**Purpose**: Triggers batch calculation processing for all portfolios or a specific portfolio. Returns a `batch_run_id` for real-time progress monitoring via polling.

**Concurrent Run Prevention**: Returns 409 Conflict if a batch is already running, unless `force=true` is specified.

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio UUID or omit for all portfolios
- `force` (query, optional): Set to `true` to force run even if batch already running (default: `false`)

**Response** (200 OK):
```json
{
  "status": "started",
  "batch_run_id": "84728a8c-f7ac-4c72-a7cb-8cdb212198c4",
  "portfolio_id": "all",
  "triggered_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T13:28:00Z",
  "poll_url": "/api/v1/admin/batch/run/current"
}
```

**Response** (409 Conflict - Batch Already Running):
```json
{
  "detail": "Batch already running. Use force=true to override."
}
```

**Usage Notes**:
- Poll `/admin/batch/run/current` every 2-5 seconds to monitor progress
- Use `force=true` query parameter to override concurrent run prevention (not recommended)
- Batch runs execute 8 calculation engines sequentially per portfolio
- Background execution via FastAPI BackgroundTasks

---

### 20. Get Current Batch Status
**Endpoint**: `GET /admin/batch/run/current`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `get_current_batch_status()` (lines 74-115)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Get status of currently running batch process"
**Database Access**: None (uses in-memory tracker)
**Service Layer**: `batch_run_tracker.get_current()`

**Purpose**: Real-time status polling endpoint for monitoring batch progress. Returns "idle" if no batch is running, or detailed progress information if batch is active.

**Polling Recommendation**: Poll every 2-5 seconds for real-time updates.

**Parameters**: None

**Response** (200 OK - Running):
```json
{
  "status": "running",
  "batch_run_id": "84728a8c-f7ac-4c72-a7cb-8cdb212198c4",
  "started_at": "2025-10-06T13:28:00Z",
  "elapsed_seconds": 135.2,
  "triggered_by": "admin@sigmasight.com",
  "jobs": {
    "total": 8,
    "completed": 3,
    "failed": 0,
    "pending": 5
  },
  "current_job": "position_factor_analysis_c0510ab8...",
  "current_portfolio": "Demo High Net Worth Portfolio",
  "progress_percent": 37.5
}
```

**Response** (200 OK - Idle):
```json
{
  "status": "idle",
  "batch_run_id": null,
  "message": "No batch processing currently running"
}
```

**Usage Notes**:
- Designed for frontend progress bars and real-time dashboards
- Lightweight in-memory tracking (no database overhead)
- Progress percentage calculated from completed/total jobs
- Current job name truncated for display

---

### 21. Trigger Market Data Update
**Endpoint**: `POST /admin/batch/trigger/market-data`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `trigger_market_data_update()` (lines 118-138)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Manually trigger market data update for all symbols"
**Database Access**: Via market data sync service
**Service Layer**: `app.batch.market_data_sync.sync_market_data()`

**Purpose**: Manually triggers market data synchronization from external providers (FMP, Polygon, yfinance) for all active position symbols.

**Parameters**: None

**Response** (200 OK):
```json
{
  "status": "started",
  "message": "Market data update started",
  "triggered_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T14:30:00Z"
}
```

**Usage Notes**:
- Runs in background via FastAPI BackgroundTasks
- Syncs data for all symbols in active positions
- No waiting for completion (fire-and-forget)
- Typically takes 30-60 seconds depending on symbol count

---

### 22. Trigger Correlation Calculation
**Endpoint**: `POST /admin/batch/trigger/correlations`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `trigger_correlation_calculation()` (lines 141-164)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Manually trigger correlation calculations"
**Database Access**: Via batch orchestrator
**Service Layer**: `batch_orchestrator_v2.run_daily_batch_sequence(run_correlations=True)`

**Purpose**: Manually triggers position correlation calculations (normally runs weekly on Tuesday).

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio UUID or omit for all portfolios

**Response** (200 OK):
```json
{
  "status": "started",
  "message": "Correlation calculation started for all portfolios",
  "triggered_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T14:35:00Z"
}
```

**Usage Notes**:
- Runs full batch sequence with correlations enabled
- Computationally intensive for large portfolios
- Results saved to `correlation_calculations` and `pairwise_correlations` tables

---

### 23. Get Data Quality Status
**Endpoint**: `GET /admin/batch/data-quality`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `get_data_quality_status()` (lines 167-199)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Get data quality status and metrics for portfolios"
**Database Access**: Portfolio, Position, MarketDataCache tables
**Service Layer**: `app.batch.data_quality.pre_flight_validation()`

**Purpose**: Provides pre-flight validation results showing data completeness and quality scores without running batch processing.

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio UUID or omit for all portfolios

**Response** (200 OK):
```json
{
  "quality_score": 0.85,
  "portfolios_assessed": 3,
  "total_positions": 63,
  "coverage_details": {
    "current_prices": {
      "total_positions": 63,
      "positions_with_prices": 63,
      "missing_prices": 0,
      "coverage_percentage": 1.0
    },
    "historical_data": {
      "total_positions": 63,
      "positions_with_data": 29,
      "sufficient_depth": 0,
      "coverage_percentage": 0.0,
      "depth_requirement": "90+ days for factor analysis"
    }
  },
  "issues": [
    "Insufficient historical data depth (need 90+ days, have 21 days avg)"
  ],
  "recommendations": [
    "Backfill historical market data to at least 90 days",
    "Current price coverage is excellent (100%)"
  ],
  "requested_by": "admin@sigmasight.com",
  "request_timestamp": "2025-10-06T14:40:00Z"
}
```

**Usage Notes**:
- Does not modify any data
- Fast read-only assessment
- Quality score ranges from 0.0 to 1.0 (0% to 100%)
- Use before running batch to identify data gaps

---

### 24. Refresh Market Data for Quality
**Endpoint**: `POST /admin/batch/data-quality/refresh`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/endpoints/admin_batch.py`
**Function**: `refresh_market_data_for_quality()` (lines 202-246)
**Authentication**: Required (Admin)
**OpenAPI Description**: "Refresh market data to improve data quality scores"
**Database Access**: Via pre_flight_validation and batch orchestrator
**Service Layer**: `batch_orchestrator_v2._update_market_data()`

**Purpose**: Triggers targeted market data refresh based on data quality assessment recommendations.

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio UUID or omit for all portfolios

**Response** (200 OK - Refresh Started):
```json
{
  "status": "refresh_started",
  "message": "Market data refresh started to improve data quality",
  "current_quality_score": 0.85,
  "recommendations": [
    "Backfill historical market data to at least 90 days",
    "Update stale price data for 3 positions",
    "Sync missing company profiles"
  ],
  "requested_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T14:45:00Z"
}
```

**Response** (200 OK - No Action Needed):
```json
{
  "status": "no_action_needed",
  "message": "Data quality is already within acceptable thresholds",
  "current_quality_score": 0.95,
  "requested_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T14:45:00Z"
}
```

**Usage Notes**:
- Runs in background via FastAPI BackgroundTasks
- Only refreshes if quality score below thresholds
- Intelligent targeting based on pre-flight validation
- Shows top 3 recommendations for transparency

---

### Removed Endpoints (October 6, 2025)

The following endpoints were **removed** and are no longer available:

- ❌ `POST /admin/batch/scheduler/start` - Removed (scheduler control deprecated)
- ❌ `POST /admin/batch/scheduler/stop` - Removed (scheduler control deprecated)
- ❌ `POST /admin/batch/scheduler/pause` - Removed (scheduler control deprecated)
- ❌ `POST /admin/batch/scheduler/resume` - Removed (scheduler control deprecated)
- ❌ `GET /admin/batch/jobs/status` - Removed (BatchJob table not used)
- ❌ `GET /admin/batch/jobs/summary` - Removed (BatchJob table not used)
- ❌ `DELETE /admin/batch/jobs/{job_id}/cancel` - Removed (BatchJob table not used)
- ❌ `POST /admin/batch/trigger/factors` - Removed (use POST /admin/batch/run instead)

**Migration Path**:
- For batch control: Use `POST /admin/batch/run` with optional `portfolio_id`
- For monitoring: Poll `GET /admin/batch/run/current` for real-time status
- For targeted operations: Use `POST /admin/batch/trigger/market-data` or `POST /admin/batch/trigger/correlations`

---


## E. Target Prices Endpoints

These endpoints manage portfolio-specific target prices for securities, enabling different price targets per portfolio with comprehensive pricing intelligence, risk analysis, and scenario modeling.

### Base Information
- **Base Path**: `/api/v1/target-prices`
- **Authentication**: Required (Bearer token)
- **Database**: `portfolio_target_prices` table via TargetPrice model
- **Service Layer**: Full service-layer implementation with price resolution, equity-based weighting, and risk calculations
- **Serialization**: Numeric values are serialized as JSON numbers; Decimal fields converted to floats via Pydantic encoders
- **Features**: Smart price resolution, equity-based position weights, options support, bulk operations, CSV import/export

### Implementation Features (Phase 1 & 2 Complete)
- **Smart Price Resolution**: Automatic price lookup from market data with investment class detection (PUBLIC/OPTIONS/PRIVATE)
- **Equity-Based Weighting**: Position weights calculated using `equity_balance` for accurate portfolio analysis
- **Options Support**: Automatic underlying symbol resolution for LC/LP/SC/SP positions with proper volatility calculations
- **Risk Contributions**: Formula: `risk_contribution = position_weight × volatility × beta`
- **Performance Optimized**: SQL-level filtering, bulk operation indexing, stale data detection
- **Breaking Changes Applied**: Removed deprecated fields, standardized response formats

### Price Source Behavior
**PUBLIC/OPTIONS Securities:**
- Primary: Latest from MarketDataCache (with staleness detection)
- Fallback: Live MarketDataService API call
- Final Fallback: User-provided `current_price` parameter

**PRIVATE Investments:**
- Requires user-provided `current_price` (rejects request if missing)
- No market data lookup attempted

**Options Handling:**
- Price resolution uses underlying symbol when position linked
- Volatility calculation uses underlying symbol for accurate risk metrics

### 23. Create Target Price

**Endpoint**: `POST /target-prices/{portfolio_id}`  
**Status**: ✅ Fully Implemented with Price Resolution  
**File**: `app/api/v1/target_prices.py` → `create_target_price()`  
**Service**: `TargetPriceService.create_target_price()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Create a new target price for a portfolio position"  
**OpenAPI Description**: "Creates a portfolio-specific target price with smart price resolution, automatic position linking, and investment class detection. Supports equity and options positions with automatic underlying symbol resolution for accurate pricing."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Request Body** (TargetPriceCreate):
```json
{
  "symbol": "AAPL",
  "position_type": "LONG",
  "position_id": "uuid-optional",
  "target_price_eoy": 200.00,
  "target_price_next_year": 220.00,
  "downside_target_price": 150.00,
  "current_price": 180.00
}
```

**Request Schema Notes**:
- `symbol` (required): Security symbol (equity or options contract)
- `position_type` (optional): LONG, SHORT, LC, LP, SC, SP (defaults to LONG)
- `position_id` (optional): Direct position link; if not provided, service resolves automatically
- `current_price` (required): Used as fallback if market data unavailable
- **Removed fields**: `analyst_notes`, `data_source`, `current_implied_vol` (Phase 2 breaking changes)

**Service Layer Features**:
- **Position Resolution**: Automatic position lookup by symbol if `position_id` not provided
- **Price Resolution Contract**: Market data → Live API → User provided (with staleness detection)
- **Investment Class Detection**: PUBLIC/OPTIONS/PRIVATE classification
- **Options Handling**: Automatic underlying symbol resolution for options positions
- **Position Metrics**: Equity-based weight calculation and risk contribution analysis

**Response** (TargetPriceResponse):
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "position_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "symbol": "AAPL",
  "position_type": "LONG",
  "target_price_eoy": 200.00,
  "target_price_next_year": 220.00,
  "downside_target_price": 150.00,
  "current_price": 180.00,
  "expected_return_eoy": 11.11,
  "expected_return_next_year": 22.22,
  "downside_return": -16.67,
  "position_weight": 5.25,
  "contribution_to_portfolio_return": 0.58,
  "contribution_to_portfolio_risk": 0.42,
  "price_updated_at": "2025-09-18T10:30:00Z",
  "created_by": "user-uuid",
  "created_at": "2025-09-18T10:30:00Z",
  "updated_at": "2025-09-18T10:30:00Z"
}
```

**Response Notes**:
- `contribution_to_portfolio_risk`: May be null if beta, volatility, or position weight unavailable
- `position_weight`: Returned as percentage (0-100) for API compatibility
- All calculated fields depend on successful price resolution and position linking

### 24. Get Portfolio Target Prices

**Endpoint**: `GET /target-prices/{portfolio_id}`  
**Status**: ✅ Fully Implemented with SQL Filtering  
**File**: `app/api/v1/target_prices.py` → `get_portfolio_target_prices()`  
**Service**: `TargetPriceService.get_portfolio_target_prices()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Get all target prices for a portfolio with optional filtering"  
**OpenAPI Description**: "Returns all target prices for a portfolio with optional server-side filtering by symbol or position type. Filtering is applied at the SQL level for optimal performance."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID
- `symbol` (query, optional): Filter by specific symbol (case-insensitive)
- `position_type` (query, optional): Filter by position type (LONG, SHORT, LC, LP, SC, SP)

**Service Layer Features**:
- **SQL-Level Filtering**: Filters applied in database query for performance
- **Portfolio Ownership**: Automatic verification of user portfolio access
- **Efficient Queries**: Indexed lookups with optimized joins
- **Sorting**: Results ordered by symbol (ascending)
- **No Pagination**: Returns all matching records (pagination planned for future)

**Response**: Array of TargetPriceResponse objects (same schema as create response, with nullability notes above)

### 25. Get Portfolio Target Price Summary

**Endpoint**: `GET /target-prices/{portfolio_id}/summary`  
**Status**: ✅ Fully Implemented with Equity-Based Weighting  
**File**: `app/api/v1/target_prices.py` → `get_portfolio_target_summary()`  
**Service**: `TargetPriceService.get_portfolio_summary()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Get portfolio target price summary with aggregated metrics"  
**OpenAPI Description**: "Returns comprehensive portfolio-level target price analytics including coverage statistics, equity-weighted returns, and risk-adjusted metrics. Uses portfolio equity_balance for accurate weighting calculations."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Service Layer Features**:
- **Equity-Based Weighting**: Uses `portfolio.equity_balance` for position weight calculations
- **Risk-Adjusted Metrics**: Sharpe and Sortino ratios based on target return distributions
- **Coverage Analysis**: Percentage of positions with target prices
- **Graceful Degradation**: Returns null for weighted metrics when equity_balance unavailable

**Response** (PortfolioTargetPriceSummary):
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "portfolio_name": "Growth Portfolio",
  "total_positions": 25,
  "positions_with_targets": 18,
  "coverage_percentage": 72.0,
  "weighted_expected_return_eoy": 12.5,
  "weighted_expected_return_next_year": 18.3,
  "weighted_downside_return": -8.2,
  "expected_sharpe_ratio": 1.25,
  "expected_sortino_ratio": 1.68,
  "target_prices": [
    {
      "id": "uuid",
      "symbol": "AAPL",
      "target_price_eoy": 200.00,
      "expected_return_eoy": 11.11
    }
  ],
  "last_updated": "2025-09-18T10:30:00Z"
}
```

### 26. Get Target Price by ID

**Endpoint**: `GET /target-prices/target/{target_price_id}`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/target_prices.py` → `get_target_price()`  
**Service**: `TargetPriceService.get_target_price()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Get a specific target price by ID"  
**OpenAPI Description**: "Retrieves a single target price record with portfolio ownership verification and complete calculated metrics."

**Parameters**:
- `target_price_id` (path, required): Target price UUID

**Response**: TargetPriceResponse (same schema as create response)

### 27. Update Target Price

**Endpoint**: `PUT /target-prices/target/{target_price_id}`  
**Status**: ✅ Fully Implemented with Price Resolution  
**File**: `app/api/v1/target_prices.py` → `update_target_price()`  
**Service**: `TargetPriceService.update_target_price()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Update an existing target price"  
**OpenAPI Description**: "Updates target price fields with automatic recalculation of expected returns and position metrics. Includes smart price resolution for current_price updates."

**Parameters**:
- `target_price_id` (path, required): Target price UUID

**Request Body** (TargetPriceUpdate):
```json
{
  "target_price_eoy": 210.00,
  "target_price_next_year": 235.00,
  "downside_target_price": 160.00,
  "current_price": 185.00
}
```

**Service Layer Features**:
- **Selective Updates**: Only provided fields are updated
- **Automatic Recalculation**: Expected returns recalculated with resolved prices
- **Price Resolution**: When `current_price` updated, applies same resolution logic as create
- **Position Metrics**: Recalculates weights and risk contributions when position linked

**Response**: TargetPriceResponse with updated values

### 28. Delete Target Price

**Endpoint**: `DELETE /target-prices/target/{target_price_id}`  
**Status**: ✅ Fully Implemented with Standardized Response  
**File**: `app/api/v1/target_prices.py` → `delete_target_price()`  
**Service**: `TargetPriceService.delete_target_price()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Delete a target price"  
**OpenAPI Description**: "Permanently removes a target price record with portfolio ownership verification. Returns standardized deletion result."

**Parameters**:
- `target_price_id` (path, required): Target price UUID

**Response** (TargetPriceDeleteResponse - Phase 2 Standardization):
```json
{
  "deleted": 1,
  "errors": []
}
```

**Response Notes**:
- `deleted`: Number of records deleted (0 or 1)
- `errors`: Array of error messages (empty on success)
- **Breaking Change**: Updated from `{"message": "Target price deleted successfully"}` in Phase 2

### 29. Bulk Create Target Prices

**Endpoint**: `POST /target-prices/{portfolio_id}/bulk`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/target_prices.py` → `bulk_create_target_prices()`  
**Service**: `TargetPriceService.bulk_create_target_prices()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Create multiple target prices at once"  
**OpenAPI Description**: "Creates multiple target prices in a single operation with automatic duplicate handling. Skips existing symbol/position_type combinations and applies price resolution to each record."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Request Body** (TargetPriceBulkCreate):
```json
{
  "target_prices": [
    {
      "symbol": "AAPL",
      "position_type": "LONG",
      "target_price_eoy": 200.00,
      "current_price": 180.00
    },
    {
      "symbol": "MSFT",
      "position_type": "LONG",
      "target_price_eoy": 450.00,
      "current_price": 425.00
    }
  ]
}
```

**Service Layer Features**:
- **Duplicate Handling**: Skips existing symbol/position_type combinations
- **Individual Processing**: Each target price gets full price resolution and position linking
- **Error Resilience**: Continues processing even if individual records fail

**Response**: Array of TargetPriceResponse objects for successfully created records

### 30. Bulk Update Target Prices

**Endpoint**: `PUT /target-prices/{portfolio_id}/bulk-update`
**Status**: ✅ Fully Implemented with Performance Optimization
**File**: `app/api/v1/target_prices.py` → `bulk_update_target_prices()` (lines 278-319)
**Optimization**: Route-level in-memory indexing for O(1) lookups
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Bulk update target prices by symbol"
**OpenAPI Description**: "Updates multiple target prices by symbol and position type with route-level optimization and comprehensive error tracking. Uses in-route indexed lookups for efficient bulk operations."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Request Body** (TargetPriceBulkUpdate):
```json
{
  "updates": [
    {
      "symbol": "AAPL",
      "position_type": "LONG",
      "target_price_eoy": 210.00,
      "current_price": 185.00
    },
    {
      "symbol": "MSFT",
      "position_type": "LONG",
      "target_price_next_year": 475.00
    }
  ]
}
```

**Performance Features (Phase 1 Optimization)**:
- **O(1) Lookups**: Pre-indexes target prices by (symbol, position_type) for fast updates
- **Single Query**: Fetches all portfolio target prices once instead of per-update
- **Error Tracking**: Detailed error reporting for failed updates

**Response**:
```json
{
  "updated": 2,
  "errors": []
}
```

### 31. Import Target Prices from CSV

**Endpoint**: `POST /target-prices/{portfolio_id}/import-csv`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/target_prices.py` → `import_target_prices_csv()`  
**Service**: `TargetPriceService.import_from_csv()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Import target prices from CSV format"  
**OpenAPI Description**: "Imports target prices from CSV with configurable update behavior. Supports standard CSV format with comprehensive validation and error reporting."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Request Body** (TargetPriceImportCSV):
```json
{
  "csv_content": "symbol,position_type,target_eoy,target_next_year,downside,current_price\nAAPL,LONG,200,220,150,180\nMSFT,LONG,400,450,350,375",
  "update_existing": false
}
```

**CSV Format Requirements**:
- **Required headers**: `symbol,position_type,target_eoy,target_next_year,downside,current_price`
- **Position types**: LONG, SHORT, LC, LP, SC, SP
- **Validation**: Automatic data type validation and error reporting

**Service Layer Features**:
- **Configurable Behavior**: `update_existing` controls handling of duplicates
- **Full Validation**: CSV parsing with comprehensive error messages
- **Price Resolution**: Each imported record gets same price resolution as manual creation

**Response**:
```json
{
  "created": 15,
  "updated": 3,
  "total": 18,
  "errors": ["Row 8: Invalid position_type 'INVALID'"]
}
```

**Response Schema Notes**:
- `created`: Number of new target prices created
- `updated`: Number of existing target prices updated (when update_existing=true)
- `total`: Total records processed successfully (created + updated)
- `errors`: Array of error messages for failed rows

### 32. Export Target Prices

**Endpoint**: `POST /target-prices/{portfolio_id}/export`  
**Status**: ✅ Fully Implemented with Simplified Format  
**File**: `app/api/v1/target_prices.py` → `export_target_prices()`  
**Service**: `TargetPriceService.get_portfolio_target_prices()`  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Export target prices to CSV or JSON format"  
**OpenAPI Description**: "Exports portfolio target prices with configurable format options. Always includes calculated returns and metrics. Optional metadata includes timestamps."

**Parameters**:
- `portfolio_id` (path, required): Portfolio UUID

**Request Body** (TargetPriceExportRequest - Phase 2 Simplified):
```json
{
  "format": "csv",
  "include_metadata": false
}
```

**Request Schema Changes (Phase 2)**:
- **Removed**: `include_calculations` parameter (always included now)
- **Simplified**: Export always includes expected returns and risk metrics
- **Metadata Option**: Controls inclusion of created_at/updated_at fields only

**Response for JSON format**:
```json
[
  {
    "symbol": "AAPL",
    "position_type": "LONG",
    "target_price_eoy": 200.00,
    "target_price_next_year": 220.00,
    "downside_target_price": 150.00,
    "current_price": 180.00,
    "expected_return_eoy": 11.11,
    "expected_return_next_year": 22.22,
    "downside_return": -16.67
  }
]
```

**Response for CSV format**:
```json
{
  "csv": "symbol,position_type,target_eoy,target_next_year,downside,current_price,expected_return_eoy,expected_return_next_year,downside_return\nAAPL,LONG,200.0,220.0,150.0,180.0,11.11,22.22,-16.67"
}
```

### Target Price API Summary

**Total Endpoints**: 10 fully implemented  
**Service Layer**: Complete with advanced features  
**Performance**: Optimized for production use  
**Phase Status**: Phases 1 & 2 complete with breaking changes applied  

**Key Capabilities**:
- ✅ Smart price resolution with investment class detection
- ✅ Equity-based position weighting and risk calculations  
- ✅ Options support with underlying symbol resolution
- ✅ Bulk operations with performance optimization
- ✅ CSV import/export with comprehensive validation
- ✅ SQL-level filtering and indexed lookups
- ✅ Standardized response formats and error handling

**Ready for**: Frontend integration, Phase 3 testing, production deployment

---

## F. Tag Management Endpoints

These endpoints manage the **tag entities themselves** - creating, updating, and organizing tags as standalone objects. Tags are user-scoped labels that can be applied to positions for flexible organization and filtering.

**Implementation Date**: October 2, 2025
**Architecture**: 3-tier separation (position_tags.py, tags.py, tags_v2.py)
**Database**: `tags_v2` table with user_id, display_order, usage_count, soft delete support
**Frontend Service**: `src/services/tagsApi.ts` (methods: create, list, update, delete, restore, defaults, reorder, batchUpdate)

**Note**: `usage_count` reflects the number of active position-tag assignments (strategy tags removed October 2025).

### Base Information
- **Base Path**: `/api/v1/tags`
- **Authentication**: Required (Bearer token)
- **User Scoping**: All tags scoped to authenticated user
- **Soft Delete**: Tags archived (not deleted) to preserve history

### 33. Create Tag
**Endpoint**: `POST /tags/`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `create_tag()` (lines 65-88)
**Frontend Method**: `tagsApi.create()`

**Authentication**: Required (Bearer token)
**Database Access**: Insert into `tags_v2` table
**Service Layer**: `app/services/tag_service.py`
  - Class: `TagService`
  - Method**: `create_tag(user_id, name, color, description, display_order)`
  - Validates unique name per user
  - Auto-increments display_order if not provided

**Purpose**: Create a new user-scoped tag for position organization

**Request Body** (CreateTagRequest):
```json
{
  "name": "Growth Portfolio",
  "color": "#3B82F6",
  "description": "High-growth technology stocks",
  "display_order": 1
}
```

**Response** (TagResponse):
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Growth Portfolio",
  "color": "#3B82F6",
  "description": "High-growth technology stocks",
  "display_order": 1,
  "usage_count": 0,
  "position_count": 0,
  "strategy_count": 0,
  "is_archived": false,
  "created_at": "2025-10-04T12:00:00Z",
  "updated_at": "2025-10-04T12:00:00Z"
}
```

### 34. List Tags
**Endpoint**: `GET /tags/`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `list_tags()` (lines 92-119)
**Frontend Method**: `tagsApi.list()`

**Authentication**: Required (Bearer token)
**Database Access**: Query `tags_v2` filtered by user_id
**Service Layer**: `app/services/tag_service.py`
  - Method: `get_user_tags(user_id, include_archived, include_usage_stats)`
  - Ordered by display_order ASC

**Parameters**:
- `include_archived` (query, default false): Include archived tags
- `include_usage_stats` (query, default true): Include position usage counts

**Response** (TagListResponse):
```json
{
  "tags": [
    {
      "id": "uuid1",
      "name": "Growth",
      "color": "#3B82F6",
      "usage_count": 12,
      "position_count": 12
    },
    {
      "id": "uuid2",
      "name": "Value",
      "color": "#10B981",
      "usage_count": 8,
      "position_count": 8
    }
  ],
  "total": 15,
  "active_count": 15,
  "archived_count": 0
}
```

### 35. Get Tag
**Endpoint**: `GET /tags/{tag_id}`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `get_tag()` (lines 123-141)
**Frontend Method**: `tagsApi.get()`

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Query `tags_v2` by id
**Service Layer**: `app/services/tag_service.py`
  - Method: `get_tag(tag_id, include_positions)`

**Parameters**:
- `tag_id` (path): Tag UUID
- `include_positions` (query, default false): Include associated position-tag relationships

**Response**: TagResponse (see Create Tag response schema)

### 36. Update Tag
**Endpoint**: `PATCH /tags/{tag_id}`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `update_tag()` (lines 145-173)
**Frontend Method**: `tagsApi.update()`

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Update `tags_v2` by id
**Service Layer**: `app/services/tag_service.py`
  - Method: `update_tag(tag_id, name, color, description, display_order)`
  - Validates unique name if changed
  - All fields optional (partial update)

**Request Body** (UpdateTagRequest - all fields optional):
```json
{
  "name": "Updated Growth",
  "color": "#10B981",
  "description": "Updated description"
}
```

**Response**: TagResponse with updated values

### 37. Archive Tag
**Endpoint**: `POST /tags/{tag_id}/archive`
**Status**: ✅ Fully Implemented (Soft Delete)
**File**: `app/api/v1/tags.py`
**Function**: `archive_tag()` (lines 177-197)
**Frontend Method**: `tagsApi.delete()` (note: frontend calls this for "delete")

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Update `tags_v2` set is_archived=true, archived_at, archived_by
**Service Layer**: `app/services/tag_service.py`
  - Method: `archive_tag(tag_id, archived_by)`
  - Soft delete preserves tag history
  - Removes tag from all positions

**Response**:
```json
{
  "message": "Tag archived successfully"
}
```

### 38. Restore Tag
**Endpoint**: `POST /tags/{tag_id}/restore`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `restore_tag()` (lines 201-218)
**Frontend Method**: `tagsApi.restore()`

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Update `tags_v2` set is_archived=false, archived_at=null
**Service Layer**: `app/services/tag_service.py`
  - Method: `restore_tag(tag_id)`

**Response**:
```json
{
  "message": "Tag restored successfully"
}
```

### 39. Create Default Tags
**Endpoint**: `POST /tags/defaults`
**Status**: ✅ Fully Implemented (Idempotent)
**File**: `app/api/v1/tags.py`
**Function**: `create_default_tags()` (lines 225-248)
**Frontend Method**: `tagsApi.defaults()`

**Authentication**: Required (Bearer token)
**Database Access**: Bulk insert into `tags_v2`
**Service Layer**: `app/services/tag_service.py`
  - Method: `create_default_tags(user_id)`
  - Creates **10 standard tags** (see `TagV2.default_tags()` in `app/models/tags_v2.py:135-149` for complete list)
  - Idempotent: returns existing tags if user already has tags

**Purpose**: Initialize new users with standard tag set

**Response**:
```json
{
  "message": "Created 10 default tags",
  "tags": [
    { "id": "uuid1", "name": "Growth", "color": "#3B82F6" },
    { "id": "uuid2", "name": "Value", "color": "#10B981" },
    { "id": "uuid3", "name": "Dividend", "color": "#F59E0B" }
  ]
}
```

## G. Position Tagging Endpoints

These endpoints manage the **relationships between tags and positions** - applying tags TO positions. This is the **preferred tagging method** (replaces legacy strategy-based tagging).

**Implementation Date**: October 2, 2025
**Architecture**: Direct position-to-tag many-to-many relationships via `position_tags` junction table
**Database**: `position_tags` table with unique constraint (position_id, tag_id), indexes for performance
**Frontend Service**: `src/services/tagsApi.ts` (methods: addPositionTags, removePositionTags, getPositionTags, replacePositionTags, getPositionsByTag)

### Base Information
- **Base Path**: `/api/v1/positions/{position_id}/tags`
- **Authentication**: Required (Bearer token) + portfolio ownership validation
- **Batch Operations**: Support adding/removing multiple tags in single request
- **Performance**: Batch fetching to prevent N+1 queries

### 40. Add Tags to Position
**Endpoint**: `POST /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `assign_tags_to_position()` (lines 58-113)
**Frontend Method**: `tagsApi.addPositionTags()`

**Authentication**: Required (Bearer token) + portfolio ownership validation
**Database Access**: Insert into `position_tags` junction table
**Service Layer**: `app/services/position_tag_service.py`
  - Class: `PositionTagService`
  - Method: `bulk_assign_tags(position_id, tag_ids, assigned_by, replace_existing)`
  - Unique constraint prevents duplicates
  - Increments tag usage_count

**Purpose**: Add multiple tags to a position (many-to-many relationship)

**Request Body** (AssignTagsToPositionRequest):
```json
{
  "tag_ids": ["uuid1", "uuid2", "uuid3"],
  "replace_existing": false
}
```

**Response** (BulkAssignResponse):
```json
{
  "message": "Assigned 3 tags to position",
  "assigned_count": 3,
  "tag_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Implementation Notes**:
- `replace_existing=true` removes old tags first (replace all)
- Validates user owns all tags and portfolio
- Idempotent: duplicate tag assignments ignored

### 41. Remove Tags from Position
**Endpoint**: `DELETE /positions/{position_id}/tags` OR `POST /positions/{position_id}/tags/remove`
**Status**: ✅ Fully Implemented (dual methods for compatibility)
**File**: `app/api/v1/position_tags.py`
**Functions**: `remove_tags_from_position_post()` (lines 116-154), `remove_tags_from_position()` (lines 156-194)
**Frontend Method**: `tagsApi.removePositionTags()` (uses POST /remove)

**Authentication**: Required (Bearer token) + portfolio ownership validation
**Database Access**: Delete from `position_tags` junction table
**Service Layer**: `app/services/position_tag_service.py`
  - Method: `bulk_remove_tags(position_id, tag_ids)`
  - Decrements tag usage_count

**Request Body** (POST method - RemoveTagsFromPositionRequest):
```json
{
  "tag_ids": ["uuid1", "uuid2"]
}
```

**Query Parameters** (DELETE method):
- `tag_ids` (query, array): Tag UUIDs to remove

**Response**:
```json
{
  "message": "Removed 2 tags from position",
  "removed_count": 2
}
```

**Implementation Notes**:
- POST method at `/remove` provided for better frontend compatibility
- DELETE method uses query parameters
- Silently ignores non-existent tag assignments

### 42. Get Position's Tags
**Endpoint**: `GET /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `get_position_tags()` (lines 195-231)
**Frontend Method**: `tagsApi.getPositionTags()`

**Authentication**: Required (Bearer token) + portfolio ownership validation
**Database Access**: Query `position_tags` joined with `tags_v2`
**Service Layer**: `app/services/position_tag_service.py`
  - Method: `get_tags_for_position(position_id)`
  - Returns tags ordered by display_order

**Purpose**: Get all tags assigned to a specific position

**Response** (Array of TagSummary):
```json
[
  {
    "id": "uuid1",
    "name": "Growth",
    "color": "#3B82F6",
    "description": "High-growth stocks"
  },
  {
    "id": "uuid2",
    "name": "Tech",
    "color": "#8B5CF6",
    "description": "Technology sector"
  }
]
```

### 43. Replace All Position Tags
**Endpoint**: `PATCH /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `update_position_tags()` (lines 235-254)
**Frontend Method**: `tagsApi.replacePositionTags()`

**Authentication**: Required (Bearer token) + portfolio ownership validation
**Database Access**: Delete old + Insert new in `position_tags` (transactional)
**Service Layer**: Calls `assign_tags_to_position()` with `replace_existing=True`

**Purpose**: Replace entire tag set for a position (atomic operation)

**Request Body** (AssignTagsToPositionRequest):
```json
{
  "tag_ids": ["uuid1", "uuid3"]
}
```

**Response**: BulkAssignResponse (see Add Tags response)

**Implementation Notes**:
- Convenience endpoint equivalent to POST with replace_existing=True
- Atomic operation: removes all old tags, adds all new tags
- Usage counts updated correctly for both removed and added tags

### 44. Get Positions by Tag (Reverse Lookup)
**Endpoint**: `GET /tags/{tag_id}/positions`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py` (tag-centric endpoint)
**Function**: `get_positions_by_tag()` (lines 251-306)
**Frontend Method**: `tagsApi.getPositionsByTag()`

**Authentication**: Required (Bearer token) + tag ownership + portfolio validation
**Database Access**: Query `position_tags` joined with `positions` and `tags_v2`
**Service Layer**: `app/services/position_tag_service.py`
  - Method: `get_positions_by_tag(tag_id, portfolio_id)`
  - Filters by portfolio_id for multi-portfolio support

**Purpose**: Find all positions with a specific tag (reverse lookup from tag → positions)

**Parameters**:
- `tag_id` (path): Tag UUID
- `portfolio_id` (query, optional): Filter by portfolio (defaults to user's portfolio)

**Response**:
```json
{
  "tag_id": "uuid",
  "tag_name": "Growth",
  "positions": [
    {
      "id": "position-uuid1",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "portfolio_id": "portfolio-uuid",
      "investment_class": "PUBLIC"
    },
    {
      "id": "position-uuid2",
      "symbol": "MSFT",
      "position_type": "LONG",
      "quantity": 50.0,
      "portfolio_id": "portfolio-uuid",
      "investment_class": "PUBLIC"
    }
  ],
  "total": 2
}
```

**Implementation Notes**:
- Tag-centric endpoint (located in tags.py for REST consistency)
- Supports multi-portfolio filtering
- Returns position summary data (not full position details)
- Useful for tag-based portfolio filtering and organization

### Position Tagging API Summary

**Total Endpoints**: 5 fully implemented
**Architecture**: REST many-to-many pattern (position-centric + tag-centric)
**Database**: `position_tags` junction table with indexes and unique constraints
**Performance**: Optimized batch operations, usage count tracking

**Key Capabilities**:
- ✅ Direct position-to-tag relationships (no strategies required)
- ✅ Multiple tags per position for flexible organization
- ✅ Batch operations for efficient bulk tagging
- ✅ Reverse lookups (find positions by tag)
- ✅ Automatic usage count tracking
- ✅ Transactional tag replacement
- ✅ Portfolio ownership validation for security

**Integration Status**:
- ✅ Backend API complete (October 2, 2025)
- ✅ Database schema with position_tags junction table
- ✅ Frontend service complete (src/services/tagsApi.ts)
- ✅ React hooks (useTags.ts, usePositionTags.ts)
- ✅ Organize page using position tagging system

---

## Getting Started

### 1. Authentication
```bash
# Get JWT token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_hnw@sigmasight.com", "password": "demo12345"}' | \
  jq -r '.access_token')
```

### 2. Get Portfolio Data
```bash
# List portfolios
curl -X GET "http://localhost:8000/api/v1/data/portfolios" \
  -H "Authorization: Bearer $TOKEN"

# Get complete portfolio
curl -X GET "http://localhost:8000/api/v1/data/portfolio/c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e/complete" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Get Market Data
```bash
# Historical prices
curl -X GET "http://localhost:8000/api/v1/data/prices/historical/AAPL?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Real-time quotes
curl -X GET "http://localhost:8000/api/v1/data/prices/quotes?symbols=AAPL,MSFT" \
  -H "Authorization: Bearer $TOKEN"
```

## ✅ CORRECTION: Analytics Endpoint IS IMPLEMENTED
**The analytics endpoint DOES exist and is fully implemented:**
- `GET /api/v1/analytics/portfolio/{id}/overview` 
- **File**: `app/api/v1/analytics/portfolio.py`
- **Function**: `get_portfolio_overview()` (line 23-75)
- **Service Layer**: `app/services/portfolio_analytics_service.py`
  - Class: `PortfolioAnalyticsService`
  - Method: `get_portfolio_overview()` (line 26-86)
- **Status**: Fully implemented with real database queries

**This endpoint provides portfolio overview with exposures, P&L, and position metrics.**

### 4. Test Portfolio Analytics
```bash
# Portfolio overview metrics
curl -X GET "http://localhost:8000/api/v1/analytics/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/overview" \
  -H "Authorization: Bearer $TOKEN"
```
