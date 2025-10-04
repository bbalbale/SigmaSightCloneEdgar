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

---

# IMPLEMENTED ENDPOINTS ✅

This section documents all **fully implemented and production-ready endpoints** in the SigmaSight Backend API.

### Complete Endpoint List

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

#### Tag Management (10 endpoints) ✨ **NEW - October 2, 2025**
- POST `/tags/` - Create tag
- GET `/tags/` - List user tags
- GET `/tags/{id}` - Get tag details
- PATCH `/tags/{id}` - Update tag
- POST `/tags/{id}/archive` - Archive tag (soft delete)
- POST `/tags/{id}/restore` - Restore archived tag
- POST `/tags/defaults` - Create default tags (idempotent)
- POST `/tags/reorder` - Reorder tags
- GET `/tags/{id}/strategies` - Get strategies by tag (deprecated)
- POST `/tags/batch-update` - Batch update tags

#### Position Tagging (5 endpoints) ✨ **NEW - October 2, 2025 - PREFERRED METHOD**
- POST `/positions/{id}/tags` - Add tags to position
- DELETE `/positions/{id}/tags` - Remove tags from position
- GET `/positions/{id}/tags` - Get position's tags
- PATCH `/positions/{id}/tags` - Replace all position tags
- GET `/tags/{id}/positions` - Get positions by tag (reverse lookup)

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

#### Market Data (removed in v1.2)
These endpoints were removed from the public API. Service‑level functionality for market data remains available internally.
- (removed) GET `/market-data/prices/{symbol}`
- (removed) GET `/market-data/current-prices` (query: `symbols`)
- (removed) GET `/market-data/sectors` (query: `symbols`)
- (removed) POST `/market-data/refresh`
- (removed) GET `/market-data/options/{symbol}`

#### Administration (not registered)
Admin endpoints exist in `app/api/v1/endpoints/admin_batch.py` but are not included in the router and are not accessible via the API.

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
**Function**: `get_user_portfolios()`  
**Authentication**: Required  
**OpenAPI Description**: "Get all portfolios for authenticated user"  
**Database Access**: Direct ORM query to `Portfolio` table with `selectinload(Portfolio.positions)` (lines 47-52)  
**Service Layer**: None - direct database access with manual calculation of total_value  

Returns all portfolios for the authenticated user with real database data.

**Response**:
```json
{
  "data": [
    {
      "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "name": "Demo High Net Worth Investor Portfolio",
      "type": "HNW",
      "created_at": "2025-08-08T12:00:00Z",
      "positions_count": 21,
      "total_value": 1662126.38
    }
  ]
}
```

### 6. Get Complete Portfolio
**Endpoint**: `GET /data/portfolio/{portfolio_id}/complete`  
**Status**: ✅ Fully Implemented  
**File**: `app/api/v1/data.py`  
**Function**: `get_portfolio_complete()`  
**Authentication**: Required  
**OpenAPI Description**: "Get complete portfolio data with optional sections"  
**Database Access**: Direct ORM queries to Portfolio, Position, MarketDataCache tables (lines 97-103, 124+)  
**Service Layer**: **Minimal usage** - Only uses:
  - File: `app/services/portfolio_data_service.py`
  - Class: `PortfolioDataService`
  - Method: `get_portfolio_overview()` (called at line 788)
  - Note: Most logic uses direct ORM queries, not service layer  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `sections` (query, optional): Comma-separated list of sections to include
- `as_of_date` (query, optional): Date for historical data (YYYY-MM-DD format)

**Special Notes**: Cash balance calculated as 5% of portfolio value (not stored in database)

**Response**:
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
    "cash_balance": 83106.32,
    "total_pnl": 125432.18,
    "positions_count": 21
  },
  "market_data": {
    "last_updated": "2025-09-05T15:30:00Z",
    "data_quality": 95.5
  }
}
```

### 7. Get Data Quality
**Endpoint**: `GET /data/portfolio/{portfolio_id}/data-quality`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get data quality metrics for portfolio"  
**Database Access**: Position, MarketDataCache tables  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "overall_score": 95.5,
  "metrics": {
    "price_coverage": {
      "score": 98.0,
      "total_positions": 21,
      "positions_with_prices": 21,
      "missing_prices": 0
    },
    "data_freshness": {
      "score": 93.0,
      "last_updated": "2025-09-05T15:30:00Z",
      "hours_since_update": 2.5
    },
    "greeks_coverage": {
      "score": 85.0,
      "options_positions": 8,
      "positions_with_greeks": 7,
      "missing_greeks": 1
    }
  },
  "recommendations": [
    "Update options Greeks for SPY position",
    "Refresh intraday prices during market hours"
  ],
  "last_assessed": "2025-09-05T18:00:00Z"
}
```

### 8. Get Position Details
**Endpoint**: `GET /data/positions/details`  
**Status**: ✅ Fully Implemented  
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
  "data": [
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
      "day_change": 285.00,
      "day_change_percent": 1.65,
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
      "day_change": 125.00,
      "day_change_percent": 6.33,
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
**Endpoint**: `GET /data/prices/historical/{symbol_or_position_id}`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get historical price data for symbol or position"  
**Database Access**: MarketDataCache table  
**Service Layer**: Uses market data service:
  - File: `app/services/market_data_service.py`
  - Class: `MarketDataService`
  - Method: `get_historical_prices()`  

**Parameters**:
- `symbol_or_position_id` (path): Symbol or position UUID
- `days` (query, optional): Number of days of history (default 30)
- `start_date` (query, optional): Start date (YYYY-MM-DD)
- `end_date` (query, optional): End date (YYYY-MM-DD)

**Response**:
```json
{
  "symbol": "AAPL",
  "data_points": 30,
  "start_date": "2025-08-06",
  "end_date": "2025-09-05",
  "prices": [
    {
      "date": "2025-09-05",
      "open": 174.80,
      "high": 176.15,
      "low": 174.25,
      "close": 175.25,
      "volume": 58432100,
      "adjusted_close": 175.25
    },
    {
      "date": "2025-09-04",
      "open": 173.50,
      "high": 175.20,
      "low": 173.10,
      "close": 174.65,
      "volume": 62145800,
      "adjusted_close": 174.65
    }
  ],
  "statistics": {
    "period_return": 0.0953,
    "volatility": 0.285,
    "max_price": 178.95,
    "min_price": 160.12,
    "avg_volume": 55328450
  },
  "last_updated": "2025-09-05T20:00:00Z"
}
```

### 10. Get Market Quotes
**Endpoint**: `GET /data/prices/quotes`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get real-time market quotes for symbols"  
**Database Access**: MarketDataCache table (latest prices)  
**Service Layer**: Uses market data service:
  - File: `app/services/market_data_service.py`
  - Class: `MarketDataService`
  - Method: `get_real_time_quotes()`  

**Parameters**:
- `symbols` (query): Comma-separated list of symbols

**Response**:
```json
{
  "quotes": [
    {
      "symbol": "AAPL",
      "price": 175.25,
      "change": 0.60,
      "change_percent": 0.34,
      "volume": 58432100,
      "bid": 175.20,
      "ask": 175.30,
      "bid_size": 200,
      "ask_size": 300,
      "high_52_week": 199.62,
      "low_52_week": 164.08,
      "market_cap": 2658745000000,
      "timestamp": "2025-09-05T20:00:00Z"
    },
    {
      "symbol": "MSFT",
      "price": 425.18,
      "change": -2.42,
      "change_percent": -0.57,
      "volume": 24785900,
      "bid": 425.10,
      "ask": 425.25,
      "bid_size": 100,
      "ask_size": 150,
      "high_52_week": 468.35,
      "low_52_week": 362.90,
      "market_cap": 3158924000000,
      "timestamp": "2025-09-05T20:00:00Z"
    }
  ],
  "market_status": "closed",
  "last_updated": "2025-09-05T20:00:00Z"
}
```

### 11. Get Factor ETF Prices
**Endpoint**: `GET /data/factors/etf-prices`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get current and historical prices for factor ETFs"  
**Database Access**: MarketDataCache table  
**Service Layer**: Uses market data service:
  - File: `app/services/market_data_service.py`
  - Class: `MarketDataService`
  - Method: `get_factor_etf_prices()`  

**Parameters**:
- `symbols` (query, optional): Specific ETF symbols to retrieve
- `days` (query, optional): Number of days of history

**Response**:
```json
{
  "factor_etfs": [
    {
      "symbol": "VTI",
      "name": "Vanguard Total Stock Market ETF",
      "factor_type": "market",
      "current_price": 268.45,
      "change": -1.25,
      "change_percent": -0.46,
      "volume": 2845200,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 268.45},
        {"date": "2025-09-04", "close": 269.70},
        {"date": "2025-09-03", "close": 271.15}
      ]
    },
    {
      "symbol": "VEA",
      "name": "Vanguard FTSE Developed Markets ETF",
      "factor_type": "international",
      "current_price": 52.18,
      "change": 0.15,
      "change_percent": 0.29,
      "volume": 5928400,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 52.18},
        {"date": "2025-09-04", "close": 52.03},
        {"date": "2025-09-03", "close": 51.89}
      ]
    },
    {
      "symbol": "VWO",
      "name": "Vanguard FTSE Emerging Markets ETF",
      "factor_type": "emerging_markets",
      "current_price": 45.32,
      "change": 0.87,
      "change_percent": 1.96,
      "volume": 8234600,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 45.32},
        {"date": "2025-09-04", "close": 44.45},
        {"date": "2025-09-03", "close": 44.12}
      ]
    }
  ],
  "summary": {
    "total_etfs": 7,
    "data_coverage": "100%",
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
- Uses existing aggregation engine results from batch processing
- Returns calculated exposures (long/short/gross/net)
- Includes P&L metrics and portfolio totals
- Leverages existing calculation data with graceful degradation
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
  - Method: `get_portfolio_exposures(portfolio_id)`
  - Reads: `factor_exposures` joined with `factor_definitions`
  - Enforces latest complete set: selects the most recent `calculation_date` where all active factors have exposures

**Purpose**: Return portfolio-level factor betas (and optional dollar exposures) from the latest complete calculation set for dashboards and reports.  
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

**Response Schema**: `DiversificationScoreResponse`
```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "diversification_score": 0.72,
  "calculation_date": "2025-09-05",
  "lookback_days": 90,
  "positions_analyzed": 15,
  "weighted_correlation": 0.28,
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

### 19. Get Batch Job Status
**Endpoint**: `GET /admin/batch/jobs/status`  
**Status**: ⚠️ Implemented but NOT registered in router  
**File**: `app/api/v1/endpoints/admin_batch.py`  
**Function**: `get_batch_job_status()` (lines 212-255)  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get status of recent batch jobs"  
**Database Access**: BatchJob table  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `job_name` (query, optional): Filter by job name
- `status` (query, optional): Filter by status
- `portfolio_id` (query, optional): Filter by portfolio
- `days_back` (query, optional): Number of days to look back (default 1)

**Response**:
```json
{
  "jobs": [
    {
      "id": "job_20250905_183045_market_data_update",
      "job_name": "market_data_update",
      "status": "completed",
      "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "started_at": "2025-09-05T18:30:45Z",
      "completed_at": "2025-09-05T18:32:15Z",
      "duration_seconds": 90,
      "processed_items": 21,
      "successful_items": 21,
      "failed_items": 0,
      "error_message": null,
      "metadata": {
        "source": "batch_orchestrator_v2",
        "calculation_engines": ["market_data", "greeks", "factor_exposure"]
      }
    },
    {
      "id": "job_20250905_120030_full_calculation",
      "job_name": "full_portfolio_calculation",
      "status": "running",
      "portfolio_id": "d1621bc9-d6c6-444d-becd-4f85f1ecdb5f",
      "started_at": "2025-09-05T12:00:30Z",
      "completed_at": null,
      "duration_seconds": null,
      "processed_items": 45,
      "successful_items": 38,
      "failed_items": 2,
      "error_message": null,
      "metadata": {
        "source": "api_trigger",
        "calculation_engines": ["all"]
      }
    },
    {
      "id": "job_20250905_060015_data_quality_check",
      "job_name": "data_quality_assessment",
      "status": "failed",
      "portfolio_id": null,
      "started_at": "2025-09-05T06:00:15Z",
      "completed_at": "2025-09-05T06:02:45Z",
      "duration_seconds": 150,
      "processed_items": 0,
      "successful_items": 0,
      "failed_items": 0,
      "error_message": "API rate limit exceeded for market data provider",
      "metadata": {
        "source": "scheduled_job",
        "retry_count": 3
      }
    }
  ],
  "summary": {
    "total_jobs": 3,
    "completed": 1,
    "running": 1,
    "failed": 1,
    "pending": 0
  },
  "filters_applied": {
    "days_back": 1,
    "job_name": null,
    "status": null,
    "portfolio_id": null
  },
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### 20. Get Batch Job Summary
**Endpoint**: `GET /admin/batch/jobs/summary`  
**Status**: ⚠️ Implemented but NOT registered in router  
**File**: `app/api/v1/endpoints/admin_batch.py`  
**Function**: `get_batch_job_summary()` (lines 258-313)  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get summary statistics of batch jobs"  
**Database Access**: BatchJob table  
**Service Layer**: Direct ORM queries with statistical calculations  

**Parameters**:
- `days_back` (query, optional): Number of days for summary (default 7)

**Response**:
```json
{
  "period": {
    "start_date": "2025-08-29",
    "end_date": "2025-09-05",
    "days_covered": 7
  },
  "job_statistics": {
    "total_jobs": 42,
    "completed_jobs": 35,
    "running_jobs": 2,
    "failed_jobs": 4,
    "pending_jobs": 1,
    "success_rate": 83.33,
    "avg_duration_seconds": 125.5
  },
  "by_job_type": {
    "market_data_update": {
      "total": 14,
      "completed": 13,
      "failed": 1,
      "success_rate": 92.86,
      "avg_duration": 85.2
    },
    "full_portfolio_calculation": {
      "total": 12,
      "completed": 10,
      "failed": 1,
      "success_rate": 83.33,
      "avg_duration": 245.8
    },
    "greeks_calculation": {
      "total": 8,
      "completed": 7,
      "failed": 1,
      "success_rate": 87.5,
      "avg_duration": 65.4
    },
    "factor_analysis": {
      "total": 6,
      "completed": 5,
      "failed": 1,
      "success_rate": 83.33,
      "avg_duration": 125.3
    },
    "data_quality_assessment": {
      "total": 2,
      "completed": 0,
      "failed": 0,
      "success_rate": 0.0,
      "avg_duration": null
    }
  },
  "performance_trends": {
    "daily_job_counts": [
      {"date": "2025-09-05", "total": 8, "completed": 6, "failed": 1},
      {"date": "2025-09-04", "total": 6, "completed": 5, "failed": 1},
      {"date": "2025-09-03", "total": 7, "completed": 7, "failed": 0},
      {"date": "2025-09-02", "total": 5, "completed": 4, "failed": 1},
      {"date": "2025-09-01", "total": 6, "completed": 5, "failed": 0},
      {"date": "2025-08-31", "total": 5, "completed": 4, "failed": 1},
      {"date": "2025-08-30", "total": 5, "completed": 4, "failed": 0}
    ],
    "avg_duration_trend": {
      "current_week": 125.5,
      "previous_week": 135.2,
      "improvement_percent": 7.2
    }
  },
  "error_analysis": {
    "top_error_types": [
      {
        "error_pattern": "API rate limit exceeded",
        "count": 2,
        "percentage": 50.0
      },
      {
        "error_pattern": "Database connection timeout",
        "count": 1,
        "percentage": 25.0
      },
      {
        "error_pattern": "Invalid portfolio data",
        "count": 1,
        "percentage": 25.0
      }
    ],
    "most_failed_job_type": "market_data_update"
  },
  "recommendations": [
    "Consider implementing exponential backoff for API rate limits",
    "Monitor database connection pool during peak hours",
    "Add data validation checks before portfolio calculations"
  ],
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### Cancel Batch Job
**Endpoint**: `DELETE /admin/batch/jobs/{job_id}/cancel`  
**Status**: ⚠️ Implemented but NOT registered in router  
**File**: `app/api/v1/endpoints/admin_batch.py`  
**Function**: `cancel_batch_job()` (lines 383-420)  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Cancel a running batch job"  
**Database Access**: BatchJob table (UPDATE operation)  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `job_id` (path): Batch job ID to cancel

**Response**:
```json
{
  "message": "Batch job cancelled successfully",
  "job_details": {
    "id": "job_20250905_120030_full_calculation",
    "job_name": "full_portfolio_calculation",
    "previous_status": "running",
    "new_status": "cancelled",
    "cancelled_at": "2025-09-05T18:47:30Z",
    "runtime_before_cancellation": 385,
    "processed_items": 45,
    "successful_items": 38,
    "items_in_progress": 5
  },
  "cleanup_actions": [
    "Released database connections",
    "Cleared temporary calculation cache",
    "Updated job status in database"
  ],
  "impact_assessment": {
    "affected_portfolios": 1,
    "incomplete_calculations": 5,
    "data_consistency_status": "maintained",
    "rollback_required": false
  }
}
```

### 21. Get Data Quality Status
**Endpoint**: `GET /admin/batch/data-quality`  
**Status**: ⚠️ Implemented but NOT registered in router  
**File**: `app/api/v1/endpoints/admin_batch.py`  
**Function**: `get_data_quality_status()` (lines 423-455)  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get data quality status and metrics for portfolios"  
**Database Access**: Portfolio, Position, MarketDataCache tables  
**Service Layer**: Uses batch validation:
  - File: `app/batch/data_quality.py`
  - Function: `pre_flight_validation()` (async function)  

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio ID or all portfolios

**Response**:
```json
{
  "system_overview": {
    "total_portfolios": 8,
    "active_portfolios": 8,
    "total_positions": 74,
    "overall_data_quality_score": 88.5,
    "last_assessment": "2025-09-05T18:45:00Z"
  },
  "portfolio_quality": [
    {
      "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "portfolio_name": "Demo High Net Worth Investor Portfolio",
      "quality_score": 95.5,
      "position_count": 21,
      "data_completeness": {
        "price_coverage": 100.0,
        "greeks_coverage": 87.5,
        "factor_coverage": 90.5,
        "historical_data_coverage": 98.2
      },
      "data_freshness": {
        "last_price_update": "2025-09-05T20:00:00Z",
        "hours_since_update": 2.75,
        "freshness_score": 93.0
      },
      "issues": [
        "Missing Greeks for 1 options position",
        "Historical data gap for 2 positions"
      ]
    },
    {
      "portfolio_id": "d1621bc9-d6c6-444d-becd-4f85f1ecdb5f",
      "portfolio_name": "Demo Retail Investor Portfolio",
      "quality_score": 82.3,
      "position_count": 15,
      "data_completeness": {
        "price_coverage": 93.3,
        "greeks_coverage": 75.0,
        "factor_coverage": 86.7,
        "historical_data_coverage": 89.5
      },
      "data_freshness": {
        "last_price_update": "2025-09-05T19:30:00Z",
        "hours_since_update": 3.25,
        "freshness_score": 85.0
      },
      "issues": [
        "Missing prices for 1 position",
        "Stale Greeks data for 2 positions",
        "Factor exposures need recalculation"
      ]
    }
  ],
  "data_source_status": {
    "market_data_providers": {
      "fmp": {
        "status": "operational",
        "last_successful_call": "2025-09-05T20:00:00Z",
        "daily_api_calls": 1245,
        "daily_limit": 10000,
        "error_rate_24h": 0.02
      },
      "polygon": {
        "status": "operational",
        "last_successful_call": "2025-09-05T19:45:00Z",
        "daily_api_calls": 358,
        "daily_limit": 5000,
        "error_rate_24h": 0.01
      }
    },
    "database_health": {
      "status": "healthy",
      "connection_pool_usage": 45,
      "avg_query_time_ms": 12.5,
      "slow_queries_24h": 3
    }
  },
  "quality_trends": {
    "score_history_7d": [
      {"date": "2025-09-05", "score": 88.5},
      {"date": "2025-09-04", "score": 87.2},
      {"date": "2025-09-03", "score": 89.1},
      {"date": "2025-09-02", "score": 85.8},
      {"date": "2025-09-01", "score": 84.5},
      {"date": "2025-08-31", "score": 86.9},
      {"date": "2025-08-30", "score": 88.0}
    ],
    "improvement_areas": [
      "Options Greeks calculation frequency",
      "Factor exposure refresh timing",
      "Historical data backfill for new positions"
    ]
  },
  "recommendations": [
    "Increase Greeks calculation frequency to twice daily",
    "Implement real-time factor exposure updates",
    "Set up automated data quality alerts for scores below 80%",
    "Consider adding backup data provider for critical market data"
  ],
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### 22. Refresh Market Data for Quality
**Endpoint**: `POST /admin/batch/data-quality/refresh`  
**Status**: ⚠️ Implemented but NOT registered in router  
**File**: `app/api/v1/endpoints/admin_batch.py`  
**Function**: `refresh_market_data_for_quality()` (lines 458-502)  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Refresh market data to improve data quality scores"  
**Database Access**: Uses pre_flight_validation and batch orchestrator  
**Service Layer**: Uses batch orchestration:
  - File: `app/batch/batch_orchestrator_v2.py`
  - Object: `batch_orchestrator_v2` (imported as `batch_orchestrator`)
  - Method: `_update_market_data()` (private method)
  - Execution: Via BackgroundTasks for async processing  

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio ID or all portfolios

**Response**:
```json
{
  "refresh_initiated": true,
  "job_details": {
    "job_id": "job_20250905_184800_data_quality_refresh",
    "job_name": "data_quality_refresh",
    "status": "running",
    "initiated_at": "2025-09-05T18:48:00Z",
    "estimated_duration_minutes": 15
  },
  "scope": {
    "portfolios_targeted": 8,
    "positions_to_refresh": 74,
    "data_types": [
      "market_prices",
      "options_greeks",
      "factor_exposures",
      "historical_data"
    ]
  },
  "pre_refresh_quality": {
    "overall_score": 88.5,
    "portfolios_below_threshold": 2,
    "critical_issues": [
      "Missing prices for 1 position",
      "Stale Greeks for 3 options",
      "Factor exposures outdated by 2 days"
    ]
  },
  "expected_improvements": {
    "estimated_score_increase": 6.5,
    "target_quality_score": 95.0,
    "issues_to_resolve": 5,
    "data_freshness_improvement": "Will bring all data to within 1 hour"
  },
  "monitoring": {
    "progress_endpoint": "/admin/batch/jobs/job_20250905_184800_data_quality_refresh/status",
    "completion_webhook": null,
    "notification_channels": ["system_log", "admin_dashboard"]
  },
  "backup_plan": {
    "fallback_providers": ["polygon", "manual_entry"],
    "rollback_available": true,
    "previous_data_retained": true
  },
  "message": "Data quality refresh initiated successfully. Monitor progress via job status endpoint."
}
```

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
**File**: `app/api/v1/target_prices.py` → `bulk_update_target_prices()`  
**Service**: Optimized with indexing for O(1) lookups  
**Authentication**: Required (Bearer token)

**OpenAPI Summary**: "Bulk update target prices by symbol"  
**OpenAPI Description**: "Updates multiple target prices by symbol and position type with optimized performance and comprehensive error tracking. Uses indexed lookups for efficient bulk operations."

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

### Base Information
- **Base Path**: `/api/v1/tags`
- **Authentication**: Required (Bearer token)
- **User Scoping**: All tags scoped to authenticated user
- **Soft Delete**: Tags archived (not deleted) to preserve history

### 33. Create Tag
**Endpoint**: `POST /tags/`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `create_tag()` (lines 73-97)
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
  "is_archived": false,
  "created_at": "2025-10-04T12:00:00Z",
  "updated_at": "2025-10-04T12:00:00Z"
}
```

### 34. List Tags
**Endpoint**: `GET /tags/`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `list_tags()` (lines 100-128)
**Frontend Method**: `tagsApi.list()`

**Authentication**: Required (Bearer token)
**Database Access**: Query `tags_v2` filtered by user_id
**Service Layer**: `app/services/tag_service.py`
  - Method: `get_user_tags(user_id, include_archived, include_usage_stats)`
  - Ordered by display_order ASC

**Parameters**:
- `include_archived` (query, default false): Include archived tags
- `include_usage_stats` (query, default true): Include position/strategy counts

**Response** (TagListResponse):
```json
{
  "tags": [
    {
      "id": "uuid1",
      "name": "Growth",
      "color": "#3B82F6",
      "usage_count": 12
    },
    {
      "id": "uuid2",
      "name": "Value",
      "color": "#10B981",
      "usage_count": 8
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
**Function**: `get_tag()` (lines 131-150)
**Frontend Method**: `tagsApi.get()`

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Query `tags_v2` by id
**Service Layer**: `app/services/tag_service.py`
  - Method: `get_tag(tag_id, include_strategies)`

**Parameters**:
- `tag_id` (path): Tag UUID
- `include_strategies` (query, default false): Include associated strategies (deprecated)

**Response**: TagResponse (see Create Tag response schema)

### 36. Update Tag
**Endpoint**: `PATCH /tags/{tag_id}`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `update_tag()` (lines 153-182)
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
**Function**: `archive_tag()` (lines 185-206)
**Frontend Method**: `tagsApi.delete()` (note: frontend calls this for "delete")

**Authentication**: Required (Bearer token) + ownership validation
**Database Access**: Update `tags_v2` set is_archived=true, archived_at, archived_by
**Service Layer**: `app/services/tag_service.py`
  - Method: `archive_tag(tag_id, archived_by)`
  - Soft delete preserves tag history
  - Removes tag from all positions/strategies

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
**Function**: `restore_tag()` (lines 209-230)
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
**Function**: `create_default_tags()` (lines 412-435)
**Frontend Method**: `tagsApi.defaults()`

**Authentication**: Required (Bearer token)
**Database Access**: Bulk insert into `tags_v2`
**Service Layer**: `app/services/tag_service.py`
  - Method: `create_default_tags(user_id)`
  - Creates standard tags: Growth, Value, Dividend, Speculative, Core, Satellite, Defensive
  - Idempotent: returns existing tags if user already has tags

**Purpose**: Initialize new users with standard tag set

**Response**:
```json
{
  "message": "Created 7 default tags",
  "tags": [
    { "id": "uuid1", "name": "Growth", "color": "#3B82F6" },
    { "id": "uuid2", "name": "Value", "color": "#10B981" },
    { "id": "uuid3", "name": "Dividend", "color": "#F59E0B" }
  ]
}
```

### 40. Reorder Tags
**Endpoint**: `POST /tags/reorder`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `reorder_tags()` (not shown in file snippet - exists)
**Frontend Method**: `tagsApi.reorder()`

**Authentication**: Required (Bearer token)
**Database Access**: Bulk update `tags_v2.display_order`
**Service Layer**: `app/services/tag_service.py`
  - Method: `reorder_tags(tag_ids)`
  - Updates display_order based on array position

**Purpose**: Set custom display order for tags (drag-drop UI support)

**Request Body**:
```json
{
  "tag_ids": ["uuid3", "uuid1", "uuid2"]
}
```

**Response**:
```json
{
  "message": "Tags reordered successfully",
  "updated_count": 3
}
```

### 41. Get Strategies by Tag (DEPRECATED)
**Endpoint**: `GET /tags/{tag_id}/strategies`
**Status**: ⚠️ Deprecated
**File**: `app/api/v1/tags.py`
**Function**: `get_strategies_by_tag()` (lines 363-409)
**Frontend Method**: `tagsApi.getStrategies()`

**Deprecation Note**: Use `/tags/{id}/positions` for position tagging instead. This endpoint is kept for backward compatibility only.

**Purpose**: Find strategies with this tag (legacy strategy tagging system)

### 42. Batch Update Tags
**Endpoint**: `POST /tags/batch-update`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py`
**Function**: `batch_update_tags()` (not shown in file snippet - exists)
**Frontend Method**: `tagsApi.batchUpdate()`

**Authentication**: Required (Bearer token)
**Database Access**: Bulk update `tags_v2`
**Service Layer**: `app/services/tag_service.py`
  - Method: `batch_update_tags(updates)`
  - Validates ownership for all tags

**Request Body**:
```json
{
  "updates": [
    { "id": "uuid1", "name": "New Name 1" },
    { "id": "uuid2", "color": "#EF4444" },
    { "id": "uuid3", "description": "Updated description" }
  ]
}
```

**Response**:
```json
{
  "message": "Updated 3 tags successfully",
  "tags": [
    { "id": "uuid1", "name": "New Name 1", "color": "#3B82F6" },
    { "id": "uuid2", "name": "Value", "color": "#EF4444" }
  ]
}
```

---

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

### 43. Add Tags to Position
**Endpoint**: `POST /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `assign_tags_to_position()` (lines 57-112)
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

### 44. Remove Tags from Position
**Endpoint**: `DELETE /positions/{position_id}/tags` OR `POST /positions/{position_id}/tags/remove`
**Status**: ✅ Fully Implemented (dual methods for compatibility)
**File**: `app/api/v1/position_tags.py`
**Functions**: `remove_tags_from_position()` (lines 155-191), `remove_tags_from_position_post()` (lines 115-152)
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

### 45. Get Position's Tags
**Endpoint**: `GET /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `get_position_tags()` (lines 194-231)
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

### 46. Replace All Position Tags
**Endpoint**: `PATCH /positions/{position_id}/tags`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/position_tags.py`
**Function**: `update_position_tags()` (lines 234-254)
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

### 47. Get Positions by Tag (Reverse Lookup)
**Endpoint**: `GET /tags/{tag_id}/positions`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/tags.py` (tag-centric endpoint)
**Function**: `get_positions_by_tag()` (lines 438-489)
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

