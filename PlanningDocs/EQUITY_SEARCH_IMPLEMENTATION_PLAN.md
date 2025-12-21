# Equity Search Page Implementation Plan

**Status**: Implemented (December 21, 2025)

## Overview
Build a new Equity Search page that allows authenticated users to search, filter, and sort equities by market cap, enterprise value, P/E, P/S, Revenue, EBIT, FCF, and factor betas.

## Requirements Summary
- **Search**: Full-text search on ticker + company name
- **Filters**: Sector, market cap range, P/E range
- **Sort by**: Market Cap, Enterprise Value, P/S Ratio, P/E Ratio, Revenue, EBIT, FCF, Factor Betas
- **Period selector**: TTM, Last Year, Forward Estimates, Last Quarter
- **Auth**: Requires login
- **Navigation**: Accessible from dropdown menu

---

## Implementation Summary

### Backend Files Created

| File | Purpose |
|------|---------|
| `backend/app/schemas/equity_search.py` | Pydantic request/response models |
| `backend/app/services/equity_search_service.py` | Search logic, period handling |
| `backend/app/api/v1/equity_search.py` | API endpoints |

### Backend Files Modified

| File | Change |
|------|--------|
| `backend/app/api/v1/router.py` | Register equity_search router |

### Frontend Files Created

| File | Purpose |
|------|---------|
| `frontend/app/equity-search/page.tsx` | Page route (thin) |
| `frontend/src/containers/EquitySearchContainer.tsx` | Business logic |
| `frontend/src/components/equity-search/EquitySearchTable.tsx` | Sortable table |
| `frontend/src/components/equity-search/EquitySearchFilters.tsx` | Filter controls |
| `frontend/src/components/equity-search/PeriodSelector.tsx` | Period dropdown |
| `frontend/src/services/equitySearchApi.ts` | API client |
| `frontend/src/hooks/useEquitySearch.ts` | Data fetching hooks |

### Frontend Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/navigation/NavigationDropdown.tsx` | Add nav item |
| `frontend/src/config/api.ts` | Add EQUITY_SEARCH endpoints |

---

## API Endpoints

### `GET /api/v1/equity-search`

Main search endpoint with filters, sorting, and pagination.

**Query Parameters:**
- `query` (optional): Text search on symbol or company name
- `sectors` (optional): Comma-separated list of sectors
- `industries` (optional): Comma-separated list of industries
- `min_market_cap` / `max_market_cap` (optional): Market cap range
- `min_pe_ratio` / `max_pe_ratio` (optional): P/E ratio range
- `period`: One of `ttm`, `last_year`, `forward`, `last_quarter`
- `sort_by`: Column to sort by (market_cap, pe_ratio, factor_momentum, etc.)
- `sort_order`: `asc` or `desc`
- `limit`: Max results (1-200, default 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "items": [
    {
      "symbol": "AAPL",
      "company_name": "Apple Inc",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "market_cap": 3200000000000,
      "enterprise_value": 3100000000000,
      "ps_ratio": 8.5,
      "pe_ratio": 28.5,
      "revenue": 394328000000,
      "ebit": 119437000000,
      "fcf": 111443000000,
      "period_label": "TTM",
      "factor_value": 0.12,
      "factor_growth": 0.45,
      "factor_momentum": 0.67,
      "factor_quality": 0.89,
      "factor_size": -0.23,
      "factor_low_vol": 0.34
    }
  ],
  "total_count": 500,
  "filters_applied": {},
  "period": "ttm",
  "sort_by": "market_cap",
  "sort_order": "desc",
  "metrics_date": "2025-12-20"
}
```

### `GET /api/v1/equity-search/filters`

Returns available filter options for the UI.

**Response:**
```json
{
  "sectors": ["Technology", "Healthcare", "Financial Services", ...],
  "industries": ["Consumer Electronics", "Software", ...],
  "market_cap_ranges": [
    { "label": "Mega Cap (>$200B)", "min_value": 200000000000, "max_value": null },
    { "label": "Large Cap ($10B-$200B)", "min_value": 10000000000, "max_value": 200000000000 },
    ...
  ]
}
```

---

## Key Data Sources

**Primary Table**: `symbol_daily_metrics`
- market_cap, enterprise_value, pe_ratio, ps_ratio
- factor_value, factor_growth, factor_momentum, factor_quality, factor_size, factor_low_vol
- sector, industry, company_name
- Indexed for fast sorting

**Supplementary Tables** (for period-specific fundamentals):
- `income_statements` - Revenue, EBIT (TTM = sum last 4 quarters)
- `cash_flows` - FCF
- `balance_sheets` - For EV calculation (total_debt - cash)
- `company_profiles` - Forward estimates

---

## Period-Specific Data Sources

| Period | Revenue Source | EBIT Source | FCF Source |
|--------|---------------|-------------|------------|
| TTM | Sum last 4 quarters from income_statements | income_statements | cash_flows |
| Last Year | frequency='A' from income_statements | income_statements | cash_flows |
| Last Quarter | Latest frequency='Q' | income_statements | cash_flows |
| Forward | company_profiles.current_year_revenue_avg | N/A | N/A |

---

## UX Notes

- Dark theme with CSS variables (`--bg-primary`, `--text-secondary`, etc.)
- ShadCN UI components (Button, Select, Input)
- Lucide icons (BarChart3 for nav)
- Responsive design
- Loading states with spinner
- Error states with message
- "Load More" pagination
- Debounced search (300ms)
- Sortable column headers with chevron indicators
