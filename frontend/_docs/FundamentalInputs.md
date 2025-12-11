# User-Input Fundamentals for Research & Analyze Page

**Created**: 2025-12-11
**Status**: Planning
**Author**: Claude Code

---

## Overview

This document outlines the plan for allowing users to input their own fundamental estimates about companies on the Research & Analyze page. This feature enables users to override analyst consensus estimates with their own projections for revenue, EPS, and other key metrics.

---

## Current State

### What Exists Today

1. **FinancialsTab** (in expanded row) displays:
   - 4 years historical data (Revenue, Gross Profit, EBIT, Net Income, EPS, FCF)
   - 2 years forward estimates from analyst consensus
   - All data comes from backend via `fundamentalsApi` (income statements, cash flows, analyst estimates)

2. **User-editable fields already exist:**
   - Target prices (EOY, Next Year) - stored in `portfolio_target_prices` table
   - These are inline-editable in the Research table

3. **Data sources:**
   - Historical: Backend database populated by batch orchestrator (FMP data)
   - Forward estimates: Analyst consensus from company profiles

### Relevant Files

**Frontend:**
- `frontend/src/hooks/useFundamentals.ts` - Fetches and transforms fundamental data
- `frontend/src/services/fundamentalsApi.ts` - API service for fundamentals
- `frontend/src/containers/ResearchAndAnalyzeContainer.tsx` - Main page container
- `frontend/src/components/research/ResearchTableViewDesktop.tsx` - Desktop table with expandable rows

**Backend:**
- `backend/app/api/v1/fundamentals.py` - Fundamentals API endpoints
- `backend/app/models/target_prices.py` - Reference pattern for user inputs

---

## Proposed Solution

### 1. Backend Changes

#### New Database Model - `user_fundamentals.py`

```python
"""
User Fundamental Estimates model for portfolio-specific financial projections
"""
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Text, UniqueConstraint, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database import Base


class UserFundamental(Base):
    """
    Portfolio-specific fundamental estimates for positions.
    Allows users to input their own projections that override analyst consensus.
    """
    __tablename__ = "user_fundamentals"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    portfolio_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False
    )
    position_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=True  # Optional link to specific position
    )

    # Symbol and period
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 2025, 2026
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)  # True for forward-looking

    # Revenue metrics
    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)  # As decimal (0.15 = 15%)

    # Profitability metrics
    gross_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    gross_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    ebit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    ebit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    net_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Per-share metrics
    eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    eps_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Cash flow metrics
    fcf: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    fcf_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # User's rationale
    data_source: Mapped[str] = mapped_column(
        String(50),
        default="USER_INPUT"
    )  # USER_INPUT, MODEL, ADJUSTED_ANALYST

    # Audit fields
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="user_fundamentals")
    position: Mapped[Optional["Position"]] = relationship("Position", back_populates="user_fundamentals")

    # Table constraints and indexes
    __table_args__ = (
        # One estimate per portfolio/symbol/year combination
        UniqueConstraint('portfolio_id', 'symbol', 'fiscal_year', name='uq_portfolio_symbol_year'),

        # Performance indexes
        Index('ix_user_fundamentals_portfolio_id', 'portfolio_id'),
        Index('ix_user_fundamentals_symbol', 'symbol'),
        Index('ix_user_fundamentals_fiscal_year', 'fiscal_year'),
        Index('ix_user_fundamentals_position_id', 'position_id'),
    )

    def __repr__(self):
        return (
            f"<UserFundamental(portfolio={self.portfolio_id}, symbol={self.symbol}, "
            f"year={self.fiscal_year}, eps={self.eps}, revenue={self.revenue})>"
        )
```

#### New API Endpoints (~6 endpoints)

**File:** `backend/app/api/v1/user_fundamentals.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/user-fundamentals` | Create user fundamental estimate |
| `GET` | `/api/v1/user-fundamentals` | List estimates (filter by portfolio, symbol, year) |
| `GET` | `/api/v1/user-fundamentals/{id}` | Get single estimate |
| `PUT` | `/api/v1/user-fundamentals/{id}` | Update estimate |
| `DELETE` | `/api/v1/user-fundamentals/{id}` | Delete estimate |
| `POST` | `/api/v1/user-fundamentals/bulk` | Bulk create/update estimates |

#### Alembic Migration

Create migration for `user_fundamentals` table with proper indexes and constraints.

---

### 2. Frontend Changes

#### New Service - `userFundamentalsApi.ts`

```typescript
// frontend/src/services/userFundamentalsApi.ts

import { apiClient } from './apiClient';
import { authManager } from './authManager';

export interface UserFundamental {
  id: string;
  portfolio_id: string;
  position_id?: string;
  symbol: string;
  fiscal_year: number;
  is_estimate: boolean;

  // Metrics
  revenue?: number;
  revenue_growth?: number;
  gross_profit?: number;
  gross_margin?: number;
  ebit?: number;
  ebit_margin?: number;
  net_income?: number;
  net_margin?: number;
  eps?: number;
  eps_growth?: number;
  fcf?: number;
  fcf_margin?: number;

  // Metadata
  notes?: string;
  data_source: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUserFundamentalRequest {
  portfolio_id: string;
  position_id?: string;
  symbol: string;
  fiscal_year: number;
  revenue?: number;
  eps?: number;
  net_income?: number;
  // ... other optional fields
  notes?: string;
}

class UserFundamentalsApi {
  async create(data: CreateUserFundamentalRequest): Promise<UserFundamental> {
    // ...
  }

  async list(params: {
    portfolio_id?: string;
    symbol?: string;
    fiscal_year?: number
  }): Promise<UserFundamental[]> {
    // ...
  }

  async get(id: string): Promise<UserFundamental> {
    // ...
  }

  async update(id: string, data: Partial<CreateUserFundamentalRequest>): Promise<UserFundamental> {
    // ...
  }

  async delete(id: string): Promise<void> {
    // ...
  }

  async bulkUpsert(data: CreateUserFundamentalRequest[]): Promise<UserFundamental[]> {
    // ...
  }
}

export default new UserFundamentalsApi();
```

#### Update `useFundamentals.ts` Hook

Add logic to:
1. Fetch user fundamentals alongside analyst estimates
2. Merge data with user estimates taking precedence
3. Track which values are user-provided vs analyst consensus

```typescript
// Enhanced return type
export interface FinancialYearData {
  year: number;
  isEstimate: boolean;
  isUserProvided: boolean;  // NEW: Track if user provided this data

  revenue: number | null;
  revenueGrowth: number | null;
  revenueSource: 'analyst' | 'user';  // NEW: Track source

  eps: number | null;
  epsGrowth: number | null;
  epsSource: 'analyst' | 'user';  // NEW: Track source

  // ... other fields with source tracking
}
```

#### Update FinancialsTab Component

**New capabilities:**
- Editable cells for forward estimate years (2025E, 2026E)
- Visual distinction between analyst vs user data
- "Reset to Analyst" option per field or per year

---

### 3. UI/UX Design Options

#### Option A: Inline Editing (Recommended)

**Pros:**
- Consistent with existing target price editing pattern
- Familiar UX for users
- Quick edits without leaving context

**Cons:**
- Limited space for notes/rationale
- Can feel cramped for many fields

**Implementation:**
- Click on estimate cell to edit
- Auto-save on blur
- Show pencil icon on hover
- Badge showing "Your Estimate" vs "Analyst"

```
┌─────────────────────────────────────────────────────────────────┐
│ Financials                                    2024   2025E  2026E│
├─────────────────────────────────────────────────────────────────┤
│ Revenue ($B)                                  391.0  [420.5] 455.0│
│                                                      ↑ Your Est   │
│ Revenue Growth                                 8.2%  [7.5%] 8.2% │
│ EPS                                          $6.42  [$7.10] $7.85│
│                                                      ↑ Your Est   │
└─────────────────────────────────────────────────────────────────┘
```

#### Option B: Edit Modal/Drawer

**Pros:**
- More space for detailed inputs
- Room for notes/rationale
- Better for bulk edits

**Cons:**
- Extra click to open modal
- Context switching

**Implementation:**
- "Edit Estimates" button opens modal
- Form with all fields for selected year
- Text area for notes
- Save/Cancel buttons

#### Option C: Side-by-Side Comparison View

**Pros:**
- Clear comparison of user vs analyst
- Educational - see where you differ
- Good for analysis

**Cons:**
- Takes more screen space
- More complex UI

**Implementation:**
- Toggle switch: "Show My Estimates | Analyst Consensus | Compare"
- Compare view shows both columns with diff highlighting

---

### 4. Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                 │
└──────────────────────────────────────────────────────────────────┘

User clicks "Edit" on 2025E EPS cell
              │
              ▼
┌─────────────────────────────────┐
│  Opens inline editor            │
│  Shows current value: $3.85     │
│  (Analyst consensus)            │
└─────────────────────────────────┘
              │
              ▼
User enters their estimate: $4.10
              │
              ▼
┌─────────────────────────────────┐
│  Frontend calls                 │
│  userFundamentalsApi.create()   │
│  or .update() if exists         │
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Backend saves to               │
│  user_fundamentals table        │
│  with portfolio_id scope        │
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  useFundamentals hook           │
│  re-fetches and merges data     │
│  User data overrides analyst    │
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  FinancialsTab displays:        │
│  EPS: $4.10 [Your Estimate]     │
│  with blue badge indicator      │
└─────────────────────────────────┘
```

---

### 5. Estimated Implementation Scope

| Component | Effort | Notes |
|-----------|--------|-------|
| Backend model + migration | Small | Single table, follows target_prices pattern |
| Backend API (6 endpoints) | Medium | CRUD + bulk, follows existing patterns |
| Backend tests | Small | Unit tests for endpoints |
| Frontend service | Small | Similar to targetPricesApi |
| useFundamentals update | Medium | Add merge logic, source tracking |
| FinancialsTab UI updates | Medium-Large | Inline editing, badges, reset functionality |
| Frontend tests | Medium | Component + integration tests |
| E2E testing | Medium | Full flow validation |

**Total Estimate:** 2-3 days of focused development

---

### 6. Design Decisions Required

Before implementation, the following decisions need to be made:

#### 6.1 Scope of Editability

**Question:** Which metrics should users be able to edit?

| Option | Fields | Recommendation |
|--------|--------|----------------|
| Minimal | EPS, Revenue only | Start here - most impactful for valuation |
| Standard | + Net Income, FCF | Good balance |
| Full | All fields (EBIT, Gross Profit, margins) | Maximum flexibility |

**Recommendation:** Start with **Minimal** (EPS, Revenue) and expand based on user feedback.

#### 6.2 Year Scope

**Question:** How many forward years can users edit?

| Option | Years | Notes |
|--------|-------|-------|
| Match Analyst | Current Year + Next Year | Consistent with existing data |
| Extended | Up to 5 years forward | For DCF modeling |

**Recommendation:** Start with **Current Year + Next Year** to match analyst data structure.

#### 6.3 Historical Overrides

**Question:** Allow users to input historical data?

| Option | Use Case |
|--------|----------|
| No historical | Only forward estimates editable |
| Allow historical | For private companies or missing data |

**Recommendation:** **No historical** initially - focus on forward estimates.

#### 6.4 Portfolio vs. Global Scope

**Question:** Should estimates be portfolio-specific or global?

| Option | Behavior |
|--------|----------|
| Per-Portfolio | Different estimates possible per portfolio (like target prices) |
| Global | One set of estimates per symbol across all portfolios |

**Recommendation:** **Per-Portfolio** for consistency with target prices and flexibility.

#### 6.5 UI Pattern

**Question:** How should users edit estimates?

| Option | Best For |
|--------|----------|
| Inline Editing | Quick changes, familiar pattern |
| Modal Form | Detailed edits with notes |
| Hybrid | Inline for values, modal for notes |

**Recommendation:** **Inline Editing** with optional notes popover.

#### 6.6 Validation Rules

**Question:** What validation should be applied?

| Field | Validation |
|-------|------------|
| Revenue | Must be positive, reasonable range |
| EPS | Can be negative (losses), reasonable range |
| Growth rates | -100% to +1000% (reasonable bounds) |
| Margins | 0% to 100% (or negative for losses) |

---

### 7. Implementation Phases

#### Phase 1: Backend Foundation
1. Create Alembic migration for `user_fundamentals` table
2. Create `UserFundamental` model
3. Create Pydantic schemas
4. Implement 6 API endpoints
5. Add unit tests

#### Phase 2: Frontend Service Layer
1. Create `userFundamentalsApi.ts` service
2. Update `useFundamentals.ts` hook with merge logic
3. Add source tracking to `FinancialYearData` type

#### Phase 3: UI Implementation
1. Add inline editing to FinancialsTab
2. Implement "Your Estimate" badge
3. Add "Reset to Analyst" functionality
4. Style updates for edit states

#### Phase 4: Testing & Polish
1. E2E testing of full flow
2. Edge case handling
3. Loading/error states
4. Mobile responsiveness (if applicable)

---

### 8. Future Enhancements

Once the core feature is implemented, consider:

1. **Estimate Templates**: Save and apply estimate templates across positions
2. **Import from Spreadsheet**: Bulk import estimates from Excel/CSV
3. **Estimate History**: Track changes to estimates over time
4. **Comparison Dashboard**: Dedicated view comparing user vs analyst estimates
5. **AI-Assisted Estimates**: Use AI to suggest estimates based on user's thesis
6. **Sharing**: Share estimates with other users (for teams)

---

### 9. Related Documentation

- `frontend/_docs/FundamentalData/` - Existing fundamental data documentation
- `backend/app/models/target_prices.py` - Reference pattern for user inputs
- `frontend/src/hooks/useFundamentals.ts` - Current fundamentals hook
- `frontend/src/services/fundamentalsApi.ts` - Current API service

---

### 10. Open Questions

1. Should we show a "confidence" indicator for user estimates?
2. Should estimates auto-expire after the fiscal year passes?
3. Should we notify users when analyst estimates change significantly?
4. Integration with AI chat - should the AI be able to reference user estimates?
