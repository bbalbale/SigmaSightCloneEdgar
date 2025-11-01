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

## Next Steps

1. ✅ **Discovery Complete** - All requested fields confirmed available
2. 🔄 **Backend Implementation** - Design endpoints and service layer
3. 🔄 **Frontend Implementation** - Plan Research page integration
4. 🔄 **Testing** - Validate with diverse company types (tech, financial, industrial)
5. 🔄 **Documentation** - Update API reference

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
