# EDGAR Fundamentals Integration Plan

**Project**: Integrate StockFundamentals (SEC EDGAR) into SigmaSight
**Approach**: Option A - Microservice Architecture
**Created**: 2025-12-17
**Status**: Planning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Phase 1: Infrastructure Setup](#phase-1-infrastructure-setup)
4. [Phase 2: StockFundamentals Service Deployment](#phase-2-stockfundamentals-service-deployment)
5. [Phase 3: SigmaSight Proxy Layer](#phase-3-sigmasight-proxy-layer)
6. [Phase 4: Data Caching & Persistence](#phase-4-data-caching--persistence)
7. [Phase 5: Frontend Integration](#phase-5-frontend-integration)
8. [Phase 6: Testing & Validation](#phase-6-testing--validation)
9. [Deployment Strategy](#deployment-strategy)
10. [Risk Assessment](#risk-assessment)
11. [Appendices](#appendices)

---

## 1. Executive Summary

### Objective
Integrate the StockFundamentals microservice into SigmaSight to provide users with **authoritative SEC EDGAR financial data** (10-K, 10-Q filings) alongside existing YahooQuery fundamentals.

### Value Proposition
- **Authoritative Data**: Direct from SEC EDGAR vs. third-party providers
- **60+ Financial Metrics**: Comprehensive XBRL-normalized data
- **Historical Depth**: 5+ years of quarterly and annual data
- **Non-GAAP Extraction**: AI-powered extraction from 8-K filings (future)
- **Audit Trail**: Direct links to SEC filings

### Approach
Deploy StockFundamentals as a separate microservice that SigmaSight calls via HTTP API. This maintains separation of concerns and allows independent scaling.

### Timeline Estimate
- **Total Duration**: 5-7 working days
- **Phase 1-2**: Infrastructure & Deployment (2 days)
- **Phase 3**: SigmaSight Integration Layer (2 days)
- **Phase 4**: Caching - Optional/Skip initially
- **Phase 5-6**: Frontend & Testing (2-3 days)

### Key Principle: Clean Separation
- **StockFundamentals** stays in its own repo (`bbalbalbae/StockFundamentals`)
- **SigmaSight** only adds a thin HTTP client + proxy endpoints (~300 lines)
- **No code copying** - services communicate via HTTP API

### Database Architecture (IMPORTANT)
```
┌─────────────────────────┐          ┌─────────────────────────┐
│   SigmaSight Database   │          │ StockFundamentals DB    │
│   (existing, NO CHANGES)│          │ (NEW, separate)         │
├─────────────────────────┤          ├─────────────────────────┤
│ users                   │          │ companies               │
│ portfolios              │   HTTP   │ filings                 │
│ positions               │◀────────▶│ financials              │
│ snapshots               │          │ non_gaap_adjustments    │
│ ... (existing tables)   │          │                         │
└─────────────────────────┘          └─────────────────────────┘
      │                                      │
      │ NO migrations                        │ Own Alembic
      │ NO schema changes                    │ Own migrations
      │                                      │
      └──────────────────────────────────────┘
```

**SigmaSight changes: ZERO database changes, ZERO Alembic migrations.**
All Alembic commands in this plan run in the StockFundamentals repo.

---

## 2. Architecture Overview

### Current State
```
┌─────────────────────────────────────────────────────────────┐
│                        SigmaSight                           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   Frontend  │───▶│   Backend    │───▶│  PostgreSQL   │  │
│  │  (Next.js)  │    │  (FastAPI)   │    │   (Railway)   │  │
│  └─────────────┘    └──────┬───────┘    └───────────────┘  │
│                            │                                │
│                            ▼                                │
│                    ┌───────────────┐                        │
│                    │  YahooQuery   │                        │
│                    │  (External)   │                        │
│                    └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Target State
```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SigmaSight                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐               │
│  │   Frontend  │───▶│   Backend    │───▶│  PostgreSQL   │               │
│  │  (Next.js)  │    │  (FastAPI)   │    │   (Railway)   │               │
│  └─────────────┘    └──────┬───────┘    └───────┬───────┘               │
│                            │                    │                        │
│              ┌─────────────┼────────────────────┤                        │
│              │             │                    │                        │
│              ▼             ▼                    │                        │
│    ┌───────────────┐ ┌─────────────────────────┴────────────────────┐   │
│    │  YahooQuery   │ │         StockFundamentals Service            │   │
│    │  (Fallback)   │ │  ┌──────────┐  ┌────────┐  ┌─────────────┐   │   │
│    └───────────────┘ │  │ FastAPI  │  │ Redis  │  │ PostgreSQL  │   │   │
│                      │  │  :8001   │  │ :6379  │  │   :5433     │   │   │
│                      │  └────┬─────┘  └────────┘  └─────────────┘   │   │
│                      │       │                                       │   │
│                      │       ▼                                       │   │
│                      │  ┌──────────┐                                 │   │
│                      │  │SEC EDGAR │                                 │   │
│                      │  │  (API)   │                                 │   │
│                      │  └──────────┘                                 │   │
│                      └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Service Communication
```
SigmaSight Backend                    StockFundamentals
       │                                      │
       │  GET /v1/financials/{ticker}/periods │
       │─────────────────────────────────────▶│
       │                                      │
       │  { ticker, periods: [...], ... }     │
       │◀─────────────────────────────────────│
       │                                      │
```

---

## Phase 1: Infrastructure Setup

### 1.1 Local Development Environment

**Objective**: Configure local environment to run both services.

> **Note**: Full Docker Compose configuration is in the [Deployment Strategy](#deployment-strategy) section.

#### Tasks

##### 1.1.1 Environment Variables
Add to SigmaSight `backend/.env`:

```env
# StockFundamentals Integration
STOCKFUND_API_URL=http://localhost:8001
STOCKFUND_API_KEY=sigmasight_internal_key
EDGAR_ENABLED=true
```

##### 1.1.2 Verify StockFundamentals Repo
Ensure StockFundamentals is cloned alongside SigmaSight:

```
CascadeProjects/
├── SigmaSight/           # This repo
└── StockFundamentals/    # EDGAR fundamentals service
```

#### Acceptance Criteria
- [ ] StockFundamentals repo exists at `../StockFundamentals`
- [ ] Environment variables added to SigmaSight `.env`
- [ ] Can start StockFundamentals locally on port 8001

---

### 1.2 Start Local Services

See [Deployment Strategy > Local Development](#local-development) for full Docker Compose setup and startup commands.

---

## Phase 2: StockFundamentals Service Deployment

### 2.1 Service Preparation

**Objective**: Prepare StockFundamentals for production deployment.

#### Tasks

##### 2.1.1 Configuration Updates
Update StockFundamentals config for SigmaSight integration:

```python
# StockFundamentals/backend/app/core/config.py additions
class Settings:
    # ... existing settings ...

    # SigmaSight integration
    sigmasight_mode: bool = True  # Enables SigmaSight-specific behaviors
    cache_ttl_seconds: int = 3600  # 1 hour cache for API responses
```

##### 2.1.2 Health Check Endpoint Enhancement
Ensure `/health` returns comprehensive status:

```python
@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "stockfundamentals",
        "version": "1.0.0",
        "database": await check_db_connection(),
        "redis": await check_redis_connection(),
        "edgar_api": await check_edgar_reachable()
    }
```

##### 2.1.3 Rate Limiting Configuration
Configure rate limits for EDGAR API compliance:
- Max 10 requests/second to SEC EDGAR (current: 8/sec with buffer)
- Implement request queuing for burst protection

#### Acceptance Criteria
- [ ] Health endpoint returns detailed status
- [ ] Rate limiting prevents SEC EDGAR violations
- [ ] Service starts cleanly with all dependencies

---

### 2.2 Database Initialization

#### Tasks

##### 2.2.1 Run Migrations
```bash
cd StockFundamentals/backend
uv run alembic upgrade head
```

##### 2.2.2 Verify Schema
Confirm tables exist:
- `companies` - Company CIK and metadata
- `filings` - SEC filing records
- `financials` - Normalized financial facts
- `non_gaap_adjustments` - AI-extracted metrics (future)

#### Acceptance Criteria
- [ ] All migrations applied successfully
- [ ] Tables created with correct schema
- [ ] Foreign key relationships intact

---

## Phase 3: SigmaSight Proxy Layer

### 3.1 Create EDGAR Service Client

**Objective**: Build HTTP client in SigmaSight to call StockFundamentals.

#### Tasks

##### 3.1.1 Create Service Client
Create `backend/app/services/edgar_client.py`:

```python
"""
EDGAR Fundamentals Client

HTTP client for communicating with StockFundamentals microservice.
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import date

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EdgarClientError(Exception):
    """Base exception for EDGAR client errors."""
    pass


class EdgarClient:
    """Async HTTP client for StockFundamentals API."""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: float = 30.0
    ):
        self.base_url = (base_url or settings.STOCKFUND_API_URL).rstrip("/")
        self.api_key = api_key or settings.STOCKFUND_API_KEY
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Check StockFundamentals service health."""
        client = await self._get_client()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("EDGAR service health check failed", error=str(e))
            raise EdgarClientError(f"Health check failed: {e}")

    async def get_financials(
        self,
        ticker: str,
        freq: str = "quarter",
        periods: int = 4,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Fetch multi-period financial data from EDGAR.

        Args:
            ticker: Stock ticker symbol
            freq: "quarter" or "annual"
            periods: Number of periods (max 20)
            end_date: Optional end date filter

        Returns:
            Financial data with periods array
        """
        client = await self._get_client()

        params = {
            "freq": freq,
            "periods": periods,
        }
        if end_date:
            params["end_date"] = end_date.isoformat()

        try:
            response = await client.get(
                f"/v1/financials/{ticker.upper()}/periods",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Ticker not found in EDGAR", ticker=ticker)
                return None
            logger.error("EDGAR API error", ticker=ticker, error=str(e))
            raise EdgarClientError(f"API error: {e}")
        except httpx.HTTPError as e:
            logger.error("EDGAR request failed", ticker=ticker, error=str(e))
            raise EdgarClientError(f"Request failed: {e}")

    async def get_single_period(
        self,
        ticker: str,
        period_end: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Fetch single period financial data."""
        client = await self._get_client()

        params = {}
        if period_end:
            params["period_end"] = period_end.isoformat()

        try:
            response = await client.get(
                f"/v1/financials/{ticker.upper()}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise EdgarClientError(f"API error: {e}")

    async def refresh_ticker(
        self,
        ticker: str,
        form_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger async refresh from EDGAR for a ticker."""
        client = await self._get_client()

        params = {}
        if form_type:
            params["form_type"] = form_type

        try:
            response = await client.post(
                f"/v1/financials/refresh/{ticker.upper()}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise EdgarClientError(f"Refresh failed: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


# Singleton instance
edgar_client = EdgarClient()
```

##### 3.1.2 Create Pydantic Schemas
Create `backend/app/schemas/edgar_fundamentals.py`:

```python
"""
EDGAR Fundamentals Schemas

Pydantic models for EDGAR financial data responses.
"""

from typing import Optional, Dict, List, Any
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class EdgarFinancialFields(BaseModel):
    """60+ XBRL-normalized financial fields."""

    # Income Statement
    revenue: Optional[Decimal] = None
    cost_of_revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    research_and_development: Optional[Decimal] = None
    selling_general_administrative: Optional[Decimal] = None
    stock_based_compensation: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    operating_income_loss: Optional[Decimal] = None
    interest_expense: Optional[Decimal] = None
    interest_income: Optional[Decimal] = None
    income_before_taxes: Optional[Decimal] = None
    income_tax_expense: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    earnings_per_share_basic: Optional[Decimal] = None
    earnings_per_share_diluted: Optional[Decimal] = None

    # Balance Sheet
    cash_and_equivalents: Optional[Decimal] = None
    short_term_investments: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    current_assets: Optional[Decimal] = None
    property_plant_equipment_net: Optional[Decimal] = None
    goodwill: Optional[Decimal] = None
    intangible_assets_net: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None
    accounts_payable: Optional[Decimal] = None
    current_liabilities: Optional[Decimal] = None
    long_term_debt: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    stockholders_equity: Optional[Decimal] = None

    # Cash Flow
    operating_cash_flow: Optional[Decimal] = None
    capital_expenditures: Optional[Decimal] = None
    investing_cash_flow: Optional[Decimal] = None
    financing_cash_flow: Optional[Decimal] = None
    free_cash_flow: Optional[Decimal] = None
    dividends_paid: Optional[Decimal] = None
    stock_repurchases: Optional[Decimal] = None

    class Config:
        extra = "allow"  # Allow additional XBRL fields


class EdgarPeriod(BaseModel):
    """Single reporting period from EDGAR."""

    period_end: date
    filing_type: str = Field(..., description="10-K or 10-Q")
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None  # Q1, Q2, Q3, Q4, FY
    filing_date: Optional[date] = None
    fields: EdgarFinancialFields


class EdgarCoverage(BaseModel):
    """Data coverage status."""

    required_years: int
    missing_years: List[int] = []
    missing_quarters: List[str] = []
    incomplete_periods: List[str] = []
    has_data: bool
    is_complete: bool


class EdgarFinancialsResponse(BaseModel):
    """Multi-period financial response from EDGAR."""

    ticker: str
    frequency: str
    periods: List[EdgarPeriod]
    source: str = "EDGAR XBRL"
    coverage: Optional[EdgarCoverage] = None


class EdgarHealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    database: Optional[bool] = None
    redis: Optional[bool] = None
    edgar_api: Optional[bool] = None
```

#### Acceptance Criteria
- [ ] EdgarClient successfully calls StockFundamentals
- [ ] Proper error handling and logging
- [ ] Schemas match StockFundamentals responses
- [ ] Connection pooling and timeout handling

---

### 3.2 Create API Endpoints

**Objective**: Expose EDGAR data through SigmaSight API.

#### Tasks

##### 3.2.1 Create EDGAR Router
Create `backend/app/api/v1/edgar_fundamentals.py`:

```python
"""
EDGAR Fundamentals API Endpoints

Proxy endpoints for SEC EDGAR financial data via StockFundamentals service.
"""

from typing import Optional
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.users import User
from app.services.edgar_client import edgar_client, EdgarClientError
from app.schemas.edgar_fundamentals import (
    EdgarFinancialsResponse,
    EdgarHealthResponse,
)

router = APIRouter(prefix="/edgar", tags=["EDGAR Fundamentals"])


@router.get("/health", response_model=EdgarHealthResponse)
async def check_edgar_service_health():
    """
    Check StockFundamentals service health.

    Returns service status, database connectivity, and EDGAR API reachability.
    """
    try:
        health = await edgar_client.health_check()
        return EdgarHealthResponse(**health)
    except EdgarClientError as e:
        raise HTTPException(
            status_code=503,
            detail=f"EDGAR service unavailable: {str(e)}"
        )


@router.get(
    "/financials/{ticker}/periods",
    response_model=EdgarFinancialsResponse,
    summary="Get multi-period EDGAR financials"
)
async def get_edgar_financials(
    ticker: str = Path(..., description="Stock ticker symbol"),
    freq: str = Query("quarter", description="Frequency: quarter or annual"),
    periods: int = Query(4, ge=1, le=20, description="Number of periods"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve multi-period financial data from SEC EDGAR.

    Data is sourced directly from 10-K and 10-Q filings via the
    StockFundamentals service. Includes 60+ normalized XBRL metrics.

    **Available frequencies:**
    - `quarter`: Quarterly data from 10-Q filings
    - `annual`: Annual data from 10-K filings

    **Coverage:**
    - Minimum 5 years of historical data
    - Automatic backfill from EDGAR if data missing
    """
    try:
        result = await edgar_client.get_financials(
            ticker=ticker,
            freq=freq,
            periods=periods,
            end_date=end_date,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No EDGAR data found for ticker: {ticker}"
            )

        return EdgarFinancialsResponse(**result)

    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"EDGAR service error: {str(e)}"
        )


@router.get(
    "/financials/{ticker}",
    summary="Get latest EDGAR financials"
)
async def get_edgar_latest(
    ticker: str = Path(..., description="Stock ticker symbol"),
    period_end: Optional[date] = Query(None, description="Specific period"),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve latest (or specific) period financial data from SEC EDGAR.
    """
    try:
        result = await edgar_client.get_single_period(
            ticker=ticker,
            period_end=period_end,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No EDGAR data found for ticker: {ticker}"
            )

        return result

    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"EDGAR service error: {str(e)}"
        )


@router.post(
    "/financials/refresh/{ticker}",
    summary="Refresh EDGAR data for ticker"
)
async def refresh_edgar_data(
    ticker: str = Path(..., description="Stock ticker to refresh"),
    form_type: Optional[str] = Query(None, description="10-K or 10-Q"),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger asynchronous refresh of EDGAR data for a ticker.

    This queues a background job to fetch latest filings from SEC EDGAR.
    Returns a job ID that can be used to poll status.
    """
    try:
        result = await edgar_client.refresh_ticker(
            ticker=ticker,
            form_type=form_type,
        )
        return result

    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Refresh request failed: {str(e)}"
        )
```

##### 3.2.2 Register Router
Update `backend/app/api/v1/router.py`:

```python
# Add import
from app.api.v1.edgar_fundamentals import router as edgar_router

# Add to router includes
api_router.include_router(edgar_router)
```

##### 3.2.3 Add Configuration
Update `backend/app/core/config.py`:

```python
class Settings:
    # ... existing settings ...

    # EDGAR Integration
    STOCKFUND_API_URL: str = "http://localhost:8001"
    STOCKFUND_API_KEY: str = "sigmasight_internal_key"
    EDGAR_ENABLED: bool = True
    EDGAR_CACHE_TTL: int = 3600  # 1 hour
```

#### Acceptance Criteria
- [ ] `/api/v1/edgar/health` returns service status
- [ ] `/api/v1/edgar/financials/{ticker}/periods` returns multi-period data
- [ ] `/api/v1/edgar/financials/{ticker}` returns single period
- [ ] `/api/v1/edgar/financials/refresh/{ticker}` triggers refresh
- [ ] All endpoints require authentication
- [ ] Proper error handling for service unavailability

---

## Phase 4: Response Caching (Optional)

### 4.1 In-Memory Cache

**Objective**: Optionally cache EDGAR responses to reduce latency.

> **Note**: This is optional. StockFundamentals already caches data in its own database.
> SigmaSight-side caching only helps if you want to reduce HTTP calls between services.

#### Tasks

##### 4.1.1 Simple TTL Cache (Optional)
If needed, add a simple in-memory cache to `edgar_client.py`:

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Simple approach: use lru_cache with manual expiry check
# Or skip entirely - StockFundamentals handles its own caching
```

#### Decision Point
- **Skip caching**: StockFundamentals caches in its DB, responses are fast
- **Add caching**: Only if HTTP latency becomes an issue in production

**Recommendation**: Start without SigmaSight-side caching. Add later if needed.

---

### 4.2 No Database Changes Required

**Important**: SigmaSight does NOT need any database changes for this integration.

- StockFundamentals maintains its own PostgreSQL database
- SigmaSight calls StockFundamentals via HTTP API
- No Alembic migrations needed in SigmaSight
- Existing `fundamentals_service.py` (Yahoo) remains unchanged

---

## Phase 5: Frontend Integration

### 5.1 API Service

**Objective**: Create frontend service for EDGAR fundamentals.

#### Tasks

##### 5.1.1 Create EDGAR Service
Create `frontend/src/services/edgarApi.ts`:

```typescript
/**
 * EDGAR Fundamentals API Service
 *
 * Client for SEC EDGAR financial data via SigmaSight backend.
 */

import { apiClient } from './apiClient';

export interface EdgarFinancialFields {
  revenue?: number;
  cost_of_revenue?: number;
  gross_profit?: number;
  research_and_development?: number;
  operating_income_loss?: number;
  net_income?: number;
  earnings_per_share_basic?: number;
  earnings_per_share_diluted?: number;
  total_assets?: number;
  total_liabilities?: number;
  stockholders_equity?: number;
  operating_cash_flow?: number;
  capital_expenditures?: number;
  free_cash_flow?: number;
  // ... 60+ fields
  [key: string]: number | undefined;
}

export interface EdgarPeriod {
  period_end: string;
  filing_type: string;
  fiscal_year?: number;
  fiscal_period?: string;
  filing_date?: string;
  fields: EdgarFinancialFields;
}

export interface EdgarFinancialsResponse {
  ticker: string;
  frequency: string;
  periods: EdgarPeriod[];
  source: string;
  coverage?: {
    required_years: number;
    missing_years: number[];
    missing_quarters: string[];
    is_complete: boolean;
  };
}

export interface EdgarHealthResponse {
  status: string;
  service: string;
  version: string;
  database?: boolean;
  redis?: boolean;
  edgar_api?: boolean;
}

class EdgarApi {
  private basePath = '/api/v1/edgar';

  /**
   * Check EDGAR service health
   */
  async checkHealth(): Promise<EdgarHealthResponse> {
    const response = await apiClient.get<EdgarHealthResponse>(
      `${this.basePath}/health`
    );
    return response.data;
  }

  /**
   * Get multi-period financial data from EDGAR
   */
  async getFinancials(
    ticker: string,
    options?: {
      freq?: 'quarter' | 'annual';
      periods?: number;
      endDate?: string;
    }
  ): Promise<EdgarFinancialsResponse> {
    const params = new URLSearchParams();
    if (options?.freq) params.append('freq', options.freq);
    if (options?.periods) params.append('periods', options.periods.toString());
    if (options?.endDate) params.append('end_date', options.endDate);

    const response = await apiClient.get<EdgarFinancialsResponse>(
      `${this.basePath}/financials/${ticker}/periods?${params.toString()}`
    );
    return response.data;
  }

  /**
   * Get latest financial data for a ticker
   */
  async getLatest(
    ticker: string,
    periodEnd?: string
  ): Promise<EdgarPeriod> {
    const params = periodEnd ? `?period_end=${periodEnd}` : '';
    const response = await apiClient.get<EdgarPeriod>(
      `${this.basePath}/financials/${ticker}${params}`
    );
    return response.data;
  }

  /**
   * Trigger refresh of EDGAR data
   */
  async refreshTicker(
    ticker: string,
    formType?: '10-K' | '10-Q'
  ): Promise<{ job_id: string; status: string }> {
    const params = formType ? `?form_type=${formType}` : '';
    const response = await apiClient.post(
      `${this.basePath}/financials/refresh/${ticker}${params}`
    );
    return response.data;
  }
}

export const edgarApi = new EdgarApi();
export default edgarApi;
```

##### 5.1.2 Create React Hook
Create `frontend/src/hooks/useEdgarFundamentals.ts`:

```typescript
/**
 * Hook for fetching EDGAR fundamentals data
 */

import { useState, useEffect, useCallback } from 'react';
import { edgarApi, EdgarFinancialsResponse } from '@/services/edgarApi';

interface UseEdgarFundamentalsOptions {
  freq?: 'quarter' | 'annual';
  periods?: number;
  enabled?: boolean;
}

interface UseEdgarFundamentalsResult {
  data: EdgarFinancialsResponse | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useEdgarFundamentals(
  ticker: string | null,
  options: UseEdgarFundamentalsOptions = {}
): UseEdgarFundamentalsResult {
  const { freq = 'quarter', periods = 4, enabled = true } = options;

  const [data, setData] = useState<EdgarFinancialsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!ticker || !enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await edgarApi.getFinancials(ticker, { freq, periods });
      setData(result);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch EDGAR data';
      setError(message);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [ticker, freq, periods, enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}
```

#### Acceptance Criteria
- [ ] Service correctly calls backend API
- [ ] Hook manages loading/error states
- [ ] TypeScript types match API responses
- [ ] Refetch functionality works

---

### 5.2 UI Components

**Objective**: Create components to display EDGAR data.

#### Tasks

##### 5.2.1 Financial Table Component
Create `frontend/src/components/fundamentals/EdgarFinancialsTable.tsx`:

```typescript
/**
 * EDGAR Financials Table Component
 *
 * Displays multi-period financial data in a comparison table.
 */

'use client';

import React from 'react';
import { EdgarFinancialsResponse, EdgarPeriod } from '@/services/edgarApi';
import { formatCurrency, formatNumber } from '@/lib/formatters';

interface EdgarFinancialsTableProps {
  data: EdgarFinancialsResponse;
  showAllFields?: boolean;
}

// Key metrics to display by default
const KEY_METRICS = [
  { key: 'revenue', label: 'Revenue' },
  { key: 'gross_profit', label: 'Gross Profit' },
  { key: 'operating_income_loss', label: 'Operating Income' },
  { key: 'net_income', label: 'Net Income' },
  { key: 'earnings_per_share_diluted', label: 'EPS (Diluted)' },
  { key: 'total_assets', label: 'Total Assets' },
  { key: 'total_liabilities', label: 'Total Liabilities' },
  { key: 'stockholders_equity', label: 'Stockholders Equity' },
  { key: 'operating_cash_flow', label: 'Operating Cash Flow' },
  { key: 'free_cash_flow', label: 'Free Cash Flow' },
];

export function EdgarFinancialsTable({
  data,
  showAllFields = false,
}: EdgarFinancialsTableProps) {
  const metrics = showAllFields
    ? Object.keys(data.periods[0]?.fields || {}).map(key => ({
        key,
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      }))
    : KEY_METRICS;

  const formatValue = (value: number | undefined, key: string): string => {
    if (value === undefined || value === null) return '—';

    // EPS and per-share metrics
    if (key.includes('per_share') || key.includes('eps')) {
      return `$${value.toFixed(2)}`;
    }

    // Large currency values (in millions)
    if (Math.abs(value) >= 1_000_000) {
      return formatCurrency(value / 1_000_000) + 'M';
    }

    return formatNumber(value);
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Metric
            </th>
            {data.periods.map((period) => (
              <th
                key={period.period_end}
                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase"
              >
                {period.fiscal_period || period.period_end}
                <div className="text-xs font-normal text-gray-400">
                  {period.filing_type}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {metrics.map(({ key, label }) => (
            <tr key={key} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                {label}
              </td>
              {data.periods.map((period) => (
                <td
                  key={`${period.period_end}-${key}`}
                  className="px-4 py-3 text-sm text-right text-gray-700"
                >
                  {formatValue(period.fields[key], key)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-2 text-xs text-gray-500">
        Source: {data.source} | Data as of most recent filing
      </div>
    </div>
  );
}
```

##### 5.2.2 Data Source Toggle
Create component to switch between EDGAR and Yahoo data:

```typescript
/**
 * Data Source Selector
 */

'use client';

import React from 'react';

interface DataSourceSelectorProps {
  source: 'edgar' | 'yahoo';
  onChange: (source: 'edgar' | 'yahoo') => void;
}

export function DataSourceSelector({
  source,
  onChange,
}: DataSourceSelectorProps) {
  return (
    <div className="flex items-center space-x-2">
      <span className="text-sm text-gray-600">Data Source:</span>
      <div className="flex rounded-md shadow-sm">
        <button
          onClick={() => onChange('edgar')}
          className={`px-3 py-1 text-sm rounded-l-md border ${
            source === 'edgar'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          SEC EDGAR
        </button>
        <button
          onClick={() => onChange('yahoo')}
          className={`px-3 py-1 text-sm rounded-r-md border-t border-b border-r ${
            source === 'yahoo'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          Yahoo Finance
        </button>
      </div>
    </div>
  );
}
```

#### Acceptance Criteria
- [ ] Table displays financial data correctly
- [ ] Values formatted appropriately
- [ ] Toggle switches data sources
- [ ] Responsive design works

---

## Phase 6: Testing & Validation

### 6.1 Backend Testing

#### Tasks

##### 6.1.1 Unit Tests
Create `backend/tests/test_edgar_client.py`:

```python
"""Tests for EDGAR client."""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.edgar_client import EdgarClient, EdgarClientError


@pytest.fixture
def edgar_client():
    return EdgarClient(
        base_url="http://test:8001",
        api_key="test_key"
    )


@pytest.mark.asyncio
async def test_get_financials_success(edgar_client):
    """Test successful financial data retrieval."""
    mock_response = {
        "ticker": "AAPL",
        "frequency": "quarter",
        "periods": [
            {
                "period_end": "2024-09-30",
                "filing_type": "10-Q",
                "fields": {"revenue": 94930000000}
            }
        ]
    }

    with patch.object(edgar_client, '_get_client') as mock_get:
        mock_client = AsyncMock()
        mock_client.get.return_value.json.return_value = mock_response
        mock_client.get.return_value.raise_for_status = lambda: None
        mock_get.return_value = mock_client

        result = await edgar_client.get_financials("AAPL")

        assert result["ticker"] == "AAPL"
        assert len(result["periods"]) == 1


@pytest.mark.asyncio
async def test_get_financials_not_found(edgar_client):
    """Test 404 response handling."""
    with patch.object(edgar_client, '_get_client') as mock_get:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        mock_client.get.return_value.raise_for_status.side_effect = Exception()
        mock_get.return_value = mock_client

        result = await edgar_client.get_financials("INVALID")
        assert result is None
```

##### 6.1.2 Integration Tests
Create `backend/tests/test_edgar_integration.py`:

```python
"""Integration tests for EDGAR endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_edgar_health_endpoint():
    """Test EDGAR health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/edgar/health")
        # Will fail if StockFundamentals not running
        assert response.status_code in [200, 503]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_edgar_financials_endpoint(auth_headers):
    """Test EDGAR financials endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/edgar/financials/AAPL/periods",
            headers=auth_headers,
            params={"periods": 4}
        )
        assert response.status_code in [200, 404, 502]
```

#### Acceptance Criteria
- [ ] Unit tests pass without external dependencies
- [ ] Integration tests verify end-to-end flow
- [ ] Error cases properly tested
- [ ] Test coverage > 80%

---

### 6.2 Frontend Testing

#### Tasks

##### 6.2.1 Component Tests
Create `frontend/src/components/fundamentals/__tests__/EdgarFinancialsTable.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { EdgarFinancialsTable } from '../EdgarFinancialsTable';

const mockData = {
  ticker: 'AAPL',
  frequency: 'quarter',
  periods: [
    {
      period_end: '2024-09-30',
      filing_type: '10-Q',
      fiscal_period: 'Q4',
      fields: {
        revenue: 94930000000,
        net_income: 21448000000,
      },
    },
  ],
  source: 'EDGAR XBRL',
};

describe('EdgarFinancialsTable', () => {
  it('renders financial data correctly', () => {
    render(<EdgarFinancialsTable data={mockData} />);

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Q4')).toBeInTheDocument();
  });

  it('formats large numbers in millions', () => {
    render(<EdgarFinancialsTable data={mockData} />);

    // Revenue should show as ~$94,930M
    expect(screen.getByText(/94.*M/)).toBeInTheDocument();
  });
});
```

#### Acceptance Criteria
- [ ] Component tests pass
- [ ] Data formatting verified
- [ ] Accessibility tested
- [ ] Responsive layout tested

---

## Deployment Strategy

### Infrastructure Choice: Option 2 (Core Stack)

**Selected Stack:**
```
PostgreSQL + Redis + Celery Worker (No MinIO)
```

**Rationale:**
- Full 60+ XBRL metrics from 10-K/10-Q filings
- Background jobs prevent API timeouts on EDGAR fetches
- No MinIO complexity - can add Non-GAAP AI extraction later
- Redis is cheap on Railway ($5/mo or free tier)

---

### Local Development

#### Docker Compose Setup
Create `docker-compose.dev.yml` in SigmaSight root:

```yaml
version: '3.8'

services:
  # ============================================
  # SIGMASIGHT SERVICES (existing)
  # ============================================
  sigmasight-db:
    image: postgres:15
    container_name: sigmasight-db
    environment:
      POSTGRES_USER: sigmasight
      POSTGRES_PASSWORD: sigmasight_dev
      POSTGRES_DB: sigmasight_db
    ports:
      - "5432:5432"
    volumes:
      - sigmasight_postgres_data:/var/lib/postgresql/data
    networks:
      - sigmasight-network

  # ============================================
  # STOCKFUNDAMENTALS SERVICES
  # ============================================
  stockfund-db:
    image: postgres:15
    container_name: stockfund-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: stock_fundamentals
    ports:
      - "5433:5432"
    volumes:
      - stockfund_postgres_data:/var/lib/postgresql/data
    networks:
      - sigmasight-network

  stockfund-redis:
    image: redis:7-alpine
    container_name: stockfund-redis
    ports:
      - "6379:6379"
    networks:
      - sigmasight-network

volumes:
  sigmasight_postgres_data:
  stockfund_postgres_data:

networks:
  sigmasight-network:
    driver: bridge
```

#### Start Local Development
```bash
# 1. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# 2. Start StockFundamentals API (in separate terminal)
cd ../StockFundamentals/backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001

# 3. Start StockFundamentals Celery worker (in separate terminal)
cd ../StockFundamentals/backend
uv run celery -A app.tasks.worker worker -l info

# 4. Start SigmaSight backend
cd backend && uv run python run.py

# 5. Start SigmaSight frontend
cd frontend && npm run dev
```

---

### Railway Deployment

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Railway Platform                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              SigmaSight Project (existing)                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │   Frontend   │  │   Backend    │  │   PostgreSQL     │   │   │
│  │  │   (Next.js)  │  │   (FastAPI)  │  │   (existing)     │   │   │
│  │  └──────────────┘  └──────┬───────┘  └──────────────────┘   │   │
│  └───────────────────────────┼─────────────────────────────────┘   │
│                              │                                      │
│                              │ HTTP (private network)               │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           StockFundamentals Project (NEW)                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │   API        │  │   Celery     │  │   PostgreSQL     │   │   │
│  │  │   (FastAPI)  │  │   Worker     │  │   (separate)     │   │   │
│  │  │   :8000      │  │              │  │                  │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────┐                                            │   │
│  │  │    Redis     │                                            │   │
│  │  │              │                                            │   │
│  │  └──────────────┘                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Step 1: Create StockFundamentals Railway Project

```bash
# 1. Navigate to StockFundamentals repo
cd ~/CascadeProjects/StockFundamentals

# 2. Login to Railway CLI
railway login

# 3. Create new project
railway init
# Name: stockfundamentals-prod (or stockfundamentals-sandbox)
```

#### Step 2: Add PostgreSQL Database

```bash
# Add PostgreSQL plugin to the project
railway add --plugin postgresql

# Or via Railway Dashboard:
# 1. Open project in Railway dashboard
# 2. Click "New" → "Database" → "PostgreSQL"
# 3. Wait for provisioning
```

#### Step 3: Add Redis

```bash
# Add Redis plugin
railway add --plugin redis

# Or via Railway Dashboard:
# 1. Click "New" → "Database" → "Redis"
# 2. Wait for provisioning
```

#### Step 4: Deploy API Service

**Create `Dockerfile` in StockFundamentals/backend:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Create `railway.toml` in StockFundamentals/backend:**
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
numReplicas = 1
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

**Deploy via CLI:**
```bash
cd backend
railway up
```

#### Step 5: Deploy Celery Worker Service

**Create `Dockerfile.worker` in StockFundamentals/backend:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Run Celery worker
CMD ["uv", "run", "celery", "-A", "app.tasks.worker", "worker", "-l", "info", "--concurrency", "2"]
```

**In Railway Dashboard:**
1. Click "New" → "Empty Service"
2. Name it "celery-worker"
3. Connect to same GitHub repo
4. Set Dockerfile path: `backend/Dockerfile.worker`
5. Link to same PostgreSQL and Redis

#### Step 6: Configure Environment Variables

**StockFundamentals API Service:**
```env
# Database (auto-populated by Railway plugin)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (auto-populated by Railway plugin)
REDIS_URL=${{Redis.REDIS_URL}}

# SEC EDGAR Configuration
EDGAR_USER_AGENT=SigmaSight Platform (contact@sigmasight.com)

# API Authentication
API_KEYS=sigmasight_internal_abc123xyz,devtoken123

# Disable MinIO/S3 (not using Non-GAAP extraction)
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=

# Optional: Anthropic (only if enabling Non-GAAP later)
# ANTHROPIC_API_KEY=
```

**StockFundamentals Celery Worker:**
```env
# Same database and redis
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Same EDGAR config
EDGAR_USER_AGENT=SigmaSight Platform (contact@sigmasight.com)
```

#### Step 7: Enable Private Networking

Railway provides private networking between services in the same project and across projects.

**Get the private URL:**
1. In Railway dashboard, click on the API service
2. Go to Settings → Networking
3. Enable "Private Networking"
4. Copy the private URL: `stockfundamentals-api.railway.internal`

**For cross-project communication:**
1. Both projects must be in the same Railway team/account
2. Use the private DNS: `<service-name>.<project-name>.railway.internal`

#### Step 8: Update SigmaSight Configuration

**Add to SigmaSight backend environment (Railway):**
```env
# StockFundamentals Integration
STOCKFUND_API_URL=http://stockfundamentals-api.railway.internal:8000
STOCKFUND_API_KEY=sigmasight_internal_abc123xyz
EDGAR_ENABLED=true
```

**Or if separate Railway projects, use public URL temporarily:**
```env
# Public URL (less ideal, but works across projects)
STOCKFUND_API_URL=https://stockfundamentals-prod.up.railway.app
STOCKFUND_API_KEY=sigmasight_internal_abc123xyz
EDGAR_ENABLED=true
```

#### Step 9: Verify Deployment

```bash
# Test StockFundamentals health endpoint
curl https://stockfundamentals-prod.up.railway.app/health

# Expected response:
{
  "status": "ok",
  "service": "stockfundamentals",
  "version": "1.0.0"
}

# Test financial data endpoint
curl -H "X-API-Key: sigmasight_internal_abc123xyz" \
  "https://stockfundamentals-prod.up.railway.app/v1/financials/AAPL/periods?periods=4"
```

---

### Railway Cost Estimate

| Service | Railway Plan | Estimated Cost |
|---------|--------------|----------------|
| StockFundamentals API | Hobby | ~$5/mo |
| Celery Worker | Hobby | ~$5/mo |
| PostgreSQL | Hobby | ~$5/mo |
| Redis | Hobby | ~$0-5/mo |
| **Total** | | **~$15-20/mo** |

*Note: Costs vary based on usage. The Hobby plan includes $5 free credits.*

---

### Alternative: Single Railway Project

If you want to keep everything in one Railway project:

1. Add StockFundamentals services to existing SigmaSight project
2. Use shared PostgreSQL or add a second one
3. Simpler networking (all services in same project)
4. More services to manage in one place

**Recommendation:** Start with separate projects for cleaner separation, merge later if desired.

---

## Risk Assessment

### High Risk
| Risk | Mitigation |
|------|------------|
| SEC EDGAR rate limiting | Implemented 8 req/sec limit with backoff |
| StockFundamentals service downtime | Fallback to YahooQuery, caching layer |
| Data inconsistency between sources | Clear source labeling in UI |

### Medium Risk
| Risk | Mitigation |
|------|------------|
| Network latency between services | Response caching, connection pooling |
| Redis/infrastructure complexity | Can deploy without Celery initially |
| API versioning conflicts | Version-pinned internal API calls |

### Low Risk
| Risk | Mitigation |
|------|------------|
| Schema changes in EDGAR | XBRL mapping is standardized |
| Authentication complexity | Simple API key for internal communication |

---

## Appendices

### A. XBRL Field Mapping (60+ fields)

See `StockFundamentals/backend/config/xbrl_map.json` for complete mapping.

**Income Statement** (15 fields):
- revenue, cost_of_revenue, gross_profit
- research_and_development, selling_general_administrative
- operating_income_loss, net_income, earnings_per_share_*

**Balance Sheet** (20 fields):
- cash_and_equivalents, accounts_receivable, inventory
- total_assets, total_liabilities, stockholders_equity

**Cash Flow** (15 fields):
- operating_cash_flow, capital_expenditures
- investing_cash_flow, financing_cash_flow

### B. API Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/edgar/health` | GET | Service health check |
| `/api/v1/edgar/financials/{ticker}/periods` | GET | Multi-period financials |
| `/api/v1/edgar/financials/{ticker}` | GET | Single period financials |
| `/api/v1/edgar/financials/refresh/{ticker}` | POST | Trigger data refresh |

### C. File Checklist

**SigmaSight Backend (integration layer only):**
- [ ] `app/services/edgar_client.py` - HTTP client (~100 lines)
- [ ] `app/schemas/edgar_fundamentals.py` - Response schemas (~80 lines)
- [ ] `app/api/v1/edgar_fundamentals.py` - Proxy endpoints (~80 lines)
- [ ] `tests/test_edgar_client.py` - Unit tests

**SigmaSight Frontend:**
- [ ] `src/services/edgarApi.ts` - API service (~60 lines)
- [ ] `src/hooks/useEdgarFundamentals.ts` - React hook (~40 lines)
- [ ] `src/components/fundamentals/EdgarFinancialsTable.tsx` - Display component

**Configuration Updates:**
- [ ] `docker-compose.dev.yml` (new file for local dev)
- [ ] `backend/.env` (add 3 EDGAR variables)
- [ ] `backend/app/core/config.py` (add 3 settings)
- [ ] `backend/app/api/v1/router.py` (1 line to register router)

**StockFundamentals Repo (NO CHANGES to SigmaSight):**
- Stays in separate `bbalbalbae/StockFundamentals` repo
- Has its own database, migrations, models
- Deployed as separate service (Railway project or Docker container)
- SigmaSight only calls it via HTTP API

---

## Next Steps

1. **Review and approve this plan**
2. **Phase 1**: Set up local development environment with Docker
3. **Phase 2**: Deploy and test StockFundamentals locally
4. **Phase 3**: Build SigmaSight proxy layer
5. **Phase 4**: Implement caching
6. **Phase 5**: Frontend integration
7. **Phase 6**: Testing and validation
8. **Deploy to Railway**

---

*Document created by Claude Code*
*Last updated: 2025-12-17*
