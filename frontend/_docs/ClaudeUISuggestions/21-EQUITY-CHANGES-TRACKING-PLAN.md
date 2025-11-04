# Equity Changes Tracking - Planning Document

**Feature**: Capital Contributions & Withdrawals Tracking
**Created**: November 3, 2025
**Updated**: November 3, 2025 (Added Phase 0 prerequisite)
**Status**: Planning Phase - **Requires Phase 0 Completion**
**Priority**: High
**Estimated Effort**: 5-8 days

---

## 🚨 CRITICAL PREREQUISITE: Phase 0 Must Be Complete

**This feature depends on Phase 0: Realized P&L Tracking being fully implemented first.**

Before starting this implementation:
- ✅ Phase 0 must be complete and tested
- ✅ Realized P&L calculations must be working
- ✅ Portfolio snapshots must include `daily_realized_pnl` and `cumulative_realized_pnl`
- ✅ Equity rollforward formula must include realized P&L component

**Related Documents**:
- **[22-EQUITY-AND-PNL-TRACKING-SUMMARY.md](./22-EQUITY-AND-PNL-TRACKING-SUMMARY.md)** - Master summary plan
- **[23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)** - Phase 0 detailed plan

---

## Executive Summary

Add functionality to track capital contributions and withdrawals separately from P&L-driven equity changes. This enables accurate performance measurement (time-weighted returns) by distinguishing between investment gains/losses and external cash movements.

**Key Business Value:**
- Accurate portfolio performance measurement independent of capital flows
- Clear audit trail of all capital contributions and withdrawals
- Better investor reporting (separate P&L from capital movements)
- Foundation for time-weighted return (TWR) calculations

---

## Current State Analysis

### What Exists ✅

1. **Database Schema**
   - `portfolios.equity_balance` field (Decimal 16,2) stores current NAV
   - `portfolio_snapshots.equity_balance` tracks historical equity over time
   - **[Phase 0 Complete]** Realized P&L tracking for closed positions
   - **[Phase 0 Complete]** Portfolio snapshots include `daily_realized_pnl` and `cumulative_realized_pnl`
   - P&L calculator rollforward: `new_equity = previous_equity + unrealized_pnl + realized_pnl`

2. **Command Center UI**
   - "Manage Positions" side panel for adding/removing positions
   - Hero metrics display current portfolio value
   - Holdings table shows position-level details

3. **Backend Infrastructure**
   - 59 production-ready API endpoints across 9 categories
   - Batch processing system with 3 phases + Phase 2.5
   - Established patterns for CRUD operations (see target-prices endpoints)

### What's Missing ❌

1. **Data Model**: No separate tracking of contributions vs. withdrawals vs. P&L
2. **API Layer**: No endpoints for recording equity changes
3. **P&L Logic**: Calculator doesn't account for external cash movements
4. **UI Components**: No interface for users to record equity changes
5. **Reporting**: Can't distinguish investment performance from capital flows

### Key Problem

Current system conflates two distinct types of equity changes:
- **Internal**: P&L from market movements (should affect returns)
- **External**: Capital contributions/withdrawals (should NOT affect returns)

This makes accurate performance measurement impossible for accounts with deposits/withdrawals.

---

## Proposed Solution Architecture

### Overview

Implement a comprehensive equity change tracking system with:
1. Dedicated database table for contributions/withdrawals
2. REST API endpoints following existing patterns
3. UI component integrated into Command Center
4. Enhanced P&L calculation logic
5. Updated reporting to show true investment performance

---

## Phase 1: Backend - Database Schema

### New Table: `equity_changes`

**File**: `backend/app/models/equity_changes.py`

```python
"""
Equity changes - tracks capital contributions and withdrawals
"""
from datetime import datetime, date
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database import Base
import enum

class EquityChangeType(str, enum.Enum):
    """Type of equity change"""
    CONTRIBUTION = "CONTRIBUTION"  # Adding capital to portfolio
    WITHDRAWAL = "WITHDRAWAL"      # Removing capital from portfolio

class EquityChange(Base):
    """
    Tracks capital contributions and withdrawals to/from portfolio.
    Separate from P&L-driven equity changes for accurate performance measurement.
    """
    __tablename__ = "equity_changes"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    portfolio_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Change details
    change_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    change_type: Mapped[EquityChangeType] = mapped_column(
        SQLEnum(EquityChangeType, name="equity_change_type"),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(16, 2),
        nullable=False
    )  # Always positive; type indicates direction

    # Optional metadata
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )  # Soft delete

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="equity_changes")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index('ix_equity_changes_portfolio_date', 'portfolio_id', 'change_date'),
        Index('ix_equity_changes_type', 'change_type'),
        Index('ix_equity_changes_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        return f"<EquityChange {self.change_type.value} ${self.amount} on {self.change_date}>"
```

### Database Migration

**File**: `backend/alembic/versions/YYYY_MM_DD_HHMM_add_equity_changes.py`

```python
"""add equity_changes table

Revision ID: <generated>
Revises: <previous_revision>
Create Date: 2025-11-XX XX:XX:XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '<generated>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None

def upgrade():
    # Create enum type
    equity_change_type = postgresql.ENUM(
        'CONTRIBUTION',
        'WITHDRAWAL',
        name='equity_change_type'
    )
    equity_change_type.create(op.get_bind())

    # Create equity_changes table
    op.create_table(
        'equity_changes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('change_date', sa.Date(), nullable=False),
        sa.Column('change_type', equity_change_type, nullable=False),
        sa.Column('amount', sa.Numeric(16, 2), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
    )

    # Create indexes
    op.create_index('ix_equity_changes_portfolio_id', 'equity_changes', ['portfolio_id'])
    op.create_index('ix_equity_changes_change_date', 'equity_changes', ['change_date'])
    op.create_index('ix_equity_changes_portfolio_date', 'equity_changes', ['portfolio_id', 'change_date'])
    op.create_index('ix_equity_changes_type', 'equity_changes', ['change_type'])
    op.create_index('ix_equity_changes_deleted_at', 'equity_changes', ['deleted_at'])

    # Add relationship to portfolios
    # Note: This requires updating Portfolio model in code, not migration

def downgrade():
    op.drop_index('ix_equity_changes_deleted_at', 'equity_changes')
    op.drop_index('ix_equity_changes_type', 'equity_changes')
    op.drop_index('ix_equity_changes_portfolio_date', 'equity_changes')
    op.drop_index('ix_equity_changes_change_date', 'equity_changes')
    op.drop_index('ix_equity_changes_portfolio_id', 'equity_changes')
    op.drop_table('equity_changes')

    # Drop enum type
    sa.Enum(name='equity_change_type').drop(op.get_bind())
```

### Update Portfolio Model

**File**: `backend/app/models/users.py`

Add relationship to Portfolio class:

```python
# Add to Portfolio class relationships section (around line 61)
equity_changes: Mapped[List["EquityChange"]] = relationship(
    "EquityChange",
    back_populates="portfolio",
    order_by="EquityChange.change_date.desc()"
)
```

---

## Phase 2: Backend - API Endpoints

### Endpoint Design

**Base Path**: `/api/v1/equity-changes`

Following existing patterns from `target_prices.py` and `position_tags.py`.

### 6 Core Endpoints

#### 1. Record Equity Change
```
POST /api/v1/equity-changes/{portfolio_id}
```

**Request Body**:
```json
{
  "change_date": "2025-11-03",
  "change_type": "CONTRIBUTION",
  "amount": 50000.00,
  "description": "Q4 2025 capital injection"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "portfolio_id": "uuid",
  "change_date": "2025-11-03",
  "change_type": "CONTRIBUTION",
  "amount": 50000.00,
  "description": "Q4 2025 capital injection",
  "created_at": "2025-11-03T14:30:00Z",
  "created_by_user_id": "uuid",
  "portfolio_equity_after": 1712126.38
}
```

**Validations**:
- Amount must be > 0
- Date cannot be in the future
- User must own portfolio
- For WITHDRAWAL: amount cannot exceed current equity balance

#### 2. List Equity Changes
```
GET /api/v1/equity-changes/{portfolio_id}
  ?start_date=2025-01-01
  &end_date=2025-12-31
  &change_type=CONTRIBUTION
  &limit=50
  &offset=0
```

**Response** (200 OK):
```json
{
  "total": 12,
  "limit": 50,
  "offset": 0,
  "equity_changes": [
    {
      "id": "uuid",
      "change_date": "2025-11-03",
      "change_type": "CONTRIBUTION",
      "amount": 50000.00,
      "description": "Q4 2025 capital injection",
      "created_at": "2025-11-03T14:30:00Z"
    }
  ]
}
```

#### 3. Get Summary Statistics
```
GET /api/v1/equity-changes/{portfolio_id}/summary
  ?start_date=2025-01-01
  &end_date=2025-12-31
```

**Response** (200 OK):
```json
{
  "period": {
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  },
  "total_contributions": 150000.00,
  "total_withdrawals": 25000.00,
  "net_flow": 125000.00,
  "contribution_count": 8,
  "withdrawal_count": 4,
  "largest_contribution": 50000.00,
  "largest_withdrawal": 10000.00,
  "starting_equity": 1500000.00,
  "ending_equity": 1712126.38,
  "equity_from_pnl": 87126.38,
  "equity_from_flows": 125000.00
}
```

#### 4. Get Single Equity Change
```
GET /api/v1/equity-changes/change/{id}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "portfolio_id": "uuid",
  "change_date": "2025-11-03",
  "change_type": "CONTRIBUTION",
  "amount": 50000.00,
  "description": "Q4 2025 capital injection",
  "created_at": "2025-11-03T14:30:00Z",
  "created_by_user_id": "uuid",
  "updated_at": null,
  "can_edit": true,
  "can_delete": true
}
```

#### 5. Update Equity Change
```
PUT /api/v1/equity-changes/change/{id}
```

**Request Body**:
```json
{
  "amount": 55000.00,
  "description": "Updated: Q4 2025 capital injection"
}
```

**Business Rules**:
- Only allow edits within 7 days of creation
- Cannot change `change_date` or `change_type` (delete and recreate instead)
- Must still pass validation (amount > 0, etc.)

**Response** (200 OK): Same as GET single equity change

#### 6. Delete Equity Change
```
DELETE /api/v1/equity-changes/change/{id}
```

**Business Rules**:
- Only allow deletion within 30 days of creation
- Soft delete (set `deleted_at` timestamp)
- Requires portfolio ownership

**Response** (204 No Content)

### Implementation File

**File**: `backend/app/api/v1/equity_changes.py`

```python
"""
Equity Changes API endpoints
Tracks capital contributions and withdrawals
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.equity_changes import EquityChange, EquityChangeType
from app.schemas.equity_changes import (
    EquityChangeCreate,
    EquityChangeUpdate,
    EquityChangeResponse,
    EquityChangeListResponse,
    EquityChangeSummaryResponse
)

logger = get_logger(__name__)
router = APIRouter(prefix="/equity-changes", tags=["equity-changes"])

# Constants
EDIT_WINDOW_DAYS = 7
DELETE_WINDOW_DAYS = 30

# Endpoint implementations follow...
# [See full implementation in next section]
```

### Pydantic Schemas

**File**: `backend/app/schemas/equity_changes.py`

```python
"""
Pydantic schemas for equity changes
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator

from app.models.equity_changes import EquityChangeType


class EquityChangeCreate(BaseModel):
    """Schema for creating equity change"""
    change_date: date = Field(..., description="Date of contribution/withdrawal")
    change_type: EquityChangeType = Field(..., description="CONTRIBUTION or WITHDRAWAL")
    amount: Decimal = Field(..., gt=0, description="Amount (always positive)")
    description: Optional[str] = Field(None, max_length=500, description="Optional notes")

    @validator('change_date')
    def validate_date(cls, v):
        if v > date.today():
            raise ValueError('Change date cannot be in the future')
        return v


class EquityChangeUpdate(BaseModel):
    """Schema for updating equity change"""
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)


class EquityChangeResponse(BaseModel):
    """Schema for equity change response"""
    id: UUID
    portfolio_id: UUID
    change_date: date
    change_type: EquityChangeType
    amount: Decimal
    description: Optional[str]
    created_at: datetime
    created_by_user_id: UUID
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    # Computed fields
    can_edit: bool = False
    can_delete: bool = False
    portfolio_equity_after: Optional[Decimal] = None

    class Config:
        from_attributes = True


class EquityChangeListResponse(BaseModel):
    """Schema for paginated list of equity changes"""
    total: int
    limit: int
    offset: int
    equity_changes: List[EquityChangeResponse]


class EquityChangeSummaryResponse(BaseModel):
    """Schema for equity change summary statistics"""
    period: dict  # {start_date, end_date}
    total_contributions: Decimal
    total_withdrawals: Decimal
    net_flow: Decimal
    contribution_count: int
    withdrawal_count: int
    largest_contribution: Optional[Decimal]
    largest_withdrawal: Optional[Decimal]
    starting_equity: Optional[Decimal]
    ending_equity: Optional[Decimal]
    equity_from_pnl: Optional[Decimal]
    equity_from_flows: Decimal
```

---

## Phase 3: Backend - P&L Calculator Enhancement

### Current Implementation (After Phase 0)

**File**: `backend/app/batch/pnl_calculator.py`

Current equity rollforward (includes realized P&L from Phase 0):
```python
# From Phase 0: Separate unrealized and realized P&L
daily_unrealized_pnl = calculate_mark_to_market_change()
daily_realized_pnl = sum(closed_positions.realized_pnl where exit_date = today)

total_pnl = daily_unrealized_pnl + daily_realized_pnl
new_equity = previous_equity + total_pnl
```

### Enhanced Implementation (Phase 1: Add Equity Changes)

**Updated Logic**:
```python
# Phase 0: Calculate investment P&L (unrealized + realized)
daily_unrealized_pnl = calculate_mark_to_market_change()
daily_realized_pnl = sum(closed_positions.realized_pnl where exit_date = today)
investment_pnl = daily_unrealized_pnl + daily_realized_pnl

# Phase 1: Get equity changes for the calculation date
contributions = sum(changes where type=CONTRIBUTION and date=calculation_date)
withdrawals = sum(changes where type=WITHDRAWAL and date=calculation_date)

# Calculate new equity (complete formula)
new_equity = (
    previous_equity      # Starting equity
    + investment_pnl     # Unrealized + Realized P&L
    + contributions      # Capital added
    - withdrawals        # Capital removed
)

# Calculate returns on adjusted base
# (Returns should exclude the impact of external cash flows)
adjusted_previous_equity = previous_equity + contributions - withdrawals
daily_return = investment_pnl / adjusted_previous_equity if adjusted_previous_equity > 0 else 0
```

**Key Changes**:
1. Query `equity_changes` table for changes on `calculation_date`
2. Apply contributions/withdrawals to equity balance
3. Adjust return calculation to use flow-adjusted equity base
4. Add equity change amounts to snapshot metadata (for audit trail)

**Modified File Section** (~lines 140-200):

```python
async def _calculate_equity_rollforward(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    previous_snapshot: Optional[PortfolioSnapshot],
    daily_pnl: Decimal
) -> Decimal:
    """
    Calculate new equity balance accounting for:
    1. Previous equity balance
    2. Daily P&L from market movements
    3. Capital contributions (add to equity)
    4. Capital withdrawals (subtract from equity)
    """
    # Get previous equity
    previous_equity = previous_snapshot.equity_balance if previous_snapshot else Decimal('0')

    # Get equity changes for this date
    from app.models.equity_changes import EquityChange, EquityChangeType

    query = select(EquityChange).where(
        and_(
            EquityChange.portfolio_id == portfolio_id,
            EquityChange.change_date == calculation_date,
            EquityChange.deleted_at.is_(None)
        )
    )
    result = await db.execute(query)
    equity_changes = result.scalars().all()

    # Calculate contributions and withdrawals
    contributions = sum(
        ec.amount for ec in equity_changes
        if ec.change_type == EquityChangeType.CONTRIBUTION
    )
    withdrawals = sum(
        ec.amount for ec in equity_changes
        if ec.change_type == EquityChangeType.WITHDRAWAL
    )

    # Calculate new equity (Phase 1: includes contributions/withdrawals)
    # Note: daily_pnl already includes both unrealized and realized P&L from Phase 0
    new_equity = previous_equity + daily_pnl + contributions - withdrawals

    logger.info(
        f"Equity rollforward for {calculation_date}: "
        f"Previous: ${previous_equity:,.2f}, "
        f"Investment P&L: ${daily_pnl:,.2f} (unrealized + realized), "
        f"Contributions: ${contributions:,.2f}, "
        f"Withdrawals: ${withdrawals:,.2f}, "
        f"New: ${new_equity:,.2f}"
    )

    return new_equity, contributions, withdrawals
```

---

## Phase 4: Frontend - Service Layer

### API Service

**File**: `frontend/src/services/equityChangesApi.ts`

```typescript
/**
 * Equity Changes API Service
 * Handles capital contributions and withdrawals
 */

import { apiClient } from './apiClient'

export interface EquityChange {
  id: string
  portfolio_id: string
  change_date: string  // ISO date string
  change_type: 'CONTRIBUTION' | 'WITHDRAWAL'
  amount: number
  description?: string
  created_at: string
  created_by_user_id: string
  updated_at?: string
  can_edit: boolean
  can_delete: boolean
  portfolio_equity_after?: number
}

export interface EquityChangeCreate {
  change_date: string
  change_type: 'CONTRIBUTION' | 'WITHDRAWAL'
  amount: number
  description?: string
}

export interface EquityChangeUpdate {
  amount?: number
  description?: string
}

export interface EquityChangeSummary {
  period: {
    start_date: string
    end_date: string
  }
  total_contributions: number
  total_withdrawals: number
  net_flow: number
  contribution_count: number
  withdrawal_count: number
  largest_contribution?: number
  largest_withdrawal?: number
  starting_equity?: number
  ending_equity?: number
  equity_from_pnl?: number
  equity_from_flows: number
}

export interface EquityChangeListParams {
  start_date?: string
  end_date?: string
  change_type?: 'CONTRIBUTION' | 'WITHDRAWAL'
  limit?: number
  offset?: number
}

const equityChangesApi = {
  /**
   * Record a new equity change (contribution or withdrawal)
   */
  async recordEquityChange(
    portfolioId: string,
    data: EquityChangeCreate
  ): Promise<EquityChange> {
    const response = await apiClient.post(
      `/api/v1/equity-changes/${portfolioId}`,
      data
    )
    return response.data
  },

  /**
   * Get list of equity changes for portfolio
   */
  async getEquityChanges(
    portfolioId: string,
    params?: EquityChangeListParams
  ): Promise<{ total: number; equity_changes: EquityChange[] }> {
    const response = await apiClient.get(
      `/api/v1/equity-changes/${portfolioId}`,
      { params }
    )
    return response.data
  },

  /**
   * Get summary statistics for equity changes
   */
  async getSummary(
    portfolioId: string,
    startDate?: string,
    endDate?: string
  ): Promise<EquityChangeSummary> {
    const response = await apiClient.get(
      `/api/v1/equity-changes/${portfolioId}/summary`,
      { params: { start_date: startDate, end_date: endDate } }
    )
    return response.data
  },

  /**
   * Get single equity change details
   */
  async getEquityChange(changeId: string): Promise<EquityChange> {
    const response = await apiClient.get(
      `/api/v1/equity-changes/change/${changeId}`
    )
    return response.data
  },

  /**
   * Update equity change (within edit window)
   */
  async updateEquityChange(
    changeId: string,
    data: EquityChangeUpdate
  ): Promise<EquityChange> {
    const response = await apiClient.put(
      `/api/v1/equity-changes/change/${changeId}`,
      data
    )
    return response.data
  },

  /**
   * Delete equity change (soft delete, within delete window)
   */
  async deleteEquityChange(changeId: string): Promise<void> {
    await apiClient.delete(`/api/v1/equity-changes/change/${changeId}`)
  }
}

export default equityChangesApi
```

---

## Phase 5: Frontend - UI Components

### Main Component: ManageEquitySidePanel

**File**: `frontend/src/components/portfolio/ManageEquitySidePanel.tsx`

```typescript
'use client'

import React, { useState, useEffect } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import equityChangesApi, { EquityChange, EquityChangeCreate } from '@/services/equityChangesApi'
import { formatCurrency } from '@/lib/formatters'
import { Calendar, TrendingUp, TrendingDown, Info } from 'lucide-react'

interface ManageEquitySidePanelProps {
  portfolioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete?: () => void
  currentEquity?: number
}

export function ManageEquitySidePanel({
  portfolioId,
  open,
  onOpenChange,
  onComplete,
  currentEquity = 0
}: ManageEquitySidePanelProps) {
  const [formData, setFormData] = useState<EquityChangeCreate>({
    change_date: new Date().toISOString().split('T')[0],
    change_type: 'CONTRIBUTION',
    amount: 0,
    description: ''
  })

  const [recentChanges, setRecentChanges] = useState<EquityChange[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Load recent equity changes when panel opens
  useEffect(() => {
    if (open) {
      loadRecentChanges()
    }
  }, [open, portfolioId])

  const loadRecentChanges = async () => {
    try {
      const response = await equityChangesApi.getEquityChanges(portfolioId, {
        limit: 5,
        offset: 0
      })
      setRecentChanges(response.equity_changes)
    } catch (err: any) {
      console.error('Failed to load recent changes:', err)
    }
  }

  const handleSubmit = async () => {
    setError(null)
    setSuccessMessage(null)

    // Validation
    if (formData.amount <= 0) {
      setError('Amount must be greater than zero')
      return
    }

    if (formData.change_type === 'WITHDRAWAL' && formData.amount > currentEquity) {
      setError('Withdrawal amount cannot exceed current portfolio equity')
      return
    }

    setIsSubmitting(true)

    try {
      const result = await equityChangesApi.recordEquityChange(portfolioId, formData)

      setSuccessMessage(
        `${formData.change_type === 'CONTRIBUTION' ? 'Contribution' : 'Withdrawal'} of ${formatCurrency(formData.amount)} recorded successfully`
      )

      // Refresh recent changes list
      await loadRecentChanges()

      // Reset form
      setFormData({
        change_date: new Date().toISOString().split('T')[0],
        change_type: 'CONTRIBUTION',
        amount: 0,
        description: ''
      })

      // Notify parent to refresh data
      setTimeout(() => {
        onComplete?.()
      }, 1500)

    } catch (err: any) {
      setError(err.message || 'Failed to record equity change')
    } finally {
      setIsSubmitting(false)
    }
  }

  const calculateNewEquity = () => {
    if (formData.change_type === 'CONTRIBUTION') {
      return currentEquity + formData.amount
    } else {
      return currentEquity - formData.amount
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[90vw] sm:w-[500px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Manage Portfolio Equity</SheetTitle>
          <SheetDescription>
            Record capital contributions or withdrawals. This helps track performance separate from cash flows.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          {/* Current Equity Display */}
          <div className="rounded-lg p-4 themed-card">
            <p className="text-sm text-muted-foreground mb-1">Current Portfolio Equity</p>
            <p className="text-2xl font-semibold">{formatCurrency(currentEquity)}</p>
          </div>

          {/* Success Message */}
          {successMessage && (
            <Alert className="border-green-500 bg-green-50">
              <AlertDescription className="text-green-800">
                {successMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* Error Message */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Form */}
          <div className="space-y-4 p-4 border rounded-lg themed-card">
            <h4 className="text-sm font-semibold text-primary">Record Equity Change</h4>

            {/* Change Type */}
            <div className="space-y-2">
              <Label>Type *</Label>
              <Select
                value={formData.change_type}
                onValueChange={(value: 'CONTRIBUTION' | 'WITHDRAWAL') =>
                  setFormData({ ...formData, change_type: value })
                }
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CONTRIBUTION">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-green-600" />
                      <span>Contribution (Add Capital)</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="WITHDRAWAL">
                    <div className="flex items-center gap-2">
                      <TrendingDown className="h-4 w-4 text-red-600" />
                      <span>Withdrawal (Remove Capital)</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date */}
            <div className="space-y-2">
              <Label htmlFor="change_date">Date *</Label>
              <div className="relative">
                <Input
                  id="change_date"
                  type="date"
                  value={formData.change_date}
                  onChange={(e) => setFormData({ ...formData, change_date: e.target.value })}
                  max={new Date().toISOString().split('T')[0]}
                  disabled={isSubmitting}
                />
                <Calendar className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
              </div>
              {formData.change_date < new Date().toISOString().split('T')[0] && (
                <div className="flex items-start gap-2 text-xs text-amber-600">
                  <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                  <span>Backdating will affect historical P&L calculations. Changes will be reflected in next batch run.</span>
                </div>
              )}
            </div>

            {/* Amount */}
            <div className="space-y-2">
              <Label htmlFor="amount">Amount ($) *</Label>
              <Input
                id="amount"
                type="number"
                value={formData.amount || ''}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                placeholder="0.00"
                step="0.01"
                min="0"
                disabled={isSubmitting}
              />
              {formData.amount > 0 && (
                <p className="text-xs text-muted-foreground">
                  New portfolio equity: <span className="font-semibold">{formatCurrency(calculateNewEquity())}</span>
                </p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Add notes about this equity change..."
                maxLength={500}
                disabled={isSubmitting}
              />
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || formData.amount <= 0}
              className="w-full"
            >
              {isSubmitting ? 'Recording...' : 'Record Equity Change'}
            </Button>
          </div>

          {/* Recent Changes */}
          {recentChanges.length > 0 && (
            <>
              <Separator />
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-primary">Recent Equity Changes</h4>
                {recentChanges.map((change) => (
                  <div
                    key={change.id}
                    className="p-3 rounded-lg border themed-card flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      {change.change_type === 'CONTRIBUTION' ? (
                        <TrendingUp className="h-4 w-4 text-green-600" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-red-600" />
                      )}
                      <div>
                        <p className="text-sm font-medium">
                          {formatCurrency(change.amount)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(change.change_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">
                        {change.change_type === 'CONTRIBUTION' ? 'Added' : 'Removed'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
              className="flex-1"
            >
              Close
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

### Integration into Command Center

**File**: `frontend/src/containers/CommandCenterContainer.tsx`

Add state and button:

```typescript
// Add state (around line 15)
const [equitySidePanelOpen, setEquitySidePanelOpen] = useState(false)

// Add button next to "Manage Positions" (around line 83)
<div className="flex items-center gap-2">
  <Button
    onClick={() => setSidePanelOpen(true)}
    size="sm"
    className="flex items-center gap-2"
  >
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
    Manage Positions
  </Button>

  <Button
    onClick={() => setEquitySidePanelOpen(true)}
    size="sm"
    variant="outline"
    className="flex items-center gap-2"
  >
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    Manage Equity
  </Button>
</div>

// Add side panel component (after ManagePositionsSidePanel, around line 125)
{portfolioId && (
  <ManageEquitySidePanel
    portfolioId={portfolioId}
    open={equitySidePanelOpen}
    onOpenChange={setEquitySidePanelOpen}
    onComplete={handleRefresh}
    currentEquity={heroMetrics?.total_value}
  />
)}
```

---

## Phase 6: Frontend - Hero Metrics Integration

### Add Capital Flow Metrics

**Option A**: Add new metrics to existing HeroMetricsRow

Potential new hero metric cards:
1. **Net Capital Flow (YTD)**: Total contributions - withdrawals
2. **P&L vs. Capital**: Breakdown of equity change sources
3. **True TWR (YTD)**: Time-weighted return excluding capital flows

**Option B**: Create expandable section below Hero Metrics

Add collapsible "Capital Flow Summary" section that shows:
- YTD contributions
- YTD withdrawals
- Net flow
- Timeline visualization of equity changes

**Recommendation**: Start with Option A (1 new card), add Option B in future phase.

---

## Implementation Checklist

### ⚠️ Prerequisites
**Before starting Phase 1 implementation, ensure Phase 0 is complete:**
- [ ] **Phase 0: Realized P&L Tracking** fully implemented and tested
- [ ] All position closes calculate and store `realized_pnl`
- [ ] Portfolio snapshots include `daily_realized_pnl` and `cumulative_realized_pnl` fields
- [ ] P&L calculator correctly aggregates realized P&L from closed positions
- [ ] Equity rollforward includes both unrealized and realized P&L components
- [ ] All Phase 0 tests passing

See **[23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)** for Phase 0 implementation details.

---

### Phase 1: Database Schema ✅
- [ ] Create `backend/app/models/equity_changes.py`
- [ ] Create Alembic migration
- [ ] Update `Portfolio` model to add relationship
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify table created in PostgreSQL

### Phase 2: Backend API ✅
- [ ] Create `backend/app/schemas/equity_changes.py`
- [ ] Create `backend/app/api/v1/equity_changes.py`
- [ ] Register router in `backend/app/api/v1/router.py`
- [ ] Test all 6 endpoints with Postman/curl
- [ ] Update API_REFERENCE.md with new endpoints

### Phase 3: P&L Calculator ✅
- [ ] Update `backend/app/batch/pnl_calculator.py`
- [ ] Add equity change query logic
- [ ] Update equity rollforward formula
- [ ] Adjust return calculation logic
- [ ] Test with manual batch run

### Phase 4: Frontend Service ✅
- [ ] Create `frontend/src/services/equityChangesApi.ts`
- [ ] Export from `frontend/src/services/index.ts`
- [ ] Test service methods in browser console

### Phase 5: Frontend UI ✅
- [ ] Create `frontend/src/components/portfolio/ManageEquitySidePanel.tsx`
- [ ] Update `frontend/src/containers/CommandCenterContainer.tsx`
- [ ] Add "Manage Equity" button
- [ ] Test UI flow (open, submit, close, refresh)

### Phase 6: Hero Metrics ✅
- [ ] Add capital flow metric card to HeroMetricsRow
- [ ] Update `useCommandCenterData` hook to fetch equity summary
- [ ] Test metric display and updates

### Phase 7: Testing ✅
- [ ] Unit tests for backend endpoints
- [ ] Integration test: record equity change → batch run → verify snapshot
- [ ] Frontend component tests
- [ ] End-to-end test: full user flow

### Phase 8: Documentation ✅
- [ ] Update backend CLAUDE.md
- [ ] Update frontend CLAUDE.md
- [ ] Update API_REFERENCE.md
- [ ] Create user-facing help documentation

---

## Testing Strategy

### Backend Testing

**Unit Tests**: `backend/tests/api/v1/test_equity_changes.py`
```python
async def test_create_equity_change():
    # Test valid contribution
    # Test valid withdrawal
    # Test validation errors (negative amount, future date, etc.)
    # Test withdrawal > equity balance

async def test_list_equity_changes():
    # Test pagination
    # Test date filtering
    # Test type filtering

async def test_get_summary():
    # Test with multiple contributions and withdrawals
    # Test date range filtering
    # Verify calculations
```

**Integration Tests**: `backend/tests/batch/test_pnl_with_equity_changes.py`
```python
async def test_pnl_calculation_with_contribution():
    # Create portfolio snapshot (day 1)
    # Record contribution (day 2)
    # Run batch calculator for day 2
    # Verify new equity = old equity + pnl + contribution

async def test_pnl_calculation_with_withdrawal():
    # Similar test for withdrawal

async def test_backdated_equity_change():
    # Record equity change for past date
    # Verify snapshots marked for recalculation
```

### Frontend Testing

**Component Tests**: `frontend/src/components/portfolio/__tests__/ManageEquitySidePanel.test.tsx`
```typescript
describe('ManageEquitySidePanel', () => {
  test('renders form correctly')
  test('validates amount > 0')
  test('prevents withdrawal > current equity')
  test('prevents future dates')
  test('displays success message on submit')
  test('loads recent changes on open')
})
```

**Integration Tests**:
```typescript
describe('Equity Changes Integration', () => {
  test('record contribution and verify hero metrics update')
  test('record withdrawal and verify portfolio value decrease')
  test('backdated change shows warning message')
})
```

### End-to-End Testing

**Manual Test Scenarios**:
1. Login → Navigate to Command Center → Click "Manage Equity"
2. Record $50,000 contribution for today
3. Verify success message
4. Close panel and verify portfolio equity increased by $50,000
5. Reopen panel and verify contribution appears in recent changes
6. Run batch calculation manually
7. Verify snapshot equity_balance includes contribution

---

## Open Questions & Decisions Needed

### 1. Historical Data Strategy
**Question**: Should we allow users to backfill historical equity changes?

**Options**:
- **A**: Allow unrestricted backdating (any past date)
- **B**: Limit backdating to X days (e.g., 90 days)
- **C**: No backdating - only current/future dates

**Recommendation**: Option B (90-day limit)
- Balances flexibility with data integrity
- Prevents abuse of historical performance manipulation
- Still allows correction of recent missed entries

### 2. Snapshot Recalculation
**Question**: How should we handle backdated equity changes?

**Options**:
- **A**: Immediate recalculation (blocks API response)
- **B**: Mark snapshots as "stale", recalculate in next batch run
- **C**: Manual recalculation trigger (admin action)

**Recommendation**: Option B (async batch recalculation)
- Better user experience (no blocking)
- Consistent with existing batch architecture
- Adequate for typical use case

### 3. Access Control
**Question**: Should large equity changes require additional approval?

**Options**:
- **A**: No approval - all users can record any amount
- **B**: Require 2FA for changes > $X threshold
- **C**: Admin approval workflow for changes > $X

**Recommendation**: Option A for MVP
- Keep it simple initially
- Add approval workflow in future if abuse detected
- Audit trail (created_by_user_id) provides accountability

### 4. Hero Metrics Display
**Question**: How prominently should capital flow metrics be displayed?

**Options**:
- **A**: Add 1-2 cards to existing HeroMetricsRow (6 → 7-8 cards)
- **B**: Create separate "Capital Flows" section below hero metrics
- **C**: Add to sidebar/accordion (less prominent)

**Recommendation**: Option A (add 1 card: "Net Capital Flow YTD")
- Most visible to users
- Aligns with importance of metric
- Can expand to Option B in future phase

### 5. Batch Integration
**Question**: Should equity changes trigger automatic batch recalculation?

**Options**:
- **A**: Trigger full batch run immediately after equity change
- **B**: Trigger partial recalculation (only affected snapshots)
- **C**: No automatic trigger - wait for scheduled batch run

**Recommendation**: Option C (scheduled batch) for MVP
- Avoids performance issues with multiple equity changes
- Consistent with current batch architecture
- Can optimize later with Option B if needed

---

## Success Criteria

### Functional Requirements ✅
- [ ] Users can record capital contributions
- [ ] Users can record capital withdrawals
- [ ] System prevents invalid equity changes (future dates, negative amounts, overdrafts)
- [ ] Equity changes appear in recent activity list
- [ ] Portfolio equity balance updates correctly
- [ ] P&L calculator accounts for equity changes in rollforward
- [ ] Snapshots reflect equity changes
- [ ] Hero metrics display capital flow information

### Non-Functional Requirements ✅
- [ ] API response time < 500ms for equity change recording
- [ ] UI loads recent changes in < 1 second
- [ ] Batch recalculation completes in existing time window
- [ ] No degradation to existing Command Center performance

### User Experience ✅
- [ ] Intuitive UI (similar to existing ManagePositionsSidePanel)
- [ ] Clear validation messages
- [ ] Success confirmation after recording change
- [ ] Warning when backdating changes
- [ ] Recent changes visible without leaving page

### Data Integrity ✅
- [ ] Equity changes persist correctly in database
- [ ] Soft deletes work as expected
- [ ] Audit trail (created_by, created_at) populated
- [ ] No orphaned records after portfolio deletion (ON DELETE CASCADE)

---

## Risk Assessment

### Technical Risks

**1. Snapshot Recalculation Complexity** (Medium)
- **Risk**: Backdated equity changes require recalculating all subsequent snapshots
- **Mitigation**: Implement incremental recalculation, limit backdating window

**2. Performance Impact** (Low)
- **Risk**: Additional database queries slow down batch processing
- **Mitigation**: Efficient indexing, batch fetching of equity changes

**3. Data Migration** (Low)
- **Risk**: Existing portfolios need equity_balance initialization
- **Mitigation**: Migration script sets initial equity from latest snapshot

### Business Risks

**1. User Confusion** (Medium)
- **Risk**: Users don't understand difference between contributions and P&L
- **Mitigation**: Clear UI labels, help text, examples

**2. Performance Manipulation** (Low)
- **Risk**: Users backdate equity changes to manipulate historical returns
- **Mitigation**: Audit trail, limit backdate window, admin review capabilities

**3. Adoption** (Low)
- **Risk**: Users don't use feature because it's not prominent enough
- **Mitigation**: Add to Command Center (high-traffic page), show in hero metrics

---

## Future Enhancements (Out of Scope for MVP)

### Phase 2 Enhancements
1. **Bulk Import**: Upload CSV of historical equity changes
2. **Recurring Contributions**: Set up automatic monthly contributions
3. **Capital Flow Timeline**: Visual timeline chart of contributions/withdrawals
4. **Email Notifications**: Notify user after recording large equity change
5. **Excel Export**: Export equity change history

### Phase 3 Enhancements
1. **True Time-Weighted Return (TWR)**: Accurate performance measurement
2. **Money-Weighted Return (MWR/IRR)**: Alternative return calculation
3. **Benchmark Comparison**: Compare returns to S&P 500 (adjusting for flows)
4. **Performance Attribution**: Break down returns (market, stock selection, timing, flows)

### Advanced Features
1. **Multi-Currency**: Handle contributions/withdrawals in different currencies
2. **Linked Accounts**: Track transfers between portfolios
3. **Tax Implications**: Flag withdrawals for tax consideration
4. **Scheduled Transfers**: Set up future contributions/withdrawals

---

## Implementation Timeline

### Prerequisites: Phase 0 Complete
**Before starting Phase 1**, ensure Phase 0 (Realized P&L Tracking) is complete:
- Phase 0 implementation: 2-3 days
- Testing and validation: Complete
- **Checkpoint**: Review realized P&L calculations before proceeding

### Week 1: Backend Foundation (Phase 1)
- **Day 1-2**: Database schema, migration, model
- **Day 3-4**: API endpoints implementation
- **Day 5**: P&L calculator enhancement (add equity changes)

### Week 2: Frontend Development
- **Day 1-2**: Service layer and types
- **Day 3-4**: ManageEquitySidePanel component
- **Day 5**: Command Center integration

### Week 3: Testing & Polish
- **Day 1-2**: Backend and frontend tests
- **Day 3**: End-to-end testing
- **Day 4**: Bug fixes and polish
- **Day 5**: Documentation and deployment prep

### Week 4: Deployment & Monitoring
- **Day 1**: Deploy to Railway
- **Day 2-3**: Monitor for issues, user feedback
- **Day 4-5**: Refinements based on feedback

**Total Estimated Effort**:
- **Phase 0**: 2-3 days (prerequisite)
- **Phase 1**: 15-20 days (3-4 weeks)
- **Combined**: 17-23 days (4-5 weeks total)

---

## Conclusion

This feature adds critical functionality for accurately measuring portfolio performance independent of capital flows. By separating P&L-driven equity changes from external contributions/withdrawals, users can see their true investment returns.

**Implementation Dependency**:
This feature **requires Phase 0: Realized P&L Tracking** to be complete before implementation. The equity rollforward formula depends on having accurate realized P&L calculations from closed positions. See **[23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)** for Phase 0 details.

The implementation follows established architectural patterns in SigmaSight:
- Backend: SQLAlchemy ORM, Alembic migrations, FastAPI REST endpoints
- Frontend: Service layer, side panel UI pattern, React hooks
- Batch: Integration with existing P&L calculator (enhanced with realized P&L from Phase 0)

The MVP scope is intentionally focused on core functionality, with clear paths for future enhancements based on user feedback and usage patterns.

**Related Documents**:
- **[22-EQUITY-AND-PNL-TRACKING-SUMMARY.md](./22-EQUITY-AND-PNL-TRACKING-SUMMARY.md)** - Master summary and overview
- **[23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)** - Phase 0 detailed implementation plan

---

## Appendix A: Example User Flows

### Flow 1: Record Capital Contribution
1. User navigates to Command Center
2. Clicks "Manage Equity" button
3. Side panel opens with form
4. User selects "Contribution" type
5. Enters $50,000 amount
6. Adds description: "Q4 2025 bonus investment"
7. Clicks "Record Equity Change"
8. Success message appears
9. Recent changes list updates
10. Panel closes automatically after 1.5s
11. Hero metrics refresh to show new portfolio value

### Flow 2: Record Capital Withdrawal
1. User navigates to Command Center
2. Clicks "Manage Equity" button
3. Side panel opens
4. User selects "Withdrawal" type
5. Enters $25,000 amount
6. Adds description: "Down payment for house"
7. System validates withdrawal amount ≤ current equity
8. Clicks "Record Equity Change"
9. Success message appears
10. Portfolio equity decreases by $25,000

### Flow 3: View Capital Flow History
1. User opens "Manage Equity" panel
2. Scrolls down to "Recent Equity Changes" section
3. Sees last 5 equity changes with dates and amounts
4. Each entry shows contribution (↑) or withdrawal (↓) icon
5. Can view full history by implementing "View All" button (future enhancement)

---

## Appendix B: Database Queries

### Common Queries for Equity Changes

**Get equity changes for portfolio on specific date:**
```sql
SELECT *
FROM equity_changes
WHERE portfolio_id = $1
  AND change_date = $2
  AND deleted_at IS NULL
ORDER BY created_at ASC;
```

**Calculate net flow for date range:**
```sql
SELECT
  SUM(CASE WHEN change_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
  SUM(CASE WHEN change_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
  SUM(CASE WHEN change_type = 'CONTRIBUTION' THEN amount ELSE -amount END) as net_flow
FROM equity_changes
WHERE portfolio_id = $1
  AND change_date BETWEEN $2 AND $3
  AND deleted_at IS NULL;
```

**Get recent equity changes with user info:**
```sql
SELECT
  ec.*,
  u.full_name as created_by_name
FROM equity_changes ec
JOIN users u ON ec.created_by_user_id = u.id
WHERE ec.portfolio_id = $1
  AND ec.deleted_at IS NULL
ORDER BY ec.change_date DESC, ec.created_at DESC
LIMIT 10;
```

---

## Appendix C: Error Handling

### Backend Error Codes

| Error Code | HTTP Status | Description | User Message |
|------------|-------------|-------------|--------------|
| `EQUITY_001` | 400 | Amount must be positive | "Amount must be greater than zero" |
| `EQUITY_002` | 400 | Future date not allowed | "Cannot record equity changes for future dates" |
| `EQUITY_003` | 400 | Withdrawal exceeds balance | "Withdrawal amount cannot exceed current portfolio equity" |
| `EQUITY_004` | 404 | Portfolio not found | "Portfolio not found" |
| `EQUITY_005` | 403 | User doesn't own portfolio | "You do not have access to this portfolio" |
| `EQUITY_006` | 400 | Edit window expired | "Equity changes can only be edited within 7 days of creation" |
| `EQUITY_007` | 400 | Delete window expired | "Equity changes can only be deleted within 30 days of creation" |
| `EQUITY_008` | 404 | Equity change not found | "Equity change not found" |
| `EQUITY_009` | 409 | Already deleted | "This equity change has already been deleted" |

---

**Document End**

*This planning document should be reviewed and approved before beginning implementation. Any deviations from the plan should be documented with rationale.*
