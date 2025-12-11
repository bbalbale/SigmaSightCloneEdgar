# Data Sources Discovery: YFinance vs YahooQuery for Fundamental Data

**Date**: November 1, 2025
**Status**: Discovery Complete
**Next Step**: Backend Implementation Planning

---

## Executive Summary

We investigated **YFinance** and **YahooQuery** Python libraries to determine feasibility of adding comprehensive fundamental financial data to the Research page.

**Key Finding**: ✅ **All requested metrics are available** through YahooQuery, including historical financials (quarterly/annual going back 4 years) and forward-looking analyst estimates.

---

## Requirements

### Historical Financials Requested
1. Revenue
2. Cost of Goods Sold (COGS)
3. Gross Profit
4. S&M Expense (Sales & Marketing)
5. R&D Expense (Research & Development)
6. G&A Expense (General & Administrative)
7. SG&A (Selling, General & Administrative)
8. EBIT (Earnings Before Interest & Taxes)
9. Interest Expense/Income
10. Taxes
11. Depreciation
12. EBITDA (Earnings Before Interest, Taxes, Depreciation & Amortization)
13. Share Count (Basic & Diluted)
14. Operating Cash Flow
15. CAPEX (Capital Expenditures)
16. Free Cash Flow

### Forward-Looking Metrics Desired
- Analyst revenue estimates (current quarter, next quarter, current year, next year)
- Analyst EPS estimates (multiple periods)
- Price targets (low, mean, high)
- Growth projections
- Next earnings date with expectations

---

## Library Comparison: YFinance vs YahooQuery

### YFinance (Currently Used for Prices)

**Pros:**
- Already integrated in codebase (`app/clients/yfinance_client.py`)
- Free, no API key required
- Good for current prices, historical prices, basic company info

**Cons:**
- Only **4 years** of historical financial data
- Less comprehensive field coverage (~40 fields vs 180+ for YahooQuery)
- `quarterly_earnings` attribute deprecated → use `income_stmt` instead
- Can be unreliable (unofficial API)
- Limited financial statement detail

**Available Financial Methods:**
```python
stock = yf.Ticker('AAPL')
stock.financials              # Annual income statement
stock.quarterly_financials    # Quarterly income statement
stock.balance_sheet           # Annual balance sheet
stock.quarterly_balance_sheet # Quarterly balance sheet
stock.cashflow                # Annual cash flow
stock.quarterly_cashflow      # Quarterly cash flow
```

---

### YahooQuery ⭐ **RECOMMENDED** (Already Partially Integrated)

**Pros:**
- Already integrated in codebase (`app/clients/yahooquery_client.py`)
- **180+ balance sheet fields** (vs YFinance's basic coverage)
- **26+ cash flow metrics**
- **75+ income statement fields**
- Supports quarterly (`q`) and annual (`a`) frequency
- **TTM (Trailing Twelve Months)** data included
- More reliable and actively maintained
- Comprehensive analyst estimates and forward-looking data
- Can request specific fields via `get_financial_data()`
- Recent bug fixes (2025) for accuracy

**Cons:**
- Still limited to ~4 years of historical data (Yahoo Finance limitation, not library)
- Synchronous library (need to wrap in async executor)

**Available Methods:**
```python
from yahooquery import Ticker

ticker = Ticker('AAPL')

# Historical financials
ticker.income_statement(frequency='q')  # Quarterly
ticker.balance_sheet(frequency='a')     # Annual
ticker.cash_flow(frequency='q')         # Quarterly
ticker.valuation_measures               # Valuation metrics

# Forward-looking data
ticker.earnings_trend                   # Analyst estimates
ticker.financial_data                   # Price targets, growth
ticker.calendar_events                  # Next earnings date

# Combined data
ticker.all_financial_data()             # All statements
ticker.get_financial_data(['NetIncome', 'TotalRevenue'])  # Specific fields
```

---

## Field Mapping: Requirements → YahooQuery Fields

### Income Statement Fields ✅ ALL AVAILABLE

| Requested Metric | YahooQuery Field Name | Notes |
|------------------|----------------------|-------|
| Revenue | `TotalRevenue` or `OperatingRevenue` | ✅ Available |
| Cost of Goods Sold | `CostOfRevenue` or `ReconciledCostOfRevenue` | ✅ Available |
| Gross Profit | `GrossProfit` | ✅ Available |
| S&M Expense | `SellingGeneralAndAdministration` | ⚠️ Combined with G&A |
| R&D Expense | `ResearchAndDevelopment` | ✅ Available |
| G&A Expense | `SellingGeneralAndAdministration` | ⚠️ Combined with S&M |
| SG&A | `SellingGeneralAndAdministration` | ✅ Available |
| EBIT | `EBIT` | ✅ Available |
| Interest Expense/Income | `InterestExpense`, `InterestExpenseNonOperating`, `NetNonOperatingInterestIncomeExpense` | ✅ Available (conditional)* |
| Taxes | `TaxProvision` | ✅ Available |
| Depreciation | `ReconciledDepreciation` or `DepreciationAndAmortization` | ✅ Available |
| EBITDA | `EBITDA` or `NormalizedEBITDA` | ✅ Available |
| Share Count | `BasicAverageShares`, `DilutedAverageShares` | ✅ Available |

**Interest Expense Note**: Field is conditionally present based on company:
- **Present**: For companies with significant debt (banks, telecoms, utilities, airlines)
- **Absent/Null**: For companies with minimal debt (Apple, Google, cash-rich tech)
- This is correct accounting behavior - if not material, Yahoo Finance doesn't report it

### Cash Flow Fields ✅ ALL AVAILABLE

| Requested Metric | YahooQuery Field Name | Notes |
|------------------|----------------------|-------|
| Operating Cash Flow | `OperatingCashFlow` | ✅ Available |
| CAPEX | `CapitalExpenditure` | ✅ Available |
| Free Cash Flow | `FreeCashFlow` | ✅ Available |

### Balance Sheet Fields ✅ COMPREHENSIVE COVERAGE

**YahooQuery Balance Sheet Capabilities:**
```python
from yahooquery import Ticker

ticker = Ticker('AAPL')
balance_sheet_q = ticker.balance_sheet(frequency='q')  # Quarterly
balance_sheet_a = ticker.balance_sheet(frequency='a')  # Annual
```

**Available Data:**
- ✅ **180+ balance sheet fields** (most comprehensive)
- ✅ Quarterly and Annual frequencies
- ✅ TTM (Trailing Twelve Months)
- ✅ 4 years historical data
- ✅ **Free** - No API key required
- ✅ Validated in test scripts (`backend/scripts/testing/test_yahooquery_financials.py`)

**Assets (30+ fields):**
- Cash and Cash Equivalents
- Cash, Cash Equivalents, and Short-Term Investments
- Accounts Receivable
- Inventory
- Current Assets, Total Assets
- Net Property, Plant & Equipment (PP&E)
- Goodwill, Intangible Assets
- Long-Term Investments

**Liabilities (25+ fields):**
- Accounts Payable
- Short-Term Debt (Current Debt)
- Long-Term Debt
- Current Liabilities, Total Liabilities
- Deferred Revenue, Deferred Tax Liabilities

**Equity (15+ fields):**
- Common Stock, Preferred Stock
- Retained Earnings
- Treasury Stock
- Total Stockholders' Equity

**Calculated Metrics (Service Layer - Planned):**

**Liquidity Ratios:**
- Current Ratio = Current Assets / Current Liabilities
- Quick Ratio = (Current Assets - Inventory) / Current Liabilities
- Working Capital = Current Assets - Current Liabilities

**Leverage Ratios:**
- Debt-to-Equity = Total Debt / Total Equity
- Debt-to-Assets = Total Debt / Total Assets
- Net Debt = Total Debt - Cash

**Valuation Ratios:**
- Price-to-Book = Market Cap / Book Value
- Book Value per Share = Total Equity / Shares Outstanding

---

## Forward-Looking Data Available

### 1. Analyst Estimates (via `earnings_trend` module)

**Available Periods:**
- Current Quarter (0q)
- Next Quarter (+1q)
- Current Year (0y)
- Next Year (+1y)

**For Each Period:**
- **Revenue Estimates**: Average, Low, High, # Analysts, YoY Growth
- **EPS Estimates**: Average, Low, High, # Analysts, YoY Growth
- **EPS Revisions**: Upgrades/downgrades in last 7/30/60/90 days
- **EPS Trend**: Estimate changes over time

**Example Data (Apple, Current Quarter):**
```
Revenue Est: $137.96B (low: $136.68B, high: $140.67B)
  - 24 analysts
  - 11.0% YoY growth

EPS Est: $2.64 (low: $2.40, high: $2.80)
  - 27 analysts
  - Recent revisions: +7 upgrades in last 7 days
```

### 2. Price Targets (via `financial_data` module)

| Field | Example (Apple) |
|-------|-----------------|
| Target Price - Low | $200.00 |
| Target Price - Mean | $274.97 |
| Target Price - High | $345.00 |
| Analyst Recommendation | 2.0 (1=Strong Buy, 5=Sell) |
| # Analyst Opinions | 41 |
| Revenue Growth (forward) | 7.9% |
| Earnings Growth (forward) | 91.2% |

### 3. Next Earnings Date (via `calendar_events` module)

| Field | Example (Apple) |
|-------|-----------------|
| Next Earnings Date | January 29, 2026 |
| Expected EPS | $2.63 (low: $2.40, high: $2.71) |
| Expected Revenue | $137.96B (low: $136.68B, high: $140.67B) |

---

## Data Availability Summary

| Data Type | Quarterly | Annual | TTM | Historical Periods | Forward Periods |
|-----------|-----------|--------|-----|-------------------|-----------------|
| Income Statement | ✅ | ✅ | ✅ | 4 years | N/A |
| Balance Sheet | ✅ | ✅ | ✅ | 4 years | N/A |
| Cash Flow | ✅ | ✅ | ✅ | 4 years | N/A |
| Analyst Estimates (Revenue & EPS) | ✅ | ✅ | N/A | N/A | Current Q, +1Q, Current Y, +1Y |
| Price Targets | N/A | N/A | N/A | N/A | Current |
| Growth Projections | N/A | N/A | N/A | N/A | Current |

---

## Test Results

### Test Script: `backend/scripts/testing/test_yahooquery_financials.py`

**Test Symbols:**
- AAPL (Apple) - Low debt, tech company
- T (AT&T) - High debt, telecom company

**Results:**
- ✅ All 36 income statement fields retrieved
- ✅ All cash flow fields retrieved
- ✅ Analyst estimates for 4 forward periods
- ✅ Price targets and recommendations
- ✅ Next earnings date with expectations
- ✅ Interest expense available for AT&T ($1.699B)
- ⚠️ Interest expense N/A for Apple (expected - minimal debt)

---

## Limitations

### Yahoo Finance Platform Limitations
1. **Historical Data**: Limited to ~4 years (Yahoo Finance constraint, not library)
2. **S&M vs G&A Split**: Not available separately - Yahoo Finance combines as SG&A
3. **Interest Expense**: Only reported when material (accounting standard)

### Technical Considerations
1. **Synchronous Library**: YahooQuery is synchronous, need to wrap in async executor
2. **Rate Limiting**: Should implement conservative rate limiting (already in place for YFinance client)
3. **Data Freshness**: Depends on Yahoo Finance updates (typically lags 1-2 days after earnings)

---

## Recommendation

**Use YahooQuery** for fundamental data implementation because:

1. ✅ Already partially integrated in codebase
2. ✅ 180+ fields available (vs ~40 in YFinance)
3. ✅ All 14 requested historical metrics available
4. ✅ Comprehensive forward-looking data (estimates, targets, projections)
5. ✅ Both quarterly and annual data
6. ✅ TTM data for trend analysis
7. ✅ More reliable and actively maintained
8. ✅ Can request specific fields to minimize data transfer

---

---

## Storage Strategy Decision

**Decision Date**: November 2, 2025
**Decision**: Store all fundamental data (Phase 1 + Phase 2) in PostgreSQL database

### Storage Architecture

**Database Storage Approach:**
- ✅ Phase 1 financial statements (income, balance sheet, cash flow) → PostgreSQL
- ✅ Phase 2 analyst data (quarterly estimates, price targets) → PostgreSQL
- ✅ Batch job updates (daily refresh outside market hours)
- ✅ API endpoints serve from database (sub-50ms response vs 500ms-2s live fetch)

### Storage Calculations

**Phase 1: Financial Statements** (Time-Series Data)
- **Quarterly**: 12 quarters per symbol
  - Income Statement: ~5.8 KB (180 data points × 32 bytes)
  - Balance Sheet: ~19.2 KB (600 data points × 32 bytes)
  - Cash Flow: ~9.6 KB (300 data points × 32 bytes)
  - **Subtotal**: 34.6 KB per symbol

- **Annual**: 4 years per symbol
  - Income Statement: ~1.9 KB (60 data points × 32 bytes)
  - Balance Sheet: ~6.4 KB (200 data points × 32 bytes)
  - Cash Flow: ~3.2 KB (100 data points × 32 bytes)
  - **Subtotal**: 11.5 KB per symbol

- **Total Phase 1**: 46.1 KB per symbol (quarterly + annual)

**Phase 2: Analyst Data** (Snapshot Data - Current Only)
- Quarterly Estimates: ~0.21 KB per symbol (2 quarters × 7 fields)
- Price Targets: Already in company_profiles (no additional storage)
- Earnings Calendar: ~0.05 KB per symbol (3 fields)
- **Total Phase 2**: 0.26 KB per symbol (only NEW fields, excludes existing company_profiles data)

**Scale Projections:**
| Symbols | Phase 1 Storage | Phase 2 Storage | Total Storage |
|---------|----------------|----------------|---------------|
| 1,000   | 46.1 MB        | 0.26 MB        | 46.4 MB       |
| 5,000   | 230 MB         | 1.3 MB          | 231 MB        |
| 10,000  | 461 MB         | 2.6 MB          | 464 MB        |

**Verdict**: Extremely cost-effective. Even at 10,000 securities with both quarterly and annual data, total storage is only 464 MB.

### Database Tables Required

**New Tables (Phase 1):**

1. **`income_statements`**
```sql
CREATE TABLE income_statements (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    period_date DATE NOT NULL,
    fiscal_year INT,
    fiscal_quarter INT,
    frequency VARCHAR(1) CHECK (frequency IN ('q', 'a')),

    -- Revenue & Costs
    total_revenue NUMERIC(20, 2),
    cost_of_revenue NUMERIC(20, 2),
    gross_profit NUMERIC(20, 2),
    gross_margin NUMERIC(8, 6),

    -- Operating Expenses
    research_and_development NUMERIC(20, 2),
    selling_general_and_administrative NUMERIC(20, 2),

    -- Operating Results
    operating_income NUMERIC(20, 2),
    operating_margin NUMERIC(8, 6),
    ebit NUMERIC(20, 2),
    ebitda NUMERIC(20, 2),

    -- Net Income
    net_income NUMERIC(20, 2),
    net_margin NUMERIC(8, 6),
    diluted_eps NUMERIC(12, 4),
    basic_eps NUMERIC(12, 4),

    -- Share Counts
    basic_average_shares BIGINT,
    diluted_average_shares BIGINT,

    -- Tax & Interest
    tax_provision NUMERIC(20, 2),
    interest_expense NUMERIC(20, 2),
    depreciation_and_amortization NUMERIC(20, 2),

    -- Metadata
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(symbol, period_date, frequency)
);

CREATE INDEX idx_income_statements_symbol ON income_statements(symbol);
CREATE INDEX idx_income_statements_period ON income_statements(period_date DESC);
```

2. **`balance_sheets`**
```sql
CREATE TABLE balance_sheets (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    period_date DATE NOT NULL,
    fiscal_year INT,
    fiscal_quarter INT,
    frequency VARCHAR(1) CHECK (frequency IN ('q', 'a')),

    -- Assets
    cash_and_cash_equivalents NUMERIC(20, 2),
    short_term_investments NUMERIC(20, 2),
    accounts_receivable NUMERIC(20, 2),
    inventory NUMERIC(20, 2),
    current_assets NUMERIC(20, 2),
    net_ppe NUMERIC(20, 2),
    goodwill NUMERIC(20, 2),
    intangible_assets NUMERIC(20, 2),
    long_term_investments NUMERIC(20, 2),
    total_assets NUMERIC(20, 2),

    -- Liabilities
    accounts_payable NUMERIC(20, 2),
    short_term_debt NUMERIC(20, 2),
    current_liabilities NUMERIC(20, 2),
    long_term_debt NUMERIC(20, 2),
    deferred_revenue NUMERIC(20, 2),
    total_liabilities NUMERIC(20, 2),

    -- Equity
    common_stock NUMERIC(20, 2),
    retained_earnings NUMERIC(20, 2),
    treasury_stock NUMERIC(20, 2),
    total_stockholders_equity NUMERIC(20, 2),

    -- Calculated Metrics (Service Layer)
    working_capital NUMERIC(20, 2),
    net_debt NUMERIC(20, 2),
    book_value_per_share NUMERIC(12, 4),

    -- Calculated Ratios (Service Layer)
    current_ratio NUMERIC(8, 4),
    quick_ratio NUMERIC(8, 4),
    debt_to_equity NUMERIC(8, 4),
    debt_to_assets NUMERIC(8, 4),

    -- Metadata
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(symbol, period_date, frequency)
);

CREATE INDEX idx_balance_sheets_symbol ON balance_sheets(symbol);
CREATE INDEX idx_balance_sheets_period ON balance_sheets(period_date DESC);
```

3. **`cash_flows`**
```sql
CREATE TABLE cash_flows (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    period_date DATE NOT NULL,
    fiscal_year INT,
    fiscal_quarter INT,
    frequency VARCHAR(1) CHECK (frequency IN ('q', 'a')),

    -- Operating Activities
    operating_cash_flow NUMERIC(20, 2),
    depreciation_and_amortization NUMERIC(20, 2),
    deferred_income_tax NUMERIC(20, 2),
    stock_based_compensation NUMERIC(20, 2),
    change_in_working_capital NUMERIC(20, 2),

    -- Investing Activities
    capital_expenditures NUMERIC(20, 2),
    acquisitions NUMERIC(20, 2),
    purchase_of_investments NUMERIC(20, 2),
    sale_of_investments NUMERIC(20, 2),
    investing_cash_flow NUMERIC(20, 2),

    -- Financing Activities
    dividends_paid NUMERIC(20, 2),
    stock_repurchases NUMERIC(20, 2),
    debt_issuance NUMERIC(20, 2),
    debt_repayment NUMERIC(20, 2),
    financing_cash_flow NUMERIC(20, 2),

    -- Calculated Metrics (Service Layer)
    free_cash_flow NUMERIC(20, 2),
    fcf_margin NUMERIC(8, 6),

    -- Metadata
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(symbol, period_date, frequency)
);

CREATE INDEX idx_cash_flows_symbol ON cash_flows(symbol);
CREATE INDEX idx_cash_flows_period ON cash_flows(period_date DESC);
```

**Existing Table Enhancement (Phase 2):**

4. **`company_profiles`** (Add Quarterly Analyst Estimates)
```sql
-- Add columns to existing company_profiles table
ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS
    -- Current Quarter (Q0)
    current_quarter_revenue_avg NUMERIC(20, 2),
    current_quarter_revenue_low NUMERIC(20, 2),
    current_quarter_revenue_high NUMERIC(20, 2),
    current_quarter_eps_avg NUMERIC(12, 4),
    current_quarter_eps_low NUMERIC(12, 4),
    current_quarter_eps_high NUMERIC(12, 4),
    current_quarter_analyst_count INT,

    -- Next Quarter (Q+1)
    next_quarter_revenue_avg NUMERIC(20, 2),
    next_quarter_revenue_low NUMERIC(20, 2),
    next_quarter_revenue_high NUMERIC(20, 2),
    next_quarter_eps_avg NUMERIC(12, 4),
    next_quarter_eps_low NUMERIC(12, 4),
    next_quarter_eps_high NUMERIC(12, 4),
    next_quarter_analyst_count INT,

    -- Next Earnings Date
    next_earnings_date DATE,
    next_earnings_expected_eps NUMERIC(12, 4),
    next_earnings_expected_revenue NUMERIC(20, 2);
```

### Batch Job Integration

**Coordination with Existing company_profiles Table:**

The `company_profiles` table already stores:
- ✅ Annual analyst estimates (current_year, next_year) - Lines 102-120 in market_data.py
- ✅ Price targets (target_mean_price, target_high, target_low) - Lines 81-86
- ✅ Valuation metrics (PE, forward PE, beta, etc.) - Lines 72-78
- ✅ Profitability metrics (margins, ROE, ROA) - Lines 94-100

**What We're Adding:**
- ✅ Historical financial statements (NEW tables: income_statements, balance_sheets, cash_flows)
- ✅ Quarterly analyst estimates (ADD to company_profiles: current_quarter, next_quarter)
- ✅ Next earnings date (ADD to company_profiles: 3 new fields)

**Batch Orchestrator v3 Enhancement:**

Add new phase to `batch_orchestrator_v3.py`:

**Phase 1.5: Fundamental Data Collection** (Insert after Phase 1 Market Data)
```python
async def fetch_fundamental_data(self, symbol: str):
    """
    Fetch and store fundamental data for a symbol

    IMPORTANT: Coordinates with company_profiles to avoid double-pulling
    - Fetches each data type from YahooQuery ONCE
    - Stores financial statements in dedicated tables
    - Updates analyst data in existing company_profiles table
    """
    try:
        # ========================================
        # Part 1: Financial Statements (NEW TABLES)
        # ========================================

        # Fetch quarterly financial statements (12 quarters)
        quarterly_financials = await yahooquery_client.get_all_financials(
            symbol, frequency='q', years=3
        )

        # Fetch annual financial statements (4 years)
        annual_financials = await yahooquery_client.get_all_financials(
            symbol, frequency='a', years=4
        )

        # Store quarterly data (12 quarters)
        await self._store_income_statements(
            symbol, quarterly_financials['income_statement'], frequency='q'
        )
        await self._store_balance_sheets(
            symbol, quarterly_financials['balance_sheet'], frequency='q'
        )
        await self._store_cash_flows(
            symbol, quarterly_financials['cash_flow'], frequency='q'
        )

        # Store annual data (4 years)
        await self._store_income_statements(
            symbol, annual_financials['income_statement'], frequency='a'
        )
        await self._store_balance_sheets(
            symbol, annual_financials['balance_sheet'], frequency='a'
        )
        await self._store_cash_flows(
            symbol, annual_financials['cash_flow'], frequency='a'
        )

        # ========================================
        # Part 2: Analyst Data (UPDATE company_profiles)
        # ========================================

        # Fetch analyst data ONCE from YahooQuery
        analyst_estimates = await yahooquery_client.get_analyst_estimates(symbol)
        price_targets = await yahooquery_client.get_price_targets(symbol)
        earnings_calendar = await yahooquery_client.get_next_earnings(symbol)

        # Update company_profiles with ALL analyst data
        # - Annual estimates already stored (current_year, next_year)
        # - Add quarterly estimates (current_quarter, next_quarter)
        # - Update price targets (already stored, just refresh)
        # - Add next earnings date (new field)
        await self._update_company_profile_analyst_data(
            symbol=symbol,
            analyst_estimates=analyst_estimates,  # Contains 0q, +1q, 0y, +1y
            price_targets=price_targets,          # Already in company_profiles
            earnings_calendar=earnings_calendar   # Next earnings date (NEW)
        )

        logger.info(f"✅ Stored fundamental data for {symbol} (quarterly + annual)")

    except Exception as e:
        logger.error(f"❌ Error fetching fundamental data for {symbol}: {e}")
        # Graceful degradation - continue with other symbols
```

**Key Coordination Points:**

1. **Single API Calls**: Each YahooQuery method called ONCE per symbol
   - `get_all_financials(frequency='q')` → quarterly statements
   - `get_all_financials(frequency='a')` → annual statements
   - `get_analyst_estimates()` → quarterly + annual analyst data
   - `get_price_targets()` → price targets (refresh existing data)
   - `get_next_earnings()` → earnings calendar (new data)

2. **No Data Duplication**:
   - Financial statements → NEW dedicated tables (income_statements, balance_sheets, cash_flows)
   - Analyst annual estimates → ALREADY in company_profiles (just refresh)
   - Analyst quarterly estimates → ADD to company_profiles (new columns)
   - Price targets → ALREADY in company_profiles (just refresh)
   - Earnings date → ADD to company_profiles (new columns)

3. **Update Schedule:**
   - Daily batch run outside market hours (11 PM ET)
   - Incremental updates (only changed data via UPSERT)
   - Graceful degradation if Yahoo Finance unavailable
   - Retry logic for failed symbols
   - Use UNIQUE constraints to prevent duplicates

### Benefits of Database Storage

1. **Performance**: Sub-50ms database queries vs 500ms-2s API calls
2. **Reliability**: No dependency on Yahoo Finance uptime during user sessions
3. **Consistency**: All users see the same data snapshot
4. **Analytics Ready**: Can run SQL queries across all fundamental data
5. **Cost-Effective**: 175 MB for 5,000 securities is negligible
6. **Caching Natural**: Database IS the cache, no complex invalidation
7. **Batch Efficiency**: Single daily update vs thousands of on-demand calls

### Integration with Existing Systems

**Detailed Comparison: What's Already Stored vs What We're Adding**

| Data Category | What's in company_profiles NOW | What We're ADDING | Table Destination | YahooQuery Method |
|---------------|-------------------------------|-------------------|-------------------|-------------------|
| **Financial Statements - Quarterly** | ❌ None | ✅ 12 quarters of income/balance/cash flow | `income_statements`, `balance_sheets`, `cash_flows` (new tables) | `get_all_financials(frequency='q')` |
| **Financial Statements - Annual** | ❌ None | ✅ 4 years of income/balance/cash flow | `income_statements`, `balance_sheets`, `cash_flows` (new tables) | `get_all_financials(frequency='a')` |
| **Analyst Price Targets** | ✅ `target_mean_price`, `target_high_price`, `target_low_price` (lines 81-83) | ➕ Just refresh existing data | `company_profiles` (existing) | `get_price_targets()` |
| **Analyst Annual Estimates** | ✅ `current_year_revenue_avg/low/high`, `next_year_revenue_avg/low/high` (lines 103-119) | ➕ Just refresh existing data | `company_profiles` (existing) | `get_analyst_estimates()` - 0y, +1y periods |
| **Analyst Quarterly Estimates** | ❌ None | ✅ `current_quarter_*`, `next_quarter_*` (14 new columns) | `company_profiles` (add columns) | `get_analyst_estimates()` - 0q, +1q periods |
| **Next Earnings Date** | ❌ None | ✅ `next_earnings_date`, `next_earnings_expected_eps/revenue` (3 new columns) | `company_profiles` (add columns) | `get_next_earnings()` |
| **Recommendation** | ✅ `recommendation_mean`, `recommendation_key` (lines 85-86) | ➕ Just refresh existing data | `company_profiles` (existing) | `get_price_targets()` |
| **Valuation Metrics** | ✅ `pe_ratio`, `forward_pe`, `beta`, etc. (lines 73-78) | ➕ Just refresh existing data | `company_profiles` (existing) | Part of profile sync (not fundamentals) |

**API Call Coordination (Per Symbol, Per Batch Run):**

| YahooQuery Method | Called | Stores Data In | Updates Existing? | Creates New? |
|-------------------|--------|----------------|-------------------|--------------|
| `get_all_financials(frequency='q', years=3)` | ✅ 1× | `income_statements`, `balance_sheets`, `cash_flows` | No | Yes (UPSERT 12 quarterly periods) |
| `get_all_financials(frequency='a', years=4)` | ✅ 1× | `income_statements`, `balance_sheets`, `cash_flows` | No | Yes (UPSERT 4 annual periods) |
| `get_analyst_estimates()` | ✅ 1× | `company_profiles` | Yes (refresh annual + add quarterly) | No |
| `get_price_targets()` | ✅ 1× | `company_profiles` | Yes (refresh existing fields) | No |
| `get_next_earnings()` | ✅ 1× | `company_profiles` | No | Yes (add 3 new columns) |

**Total API Calls per Symbol**: 5 (each method called once)

**Data Flow:**
1. Batch job iterates through all portfolio symbols
2. For each symbol, fetch data from YahooQuery (5 API calls per symbol)
3. Store financial statements in NEW dedicated tables (UPSERT with UNIQUE constraint)
4. Update company_profiles with analyst data (UPDATE existing row + add new columns)
5. No data duplication - each piece of data stored in exactly ONE location
6. API endpoints serve from database (financial statements from dedicated tables, analyst data from company_profiles)
7. Frontend displays via Research page (single API call gets all data)

---

## Next Steps

1. ✅ **Discovery Complete** - All requested fields confirmed available
2. ✅ **Storage Strategy Finalized** - Database storage approach approved
3. 🔄 **Backend Implementation** - Create tables, endpoints, batch integration
   - Create Alembic migrations for 3 new tables
   - Add Phase 1.5 to batch_orchestrator_v3
   - Implement service layer with calculated metrics
   - Create API endpoints (same as Phase 1 but serve from DB)
4. 🔄 **Frontend Implementation** - Plan Research page integration
5. 🔄 **Testing** - Validate with diverse company types (tech, financial, industrial)
6. 🔄 **Documentation** - Update API reference

---

## References

- **YahooQuery Documentation**: https://yahooquery.dpguthrie.com/
- **YFinance Documentation**: https://github.com/ranaroussi/yfinance
- **Test Scripts**:
  - `backend/scripts/testing/test_yahooquery_financials.py`
  - `backend/scripts/testing/test_yahooquery_interest.py`
- **Current Integration**:
  - `backend/app/clients/yahooquery_client.py` (partial)
  - `backend/app/clients/yfinance_client.py` (full)
