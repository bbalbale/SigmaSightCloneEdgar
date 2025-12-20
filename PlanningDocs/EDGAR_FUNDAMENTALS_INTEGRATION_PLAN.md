# EDGAR Fundamentals Integration Plan

**Project**: Integrate StockFundamentals (SEC EDGAR) into SigmaSight
**Approach**: Option A - Microservice Architecture (Same Railway Project)
**Created**: 2025-12-17
**Updated**: 2025-12-19
**Status**: Planning (Revised)

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
10. [Monitoring & Alerting](#monitoring--alerting)
11. [Rollback Strategy](#rollback-strategy)
12. [Risk Assessment](#risk-assessment)
13. [Appendices](#appendices)

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
Deploy StockFundamentals as services **within the existing SigmaSight Railway project**. This enables Railway's private networking between services while maintaining code separation (separate Git repos). Services communicate via HTTP API over Railway's internal network.

> ⚠️ **Critical Decision**: Railway private networking (`*.railway.internal`) only works within the SAME project. Deploying as separate Railway projects would require public URLs, adding latency and security exposure.

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

### Gradual Rollout Strategy
1. **Phase A**: Deploy with `EDGAR_ENABLED=false` - service runs but endpoints hidden
2. **Phase B**: Enable for internal testing - flip flag, verify data quality
3. **Phase C**: Enable UI toggle - users can switch between EDGAR and Yahoo
4. **Phase D**: Make EDGAR default - Yahoo becomes fallback

### Simplified Initial Deployment
Start **without Celery/Redis** for faster initial deployment:
- Synchronous EDGAR API calls (acceptable for user-triggered requests)
- Add Celery later when async refresh jobs become necessary
- Reduces Railway cost from ~$20/mo to ~$10/mo initially

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

### Target State (Same Railway Project)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Railway Project: SigmaSight                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     EXISTING SERVICES                                │    │
│  │  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐           │    │
│  │  │   Frontend  │───▶│   Backend    │───▶│  PostgreSQL   │           │    │
│  │  │  (Next.js)  │    │  (FastAPI)   │    │   (existing)  │           │    │
│  │  └─────────────┘    └──────┬───────┘    └───────────────┘           │    │
│  └────────────────────────────┼─────────────────────────────────────────┘    │
│                               │                                              │
│                               │ HTTP (*.railway.internal)                    │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     NEW SERVICES (StockFundamentals)                 │    │
│  │  ┌──────────────┐           ┌─────────────────┐                     │    │
│  │  │ stockfund-api│           │ stockfund-db    │                     │    │
│  │  │  (FastAPI)   │──────────▶│ (PostgreSQL)    │                     │    │
│  │  │  :8000       │           │ (separate DB)   │                     │    │
│  │  └──────┬───────┘           └─────────────────┘                     │    │
│  │         │                                                            │    │
│  │         ▼                                                            │    │
│  │  ┌──────────────┐                                                   │    │
│  │  │  SEC EDGAR   │   ┌───────────────────────────────────────────┐   │    │
│  │  │  (External)  │   │ OPTIONAL (Phase 2): Redis + Celery Worker │   │    │
│  │  └──────────────┘   └───────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│         YahooQuery (External) ◀─── Fallback when EDGAR unavailable          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Benefits of Same Project:**
- Private networking works (`stockfund-api.railway.internal`)
- Shared environment variable references
- Single billing/monitoring dashboard
- Simpler deployment coordination

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
Uses FastAPI dependency injection for proper lifecycle management.
"""

import httpx
from typing import Optional, Dict, Any
from datetime import date
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EdgarClientError(Exception):
    """Base exception for EDGAR client errors."""
    pass


class EdgarServiceUnavailable(EdgarClientError):
    """Raised when StockFundamentals service is unreachable."""
    pass


class EdgarTickerNotFound(EdgarClientError):
    """Raised when ticker has no EDGAR data."""
    pass


class EdgarClient:
    """
    Async HTTP client for StockFundamentals API.

    Uses dependency injection pattern - do NOT instantiate at module level.
    Use get_edgar_client() dependency instead.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
                # Connection pooling settings
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                ),
            )
        return self._client

    async def close(self):
        """Close HTTP client and release connections."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> Dict[str, Any]:
        """Check StockFundamentals service health."""
        client = await self._get_client()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            logger.error("EDGAR service unreachable", error=str(e))
            raise EdgarServiceUnavailable(f"Service unreachable: {e}")
        except httpx.TimeoutException as e:
            logger.error("EDGAR service timeout", error=str(e))
            raise EdgarServiceUnavailable(f"Service timeout: {e}")
        except httpx.HTTPError as e:
            logger.error("EDGAR service health check failed", error=str(e))
            raise EdgarClientError(f"Health check failed: {e}")

    async def get_financials(
        self,
        ticker: str,
        freq: str = "quarter",
        periods: int = 4,
        end_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch multi-period financial data from EDGAR.

        Args:
            ticker: Stock ticker symbol
            freq: "quarter" or "annual"
            periods: Number of periods (max 20)
            end_date: Optional end date filter

        Returns:
            Financial data with periods array, or None if ticker not found

        Raises:
            EdgarServiceUnavailable: Service is down or unreachable
            EdgarClientError: Other API errors
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
        except httpx.ConnectError as e:
            logger.error("EDGAR service unreachable", ticker=ticker, error=str(e))
            raise EdgarServiceUnavailable(f"Service unreachable: {e}")
        except httpx.TimeoutException as e:
            logger.error("EDGAR request timeout", ticker=ticker, error=str(e))
            raise EdgarServiceUnavailable(f"Request timeout: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info("Ticker not found in EDGAR", ticker=ticker)
                return None
            if e.response.status_code >= 500:
                logger.error("EDGAR service error", ticker=ticker, status=e.response.status_code)
                raise EdgarServiceUnavailable(f"Service error: {e.response.status_code}")
            logger.error("EDGAR API error", ticker=ticker, error=str(e))
            raise EdgarClientError(f"API error: {e}")
        except httpx.HTTPError as e:
            logger.error("EDGAR request failed", ticker=ticker, error=str(e))
            raise EdgarClientError(f"Request failed: {e}")

    async def get_single_period(
        self,
        ticker: str,
        period_end: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
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
        except httpx.ConnectError as e:
            raise EdgarServiceUnavailable(f"Service unreachable: {e}")
        except httpx.TimeoutException as e:
            raise EdgarServiceUnavailable(f"Request timeout: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            if e.response.status_code >= 500:
                raise EdgarServiceUnavailable(f"Service error: {e.response.status_code}")
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
        except httpx.ConnectError as e:
            raise EdgarServiceUnavailable(f"Service unreachable: {e}")
        except httpx.HTTPError as e:
            raise EdgarClientError(f"Refresh failed: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


# ============================================================================
# FastAPI Dependency Injection
# ============================================================================

# Global client instance - initialized via lifespan
_edgar_client: Optional[EdgarClient] = None


@asynccontextmanager
async def edgar_client_lifespan(app):
    """
    FastAPI lifespan context manager for EdgarClient.

    Usage in main.py:
        from app.services.edgar_client import edgar_client_lifespan

        app = FastAPI(lifespan=edgar_client_lifespan)
    """
    global _edgar_client

    if settings.EDGAR_ENABLED:
        _edgar_client = EdgarClient(
            base_url=settings.STOCKFUND_API_URL,
            api_key=settings.STOCKFUND_API_KEY,
        )
        logger.info("EdgarClient initialized", base_url=settings.STOCKFUND_API_URL)

    yield

    if _edgar_client:
        await _edgar_client.close()
        logger.info("EdgarClient closed")


async def get_edgar_client() -> Optional[EdgarClient]:
    """
    FastAPI dependency for EdgarClient.

    Returns None if EDGAR is disabled, allowing graceful degradation.

    Usage:
        @router.get("/financials/{ticker}")
        async def get_financials(
            ticker: str,
            edgar: Optional[EdgarClient] = Depends(get_edgar_client)
        ):
            if edgar is None:
                raise HTTPException(503, "EDGAR service disabled")
            ...
    """
    if not settings.EDGAR_ENABLED:
        return None
    return _edgar_client
```

> ⚠️ **Important Changes from Original:**
> 1. No module-level singleton - uses FastAPI lifespan for proper initialization
> 2. Specific exception types (`EdgarServiceUnavailable`, `EdgarTickerNotFound`)
> 3. Handles `ConnectError` and `TimeoutException` separately
> 4. Returns `None` when EDGAR disabled (graceful degradation)

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


class EdgarRefreshResponse(BaseModel):
    """Response from refresh endpoint."""

    ticker: str
    status: str = Field(..., description="pending, in_progress, or completed")
    job_id: Optional[str] = Field(None, description="Background job ID (if async)")
    message: Optional[str] = None
    filings_found: Optional[int] = None
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
Uses dependency injection for proper client lifecycle management.
"""

from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.users import User
from app.services.edgar_client import (
    EdgarClient,
    EdgarClientError,
    EdgarServiceUnavailable,
    get_edgar_client,
)
from app.schemas.edgar_fundamentals import (
    EdgarFinancialsResponse,
    EdgarHealthResponse,
    EdgarPeriod,
    EdgarRefreshResponse,
)

router = APIRouter(prefix="/edgar", tags=["EDGAR Fundamentals"])


def _check_edgar_enabled(edgar: Optional[EdgarClient]) -> EdgarClient:
    """Helper to check if EDGAR is enabled and client is available."""
    if not settings.EDGAR_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="EDGAR integration is disabled. Set EDGAR_ENABLED=true to enable."
        )
    if edgar is None:
        raise HTTPException(
            status_code=503,
            detail="EDGAR client not initialized. Check service configuration."
        )
    return edgar


@router.get("/health", response_model=EdgarHealthResponse)
async def check_edgar_service_health(
    edgar: Optional[EdgarClient] = Depends(get_edgar_client),
):
    """
    Check StockFundamentals service health.

    Returns service status, database connectivity, and EDGAR API reachability.
    Does not require authentication - useful for monitoring.
    """
    client = _check_edgar_enabled(edgar)

    try:
        health = await client.health_check()
        return EdgarHealthResponse(**health)
    except EdgarServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"EDGAR service unavailable: {str(e)}"
        )
    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"EDGAR service error: {str(e)}"
        )


@router.get(
    "/financials/{ticker}/periods",
    response_model=EdgarFinancialsResponse,
    summary="Get multi-period EDGAR financials"
)
async def get_edgar_financials(
    ticker: str = Path(..., description="Stock ticker symbol", min_length=1, max_length=10),
    freq: str = Query("quarter", regex="^(quarter|annual)$", description="Frequency: quarter or annual"),
    periods: int = Query(4, ge=1, le=20, description="Number of periods"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    edgar: Optional[EdgarClient] = Depends(get_edgar_client),
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
    client = _check_edgar_enabled(edgar)

    try:
        result = await client.get_financials(
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

    except EdgarServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"EDGAR service unavailable: {str(e)}"
        )
    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"EDGAR service error: {str(e)}"
        )


@router.get(
    "/financials/{ticker}",
    response_model=EdgarPeriod,  # Fixed: Now returns typed response
    summary="Get latest EDGAR financials"
)
async def get_edgar_latest(
    ticker: str = Path(..., description="Stock ticker symbol", min_length=1, max_length=10),
    period_end: Optional[date] = Query(None, description="Specific period"),
    current_user: User = Depends(get_current_user),
    edgar: Optional[EdgarClient] = Depends(get_edgar_client),
):
    """
    Retrieve latest (or specific) period financial data from SEC EDGAR.
    """
    client = _check_edgar_enabled(edgar)

    try:
        result = await client.get_single_period(
            ticker=ticker,
            period_end=period_end,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No EDGAR data found for ticker: {ticker}"
            )

        return EdgarPeriod(**result)  # Fixed: Now returns typed response

    except EdgarServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"EDGAR service unavailable: {str(e)}"
        )
    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"EDGAR service error: {str(e)}"
        )


@router.post(
    "/financials/refresh/{ticker}",
    response_model=EdgarRefreshResponse,  # Fixed: Now returns typed response
    summary="Refresh EDGAR data for ticker"
)
async def refresh_edgar_data(
    ticker: str = Path(..., description="Stock ticker to refresh", min_length=1, max_length=10),
    form_type: Optional[str] = Query(None, regex="^(10-K|10-Q)$", description="10-K or 10-Q"),
    current_user: User = Depends(get_current_user),
    edgar: Optional[EdgarClient] = Depends(get_edgar_client),
):
    """
    Trigger asynchronous refresh of EDGAR data for a ticker.

    This queues a background job to fetch latest filings from SEC EDGAR.
    Returns a job ID that can be used to poll status.

    Note: Without Celery, this runs synchronously and may take 10-30 seconds.
    """
    client = _check_edgar_enabled(edgar)

    try:
        result = await client.refresh_ticker(
            ticker=ticker,
            form_type=form_type,
        )
        return EdgarRefreshResponse(**result)

    except EdgarServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"EDGAR service unavailable: {str(e)}"
        )
    except EdgarClientError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Refresh request failed: {str(e)}"
        )
```

> ⚠️ **Important Changes from Original:**
> 1. Uses dependency injection (`Depends(get_edgar_client)`) instead of global singleton
> 2. All endpoints now return typed Pydantic models (fixed inconsistency)
> 3. Added input validation (regex for freq, min/max length for ticker)
> 4. Separate handling for `EdgarServiceUnavailable` (503) vs `EdgarClientError` (502)
> 5. Helper function `_check_edgar_enabled()` for consistent EDGAR status checking

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
 *
 * Uses stable dependencies to prevent infinite refetch loops.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
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
  isServiceAvailable: boolean;
}

export function useEdgarFundamentals(
  ticker: string | null,
  options: UseEdgarFundamentalsOptions = {}
): UseEdgarFundamentalsResult {
  const { freq = 'quarter', periods = 4, enabled = true } = options;

  const [data, setData] = useState<EdgarFinancialsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isServiceAvailable, setIsServiceAvailable] = useState(true);

  // Use ref to track if component is mounted (prevents state updates after unmount)
  const isMountedRef = useRef(true);

  // Use ref for stable callback that doesn't cause re-renders
  const optionsRef = useRef({ freq, periods, enabled });
  optionsRef.current = { freq, periods, enabled };

  const fetchData = useCallback(async () => {
    const { freq, periods, enabled } = optionsRef.current;

    if (!ticker || !enabled) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await edgarApi.getFinancials(ticker, { freq, periods });

      if (isMountedRef.current) {
        setData(result);
        setIsServiceAvailable(true);
      }
    } catch (err: any) {
      if (!isMountedRef.current) return;

      const status = err.response?.status;
      const message = err.response?.data?.detail || 'Failed to fetch EDGAR data';

      // 503 = service unavailable (EDGAR disabled or down)
      if (status === 503) {
        setIsServiceAvailable(false);
        setError('EDGAR service is currently unavailable');
      } else if (status === 404) {
        // Not an error - just no data for this ticker
        setError(null);
        setData(null);
      } else {
        setError(message);
      }
      setData(null);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [ticker]); // Only depend on ticker - options accessed via ref

  // Fetch on mount and when ticker changes
  useEffect(() => {
    isMountedRef.current = true;
    fetchData();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchData]);

  // Refetch when options change (separate effect to avoid dependency issues)
  useEffect(() => {
    if (ticker && enabled) {
      fetchData();
    }
  }, [freq, periods, enabled, ticker, fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
    isServiceAvailable,
  };
}
```

> ⚠️ **Important Changes from Original:**
> 1. Uses `useRef` for options to prevent infinite refetch loops
> 2. Added `isMountedRef` to prevent state updates after unmount
> 3. Added `isServiceAvailable` flag for graceful degradation
> 4. Handles 503 (service unavailable) distinctly from other errors
> 5. Handles 404 (no data) as non-error state

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

### Infrastructure Choice: Minimal Initial Stack

**Selected Stack (Phase 1):**
```
PostgreSQL only (No Redis, No Celery)
```

**Rationale:**
- Fastest path to production
- Synchronous EDGAR calls are acceptable for user-triggered requests (10-30 sec)
- Add Redis + Celery later when async refresh jobs become necessary
- Reduces complexity and Railway cost (~$10/mo vs ~$20/mo)

**Future Stack (Phase 2 - when needed):**
```
PostgreSQL + Redis + Celery Worker
```

### Critical: Same Railway Project

> ⚠️ **Railway private networking (`*.railway.internal`) only works within the SAME project.**

Deploy StockFundamentals services as **additional services within the existing SigmaSight Railway project**, NOT as a separate project. This enables:
- Private networking via `stockfund-api.railway.internal`
- Shared environment variable references (`${{service.VAR}}`)
- Single dashboard for monitoring all services
- Simpler CORS and authentication

---

### Local Development

#### Docker Compose Setup
Create `docker-compose.dev.yml` in SigmaSight root:

```yaml
# Note: 'version' is deprecated in Docker Compose v2+, omitted intentionally

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sigmasight -d sigmasight_db"]
      interval: 10s
      timeout: 5s
      retries: 5

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d stock_fundamentals"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (OPTIONAL - only needed for Phase 2 with Celery)
  # Uncomment when adding async job processing
  # stockfund-redis:
  #   image: redis:7-alpine
  #   container_name: stockfund-redis
  #   ports:
  #     - "6379:6379"
  #   volumes:
  #     - stockfund_redis_data:/data
  #   networks:
  #     - sigmasight-network
  #   healthcheck:
  #     test: ["CMD", "redis-cli", "ping"]
  #     interval: 10s
  #     timeout: 5s
  #     retries: 5

volumes:
  sigmasight_postgres_data:
  stockfund_postgres_data:
  # stockfund_redis_data:  # Uncomment for Phase 2

networks:
  sigmasight-network:
    driver: bridge
```

> ⚠️ **Changes from Original:**
> 1. Removed deprecated `version: '3.8'`
> 2. Added healthchecks for all services
> 3. Added Redis volume for data persistence
> 4. Commented out Redis (not needed for Phase 1)
> 5. Added comments explaining optional services

#### Start Local Development
```bash
# 1. Start infrastructure (wait for healthchecks)
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml ps  # Verify all healthy

# 2. Run StockFundamentals migrations (one-time)
cd ../StockFundamentals/backend
uv run alembic upgrade head

# 3. Start StockFundamentals API (in separate terminal)
cd ../StockFundamentals/backend
uv run uvicorn app.main:app --reload --port 8001

# 4. Start SigmaSight backend (in separate terminal)
cd backend && uv run python run.py

# 5. Start SigmaSight frontend (in separate terminal)
cd frontend && npm run dev

# OPTIONAL (Phase 2): Start Celery worker for async jobs
# cd ../StockFundamentals/backend
# uv run celery -A app.tasks.worker worker -l info
```

> **Note**: Migrations are run separately (step 2), not on every API start.
> This prevents race conditions and makes failures more visible.

---

### Railway Deployment

#### Architecture Overview (Same Project)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Railway Project: SigmaSight                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     EXISTING SERVICES                                │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐             │    │
│  │  │  Frontend   │  │   Backend    │  │  PostgreSQL     │             │    │
│  │  │  (Next.js)  │  │  (FastAPI)   │  │  (sigmasight)   │             │    │
│  │  │             │  │              │  │                 │             │    │
│  │  └─────────────┘  └──────┬───────┘  └─────────────────┘             │    │
│  └──────────────────────────┼───────────────────────────────────────────┘    │
│                             │                                                │
│                             │ HTTP via stockfund-api.railway.internal        │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     NEW SERVICES (added to same project)             │    │
│  │  ┌─────────────────┐            ┌─────────────────┐                 │    │
│  │  │  stockfund-api  │            │  stockfund-db   │                 │    │
│  │  │  (FastAPI)      │───────────▶│  (PostgreSQL)   │                 │    │
│  │  │  Port: 8000     │            │  (separate DB)  │                 │    │
│  │  └────────┬────────┘            └─────────────────┘                 │    │
│  │           │                                                          │    │
│  │           ▼                                                          │    │
│  │  ┌─────────────────┐                                                │    │
│  │  │   SEC EDGAR     │     ┌────────────────────────────────────┐     │    │
│  │  │   (External)    │     │ PHASE 2 (optional): Redis + Worker │     │    │
│  │  └─────────────────┘     └────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

> ⚠️ **Key Insight**: All services in the SAME Railway project enables private networking.
> Cross-project communication would require public URLs.

#### Step 1: Add Services to Existing SigmaSight Project

> ⚠️ **Do NOT create a new Railway project.** Add services to the existing SigmaSight project.

**Via Railway Dashboard:**
1. Open the existing **SigmaSight** project in Railway dashboard
2. Click "New" → "Database" → "PostgreSQL"
3. Name it `stockfund-db` (this creates a separate database instance)
4. Wait for provisioning

**Via CLI (alternative):**
```bash
# Link to existing SigmaSight project
cd ~/CascadeProjects/StockFundamentals
railway link  # Select existing SigmaSight project

# Add PostgreSQL to the project
railway add --plugin postgresql
```

#### Step 2: Add StockFundamentals API Service

**In Railway Dashboard:**
1. Click "New" → "GitHub Repo"
2. Select `bbalbalbae/StockFundamentals`
3. Name the service `stockfund-api`
4. Set Root Directory: `backend`
5. Railway will auto-detect Dockerfile

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

# NOTE: Migrations run via deploy hook, NOT on every container start
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
```

> ⚠️ **Critical**: Migrations are NOT in CMD. They run via deploy hook (see Step 4).

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

#### Step 3: Configure Environment Variables

**stockfund-api Service Variables:**
```env
# Database - reference the stockfund-db service
DATABASE_URL=${{stockfund-db.DATABASE_URL}}

# SEC EDGAR Configuration (REQUIRED)
# Use real contact email for SEC compliance
EDGAR_USER_AGENT=SigmaSight/1.0 (your-real-email@domain.com)

# API Authentication - generate random key!
# Generate with: openssl rand -hex 32
API_KEYS=${{shared.STOCKFUND_API_KEY}}

# Phase 1: No Redis (synchronous mode)
REDIS_URL=
CELERY_BROKER_URL=

# Feature flags
SYNC_MODE=true  # Disable Celery, run synchronously
```

**Create Shared Variables (for cross-service reference):**
1. In Railway dashboard, go to Project Settings → Variables
2. Add shared variable:
   - `STOCKFUND_API_KEY`: Generate with `openssl rand -hex 32`

**SigmaSight Backend Variables (add these):**
```env
# StockFundamentals Integration
STOCKFUND_API_URL=http://stockfund-api.railway.internal:8000
STOCKFUND_API_KEY=${{shared.STOCKFUND_API_KEY}}
EDGAR_ENABLED=false  # Start disabled, enable after testing
```

> ⚠️ **Security**: Never use example API keys. Generate with `openssl rand -hex 32`.

#### Step 4: Configure Deploy Hook for Migrations

> ⚠️ **Critical**: Running migrations in CMD causes issues with multiple replicas and failed deployments.

**Option A: Railway Deploy Hook (Recommended)**

In Railway dashboard for `stockfund-api`:
1. Go to Settings → Deploy → Build & Deploy
2. Set "Deploy Command" (runs after build, before start):
   ```bash
   uv run alembic upgrade head
   ```

**Option B: Separate One-Off Migration Service**

Create a migration-only service that runs once:
1. Create `Dockerfile.migrate`:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
   RUN pip install uv
   COPY pyproject.toml uv.lock ./
   RUN uv sync --frozen --no-dev
   COPY . .
   CMD ["uv", "run", "alembic", "upgrade", "head"]
   ```
2. Deploy as one-off service, run once, then delete

#### Step 5: Enable Private Networking

1. In Railway dashboard, click on `stockfund-api`
2. Go to Settings → Networking
3. Enable "Private Networking"
4. Note the private URL: `stockfund-api.railway.internal`

The SigmaSight backend can now reach StockFundamentals at:
```
http://stockfund-api.railway.internal:8000
```

> **No public URL needed** - private networking is sufficient for internal communication.

#### Step 6: Deploy and Verify

```bash
# 1. Deploy StockFundamentals (from StockFundamentals repo)
cd ~/CascadeProjects/StockFundamentals/backend
railway up

# 2. Check deployment logs
railway logs

# 3. Verify health (via SigmaSight backend or Railway shell)
railway run curl http://stockfund-api.railway.internal:8000/health
```

**Expected health response:**
```json
{
  "status": "ok",
  "service": "stockfundamentals",
  "version": "1.0.0",
  "database": true,
  "redis": false,
  "edgar_api": true
}
```

#### Step 7: Enable EDGAR in SigmaSight

After verifying StockFundamentals is healthy:

1. Update SigmaSight backend environment:
   ```env
   EDGAR_ENABLED=true
   ```
2. Redeploy SigmaSight backend
3. Test via SigmaSight API:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     "https://sigmasight-be-production.up.railway.app/api/v1/edgar/health"
   ```

#### Phase 2 (Later): Add Redis + Celery Worker

When async job processing is needed:

1. Add Redis to project: "New" → "Database" → "Redis"
2. Add Celery worker service with `Dockerfile.worker`
3. Update environment variables:
   ```env
   REDIS_URL=${{Redis.REDIS_URL}}
   CELERY_BROKER_URL=${{Redis.REDIS_URL}}
   SYNC_MODE=false
   ```

---

### Railway Cost Estimate

**Phase 1 (Initial - Recommended):**
| Service | Railway Plan | Estimated Cost |
|---------|--------------|----------------|
| StockFundamentals API | Hobby | ~$5/mo |
| PostgreSQL (stockfund-db) | Hobby | ~$5/mo |
| **Phase 1 Total** | | **~$10/mo** |

**Phase 2 (With Async Jobs):**
| Service | Railway Plan | Estimated Cost |
|---------|--------------|----------------|
| StockFundamentals API | Hobby | ~$5/mo |
| Celery Worker | Hobby | ~$5/mo |
| PostgreSQL (stockfund-db) | Hobby | ~$5/mo |
| Redis | Hobby | ~$3-5/mo |
| **Phase 2 Total** | | **~$18-20/mo** |

*Note: Costs vary based on usage. Railway Pro plan ($20/mo) includes more resources.*

---

## Monitoring & Alerting

### Health Monitoring

**Railway Built-in Monitoring:**
- CPU/Memory usage graphs
- Request count and latency
- Deploy status and logs

**Custom Health Endpoint Monitoring:**

Add the `/api/v1/edgar/health` endpoint to your monitoring:

```bash
# Example: Add to uptime monitoring (UptimeRobot, Pingdom, etc.)
# Monitor: https://sigmasight-be-production.up.railway.app/api/v1/edgar/health
# Check interval: 5 minutes
# Alert on: 503 (service unavailable) or timeout
```

### Key Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| EDGAR service health | `/api/v1/edgar/health` | Any non-200 |
| API response time | Railway metrics | > 5 seconds |
| Error rate | Application logs | > 5% of requests |
| Database connections | PostgreSQL metrics | > 80% pool |
| EDGAR rate limit hits | Application logs | Any 429 responses |

### Logging Strategy

**Structured Logging in StockFundamentals:**
```python
# Log all EDGAR API calls
logger.info("EDGAR request", ticker=ticker, endpoint=endpoint, response_time_ms=elapsed)

# Log rate limit warnings
logger.warning("EDGAR rate limit approaching", current_rate=rate, limit=10)

# Log errors with context
logger.error("EDGAR fetch failed", ticker=ticker, error=str(e), traceback=True)
```

**Railway Log Aggregation:**
- Logs available in Railway dashboard per service
- Use `railway logs` CLI for real-time streaming
- Consider forwarding to external service (Datadog, Logtail) for long-term retention

### SEC Rate Limit Monitoring

> ⚠️ **Critical**: SEC EDGAR rate limits are 10 requests/second per IP.

**Rate Limit Tracking:**
```python
# Add to StockFundamentals
from collections import deque
from time import time

class RateLimitMonitor:
    def __init__(self, window_seconds=1, max_requests=8):
        self.requests = deque()
        self.window = window_seconds
        self.max = max_requests  # Stay below 10 for safety

    def record_request(self):
        now = time()
        # Remove old requests outside window
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        self.requests.append(now)

        if len(self.requests) >= self.max:
            logger.warning("EDGAR rate limit threshold",
                          current=len(self.requests),
                          max=self.max)
```

---

## Rollback Strategy

### Feature Flag Rollback (Fastest)

**Disable EDGAR without redeployment:**
1. In Railway dashboard, go to SigmaSight backend service
2. Update environment variable: `EDGAR_ENABLED=false`
3. Service automatically restarts
4. EDGAR endpoints return 503 gracefully

**Time to rollback**: ~30 seconds

### Service Rollback (Railway)

**Rollback to previous deployment:**
1. In Railway dashboard, click on `stockfund-api`
2. Go to Deployments tab
3. Find last known good deployment
4. Click "Redeploy" on that deployment

**Time to rollback**: ~2-3 minutes

### Database Rollback

> ⚠️ **StockFundamentals has its own database** - SigmaSight data is unaffected.

**If migration breaks StockFundamentals:**
```bash
# 1. SSH into Railway service
railway shell -s stockfund-api

# 2. Rollback one migration
uv run alembic downgrade -1

# 3. Or rollback to specific revision
uv run alembic downgrade <revision_id>
```

**If data is corrupted:**
1. Railway PostgreSQL has automatic backups
2. In Railway dashboard → stockfund-db → Backups
3. Restore from point-in-time backup

### Complete Removal

If EDGAR integration needs to be completely removed:

1. Set `EDGAR_ENABLED=false` in SigmaSight
2. Remove the `stockfund-api` service from Railway
3. (Optional) Remove `stockfund-db` if data not needed
4. EDGAR endpoints will return 503 until code is removed
5. Remove frontend toggle and EDGAR components

### Incident Response Checklist

```markdown
## EDGAR Service Incident Response

1. [ ] Identify issue (check `/api/v1/edgar/health`)
2. [ ] Set `EDGAR_ENABLED=false` if affecting users
3. [ ] Check StockFundamentals logs: `railway logs -s stockfund-api`
4. [ ] Determine root cause:
   - [ ] SEC EDGAR down? Check https://www.sec.gov/cgi-bin/browse-edgar
   - [ ] Rate limited? Check logs for 429 errors
   - [ ] Database issue? Check `stockfund-db` metrics
   - [ ] Code bug? Check recent deployments
5. [ ] Fix or rollback as appropriate
6. [ ] Re-enable: `EDGAR_ENABLED=true`
7. [ ] Monitor for 15 minutes
8. [ ] Document incident
```

## Risk Assessment

### High Risk
| Risk | Mitigation | Status |
|------|------------|--------|
| SEC EDGAR rate limiting | 8 req/sec limit with monitoring + backoff | ✅ Addressed |
| StockFundamentals service downtime | `EDGAR_ENABLED` flag for instant disable, YahooQuery fallback | ✅ Addressed |
| Data inconsistency between sources | Clear source labeling in UI, toggle for user choice | ✅ Addressed |
| Railway private networking failure | Deploy in same project (not separate) | ✅ Addressed |

### Medium Risk
| Risk | Mitigation | Status |
|------|------------|--------|
| Network latency between services | Connection pooling, private networking | ✅ Addressed |
| Migration failures on deploy | Deploy hooks (not CMD), separate from app start | ✅ Addressed |
| Redis/infrastructure complexity | Phase 1 without Redis/Celery, add later | ✅ Addressed |
| API versioning conflicts | Version-pinned internal API calls | ⏳ Monitor |
| EdgarClient initialization timing | FastAPI lifespan + dependency injection | ✅ Addressed |

### Low Risk
| Risk | Mitigation | Status |
|------|------------|--------|
| Schema changes in EDGAR | XBRL mapping is standardized by SEC | ⏳ Monitor |
| API key exposure | Railway secrets, randomly generated keys | ✅ Addressed |
| Cross-project networking issues | Same Railway project deployment | ✅ Addressed |

### Risks NOT Fully Mitigated

| Risk | Current Status | Future Mitigation |
|------|----------------|-------------------|
| No external monitoring | Relying on Railway built-in | Add UptimeRobot or similar |
| No long-term log retention | Logs in Railway only | Consider Datadog/Logtail |
| No automated E2E tests | Manual testing only | Add Playwright tests |
| Single replica | No HA | Add second replica in Phase 2 |

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
- [ ] `app/services/edgar_client.py` - HTTP client with DI (~200 lines)
- [ ] `app/schemas/edgar_fundamentals.py` - Response schemas (~100 lines)
- [ ] `app/api/v1/edgar_fundamentals.py` - Proxy endpoints (~180 lines)
- [ ] `app/core/config.py` - Add EDGAR settings (3 lines)
- [ ] `app/api/v1/router.py` - Register router (1 line)
- [ ] `app/main.py` - Add lifespan handler (5 lines)
- [ ] `tests/test_edgar_client.py` - Unit tests

**SigmaSight Frontend:**
- [ ] `src/services/edgarApi.ts` - API service (~80 lines)
- [ ] `src/hooks/useEdgarFundamentals.ts` - React hook (~100 lines)
- [ ] `src/components/fundamentals/EdgarFinancialsTable.tsx` - Display component
- [ ] `src/components/fundamentals/DataSourceSelector.tsx` - Toggle component

**Configuration Files:**
- [ ] `docker-compose.dev.yml` (new file for local dev)
- [ ] `backend/.env` (add 3 EDGAR variables)

**StockFundamentals Repo:**
- [ ] `backend/Dockerfile` - Production container
- [ ] `backend/railway.toml` - Railway configuration
- Stays in separate `bbalbalbae/StockFundamentals` repo
- Has its own database, migrations, models
- Deployed as service within SigmaSight Railway project
- SigmaSight calls it via private networking

---

### D. Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-17 | 1.0 | Initial plan |
| 2025-12-19 | 2.0 | Major revisions: |
| | | - Changed to same Railway project (private networking) |
| | | - Added deploy hooks for migrations (not in CMD) |
| | | - Fixed EdgarClient to use FastAPI dependency injection |
| | | - Added specific exception types for better error handling |
| | | - Fixed frontend hook dependencies (useRef pattern) |
| | | - Added Monitoring & Alerting section |
| | | - Added Rollback Strategy section |
| | | - Simplified Phase 1 (no Redis/Celery) |
| | | - Fixed docker-compose (healthchecks, no deprecated version) |
| | | - Updated all code examples with fixes |

---

## Next Steps

### Immediate (This Week)
1. ✅ **Review and approve this revised plan**
2. **Set up local development environment**
   - Create `docker-compose.dev.yml` with healthchecks
   - Run StockFundamentals locally on port 8001
   - Verify EDGAR API connectivity

### Phase 1: Backend Integration (Days 1-2)
3. **Create SigmaSight integration layer**
   - `edgar_client.py` with dependency injection
   - `edgar_fundamentals.py` router
   - Add to `main.py` lifespan handler
4. **Test locally end-to-end**
   - Verify `/api/v1/edgar/health` returns status
   - Test with real ticker (AAPL, MSFT)

### Phase 2: Railway Deployment (Days 2-3)
5. **Deploy to Railway (same project)**
   - Add `stockfund-db` PostgreSQL
   - Add `stockfund-api` service
   - Configure deploy hooks for migrations
   - Enable private networking
6. **Configure and test**
   - Set `EDGAR_ENABLED=false` initially
   - Verify health via Railway shell
   - Enable and test with SigmaSight backend

### Phase 3: Frontend & Validation (Days 3-5)
7. **Frontend integration**
   - Create `edgarApi.ts` service
   - Create `useEdgarFundamentals` hook
   - Add financials table component
   - Add data source toggle
8. **Testing and validation**
   - Manual E2E testing
   - Verify data quality
   - Monitor for 24 hours

### Phase 4: Production Rollout
9. **Gradual rollout**
   - Enable for internal testing
   - Enable UI toggle for users
   - Make EDGAR default (Yahoo fallback)
10. **Post-launch**
    - Set up external monitoring
    - Document any issues
    - Consider Phase 2 (Redis + Celery) if needed

---

*Document created by Claude Code*
*Last updated: 2025-12-19 (v2.0)*
