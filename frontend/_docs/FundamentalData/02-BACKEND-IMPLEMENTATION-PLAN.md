# Backend Implementation Plan: Fundamental Financial Data

**Date**: November 1, 2025
**Status**: Planning
**Dependencies**: YahooQuery library (already in `pyproject.toml`)

---

## Overview

Implement comprehensive fundamental financial data endpoints using YahooQuery to provide:
1. Historical financial statements (income statement, balance sheet, cash flow)
2. Forward-looking analyst estimates and price targets
3. Calculated financial ratios and growth metrics

---

## Architecture Decisions

### 1. Service Layer Design

**Extend Existing YahooQuery Client** (`app/clients/yahooquery_client.py`)

Current implementation has:
- ✅ `get_historical_prices()` - Historical price data
- ✅ `get_stock_prices()` - Current quotes
- ✅ `get_fund_holdings()` - Fund holdings

**New Methods to Add:**
```python
class YahooQueryClient(MarketDataProvider):
    # ... existing methods ...

    async def get_income_statement(symbol: str, frequency: str = 'q', years: int = 4)
    async def get_balance_sheet(symbol: str, frequency: str = 'q', years: int = 4)
    async def get_cash_flow(symbol: str, frequency: str = 'q', years: int = 4)
    async def get_all_financials(symbol: str, frequency: str = 'q', years: int = 4)

    async def get_analyst_estimates(symbol: str)
    async def get_price_targets(symbol: str)
    async def get_next_earnings(symbol: str)

    async def get_valuation_measures(symbol: str)
```

**Rationale:**
- Keep financial data methods with market data client (cohesive domain)
- Reuse existing async pattern (run synchronous YahooQuery in executor)
- Maintain consistency with existing client interface

---

### 2. New Service Layer

**Create**: `app/services/fundamentals_service.py`

**Purpose**: Business logic layer for fundamental data operations
- Data transformation (YahooQuery → application format)
- Calculated metrics (ratios, growth rates, margins)
- Data validation and error handling
- Caching strategy (optional, Phase 2)

**Key Functions:**
```python
async def get_financial_statements(symbol: str, frequency: str, years: int)
async def get_forward_estimates(symbol: str)
async def calculate_financial_ratios(symbol: str, frequency: str)
async def get_growth_metrics(symbol: str)
```

---

### 3. Endpoint Structure

**New Router**: `app/api/v1/endpoints/fundamentals.py`

Group all fundamental data endpoints in one router for:
- Easier maintenance
- Consistent naming
- Clear separation from existing data endpoints

**Include in**: `app/api/v1/router.py`

---

## Proposed Endpoints

### Phase 1: Core Financial Statements (Priority: HIGH)

#### 1. Income Statement
```
GET /api/v1/fundamentals/income-statement/{symbol}
```

**Query Parameters:**
- `frequency` (optional): `q` (quarterly), `a` (annual), `ttm` (trailing twelve months)
  - Default: `q`
- `periods` (optional): Number of periods to return (max 16 for quarterly, 4 for annual)
  - Default: 12 (3 years quarterly)

**Response Schema:**
```json
{
  "symbol": "AAPL",
  "frequency": "q",
  "currency": "USD",
  "periods": [
    {
      "period_date": "2024-09-30",
      "period_type": "3M",
      "fiscal_year": 2024,
      "fiscal_quarter": "Q4",
      "metrics": {
        "revenue": 94930000000,
        "cost_of_revenue": 52300000000,
        "gross_profit": 42630000000,
        "gross_margin": 0.4487,
        "research_and_development": 7800000000,
        "selling_general_administrative": 6600000000,
        "total_operating_expenses": 14400000000,
        "operating_income": 28230000000,
        "operating_margin": 0.2974,
        "ebit": 28230000000,
        "interest_expense": null,
        "other_income_expense": 500000000,
        "pretax_income": 28730000000,
        "tax_provision": 4800000000,
        "tax_rate": 0.1671,
        "net_income": 23930000000,
        "net_margin": 0.2520,
        "ebitda": 30100000000,
        "depreciation_amortization": 1870000000,
        "basic_eps": 1.53,
        "diluted_eps": 1.52,
        "basic_shares": 15630000000,
        "diluted_shares": 15750000000
      }
    },
    // ... more periods
  ],
  "metadata": {
    "data_source": "yahooquery",
    "last_updated": "2024-11-01T12:00:00Z",
    "periods_returned": 12
  }
}
```

#### 2. Balance Sheet
```
GET /api/v1/fundamentals/balance-sheet/{symbol}
```

**Query Parameters:** Same as income statement

**Key Metrics to Include:**
- Assets: Cash, Accounts Receivable, Inventory, PP&E, Goodwill, Intangibles, Total Assets
- Liabilities: Accounts Payable, Short-term Debt, Long-term Debt, Total Liabilities
- Equity: Common Stock, Retained Earnings, Treasury Stock, Total Equity
- Calculated: Working Capital, Net Debt, Book Value per Share

#### 3. Cash Flow Statement
```
GET /api/v1/fundamentals/cash-flow/{symbol}
```

**Query Parameters:** Same as income statement

**Key Metrics to Include:**
- Operating Activities: Operating Cash Flow, Changes in Working Capital
- Investing Activities: CAPEX, Acquisitions, Asset Sales
- Financing Activities: Dividends Paid, Stock Buybacks, Debt Issuance/Repayment
- Calculated: Free Cash Flow, FCF Margin, FCF per Share

#### 4. All Financial Statements (Combined)
```
GET /api/v1/fundamentals/all-statements/{symbol}
```

**Purpose**: Get all three statements in one call (more efficient for frontend)

**Query Parameters:** Same as above

**Response**: Combined response with all three statement types

---

### Phase 2: Forward-Looking Data (Priority: HIGH)

#### 5. Analyst Estimates
```
GET /api/v1/fundamentals/analyst-estimates/{symbol}
```

**Response Schema:**
```json
{
  "symbol": "AAPL",
  "estimates": {
    "current_quarter": {
      "period": "Q1 2025",
      "end_date": "2025-12-31",
      "revenue": {
        "average": 137964127710,
        "low": 136679500000,
        "high": 140666000000,
        "num_analysts": 24,
        "year_ago": 124300000000,
        "growth": 0.1099
      },
      "eps": {
        "average": 2.64,
        "low": 2.40,
        "high": 2.80,
        "num_analysts": 27,
        "year_ago": 2.40,
        "growth": 0.0999
      },
      "eps_revisions": {
        "up_last_7_days": 7,
        "up_last_30_days": 8,
        "down_last_30_days": 0,
        "down_last_90_days": 0
      },
      "eps_trend": {
        "current": 2.64,
        "7_days_ago": 2.51,
        "30_days_ago": 2.48,
        "60_days_ago": 2.47,
        "90_days_ago": 2.47
      }
    },
    "next_quarter": { /* same structure */ },
    "current_year": { /* same structure */ },
    "next_year": { /* same structure */ }
  },
  "metadata": {
    "data_source": "yahooquery",
    "last_updated": "2024-11-01T12:00:00Z"
  }
}
```

#### 6. Price Targets
```
GET /api/v1/fundamentals/price-targets/{symbol}
```

**Response Schema:**
```json
{
  "symbol": "AAPL",
  "current_price": 225.50,
  "targets": {
    "low": 200.00,
    "mean": 274.97,
    "high": 345.00,
    "median": 270.00
  },
  "upside": {
    "to_mean": 0.2194,  // 21.94% upside to mean target
    "to_high": 0.5300,  // 53.00% upside to high target
  },
  "recommendations": {
    "mean": 2.0,  // 1=Strong Buy, 5=Sell
    "distribution": {
      "strong_buy": 15,
      "buy": 18,
      "hold": 7,
      "sell": 1,
      "strong_sell": 0
    },
    "num_analysts": 41
  },
  "metadata": {
    "data_source": "yahooquery",
    "last_updated": "2024-11-01T12:00:00Z"
  }
}
```

#### 7. Next Earnings
```
GET /api/v1/fundamentals/next-earnings/{symbol}
```

**Response Schema:**
```json
{
  "symbol": "AAPL",
  "next_earnings": {
    "date": "2026-01-29T15:00:00Z",
    "fiscal_quarter": "Q1 2026",
    "estimates": {
      "revenue": {
        "average": 137964127710,
        "low": 136679500000,
        "high": 140666000000
      },
      "eps": {
        "average": 2.63,
        "low": 2.40,
        "high": 2.71
      }
    }
  },
  "last_earnings": {
    "date": "2024-10-31",
    "revenue_actual": 94930000000,
    "revenue_estimate": 94360000000,
    "revenue_surprise": 0.0060,  // 0.6% beat
    "eps_actual": 1.64,
    "eps_estimate": 1.60,
    "eps_surprise": 0.025  // 2.5% beat
  },
  "metadata": {
    "data_source": "yahooquery",
    "last_updated": "2024-11-01T12:00:00Z"
  }
}
```

---

### Phase 3: Calculated Metrics (Priority: MEDIUM)

#### 8. Financial Ratios
```
GET /api/v1/fundamentals/financial-ratios/{symbol}
```

**Calculated Ratios:**

**Profitability:**
- Gross Margin = Gross Profit / Revenue
- Operating Margin = Operating Income / Revenue
- Net Margin = Net Income / Revenue
- EBITDA Margin = EBITDA / Revenue
- Return on Assets (ROA) = Net Income / Total Assets
- Return on Equity (ROE) = Net Income / Shareholders' Equity

**Efficiency:**
- Asset Turnover = Revenue / Total Assets
- Inventory Turnover = COGS / Average Inventory
- Days Sales Outstanding (DSO) = (Accounts Receivable / Revenue) * 365

**Leverage:**
- Debt-to-Equity = Total Debt / Total Equity
- Debt-to-Assets = Total Debt / Total Assets
- Interest Coverage = EBIT / Interest Expense

**Liquidity:**
- Current Ratio = Current Assets / Current Liabilities
- Quick Ratio = (Current Assets - Inventory) / Current Liabilities
- Cash Ratio = Cash / Current Liabilities

**Valuation:**
- P/E Ratio (from market cap and earnings)
- Price-to-Book = Market Cap / Book Value
- EV/EBITDA = Enterprise Value / EBITDA

**Cash Flow:**
- FCF Margin = Free Cash Flow / Revenue
- FCF Yield = Free Cash Flow / Market Cap
- Operating Cash Flow Ratio = Operating Cash Flow / Current Liabilities

#### 9. Growth Metrics
```
GET /api/v1/fundamentals/growth-metrics/{symbol}
```

**Calculated Growth Rates (QoQ, YoY, 3Y CAGR):**
- Revenue Growth
- Earnings Growth
- EBITDA Growth
- EPS Growth
- Operating Cash Flow Growth
- Free Cash Flow Growth
- Book Value Growth

**Response includes historical trend arrays for charting**

---

## Data Models (Pydantic Schemas)

**Create**: `app/schemas/fundamentals.py`

### Core Schemas

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal

class FinancialPeriod(BaseModel):
    """Single period of financial data"""
    period_date: date
    period_type: str  # "3M", "12M", "TTM"
    fiscal_year: int
    fiscal_quarter: Optional[str] = None  # "Q1", "Q2", etc.

class IncomeStatementMetrics(BaseModel):
    """Income statement line items for one period"""
    revenue: Optional[Decimal]
    cost_of_revenue: Optional[Decimal]
    gross_profit: Optional[Decimal]
    gross_margin: Optional[Decimal]
    research_and_development: Optional[Decimal]
    selling_general_administrative: Optional[Decimal]
    total_operating_expenses: Optional[Decimal]
    operating_income: Optional[Decimal]
    operating_margin: Optional[Decimal]
    ebit: Optional[Decimal]
    interest_expense: Optional[Decimal]
    other_income_expense: Optional[Decimal]
    pretax_income: Optional[Decimal]
    tax_provision: Optional[Decimal]
    tax_rate: Optional[Decimal]
    net_income: Optional[Decimal]
    net_margin: Optional[Decimal]
    ebitda: Optional[Decimal]
    depreciation_amortization: Optional[Decimal]
    basic_eps: Optional[Decimal]
    diluted_eps: Optional[Decimal]
    basic_shares: Optional[int]
    diluted_shares: Optional[int]

class IncomeStatementPeriod(FinancialPeriod):
    """Income statement for one period"""
    metrics: IncomeStatementMetrics

class IncomeStatementResponse(BaseModel):
    """Full income statement response"""
    symbol: str
    frequency: str  # "q", "a", "ttm"
    currency: str
    periods: List[IncomeStatementPeriod]
    metadata: Dict[str, any]

# Similar schemas for BalanceSheet, CashFlow, etc.

class EstimatePeriod(BaseModel):
    """Estimates for one period"""
    period: str
    end_date: date
    revenue: RevenueEstimate
    eps: EPSEstimate
    eps_revisions: EPSRevisions
    eps_trend: EPSTrend

class AnalystEstimatesResponse(BaseModel):
    """Analyst estimates response"""
    symbol: str
    estimates: Dict[str, EstimatePeriod]  # "current_quarter", "next_quarter", etc.
    metadata: Dict[str, any]

# ... more schemas
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Priority: HIGH**

1. **Extend YahooQueryClient** (`app/clients/yahooquery_client.py`)
   - Add financial statement methods
   - Add async wrappers for synchronous YahooQuery calls
   - Implement error handling and logging
   - Add rate limiting (already exists, verify adequate)

2. **Create Fundamentals Service** (`app/services/fundamentals_service.py`)
   - Data transformation logic
   - Field mapping (YahooQuery → application schema)
   - Null handling and validation
   - Error handling

3. **Create Pydantic Schemas** (`app/schemas/fundamentals.py`)
   - All request/response models
   - Validation rules
   - Default values

4. **Create Endpoints Router** (`app/api/v1/endpoints/fundamentals.py`)
   - Income statement endpoint
   - Balance sheet endpoint
   - Cash flow endpoint
   - All statements endpoint (combined)

5. **Testing**
   - Unit tests for service layer
   - Integration tests for endpoints
   - Test with diverse companies (tech, financial, industrial)
   - Validate field mapping accuracy

**Deliverables:**
- ✅ 4 new endpoints operational
- ✅ Comprehensive test coverage
- ✅ API documentation updated

---

### Phase 2: Forward-Looking Data (Week 2)
**Priority: HIGH**

1. **Extend YahooQueryClient**
   - Add analyst estimates methods
   - Add price targets methods
   - Add next earnings methods

2. **Extend Fundamentals Service**
   - Transform analyst estimate data
   - Calculate upside/downside to price targets
   - Format earnings history comparisons

3. **Add Endpoints**
   - Analyst estimates endpoint
   - Price targets endpoint
   - Next earnings endpoint

4. **Testing**
   - Validate estimate data accuracy
   - Test with companies of varying analyst coverage
   - Verify edge cases (no estimates, low coverage)

**Deliverables:**
- ✅ 3 new forward-looking endpoints
- ✅ Analyst estimate integration
- ✅ Price target calculations

---

### Phase 3: Calculated Metrics (Week 3)
**Priority: MEDIUM**

1. **Create Calculations Module** (`app/calculations/financial_ratios.py`)
   - Profitability ratios
   - Efficiency ratios
   - Leverage ratios
   - Liquidity ratios
   - Cash flow ratios
   - Growth calculations

2. **Extend Fundamentals Service**
   - Calculate ratios from raw financial data
   - Handle division by zero
   - Calculate growth rates (QoQ, YoY, CAGR)
   - Time-series analysis

3. **Add Endpoints**
   - Financial ratios endpoint
   - Growth metrics endpoint

4. **Testing**
   - Validate calculation accuracy
   - Test edge cases (negative values, zero denominators)
   - Compare against known benchmarks

**Deliverables:**
- ✅ 2 calculated metrics endpoints
- ✅ Comprehensive ratio calculations
- ✅ Growth trend analysis

---

### Phase 4: Optimization & Caching (Week 4)
**Priority: LOW (Future Enhancement)

1. **Caching Strategy**
   - Cache financial statements (low change frequency)
   - TTL: 24 hours for historical data
   - TTL: 1 hour for analyst estimates
   - TTL: 15 minutes for price targets

2. **Performance Optimization**
   - Batch requests where possible
   - Parallel data fetching for all-statements endpoint
   - Response compression

3. **Error Handling Enhancement**
   - Graceful degradation for missing data
   - Retry logic for transient failures
   - Fallback to FMP if YahooQuery fails (optional)

---

## Error Handling Strategy

### Expected Error Scenarios

1. **Symbol Not Found**
   - HTTP 404
   - Message: "Symbol {symbol} not found"

2. **No Financial Data Available**
   - HTTP 200 (not an error, just no data)
   - Empty periods array
   - Metadata indicates data unavailability

3. **Partial Data Available**
   - HTTP 200
   - Return available fields
   - Null for unavailable fields
   - Metadata indicates partial data

4. **Rate Limit Exceeded**
   - HTTP 429
   - Retry-After header
   - Message: "Rate limit exceeded, retry after {seconds}"

5. **Upstream Service Error**
   - HTTP 502
   - Message: "Unable to fetch data from Yahoo Finance"
   - Log detailed error for debugging

---

## Security & Validation

### Input Validation
- Symbol format: 1-5 uppercase alphanumeric characters
- Frequency: Only allow `q`, `a`, `ttm`
- Periods: Maximum 16 (4 years quarterly)

### Authentication
- All endpoints require JWT authentication (use existing `get_current_user` dependency)

### Rate Limiting
- Leverage existing YahooQuery client rate limiting
- Consider endpoint-level rate limiting if needed

---

## Database Considerations

### Storage Strategy: **API-Only (No Database Storage)**

**Rationale:**
- Financial statement data changes infrequently (quarterly/annual)
- Yahoo Finance already stores and serves this data
- Caching layer sufficient for performance
- Reduces data synchronization complexity
- No need for separate update jobs

**Future Consideration:**
If we need historical snapshots for auditing or offline access, consider:
- Store in `company_profiles` table (extend existing structure)
- Or create new `financial_statements` table
- Only store when explicitly requested by user

---

## API Documentation Updates

### Update `API_REFERENCE_V1.4.6.md`

Add new section:

```markdown
### Fundamentals (9 endpoints) ✅

**Historical Financials:**
- `GET /api/v1/fundamentals/income-statement/{symbol}` - Income statement data
- `GET /api/v1/fundamentals/balance-sheet/{symbol}` - Balance sheet data
- `GET /api/v1/fundamentals/cash-flow/{symbol}` - Cash flow statement data
- `GET /api/v1/fundamentals/all-statements/{symbol}` - All statements combined

**Forward-Looking:**
- `GET /api/v1/fundamentals/analyst-estimates/{symbol}` - Analyst revenue/EPS estimates
- `GET /api/v1/fundamentals/price-targets/{symbol}` - Analyst price targets
- `GET /api/v1/fundamentals/next-earnings/{symbol}` - Next earnings date and estimates

**Calculated:**
- `GET /api/v1/fundamentals/financial-ratios/{symbol}` - Calculated financial ratios
- `GET /api/v1/fundamentals/growth-metrics/{symbol}` - Growth trends and CAGR
```

---

## Testing Strategy

### Unit Tests
- Service layer transformation logic
- Calculation accuracy (financial ratios, growth rates)
- Error handling (null values, missing data)

### Integration Tests
- End-to-end API endpoint tests
- Multiple company types (tech, financial, industrial, retail)
- Edge cases (IPOs, no analyst coverage, high debt, no debt)

### Test Symbols
- **AAPL** (Apple) - Tech, low debt, high analyst coverage
- **T** (AT&T) - Telecom, high debt, stable business
- **TSLA** (Tesla) - High growth, volatile
- **BAC** (Bank of America) - Financial, different accounting
- **WMT** (Walmart) - Retail, mature business

---

## Dependencies

### Required (Already Available)
- ✅ `yahooquery` - Already in `pyproject.toml`
- ✅ `pandas` - Already in project
- ✅ `pydantic` - Already in project

### Optional (Future)
- `redis` or `cachetools` - For caching layer (Phase 4)

---

## Migration Path

### No Breaking Changes
All new endpoints, no modifications to existing APIs.

### Gradual Rollout
1. Phase 1: Internal testing only
2. Phase 2: Beta testing with select frontend components
3. Phase 3: Full production deployment
4. Phase 4: Optimization based on usage patterns

---

## Success Metrics

### Performance
- API response time < 500ms for single statement
- API response time < 1500ms for all statements
- Cache hit rate > 80% (Phase 4)

### Reliability
- 99%+ uptime
- Graceful degradation when Yahoo Finance unavailable
- Comprehensive error logging

### Data Quality
- 95%+ field coverage for large-cap stocks
- Accurate calculations (validated against known benchmarks)
- Fresh data (< 24 hours old for historical, < 1 hour for estimates)

---

## Open Questions

1. **Caching Strategy**: Implement immediately or defer to Phase 4?
   - Recommendation: Defer - assess need based on usage patterns

2. **Database Storage**: Store any historical snapshots?
   - Recommendation: No - start with API-only, reassess if needed

3. **Fallback Provider**: Implement FMP fallback for missing Yahoo Finance data?
   - Recommendation: Not initially - YahooQuery coverage is comprehensive

4. **Batch Endpoints**: Allow multiple symbols in one request?
   - Recommendation: Not initially - add if frontend needs it

5. **Calculated Fields**: Include in statement responses or separate endpoint?
   - Recommendation: Separate endpoint for flexibility and clarity

---

## Next Steps

1. ✅ Review and approve this implementation plan
2. 🔄 Review frontend implementation plan (see doc 03)
3. 🔄 Begin Phase 1 implementation
4. 🔄 Create detailed task breakdown in TODO system
5. 🔄 Set up test environment with diverse test symbols

---

## Appendix: Example YahooQuery Usage

```python
from yahooquery import Ticker
import asyncio

async def get_financials_example():
    """Example of using YahooQuery for financial data"""

    # Run synchronous YahooQuery in executor
    loop = asyncio.get_event_loop()

    def fetch_data():
        ticker = Ticker('AAPL')
        return {
            'income': ticker.income_statement(frequency='q'),
            'balance': ticker.balance_sheet(frequency='q'),
            'cashflow': ticker.cash_flow(frequency='q'),
            'estimates': ticker.earnings_trend,
            'targets': ticker.financial_data,
            'earnings': ticker.calendar_events
        }

    data = await loop.run_in_executor(None, fetch_data)

    # Transform and return
    return transform_data(data)
```

This pattern will be used throughout the implementation.
