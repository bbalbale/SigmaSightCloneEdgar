# Fundamental Financial Data - Planning Documents

**Created**: November 1, 2025
**Status**: Planning Phase - Ready for Review & Discussion

---

## Overview

This folder contains comprehensive planning documents for adding fundamental financial data (historical financials, analyst estimates, price targets) to the SigmaSight Research page.

---

## Documents

### 1. [Data Sources Discovery](./01-DATA-SOURCES-DISCOVERY.md)
**What it covers**: Our investigation into YFinance and YahooQuery capabilities

**Key Findings**:
- ✅ ALL 14 requested historical metrics available via YahooQuery
- ✅ Comprehensive forward-looking data (analyst estimates, price targets, next earnings)
- ✅ Both quarterly and annual data, going back 4 years
- ✅ Already integrated in backend codebase

**Read this if**: You want to understand data availability and limitations

---

### 2. [Backend Implementation Plan](./02-BACKEND-IMPLEMENTATION-PLAN.md)
**What it covers**: Complete backend architecture and implementation strategy

**Key Components**:
- 9 new API endpoints across 4 categories
- Service layer design (extend YahooQueryClient + new fundamentals service)
- Pydantic schemas for all request/response models
- 4-phase implementation plan (4 weeks)
- Error handling, caching, and optimization strategies

**Read this if**: You're implementing the backend API layer

---

### 3. [Frontend Implementation Plan](./03-FRONTEND-IMPLEMENTATION-PLAN.md) ⭐
**What it covers**: Frontend integration strategy - HOW to add this to Research page

**Recommended Approach**: Add new "FINANCIALS" tab to Research & Analyze page

**Key Design Decisions**:
- New tab alongside PUBLIC/OPTIONS/PRIVATE
- Symbol selector for focused analysis
- 4 sections: Statements, Forward Outlook, Ratios, Growth Trends
- 4-phase implementation (4 weeks)
- 8 open questions for discussion

**Read this if**: You're implementing the frontend UI or need to discuss UX approach

---

## Quick Summary

### What We Can Pull (Data Available)

**Historical Financials** (quarterly/annual, 4 years):
- Revenue, COGS, Gross Profit, Gross Margin
- R&D, SG&A, Operating Expenses
- EBIT, EBITDA, Interest Expense (when material)
- Taxes, Depreciation, Net Income, EPS
- Share Count (basic & diluted)
- Operating Cash Flow, CAPEX, Free Cash Flow

**Forward-Looking Data**:
- Analyst estimates for revenue & EPS (current Q, next Q, current Y, next Y)
- Price targets (low, mean, high) with upside calculations
- Analyst recommendations (buy/hold/sell distribution)
- Next earnings date with expected revenue/EPS
- EPS estimate revisions tracking

**Calculated Metrics**:
- Profitability ratios (margins, ROE, ROA)
- Efficiency ratios (turnover, DSO)
- Leverage ratios (debt ratios, coverage)
- Liquidity ratios (current, quick, cash)
- Growth rates (QoQ, YoY, CAGR)

---

## Implementation Timeline

### Backend (4 weeks)
- **Week 1**: Core financial statements endpoints (4 endpoints)
- **Week 2**: Forward-looking data endpoints (3 endpoints)
- **Week 3**: Calculated metrics endpoints (2 endpoints)
- **Week 4**: Optimization & caching

### Frontend (4 weeks)
- **Week 1**: Foundation (new tab, symbol selector, service layer)
- **Week 2**: Financial statements display (3 table components)
- **Week 3**: Forward-looking data display (estimates, targets, next earnings)
- **Week 4**: Calculated metrics & polish

**Parallel Development**: Backend and frontend can be developed concurrently with mock data

---

## Key Decisions Needed

Before starting implementation, we need to decide:

1. **Tab Placement**: Confirm "FINANCIALS" tab approach vs. alternatives
2. **Symbol Selection**: Portfolio-only or allow searching all symbols?
3. **Default View**: Compact (key metrics) or Full (all fields)?
4. **MVP Scope**: Include all 4 phases or ship earlier?
5. **Charts**: Include visualizations initially or defer?
6. **AI Integration**: Plan for AI chat access to fundamental data?
7. **Comparison**: Multi-symbol side-by-side view needed?
8. **Mobile**: Accept horizontal scroll or custom mobile layout?

**See**: [Frontend Implementation Plan - Section: Open Questions](./03-FRONTEND-IMPLEMENTATION-PLAN.md#open-questions--discussion-points)

---

## Data Source Recommendation

**Use YahooQuery** (not YFinance) because:
- 180+ fields available (vs ~40 in YFinance)
- All requested metrics confirmed available
- Comprehensive forward-looking data
- More reliable and actively maintained
- Already integrated in codebase

---

## Next Steps

1. ✅ **Planning Complete** - Review these 3 documents
2. 🔄 **Discuss Open Questions** - Make key decisions (see Section above)
3. 🔄 **Backend Implementation** - Start Phase 1 (Week 1)
4. 🔄 **Frontend Implementation** - Start Phase 1 (Week 1)
5. 🔄 **Testing** - Validate with diverse company types
6. 🔄 **Deployment** - Gradual rollout with beta testing

---

## Related Documentation

- **Backend API Reference**: `backend/_docs/reference/API_REFERENCE_V1.4.6.md`
- **Frontend Requirements**: `frontend/_docs/requirements/README.md`
- **Research Page Current Implementation**: `frontend/src/containers/ResearchAndAnalyzeContainer.tsx`
- **YahooQuery Documentation**: https://yahooquery.dpguthrie.com/
- **Test Scripts**:
  - `backend/scripts/testing/test_yahooquery_financials.py`
  - `backend/scripts/testing/test_yahooquery_interest.py`

---

## Questions or Concerns?

Refer to the specific document:
- **Data availability**: See Document 1 (Data Sources Discovery)
- **Backend architecture**: See Document 2 (Backend Implementation Plan)
- **Frontend UX/design**: See Document 3 (Frontend Implementation Plan)

---

**Status**: Ready for review and discussion. No code development yet - planning only.
