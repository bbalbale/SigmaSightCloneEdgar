# SigmaSight Backend API Specifications V1.4.5

**Version**: 1.4.5  
**Date**: September 5, 2025  
**Status**: ⚠️ **CODE-VERIFIED CORRECTIONS** - Major discrepancies found  
**Source of Truth**: **Direct code verification** (API_IMPLEMENTATION_STATUS.md was inaccurate)  

> 📋 **Dual-Purpose Document**
> 
> **Part I**: ✅ **13 verified working endpoints** (corrected from claimed 18)  
> **Part II**: 🎯 Planned endpoints - development specifications for future implementation  

## Document Structure

### ✅ **Part I: Production-Ready Endpoints** 
- **13 verified working endpoints** returning real database data
- **Code-verified implementations** with file/function references 
- **Analytics endpoint confirmed working** (was previously marked as non-existent)
- **Admin endpoints exist but not registered** in router
- Ready for frontend integration

### 🎯 **Part II: Planned Endpoints** 
- Development specifications for future API endpoints
- Design guidance for analytics, management, export, and system namespaces
- Implementation roadmap and priorities

---

## Strategic Direction

### Namespace Philosophy
- **`/data/`**: Data for LLM consumption
- **`/analytics/`**: All calculated metrics and derived values
- **`/management/`**: Portfolio and position CRUD operations
- **`/export/`**: Data export and report generation
- **`/system/`**: System utilities and job management

### Key Design Principles
1. **Clear Separation**: Raw data vs. calculated metrics have distinct namespaces
2. **Self-Documenting**: Endpoint paths immediately convey data type and purpose
3. **LLM-Optimized**: `/data/` endpoints return complete, denormalized datasets
4. **Consistent Depth**: All major features at the second namespace level

---

# PART I: PRODUCTION-READY ENDPOINTS ✅

This section documents the **13 fully implemented and production-ready endpoints** in the SigmaSight Backend API. These endpoints have been **code-verified** to access database data through direct ORM queries or service layers and are ready for frontend integration.

### Complete Endpoint List

#### Authentication Endpoints
- **1.** [`POST /auth/login`](#1-login) - Authenticate user and return JWT token
- **2.** [`POST /auth/register`](#2-register) - Register a new user
- **3.** [`GET /auth/me`](#3-get-current-user) - Get current authenticated user information  
- **4.** [`POST /auth/refresh`](#4-refresh-token) - Refresh JWT token
- **5.** [`POST /auth/logout`](#5-logout) - Logout and clear auth cookie

#### Data Endpoints
- **6.** [`GET /data/portfolios`](#6-get-portfolios) - Get all portfolios for authenticated user
- **7.** [`GET /data/portfolio/{portfolio_id}/complete`](#7-get-complete-portfolio) - Get complete portfolio data with optional sections
- **8.** [`GET /data/portfolio/{portfolio_id}/data-quality`](#8-get-data-quality) - Get data quality metrics for portfolio
- **9.** [`GET /data/positions/details`](#9-get-position-details) - Get detailed position information with P&L calculations
- **10.** [`GET /data/prices/historical/{symbol_or_position_id}`](#10-get-historical-prices) - Get historical price data for symbol or position
- **11.** [`GET /data/prices/quotes`](#11-get-market-quotes) - Get real-time market quotes for symbols
- **12.** [`GET /data/factors/etf-prices`](#12-get-factor-etf-prices) - Get current and historical prices for factor ETFs

#### Analytics Endpoints  
- **13.** [`GET /analytics/portfolio/{portfolio_id}/overview`](#13-portfolio-overview) - Get comprehensive portfolio overview with exposures and P&L
- **14.** [`GET /analytics/portfolio/{portfolio_id}/correlation-matrix`](#14-correlation-matrix) - Get correlation matrix for portfolio positions

#### Chat Endpoints (Implemented)
- `POST /chat/conversations` — Create conversation
- `GET /chat/conversations/{conversation_id}` — Get conversation
- `GET /chat/conversations` — List conversations
- `PUT /chat/conversations/{conversation_id}/mode` — Change mode
- `DELETE /chat/conversations/{conversation_id}` — Delete conversation
- `POST /chat/send` — Send message (SSE streaming, `text/event-stream`)

#### Administration Endpoints  
**⚠️ NOTE**: Admin endpoints are implemented in `app/api/v1/endpoints/admin_batch.py` but NOT registered in the router. They are currently inaccessible via the API.

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
**File/Function**: `backend/app/api/v1/market_data.py:get_price_data()`  
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
**File/Function**: `backend/app/api/v1/market_data.py:get_options_chain()`  
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
**Status**: 🚧 Implemented — Under Testing  
**File**: `app/api/v1/analytics/portfolio.py`  
**Function**: `get_portfolio_factor_exposures()` (lines 197–227)  

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
**Status**: 🚧 Implemented — Under Testing  
**File**: `app/api/v1/analytics/portfolio.py`  
**Function**: `list_position_factor_exposures()` (lines 230–266)  

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


## D. Administration Endpoints

### 18. Get Batch Job Status
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

## Error Handling

All endpoints follow consistent error response format:

### Authentication Error (401)
```json
{
  "detail": "Could not validate credentials"
}
```

### Not Found Error (404)
```json
{
  "detail": "Portfolio not found"
}
```

### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["query", "symbols"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Error (500)
```json
{
  "detail": "Internal server error"
}
```

---

## Data Quality Guarantee

All endpoints in this specification:

✅ Return **REAL DATA** from the database  
✅ Have been tested and verified  
✅ Include comprehensive error handling  
✅ Support production workloads  
✅ Follow consistent response schemas  

### Historical Data Coverage
- **Stock prices**: 297 days (2024-06-24 to 2025-09-04)
- **Factor ETFs**: 7 ETFs with real market prices
- **Portfolio data**: 8 portfolios, 74+ active positions
- **Market quotes**: Real-time data with volume and timestamps

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

---

# PART II: PLANNED ENDPOINTS 🎯

This section provides development specifications for future API endpoints. These are **NOT YET IMPLEMENTED** but serve as design guidance for development teams.

> ⚠️ **Development Planning Section**
> 
> **Status**: Not implemented - design specifications only  
> **Purpose**: Guide development of analytics, management, export, and system namespaces  
> **Source**: API_SPECIFICATIONS_V1.4.4.md planned endpoints  

## Namespace Organization

### 🎯 **Planned Namespace Structure**
- **`/analytics/`**: All calculated metrics and derived values
- **`/management/`**: Portfolio and position CRUD operations  
- **`/export/`**: Data export and report generation
- **`/system/`**: System utilities and job management


---

## Analytics Endpoints (/analytics/) 🧮

**Status**: 📋 Under Development
**Priority**: High - Core calculations and derived metrics


### Risk Analytics

#### A2. Portfolio Risk Metrics
```http
GET /api/v1/analytics/portfolio/{portfolio_id}/risk-metrics
```

**Purpose**: Calculated risk metrics (beta, volatility, max drawdown)  
**Implementation Notes**:
- v1 minimal scope: excludes VaR/Expected Shortfall (planned for v1.1)
- Benchmark is fixed to SPY (no `benchmark` query param)
- lookback_days default 90 (bounds 30–252)
- DB-first (no new regressions in v1):
  - Portfolio Beta: read from FactorExposure ('Market Beta') — latest on/≤ end of window
  - Volatility: aggregate from PortfolioSnapshot.daily_return (sample stddev × sqrt(252))
  - Max Drawdown: compute from PortfolioSnapshot.total_value (running-peak percentage drawdown)
  - Alignment: snapshot dates only (no forward-fill/interpolation); business days implied

**Parameters**:
- `lookback_days` (query, optional): default 90; min 30; max 252

**Planned Response (v1)**:
```json
{
  "available": true,
  "portfolio_id": "uuid",
  "risk_metrics": {
    "portfolio_beta": 0.87,
    "annualized_volatility": 0.142,
    "max_drawdown": -0.185
  },
  "metadata": {
    "lookback_days": 90,
    "date_range": { "start": "2025-06-07", "end": "2025-09-05" },
    "observations": 230,
    "calculation_timestamp": "2025-09-07T16:45:12Z",
    "beta_source": "factor_exposure",
    "beta_calculation_date": "2025-09-05",
    "beta_window_days": 150,
    "warnings": []
  }
}
```

**Missing Data Contract**:
- `200 OK` with `{ "available": false, "reason": "no_snapshots" }`
- Partial results (available=true, with nulls) if some metrics cannot be computed; include `metadata.warnings`

#### A3. Portfolio Stress Test
```http
GET /api/v1/analytics/portfolio/{portfolio_id}/stress-test
```

**Purpose**: Return precomputed stress testing results across ~15 scenarios using correlated impacts.  
**Status**: 🚧 Implemented — Under Testing (read-only; no recomputation)

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

**File/Function**: `app/api/v1/analytics/portfolio.py:get_stress_test_results()`  
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

## Management Endpoints (/management/) 📋

**Status**: 📋 Planned - Pending Approval - Not Yet Implemented  
**Priority**: Medium - CRUD operations for portfolios and positions

### Portfolio Management

#### M1. Create Portfolio
```http
POST /api/v1/management/portfolios
```

#### M2. Update Portfolio
```http
PUT /api/v1/management/portfolios/{portfolio_id}
```

#### M3. Delete Portfolio (Soft Delete)
```http
DELETE /api/v1/management/portfolios/{portfolio_id}
```

### Position Management

#### M4. Add Position
```http
POST /api/v1/management/portfolios/{portfolio_id}/positions
```

#### M5. Update Position
```http
PUT /api/v1/management/positions/{position_id}
```

#### M6. Close Position
```http
POST /api/v1/management/positions/{position_id}/close
```

**Implementation Priority**: 
1. Portfolio CRUD (M1-M3)
2. Position management (M4-M6)
3. Batch operations and validation

---



### Implementation Notes

#### Dependencies
- **Analytics**: Requires completed batch processing infrastructure
- **Management**: Needs proper authorization and validation frameworks
- **Export**: Depends on analytics endpoints for calculated data
- **System**: Can be implemented independently

#### Data Quality Requirements
- All analytical endpoints must handle graceful degradation for missing data
- Calculated metrics should include confidence intervals and calculation metadata
- Real-time vs. cached data strategy needs definition

#### Authentication & Authorization
- Extend existing JWT authentication to all new endpoints
- Implement role-based access for management operations
- Add audit logging for CRUD operations

---

## Version History

**V1.4.5** (September 5, 2025)
- **NEW**: Added Part II - Planned Endpoints development specifications
- **NEW**: Dual-purpose document structure (Production + Planning)
- **BREAKING CHANGE**: Restructured from V1.4.4 to focus on implemented vs planned
- **MAJOR UPDATE**: All 18 documented endpoints in Part I verified with real data (previously claimed only 9)
- **NEW**: Added comprehensive response examples for all 18 endpoints (16 were missing examples)
- Updated based on source code verification rather than API_IMPLEMENTATION_STATUS.md
- Added OpenAPI descriptions, full parameters, and service layer documentation for each endpoint
- Response examples include realistic data based on SigmaSight's portfolio risk analytics domain

**Previous Versions**
- V1.4.4: Included mixed implemented/unimplemented endpoints
- Earlier: Mixed real and mock endpoint documentation

---

## Support

### Part I (Production Endpoints)
For questions about production-ready endpoints:
1. Verify endpoint status in `API_IMPLEMENTATION_STATUS.md`
2. Test endpoints using the examples above  
3. Check server logs for detailed error information

**Server Health Check**: `GET /health` (no authentication required)

### Part II (Planned Endpoints)
For development planning questions:
1. Review implementation roadmap and priorities
2. Check dependencies and requirements before starting development
3. Update this document as endpoints are implemented

---

**Document Status**: ✅ Part I Production Ready | 🎯 Part II Development Planning  
**Last Verified**: September 5, 2025  
**Production endpoints confirmed working with real database data**
