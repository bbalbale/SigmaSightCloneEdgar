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
        "assets": {
          "current_assets": {
            "cash_and_equivalents": 29943000000,
            "short_term_investments": 35228000000,
            "cash_and_short_term_investments": 65171000000,
            "accounts_receivable": 25995000000,
            "inventory": 6511000000,
            "other_current_assets": 14287000000,
            "total_current_assets": 111964000000
          },
          "non_current_assets": {
            "net_ppe": 44109000000,
            "goodwill": null,
            "intangible_assets": null,
            "long_term_investments": 91060000000,
            "other_non_current_assets": 76572000000,
            "total_non_current_assets": 211741000000
          },
          "total_assets": 323705000000
        },
        "liabilities": {
          "current_liabilities": {
            "accounts_payable": 58229000000,
            "short_term_debt": 9822000000,
            "current_portion_long_term_debt": 10912000000,
            "accrued_liabilities": 29906000000,
            "deferred_revenue": 8249000000,
            "other_current_liabilities": 19600000000,
            "total_current_liabilities": 136718000000
          },
          "non_current_liabilities": {
            "long_term_debt": 85750000000,
            "deferred_tax_liabilities": null,
            "other_non_current_liabilities": 30362000000,
            "total_non_current_liabilities": 116112000000
          },
          "total_liabilities": 252830000000
        },
        "equity": {
          "common_stock": 82113000000,
          "retained_earnings": -17020000000,
          "accumulated_other_comprehensive_income": -10218000000,
          "treasury_stock": null,
          "total_stockholders_equity": 70875000000,
          "minority_interest": null
        },
        "calculated_metrics": {
          "working_capital": -24754000000,
          "net_debt": 41313000000,
          "total_debt": 106484000000,
          "book_value": 70875000000,
          "book_value_per_share": 4.53,
          "tangible_book_value": 70875000000,
          "tangible_book_value_per_share": 4.53
        },
        "ratios": {
          "current_ratio": 0.819,
          "quick_ratio": 0.771,
          "cash_ratio": 0.477,
          "debt_to_equity": 1.502,
          "debt_to_assets": 0.329,
          "equity_to_assets": 0.219
        }
      }
    },
    // ... more periods
  ],
  "metadata": {
    "data_source": "yahooquery",
    "last_updated": "2024-11-01T12:00:00Z",
    "periods_returned": 12,
    "fields_available": 180
  }
}
```

**Field Mapping (YahooQuery → Application):**

**Assets (30+ fields available):**
- `CashAndCashEquivalents` → `cash_and_equivalents`
- `CashCashEquivalentsAndShortTermInvestments` → `cash_and_short_term_investments`
- `AccountsReceivable` → `accounts_receivable`
- `Inventory` → `inventory`
- `CurrentAssets` → `total_current_assets`
- `NetPPE` → `net_ppe`
- `PropertyPlantEquipment` → `gross_ppe`
- `AccumulatedDepreciation` → `accumulated_depreciation`
- `GoodwillAndOtherIntangibleAssets` → `goodwill`
- `Goodwill` → `goodwill`
- `IntangibleAssets` → `intangible_assets`
- `LongTermEquityInvestment` → `long_term_investments`
- `TotalAssets` → `total_assets`

**Liabilities (25+ fields available):**
- `AccountsPayable` → `accounts_payable`
- `CurrentDebt` → `short_term_debt`
- `CurrentDebtAndCapitalLeaseObligation` → `current_portion_long_term_debt`
- `CurrentAccruedExpenses` → `accrued_liabilities`
- `CurrentDeferredRevenue` → `deferred_revenue`
- `CurrentLiabilities` → `total_current_liabilities`
- `LongTermDebt` → `long_term_debt`
- `LongTermDebtAndCapitalLeaseObligation` → `long_term_debt_total`
- `DeferredTaxLiabilitiesNonCurrent` → `deferred_tax_liabilities`
- `TotalNonCurrentLiabilitiesNetMinorityInterest` → `total_non_current_liabilities`
- `TotalLiabilitiesNetMinorityInterest` → `total_liabilities`

**Equity (15+ fields available):**
- `CommonStock` → `common_stock`
- `PreferredStock` → `preferred_stock`
- `RetainedEarnings` → `retained_earnings`
- `AccumulatedOtherComprehensiveIncome` → `accumulated_other_comprehensive_income`
- `TreasuryStock` → `treasury_stock`
- `StockholdersEquity` → `total_stockholders_equity`
- `MinorityInterest` → `minority_interest`

**Calculated Metrics:**
- **Working Capital** = Current Assets - Current Liabilities
- **Net Debt** = Total Debt - Cash and Cash Equivalents
- **Total Debt** = Short-term Debt + Long-term Debt
- **Book Value** = Total Stockholders' Equity
- **Book Value per Share** = Book Value / Shares Outstanding
- **Tangible Book Value** = Book Value - Goodwill - Intangible Assets
- **Tangible Book Value per Share** = Tangible Book Value / Shares Outstanding

**Liquidity Ratios:**
- **Current Ratio** = Current Assets / Current Liabilities
- **Quick Ratio** = (Current Assets - Inventory) / Current Liabilities
- **Cash Ratio** = Cash and Equivalents / Current Liabilities

**Leverage Ratios:**
- **Debt-to-Equity** = Total Debt / Total Equity
- **Debt-to-Assets** = Total Debt / Total Assets
- **Equity-to-Assets** = Total Equity / Total Assets

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

## Batch Orchestrator Integration ⭐ **CRITICAL**

### Overview

Fundamental financial data should be integrated into the **batch orchestrator v3** (`app/batch/batch_orchestrator_v3.py`) with **earnings-based timing** to avoid unnecessary API calls and database writes.

**Key Insight**: Financial statements only update quarterly (after earnings releases). Pulling this data daily or weekly is wasteful.

### Quarterly Update Strategy

**Trigger**: **3 days after earnings date** (allows time for data to be published to Yahoo Finance)

**Rationale**:
- Financial statements are released during quarterly earnings calls
- Yahoo Finance needs 1-3 days to process and publish the data
- 3-day buffer ensures data availability while keeping it fresh
- Applies to both financial statements AND company profile updates

### Implementation Architecture

#### 1. New Batch Phase: "Fundamentals Collection"

**Add to batch_orchestrator_v3** as **Phase 4** (after existing Phase 3 - Risk Analytics):

```python
# app/batch/batch_orchestrator_v3.py

class BatchOrchestratorV3:
    # ... existing phases 1-3 ...

    async def run_fundamentals_collection(self, portfolio_id: UUID = None):
        """
        Phase 4: Collect fundamental financial data

        Runs quarterly, triggered 3 days after earnings date
        Updates both financial statements AND company profiles

        Args:
            portfolio_id: If provided, only collect for positions in this portfolio
        """
        logger.info("=" * 50)
        logger.info("PHASE 4: Fundamentals Collection")
        logger.info("=" * 50)

        try:
            # Get symbols that need fundamentals update
            symbols_to_update = await self._get_symbols_needing_fundamentals_update(portfolio_id)

            if not symbols_to_update:
                logger.info("No symbols require fundamentals update at this time")
                return

            logger.info(f"Updating fundamentals for {len(symbols_to_update)} symbols")

            # Collect financial statements
            await self._collect_financial_statements(symbols_to_update)

            # Update company profiles (if also stale)
            await self._update_company_profiles(symbols_to_update)

            logger.info("Phase 4: Fundamentals collection complete")

        except Exception as e:
            logger.error(f"Phase 4 failed: {str(e)}")
            raise
```

#### 2. Earnings Date Tracking

**Create new table**: `financial_statement_updates`

```python
# app/models/fundamentals.py (NEW FILE)

from sqlalchemy import Column, String, Date, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from datetime import datetime
import uuid

class FinancialStatementUpdate(Base):
    __tablename__ = "financial_statement_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True, unique=True)

    # Earnings tracking
    last_earnings_date = Column(Date, nullable=True)  # Most recent earnings date
    next_earnings_date = Column(Date, nullable=True)  # Upcoming earnings (from YahooQuery calendar_events)

    # Update tracking
    last_financials_update = Column(DateTime, nullable=True)  # When we last pulled statements
    last_profile_update = Column(DateTime, nullable=True)     # When we last pulled company profile

    # Status flags
    needs_update = Column(Boolean, default=False)  # True if earnings_date + 3 days has passed
    update_scheduled_for = Column(Date, nullable=True)  # earnings_date + 3 days

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Migration**:
```bash
# Create Alembic migration
alembic revision --autogenerate -m "Add financial_statement_updates table"
alembic upgrade head
```

#### 3. Update Logic

**Service**: `app/services/fundamentals_update_service.py` (NEW FILE)

```python
from datetime import datetime, date, timedelta
from typing import List
from sqlalchemy import select
from yahooquery import Ticker

async def get_symbols_needing_fundamentals_update(
    db: AsyncSession,
    portfolio_id: UUID = None
) -> List[str]:
    """
    Get symbols that need fundamentals update based on earnings date + 3 days

    Logic:
    1. Check if symbol has next_earnings_date
    2. If next_earnings_date + 3 days <= today AND needs_update = False:
       - Mark needs_update = True
       - Add to update list
    3. Also check symbols with no recent update (>90 days)

    Args:
        db: Database session
        portfolio_id: Optional - only check symbols in this portfolio

    Returns:
        List of symbols needing update
    """
    today = date.today()

    # Get all symbols from positions (optionally filtered by portfolio)
    symbols_query = select(Position.symbol).distinct()
    if portfolio_id:
        symbols_query = symbols_query.where(Position.portfolio_id == portfolio_id)

    symbols_result = await db.execute(symbols_query)
    all_symbols = [row[0] for row in symbols_result.fetchall()]

    symbols_to_update = []

    for symbol in all_symbols:
        # Get update record
        update_record = await db.execute(
            select(FinancialStatementUpdate).where(
                FinancialStatementUpdate.symbol == symbol
            )
        )
        update_record = update_record.scalar_one_or_none()

        # If no record exists, create one and add to update list
        if not update_record:
            update_record = FinancialStatementUpdate(
                symbol=symbol,
                needs_update=True,
                update_scheduled_for=today
            )
            db.add(update_record)
            symbols_to_update.append(symbol)
            continue

        # Check if earnings + 3 days has passed
        if update_record.next_earnings_date:
            update_date = update_record.next_earnings_date + timedelta(days=3)
            if update_date <= today and not update_record.needs_update:
                update_record.needs_update = True
                update_record.update_scheduled_for = update_date
                symbols_to_update.append(symbol)
                continue

        # Check if last update was > 90 days ago (stale data failsafe)
        if update_record.last_financials_update:
            days_since_update = (today - update_record.last_financials_update.date()).days
            if days_since_update > 90:
                update_record.needs_update = True
                symbols_to_update.append(symbol)

    await db.commit()
    return symbols_to_update


async def update_next_earnings_dates(db: AsyncSession):
    """
    Batch update next earnings dates for all symbols

    Runs daily as part of batch orchestrator
    Uses YahooQuery calendar_events to get upcoming earnings
    """
    # Get all symbols with update records
    result = await db.execute(select(FinancialStatementUpdate))
    records = result.scalars().all()

    for record in records:
        try:
            # Fetch next earnings date from YahooQuery
            ticker = Ticker(record.symbol)
            calendar = ticker.calendar_events

            if isinstance(calendar, dict) and record.symbol in calendar:
                earnings_data = calendar[record.symbol].get('earnings', {})
                earnings_dates = earnings_data.get('earningsDate', [])

                if earnings_dates and len(earnings_dates) > 0:
                    # Take first date (next earnings)
                    next_earnings = earnings_dates[0]

                    # Convert to date object
                    if isinstance(next_earnings, str):
                        next_earnings = datetime.fromisoformat(next_earnings).date()
                    elif hasattr(next_earnings, 'date'):
                        next_earnings = next_earnings.date()

                    record.next_earnings_date = next_earnings
                    logger.info(f"{record.symbol}: Next earnings {next_earnings}")

        except Exception as e:
            logger.warning(f"Could not fetch earnings date for {record.symbol}: {str(e)}")
            continue

    await db.commit()
```

#### 4. Batch Orchestrator Integration Points

**Daily Job** (existing batch run):
1. Update next earnings dates for all symbols (lightweight YahooQuery calendar_events call)
2. Check which symbols need fundamentals update (earnings_date + 3 days logic)
3. If symbols need update, run Phase 4

**Weekly Job** (new):
1. Verify no symbols are >90 days stale
2. Force update for stale symbols

**Manual Trigger** (Admin endpoint):
```python
POST /api/v1/admin/fundamentals/update-symbol/{symbol}
# Force immediate update for a specific symbol
```

### Company Profile Integration

**Shared Timing Logic**: Company profiles should update on same schedule as financial statements

**Rationale**:
- Sector/industry rarely changes, but may during corporate actions
- Market cap changes daily (but we get that from prices)
- Earnings estimates are part of fundamentals, should update quarterly
- Description, officers, etc. rarely change

**Implementation**:
```python
# When updating financial statements, also update company profile
async def collect_fundamentals_for_symbol(symbol: str):
    # 1. Get financial statements (income, balance, cash flow)
    statements = await fundamentals_client.get_all_statements(symbol)

    # 2. Get analyst estimates and price targets
    estimates = await fundamentals_client.get_analyst_estimates(symbol)
    targets = await fundamentals_client.get_price_targets(symbol)

    # 3. Update company profile (if stale or earnings-triggered)
    profile = await company_profile_service.sync_profile(symbol)

    # 4. Store all data
    await store_financial_statements(symbol, statements)
    await store_analyst_estimates(symbol, estimates)
    await store_price_targets(symbol, targets)

    # 5. Mark as updated
    await mark_fundamentals_updated(symbol)
```

### Scheduling Strategy

**Option A: Cron-Based** (Recommended)
```python
# APScheduler configuration
scheduler.add_job(
    update_next_earnings_dates,
    trigger='cron',
    hour=1,  # 1 AM daily
    minute=0,
    id='daily_earnings_dates_update'
)

scheduler.add_job(
    check_and_run_fundamentals_updates,
    trigger='cron',
    hour=2,  # 2 AM daily (after earnings dates updated)
    minute=0,
    id='daily_fundamentals_check'
)

scheduler.add_job(
    force_update_stale_symbols,
    trigger='cron',
    day_of_week='sun',  # Weekly on Sunday
    hour=3,
    minute=0,
    id='weekly_stale_fundamentals_check'
)
```

**Option B: Event-Driven** (Future Enhancement)
- Listen for earnings announcements (external data source)
- Trigger update immediately when earnings detected
- More complex but more responsive

### Database Storage Strategy

**New Tables**:

1. **`financial_statements`** - Raw statement data
```python
class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(UUID, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    statement_type = Column(String(20))  # 'income', 'balance', 'cashflow'
    frequency = Column(String(1))  # 'q' or 'a'
    period_date = Column(Date, nullable=False)
    fiscal_year = Column(Integer)
    fiscal_quarter = Column(String(2))  # 'Q1', 'Q2', etc.
    data = Column(JSON)  # All fields as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **`analyst_estimates`** - Forward-looking data
```python
class AnalystEstimate(Base):
    __tablename__ = "analyst_estimates"

    id = Column(UUID, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    estimate_type = Column(String(20))  # 'revenue', 'eps'
    period_type = Column(String(10))  # '0q', '+1q', '0y', '+1y'
    estimate_avg = Column(Numeric(precision=20, scale=2))
    estimate_low = Column(Numeric(precision=20, scale=2))
    estimate_high = Column(Numeric(precision=20, scale=2))
    num_analysts = Column(Integer)
    as_of_date = Column(Date, nullable=False)  # When estimate was fetched
    created_at = Column(DateTime, default=datetime.utcnow)
```

3. **`price_targets`** - Analyst price targets
```python
class PriceTarget(Base):
    __tablename__ = "price_targets"

    id = Column(UUID, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    target_low = Column(Numeric(precision=10, scale=2))
    target_mean = Column(Numeric(precision=10, scale=2))
    target_high = Column(Numeric(precision=10, scale=2))
    recommendation_mean = Column(Numeric(precision=3, scale=2))
    num_analysts = Column(Integer)
    as_of_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Storage vs. API-Only Decision**:

**Recommendation**: **STORE** fundamentals data (different from original plan)

**Why?**
- Financial statements don't change retroactively (historical accuracy)
- Enables time-series analysis (track how estimates changed over time)
- Reduces API dependency for historical queries
- Allows offline access and faster queries
- Only updates quarterly (manageable data volume)

**Data Volume Estimate**:
- 3 statements × 12 quarters × 100 symbols = 3,600 records
- ~1KB per statement = ~3.6MB per symbol for 3 years
- For 100 symbols: ~360MB (very manageable)

### Benefits of Earnings-Based Timing

1. **API Efficiency**:
   - 4 updates/year instead of 365 updates/year = 98.9% reduction
   - Respects Yahoo Finance rate limits
   - Reduces unnecessary processing

2. **Data Freshness**:
   - Updates within 3 days of new data availability
   - More relevant than arbitrary weekly/monthly schedules
   - Aligns with actual reporting cycles

3. **Database Efficiency**:
   - Fewer writes
   - Historical data remains stable
   - Only new quarters added

4. **User Experience**:
   - Data is always current within 3 days of earnings
   - No stale data issues
   - Consistent update timing

5. **Shared Infrastructure**:
   - Company profiles update on same schedule
   - Consistent data freshness across features
   - Single batch job handles both

### Implementation Checklist

**Phase 1: Database Setup**
- [ ] Create `financial_statement_updates` table (Alembic migration)
- [ ] Create `financial_statements` table (Alembic migration)
- [ ] Create `analyst_estimates` table (Alembic migration)
- [ ] Create `price_targets` table (Alembic migration)

**Phase 2: Service Layer**
- [ ] Create `fundamentals_update_service.py`
- [ ] Implement `get_symbols_needing_fundamentals_update()`
- [ ] Implement `update_next_earnings_dates()`
- [ ] Implement `collect_fundamentals_for_symbol()`
- [ ] Implement `mark_fundamentals_updated()`

**Phase 3: Batch Orchestrator Integration**
- [ ] Add Phase 4 to `batch_orchestrator_v3.py`
- [ ] Add daily earnings date update job
- [ ] Add daily fundamentals check job
- [ ] Add weekly stale data check job
- [ ] Update admin endpoints to trigger manual updates

**Phase 4: Company Profile Integration**
- [ ] Modify `company_profile_service.py` to use same timing
- [ ] Add `last_profile_update` tracking to `financial_statement_updates`
- [ ] Update company profiles during fundamentals collection

**Phase 5: Testing**
- [ ] Test earnings date fetching
- [ ] Test 3-day trigger logic
- [ ] Test stale data failsafe (>90 days)
- [ ] Test manual trigger endpoint
- [ ] Verify no duplicate updates

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

# Balance Sheet Schemas
class CurrentAssets(BaseModel):
    """Current assets breakdown"""
    cash_and_equivalents: Optional[Decimal]
    short_term_investments: Optional[Decimal]
    cash_and_short_term_investments: Optional[Decimal]
    accounts_receivable: Optional[Decimal]
    inventory: Optional[Decimal]
    other_current_assets: Optional[Decimal]
    total_current_assets: Optional[Decimal]

class NonCurrentAssets(BaseModel):
    """Non-current assets breakdown"""
    net_ppe: Optional[Decimal]
    goodwill: Optional[Decimal]
    intangible_assets: Optional[Decimal]
    long_term_investments: Optional[Decimal]
    other_non_current_assets: Optional[Decimal]
    total_non_current_assets: Optional[Decimal]

class Assets(BaseModel):
    """All assets"""
    current_assets: CurrentAssets
    non_current_assets: NonCurrentAssets
    total_assets: Optional[Decimal]

class CurrentLiabilities(BaseModel):
    """Current liabilities breakdown"""
    accounts_payable: Optional[Decimal]
    short_term_debt: Optional[Decimal]
    current_portion_long_term_debt: Optional[Decimal]
    accrued_liabilities: Optional[Decimal]
    deferred_revenue: Optional[Decimal]
    other_current_liabilities: Optional[Decimal]
    total_current_liabilities: Optional[Decimal]

class NonCurrentLiabilities(BaseModel):
    """Non-current liabilities breakdown"""
    long_term_debt: Optional[Decimal]
    deferred_tax_liabilities: Optional[Decimal]
    other_non_current_liabilities: Optional[Decimal]
    total_non_current_liabilities: Optional[Decimal]

class Liabilities(BaseModel):
    """All liabilities"""
    current_liabilities: CurrentLiabilities
    non_current_liabilities: NonCurrentLiabilities
    total_liabilities: Optional[Decimal]

class Equity(BaseModel):
    """Shareholders' equity"""
    common_stock: Optional[Decimal]
    retained_earnings: Optional[Decimal]
    accumulated_other_comprehensive_income: Optional[Decimal]
    treasury_stock: Optional[Decimal]
    total_stockholders_equity: Optional[Decimal]
    minority_interest: Optional[Decimal]

class BalanceSheetCalculatedMetrics(BaseModel):
    """Calculated balance sheet metrics"""
    working_capital: Optional[Decimal]
    net_debt: Optional[Decimal]
    total_debt: Optional[Decimal]
    book_value: Optional[Decimal]
    book_value_per_share: Optional[Decimal]
    tangible_book_value: Optional[Decimal]
    tangible_book_value_per_share: Optional[Decimal]

class BalanceSheetRatios(BaseModel):
    """Balance sheet ratios"""
    current_ratio: Optional[Decimal]
    quick_ratio: Optional[Decimal]
    cash_ratio: Optional[Decimal]
    debt_to_equity: Optional[Decimal]
    debt_to_assets: Optional[Decimal]
    equity_to_assets: Optional[Decimal]

class BalanceSheetMetrics(BaseModel):
    """Balance sheet metrics for one period"""
    assets: Assets
    liabilities: Liabilities
    equity: Equity
    calculated_metrics: BalanceSheetCalculatedMetrics
    ratios: BalanceSheetRatios

class BalanceSheetPeriod(FinancialPeriod):
    """Balance sheet for one period"""
    metrics: BalanceSheetMetrics

class BalanceSheetResponse(BaseModel):
    """Full balance sheet response"""
    symbol: str
    frequency: str  # "q", "a", "ttm"
    currency: str
    periods: List[BalanceSheetPeriod]
    metadata: Dict[str, any]

# Cash Flow Schemas (similar structure)

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
