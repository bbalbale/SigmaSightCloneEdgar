# Equity Balance Tracking - Implementation Plan

**Document Version**: 1.0
**Date**: 2025-10-16
**Status**: Planning
**Owner**: Backend Team

---

## Executive Summary

### Problem Statement
Portfolio `equity_balance` values are frozen at their initial seed values and never update with daily P&L, causing:
- **Incorrect risk metrics**: Leverage calculations use stale equity values
- **Misleading frontend displays**: Users see initial capital, not current NAV
- **Broken analytics**: Position weights and exposure ratios are inaccurate

### Root Cause
The batch processing system only adds `realized_pnl` to equity_balance, but `realized_pnl` is **never calculated or populated** in the Position table, so equity_balance never changes from its seed value.

### Business Impact
- **High Priority**: Users cannot track portfolio performance
- **Risk Management**: Leverage ratios are incorrect
- **User Experience**: Stale data erodes trust in the platform

---

## Current State Analysis

### Database Schema

#### Portfolio Table (`portfolios`)
**ONE row per portfolio** - stores current live data

```python
# app/models/users.py:42
equity_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
```

**Current Behavior**:
- Set once during seeding (e.g., $1,000,000)
- Intended to update daily but doesn't
- Used by frontend for all equity calculations

#### PortfolioSnapshot Table (`portfolio_snapshots`)
**ONE row per day per portfolio** - stores daily historical snapshots

```python
# app/models/snapshots.py:48-49, 32-35
equity_balance: Mapped[Optional[Decimal]]      # Copy of portfolio.equity_balance
total_value: Mapped[Decimal]                   # Sum of position market values ✅
daily_pnl: Mapped[Optional[Decimal]]           # Today - Yesterday ✅
cumulative_pnl: Mapped[Optional[Decimal]]      # Running total ✅
```

**What Works**:
- `total_value`: Correctly sums all position market values
- `daily_pnl`: Correctly calculates day-over-day change
- `cumulative_pnl`: Correctly accumulates all P&L

**What's Broken**:
- `equity_balance`: Just copies the frozen portfolio.equity_balance value

#### Position Table (`positions`)
```python
# app/models/positions.py:58-61
last_price: Mapped[Optional[Decimal]]      # ✅ Updated daily
market_value: Mapped[Optional[Decimal]]    # ✅ Updated daily
unrealized_pnl: Mapped[Optional[Decimal]]  # ✅ Updated daily
realized_pnl: Mapped[Optional[Decimal]]    # ❌ NEVER calculated!
```

### Current Calculation Flow

#### Batch Processing Order (`batch_orchestrator_v2.py:222-234`)
```python
job_sequence = [
    ("market_data_update", ...),          # Updates market prices
    ("position_values_update", ...),      # Updates position.market_value, unrealized_pnl ✅
    ("portfolio_aggregation", ...),       # ❌ TRIES to update equity_balance (BROKEN)
    ("factor_analysis", ...),
    ("market_risk_scenarios", ...),
    ("portfolio_snapshot", ...),          # Copies equity_balance to snapshot
    ("stress_testing", ...),
    ("position_correlations", ...),
]
```

#### Incorrect Equity Calculation (`batch_orchestrator_v2.py:512-543`)
```python
# Get current equity from database
starting_equity_balance = portfolio.equity_balance  # e.g., $1,000,000

# Sum realized P&L from positions
total_realized_pnl = sum(p.realized_pnl for p in positions if p.realized_pnl)
# ⚠️ This is ALWAYS $0 because realized_pnl is never populated!

# Calculate new equity
new_equity_balance = starting_equity_balance + total_realized_pnl
# = $1,000,000 + $0 = $1,000,000 (NO CHANGE!)

# Update portfolio (only if changed, which never happens)
if new_equity_balance != starting_equity_balance:
    portfolio.equity_balance = new_equity_balance
```

**Result**: `portfolio.equity_balance` remains at seed value forever.

### Why This is Wrong

#### Example Timeline:
```
Day 0 (Seed):
  portfolios.equity_balance = $1,000,000

Day 1 (Market moves up):
  Positions unrealized_pnl = +$50,000
  portfolios.equity_balance = $1,000,000 (UNCHANGED!)
  Snapshot: equity_balance = $1,000,000 ❌

Day 2 (Market moves down):
  Positions unrealized_pnl = +$30,000 (net)
  portfolios.equity_balance = $1,000,000 (STILL UNCHANGED!)
  Snapshot: equity_balance = $1,000,000 ❌
```

**What Should Happen**:
```
Day 0 (Seed):
  portfolios.equity_balance = $1,000,000

Day 1 (Market moves up):
  Daily P&L = +$50,000
  portfolios.equity_balance = $1,050,000 ✅
  Snapshot: equity_balance = $1,050,000, daily_pnl = $50,000

Day 2 (Market moves down):
  Daily P&L = -$20,000
  portfolios.equity_balance = $1,030,000 ✅
  Snapshot: equity_balance = $1,030,000, daily_pnl = -$20,000
```

---

## Proposed Solution

### Phase 1: Fix P&L Tracking (Immediate - No Schema Changes)

**Goal**: Make equity_balance update daily with P&L without adding new database fields.

#### Approach
Update equity calculation logic to use **yesterday's equity + today's P&L** instead of trying to sum realized_pnl.

#### Implementation Location
**Option A (Recommended)**: Move calculation into `snapshots.py`
- Already has access to previous snapshot
- Already calculates daily_pnl correctly
- Can update both snapshot and portfolio table

**Option B**: Fix calculation in `batch_orchestrator_v2.py`
- Needs to fetch previous snapshot
- More complex, requires additional queries

#### Detailed Steps (Option A)

**1. Modify `app/calculations/snapshots.py:291-354`**

Current `_create_or_update_snapshot()` function needs these changes:

```python
async def _create_or_update_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    aggregations: Dict[str, Decimal],
    greeks: Dict[str, Decimal],
    pnl_data: Dict[str, Decimal],
    position_counts: Dict[str, int]
) -> PortfolioSnapshot:
    """Create or update portfolio snapshot AND update portfolio equity_balance"""

    from app.models.users import Portfolio

    # Get portfolio
    portfolio_query = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_query)
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # NEW LOGIC: Calculate today's equity from yesterday's equity + P&L
    # Get previous snapshot to find yesterday's equity
    previous_snapshot_query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < calculation_date
        )
    ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

    previous_result = await db.execute(previous_snapshot_query)
    previous_snapshot = previous_result.scalar_one_or_none()

    if previous_snapshot and previous_snapshot.equity_balance:
        # Use yesterday's equity + today's P&L
        previous_equity = previous_snapshot.equity_balance
        today_equity = previous_equity + pnl_data['daily_pnl']
    else:
        # First snapshot - use seed value from portfolio table
        today_equity = portfolio.equity_balance or Decimal('0')

    # Update portfolio table with current equity
    portfolio.equity_balance = today_equity
    await db.flush()

    # ... rest of snapshot creation logic using today_equity
    snapshot_data = {
        "portfolio_id": portfolio_id,
        "snapshot_date": calculation_date,
        "total_value": aggregations['gross_exposure'],
        # ... other fields ...
        "equity_balance": today_equity,  # Store calculated equity
        "daily_pnl": pnl_data['daily_pnl'],
        "cumulative_pnl": pnl_data['cumulative_pnl'],
    }

    # Create or update snapshot
    # ... existing logic ...
```

**2. Remove incorrect calculation from `batch_orchestrator_v2.py:512-543`**

Delete or comment out the entire section that tries to update equity_balance using realized_pnl:

```python
# DELETE THESE LINES (512-543):
# Update portfolio equity_balance = starting equity balance (from DB) + total realized P&L
# from decimal import Decimal
# ... (entire block) ...
```

**3. Update logging in `batch_orchestrator_v2.py`**

Remove the log statement at lines 538-542 since equity update happens in snapshot now.

#### Testing Phase 1

**Validation Query**:
```sql
-- Check that equity_balance changes over time
SELECT
    p.name,
    ps.snapshot_date,
    ps.equity_balance,
    ps.daily_pnl,
    ps.cumulative_pnl
FROM portfolio_snapshots ps
JOIN portfolios p ON p.id = ps.portfolio_id
WHERE p.id = 'portfolio-uuid-here'
ORDER BY ps.snapshot_date
LIMIT 10;

-- Should see equity_balance changing daily with P&L
```

**Expected Results**:
- Day 0: equity_balance = $1,000,000, daily_pnl = $0
- Day 1: equity_balance = $1,050,000, daily_pnl = $50,000
- Day 2: equity_balance = $1,030,000, daily_pnl = -$20,000

---

### Phase 2: Add Cash Flow Tracking (Future - Schema Changes Required)

**Goal**: Track equity deposits and withdrawals separately from P&L.

#### Why This Matters

**Current Problem**: Can't distinguish between P&L and cash flows.

Example:
```
Day 5: Equity = $1,100,000
```

Is this:
- A) $1,000,000 starting + $100,000 P&L ✅
- B) $1,000,000 starting + $100,000 deposit + $0 P&L ❌

Without tracking deposits/withdrawals, we can't calculate true investment returns.

#### Database Schema Changes

**Add to `portfolio_snapshots` table**:

```python
# app/models/snapshots.py (add after line 35)
equity_inflow: Mapped[Optional[Decimal]] = mapped_column(
    Numeric(16, 2),
    nullable=True,
    default=Decimal('0'),
    comment="Capital added to portfolio this day (deposits)"
)

equity_outflow: Mapped[Optional[Decimal]] = mapped_column(
    Numeric(16, 2),
    nullable=True,
    default=Decimal('0'),
    comment="Capital withdrawn from portfolio this day (distributions)"
)
```

#### Alembic Migration

**File**: `backend/alembic/versions/add_equity_cash_flows.py`

```python
"""Add equity cash flow tracking to portfolio_snapshots

Revision ID: [auto-generated]
Revises: [previous-revision]
Create Date: 2025-10-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '[auto-generated]'
down_revision = '[previous-revision]'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns with default 0 for existing records
    op.add_column('portfolio_snapshots',
        sa.Column('equity_inflow', sa.Numeric(16, 2),
                  nullable=True,
                  server_default='0',
                  comment='Capital added to portfolio this day (deposits)')
    )
    op.add_column('portfolio_snapshots',
        sa.Column('equity_outflow', sa.Numeric(16, 2),
                  nullable=True,
                  server_default='0',
                  comment='Capital withdrawn from portfolio this day (distributions)')
    )

    # Set existing records to 0 (backfill)
    op.execute("""
        UPDATE portfolio_snapshots
        SET equity_inflow = 0, equity_outflow = 0
        WHERE equity_inflow IS NULL OR equity_outflow IS NULL
    """)

def downgrade():
    op.drop_column('portfolio_snapshots', 'equity_outflow')
    op.drop_column('portfolio_snapshots', 'equity_inflow')
```

**Run Migration**:
```bash
cd backend
uv run alembic revision --autogenerate -m "add_equity_cash_flows"
uv run alembic upgrade head
```

#### Updated Equity Calculation Formula

```python
# In snapshots.py:
today_equity = (
    previous_equity
    + daily_pnl
    + equity_inflow      # New: deposits
    - equity_outflow     # New: withdrawals
)
```

---

## Backend Changes

### 1. Calculation Engine

#### File: `app/calculations/snapshots.py`

**Lines to Modify**: 291-354 (`_create_or_update_snapshot` function)

**Changes**:
- Add equity calculation logic from previous_equity + daily_pnl
- Update portfolio.equity_balance before creating snapshot
- (Phase 2) Add equity_inflow/outflow to calculation

**New Parameters** (Phase 2):
```python
async def _create_or_update_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    aggregations: Dict[str, Decimal],
    greeks: Dict[str, Decimal],
    pnl_data: Dict[str, Decimal],
    position_counts: Dict[str, int],
    equity_inflow: Decimal = Decimal('0'),   # NEW
    equity_outflow: Decimal = Decimal('0')   # NEW
) -> PortfolioSnapshot:
```

#### File: `app/batch/batch_orchestrator_v2.py`

**Lines to Remove**: 512-543 (incorrect equity calculation)

**Lines to Keep**: Everything else - batch orchestrator doesn't need to calculate equity anymore

### 2. API Changes

#### New Endpoints (Phase 2)

**POST /api/v1/analytics/portfolio/{portfolio_id}/equity-transaction**

Record a deposit or withdrawal:

```python
# app/api/v1/analytics/portfolio.py

from pydantic import BaseModel
from decimal import Decimal
from datetime import date

class EquityTransactionRequest(BaseModel):
    transaction_date: date
    transaction_type: Literal["deposit", "withdrawal"]
    amount: Decimal
    notes: Optional[str] = None

@router.post("/{portfolio_id}/equity-transaction")
async def record_equity_transaction(
    portfolio_id: UUID,
    request: EquityTransactionRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Record a capital deposit or withdrawal.
    This will be reflected in the next daily snapshot.
    """
    # Validation: portfolio belongs to user
    portfolio = await verify_portfolio_ownership(db, portfolio_id, current_user.id)

    # Get or create snapshot for transaction_date
    snapshot = await get_or_create_snapshot(db, portfolio_id, request.transaction_date)

    # Update cash flow fields
    if request.transaction_type == "deposit":
        snapshot.equity_inflow = (snapshot.equity_inflow or Decimal('0')) + request.amount
    else:
        snapshot.equity_outflow = (snapshot.equity_outflow or Decimal('0')) + request.amount

    # Recalculate equity_balance for this snapshot and all future snapshots
    await recalculate_equity_from_date(db, portfolio_id, request.transaction_date)

    await db.commit()

    return {
        "success": True,
        "message": f"{request.transaction_type.title()} of ${request.amount:,.2f} recorded",
        "new_equity_balance": float(portfolio.equity_balance)
    }
```

**GET /api/v1/analytics/portfolio/{portfolio_id}/equity-history**

Retrieve equity balance history with cash flows:

```python
@router.get("/{portfolio_id}/equity-history")
async def get_equity_history(
    portfolio_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical equity balance with breakdown of P&L vs cash flows.
    """
    portfolio = await verify_portfolio_ownership(db, portfolio_id, current_user.id)

    query = select(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == portfolio_id
    )

    if start_date:
        query = query.where(PortfolioSnapshot.snapshot_date >= start_date)
    if end_date:
        query = query.where(PortfolioSnapshot.snapshot_date <= end_date)

    query = query.order_by(PortfolioSnapshot.snapshot_date)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    history = []
    for snapshot in snapshots:
        history.append({
            "date": snapshot.snapshot_date.isoformat(),
            "equity_balance": float(snapshot.equity_balance),
            "daily_pnl": float(snapshot.daily_pnl) if snapshot.daily_pnl else 0,
            "cumulative_pnl": float(snapshot.cumulative_pnl) if snapshot.cumulative_pnl else 0,
            "equity_inflow": float(snapshot.equity_inflow) if snapshot.equity_inflow else 0,
            "equity_outflow": float(snapshot.equity_outflow) if snapshot.equity_outflow else 0,
            "total_value": float(snapshot.total_value)
        })

    return {
        "portfolio_id": str(portfolio_id),
        "portfolio_name": portfolio.name,
        "current_equity": float(portfolio.equity_balance),
        "history": history
    }
```

#### Updated Endpoints

**GET /api/v1/data/portfolio/{portfolio_id}/complete**

Already returns `equity_balance` - no changes needed, but value will now be dynamic.

```python
# app/api/v1/data.py:68
equity_balance = float(portfolio.equity_balance) if portfolio.equity_balance else 0.0
```

This will now return the **current equity** instead of frozen seed value.

### 3. Services

#### File: `app/services/portfolio_analytics_service.py`

**Lines affected**: 52 (equity_balance usage)

**No changes needed** - service already reads `portfolio.equity_balance`, which will now be dynamic.

#### File: `app/services/target_price_service.py`

**Lines affected**: 608-610, 649-652 (equity_balance for position weighting)

**No changes needed** - already using `portfolio.equity_balance` for weight calculations.

**Impact**: Position weights will now be calculated correctly as positions values and equity change.

### 4. Helper Functions (Phase 2)

#### File: `app/calculations/snapshots.py` (new functions)

```python
async def recalculate_equity_from_date(
    db: AsyncSession,
    portfolio_id: UUID,
    from_date: date
) -> None:
    """
    Recalculate equity_balance for all snapshots from a given date forward.
    Used when a historical cash flow transaction is added.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        from_date: Date to start recalculation (inclusive)
    """
    # Get all snapshots from from_date onwards
    query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= from_date
        )
    ).order_by(PortfolioSnapshot.snapshot_date)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        return

    # Get the previous snapshot before from_date
    prev_query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < from_date
        )
    ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

    prev_result = await db.execute(prev_query)
    previous_snapshot = prev_result.scalar_one_or_none()

    # Starting equity is either previous snapshot or portfolio seed value
    if previous_snapshot:
        previous_equity = previous_snapshot.equity_balance
    else:
        portfolio = await db.get(Portfolio, portfolio_id)
        previous_equity = portfolio.equity_balance or Decimal('0')

    # Recalculate each snapshot
    for snapshot in snapshots:
        new_equity = (
            previous_equity
            + snapshot.daily_pnl
            + (snapshot.equity_inflow or Decimal('0'))
            - (snapshot.equity_outflow or Decimal('0'))
        )

        snapshot.equity_balance = new_equity
        previous_equity = new_equity

    # Update portfolio table with latest equity
    portfolio = await db.get(Portfolio, portfolio_id)
    portfolio.equity_balance = previous_equity

    await db.flush()


async def get_or_create_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    snapshot_date: date
) -> PortfolioSnapshot:
    """
    Get existing snapshot for a date or create a placeholder.
    Used when recording historical cash flow transactions.
    """
    query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
    )

    result = await db.execute(query)
    snapshot = result.scalar_one_or_none()

    if snapshot:
        return snapshot

    # Create placeholder snapshot
    # Will be filled in by next batch run
    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        total_value=Decimal('0'),
        cash_value=Decimal('0'),
        long_value=Decimal('0'),
        short_value=Decimal('0'),
        gross_exposure=Decimal('0'),
        net_exposure=Decimal('0'),
        num_positions=0,
        num_long_positions=0,
        num_short_positions=0,
        equity_inflow=Decimal('0'),
        equity_outflow=Decimal('0')
    )

    db.add(snapshot)
    await db.flush()

    return snapshot
```

---

## Frontend Changes

### 1. Data Display Updates

#### Component: Portfolio Summary / Dashboard

**Files to Update**:
- `frontend/src/containers/DashboardContainer.tsx`
- `frontend/app/dashboard/page.tsx`

**Current Behavior**:
- Displays `equity_balance` from API
- Value never changes (frozen at seed)

**New Behavior**:
- Displays dynamic `equity_balance` that updates daily
- Shows daily change and cumulative P&L

**Changes Needed**:
```typescript
// Already fetching equity_balance from API
const { equity_balance } = portfolioData;

// Add change indicators
<div>
  <span>Current Equity: ${equity_balance.toLocaleString()}</span>
  <span className="text-green-600">+${dailyChange.toLocaleString()}</span>
  <span className="text-sm text-gray-500">
    ({cumulativePnlPercent.toFixed(2)}% all-time)
  </span>
</div>
```

#### Component: Position Weights

**Files**:
- Components that calculate position weights relative to portfolio

**Current Issue**:
- Using frozen equity_balance for denominator
- Weights drift as equity changes

**New Behavior**:
- Weights automatically correct as equity updates
- More accurate risk metrics

**No code changes needed** - weights recalculate automatically with updated equity.

### 2. New Features (Phase 2)

#### Feature: Equity Transaction Recording

**New Component**: `frontend/src/components/portfolio/EquityTransactionDialog.tsx`

```typescript
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useState } from "react";

interface EquityTransactionDialogProps {
  portfolioId: string;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EquityTransactionDialog({
  portfolioId,
  open,
  onClose,
  onSuccess
}: EquityTransactionDialogProps) {
  const [transactionType, setTransactionType] = useState<"deposit" | "withdrawal">("deposit");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);

    try {
      const response = await fetch(
        `/api/v1/analytics/portfolio/${portfolioId}/equity-transaction`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transaction_date: date,
            transaction_type: transactionType,
            amount: parseFloat(amount),
            notes: notes || null
          })
        }
      );

      if (!response.ok) throw new Error("Failed to record transaction");

      onSuccess();
      onClose();
    } catch (error) {
      console.error("Error recording transaction:", error);
      alert("Failed to record transaction");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Equity Transaction</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label>Transaction Type</Label>
            <RadioGroup value={transactionType} onValueChange={(v) => setTransactionType(v as any)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="deposit" id="deposit" />
                <Label htmlFor="deposit">Deposit (Add Capital)</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="withdrawal" id="withdrawal" />
                <Label htmlFor="withdrawal">Withdrawal (Remove Capital)</Label>
              </div>
            </RadioGroup>
          </div>

          <div>
            <Label htmlFor="amount">Amount ($)</Label>
            <Input
              id="amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="100000"
            />
          </div>

          <div>
            <Label htmlFor="date">Transaction Date</Label>
            <Input
              id="date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Q1 capital call"
            />
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting || !amount}>
              {isSubmitting ? "Recording..." : "Record Transaction"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

#### Feature: Equity History Chart

**New Component**: `frontend/src/components/portfolio/EquityHistoryChart.tsx`

```typescript
import { Line } from 'react-chartjs-2';
import { useEffect, useState } from 'react';

interface EquityHistoryData {
  date: string;
  equity_balance: number;
  daily_pnl: number;
  cumulative_pnl: number;
  equity_inflow: number;
  equity_outflow: number;
}

export function EquityHistoryChart({ portfolioId }: { portfolioId: string }) {
  const [data, setData] = useState<EquityHistoryData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const response = await fetch(
        `/api/v1/analytics/portfolio/${portfolioId}/equity-history`
      );
      const result = await response.json();
      setData(result.history);
      setLoading(false);
    };

    fetchData();
  }, [portfolioId]);

  if (loading) return <div>Loading equity history...</div>;

  const chartData = {
    labels: data.map(d => d.date),
    datasets: [
      {
        label: 'Equity Balance',
        data: data.map(d => d.equity_balance),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true
      },
      {
        label: 'Cumulative P&L',
        data: data.map(d => d.cumulative_pnl),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        borderDash: [5, 5]
      }
    ]
  };

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Equity Balance History</h3>
      <Line data={chartData} options={{
        responsive: true,
        plugins: {
          legend: { position: 'top' },
          title: { display: false }
        },
        scales: {
          y: {
            ticks: {
              callback: (value) => `$${(value as number).toLocaleString()}`
            }
          }
        }
      }} />

      {/* Cash flow annotations */}
      <div className="mt-4 text-sm">
        {data.filter(d => d.equity_inflow > 0 || d.equity_outflow > 0).map(d => (
          <div key={d.date} className="flex justify-between py-1">
            <span>{d.date}</span>
            <span className={d.equity_inflow > 0 ? "text-green-600" : "text-red-600"}>
              {d.equity_inflow > 0
                ? `+$${d.equity_inflow.toLocaleString()} deposit`
                : `-$${d.equity_outflow.toLocaleString()} withdrawal`
              }
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3. API Integration

**Existing APIs** (no changes needed):
- `GET /api/v1/data/portfolio/{id}/complete` - Returns updated equity_balance
- `GET /api/v1/analytics/portfolio/{id}/summary` - Uses updated equity for calculations

**New APIs to integrate** (Phase 2):
- `POST /api/v1/analytics/portfolio/{id}/equity-transaction`
- `GET /api/v1/analytics/portfolio/{id}/equity-history`

**TypeScript Types** (add to types file):

```typescript
// frontend/src/types/analytics.ts

export interface EquityTransaction {
  transaction_date: string;
  transaction_type: "deposit" | "withdrawal";
  amount: number;
  notes?: string;
}

export interface EquityHistoryPoint {
  date: string;
  equity_balance: number;
  daily_pnl: number;
  cumulative_pnl: number;
  equity_inflow: number;
  equity_outflow: number;
  total_value: number;
}

export interface EquityHistory {
  portfolio_id: string;
  portfolio_name: string;
  current_equity: number;
  history: EquityHistoryPoint[];
}
```

---

## Testing Strategy

### 1. Unit Tests

#### Backend Tests

**File**: `backend/tests/test_equity_calculations.py`

```python
import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.calculations.snapshots import _create_or_update_snapshot
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot

@pytest.mark.asyncio
async def test_equity_updates_with_daily_pnl(db_session):
    """Test that equity_balance updates with daily P&L"""
    # Create test portfolio
    portfolio = Portfolio(
        user_id=test_user_id,
        name="Test Portfolio",
        equity_balance=Decimal('1000000')
    )
    db_session.add(portfolio)
    await db_session.flush()

    # Day 1: Create first snapshot
    snapshot1 = await _create_or_update_snapshot(
        db=db_session,
        portfolio_id=portfolio.id,
        calculation_date=date.today(),
        aggregations={'gross_exposure': Decimal('1050000')},
        greeks={},
        pnl_data={'daily_pnl': Decimal('50000'), 'cumulative_pnl': Decimal('50000')},
        position_counts={'total': 10, 'long': 8, 'short': 2}
    )

    await db_session.refresh(portfolio)
    assert portfolio.equity_balance == Decimal('1050000')
    assert snapshot1.equity_balance == Decimal('1050000')

    # Day 2: Market moves down
    snapshot2 = await _create_or_update_snapshot(
        db=db_session,
        portfolio_id=portfolio.id,
        calculation_date=date.today() + timedelta(days=1),
        aggregations={'gross_exposure': Decimal('1030000')},
        greeks={},
        pnl_data={'daily_pnl': Decimal('-20000'), 'cumulative_pnl': Decimal('30000')},
        position_counts={'total': 10, 'long': 8, 'short': 2}
    )

    await db_session.refresh(portfolio)
    assert portfolio.equity_balance == Decimal('1030000')
    assert snapshot2.equity_balance == Decimal('1030000')


@pytest.mark.asyncio
async def test_equity_with_cash_flows(db_session):
    """Test equity calculation with deposits and withdrawals (Phase 2)"""
    # ... similar test with equity_inflow/outflow
```

**File**: `backend/tests/test_batch_orchestrator.py`

```python
@pytest.mark.asyncio
async def test_batch_updates_equity(db_session, demo_portfolio):
    """Test that batch processing updates portfolio equity"""
    initial_equity = demo_portfolio.equity_balance

    # Run batch processing
    from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
    await batch_orchestrator_v2.run_daily_batch_sequence(
        portfolio_id=str(demo_portfolio.id)
    )

    # Refresh portfolio
    await db_session.refresh(demo_portfolio)

    # Equity should have changed (unless markets didn't move)
    # Check that calculation ran without errors
    assert demo_portfolio.equity_balance is not None

    # Check snapshot was created
    snapshot = await db_session.execute(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == demo_portfolio.id,
            PortfolioSnapshot.snapshot_date == date.today()
        )
    )
    snapshot = snapshot.scalar_one()

    # Snapshot equity should match portfolio equity
    assert snapshot.equity_balance == demo_portfolio.equity_balance
```

#### Frontend Tests

**File**: `frontend/src/components/portfolio/__tests__/EquityDisplay.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { EquityDisplay } from '../EquityDisplay';

describe('EquityDisplay', () => {
  it('displays current equity balance', () => {
    const portfolioData = {
      equity_balance: 1050000,
      daily_pnl: 50000,
      cumulative_pnl: 50000
    };

    render(<EquityDisplay data={portfolioData} />);

    expect(screen.getByText(/\$1,050,000/)).toBeInTheDocument();
    expect(screen.getByText(/\+\$50,000/)).toBeInTheDocument();
  });

  it('shows negative changes in red', () => {
    const portfolioData = {
      equity_balance: 980000,
      daily_pnl: -20000,
      cumulative_pnl: -20000
    };

    render(<EquityDisplay data={portfolioData} />);

    const changeElement = screen.getByText(/-\$20,000/);
    expect(changeElement).toHaveClass('text-red-600');
  });
});
```

### 2. Integration Tests

#### Batch Processing Flow

**Script**: `backend/scripts/testing/test_equity_flow.py`

```python
"""
End-to-end test of equity balance calculation flow
"""
import asyncio
from datetime import date
from decimal import Decimal
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from sqlalchemy import select

async def test_equity_flow():
    """Test complete equity calculation flow"""
    async with AsyncSessionLocal() as db:
        # 1. Get demo portfolio
        result = await db.execute(
            select(Portfolio).where(Portfolio.name.like("%Individual%"))
        )
        portfolio = result.scalar_one()

        print(f"Portfolio: {portfolio.name}")
        print(f"Initial equity_balance: ${portfolio.equity_balance:,.2f}")

        # 2. Run batch processing
        print("\nRunning batch processing...")
        results = await batch_orchestrator_v2.run_daily_batch_sequence(
            portfolio_id=str(portfolio.id)
        )

        # 3. Check equity was updated
        await db.refresh(portfolio)
        print(f"Updated equity_balance: ${portfolio.equity_balance:,.2f}")

        # 4. Check snapshot
        snapshot_result = await db.execute(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == date.today()
            )
        )
        snapshot = snapshot_result.scalar_one()

        print(f"\nSnapshot data:")
        print(f"  equity_balance: ${snapshot.equity_balance:,.2f}")
        print(f"  total_value: ${snapshot.total_value:,.2f}")
        print(f"  daily_pnl: ${snapshot.daily_pnl:,.2f}")
        print(f"  cumulative_pnl: ${snapshot.cumulative_pnl:,.2f}")

        # 5. Verify consistency
        assert snapshot.equity_balance == portfolio.equity_balance, \
            "Snapshot equity doesn't match portfolio equity!"

        print("\n✅ Equity flow test passed!")

if __name__ == "__main__":
    asyncio.run(test_equity_flow())
```

**Run**:
```bash
cd backend
uv run python scripts/testing/test_equity_flow.py
```

### 3. Manual Testing Checklist

#### Phase 1 - P&L Tracking

- [ ] Run batch processing on demo portfolios
- [ ] Verify equity_balance changes in Portfolio table
- [ ] Verify equity_balance recorded in snapshots
- [ ] Check that equity matches previous_equity + daily_pnl
- [ ] Verify frontend displays updated equity
- [ ] Test leverage calculations use correct equity
- [ ] Check position weights update correctly

#### Phase 2 - Cash Flows

- [ ] Record a deposit via API
- [ ] Verify equity increases by deposit amount
- [ ] Record a withdrawal
- [ ] Verify equity decreases by withdrawal amount
- [ ] Check historical equity recalculation works
- [ ] Verify frontend shows cash flow history
- [ ] Test equity chart displays correctly

### 4. Data Validation Queries

```sql
-- Check equity updates over time
SELECT
    p.name,
    ps.snapshot_date,
    ps.equity_balance,
    ps.daily_pnl,
    LAG(ps.equity_balance) OVER (PARTITION BY p.id ORDER BY ps.snapshot_date) as prev_equity,
    ps.equity_balance - LAG(ps.equity_balance) OVER (PARTITION BY p.id ORDER BY ps.snapshot_date) as equity_change
FROM portfolio_snapshots ps
JOIN portfolios p ON p.id = ps.portfolio_id
WHERE p.id = 'your-portfolio-id'
ORDER BY ps.snapshot_date DESC
LIMIT 30;

-- equity_change should approximately equal daily_pnl (plus cash flows in Phase 2)

-- Check for consistency
SELECT
    ps.snapshot_date,
    ps.equity_balance as snapshot_equity,
    p.equity_balance as portfolio_equity,
    CASE
        WHEN ps.equity_balance = p.equity_balance THEN '✅ Match'
        ELSE '❌ Mismatch'
    END as status
FROM portfolio_snapshots ps
JOIN portfolios p ON p.id = ps.portfolio_id
WHERE ps.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM portfolio_snapshots
    WHERE portfolio_id = ps.portfolio_id
);

-- All latest snapshots should match their portfolio equity_balance
```

---

## Implementation Phases

### Phase 1: Fix P&L Tracking (IMMEDIATE)

**Timeline**: 1-2 days

**Scope**: Update equity_balance daily with P&L, no schema changes

**Steps**:
1. ✅ Modify `snapshots.py:_create_or_update_snapshot()`
2. ✅ Remove incorrect calculation from `batch_orchestrator_v2.py`
3. ✅ Add unit tests for equity calculation
4. ✅ Run batch processing on dev environment
5. ✅ Validate equity updates with SQL queries
6. ✅ Test frontend displays updated equity
7. ✅ Deploy to production

**Success Criteria**:
- Portfolio equity_balance changes daily with market movements
- Snapshot equity_balance matches portfolio table
- Frontend shows dynamic equity values
- Leverage and weight calculations use correct equity

### Phase 2: Add Cash Flow Tracking (FUTURE)

**Timeline**: 3-5 days

**Scope**: Add equity_inflow/outflow tracking with API and frontend

**Steps**:
1. ✅ Create Alembic migration for new columns
2. ✅ Update PortfolioSnapshot model
3. ✅ Implement equity transaction API endpoints
4. ✅ Add recalculation helper functions
5. ✅ Build frontend UI components
6. ✅ Add API integration to frontend
7. ✅ Write comprehensive tests
8. ✅ User documentation
9. ✅ Deploy migration to production
10. ✅ Release frontend features

**Success Criteria**:
- Users can record deposits and withdrawals
- Equity calculation includes cash flows
- Historical data recalculates correctly when cash flows added
- Frontend displays cash flow history
- Performance returns exclude cash flow effects

---

## Rollout Plan

### Pre-Deployment

#### Checklist:
- [ ] All unit tests passing
- [ ] Integration tests validated
- [ ] Code review completed
- [ ] Database backup created
- [ ] Rollback plan documented
- [ ] Staging environment tested

#### Database Backup:
```bash
# Phase 1 (no schema changes - minimal risk)
docker exec sigmasight-postgres pg_dump -U sigmasight sigmasight_db > backup_before_equity_fix.sql

# Phase 2 (schema changes - backup required)
docker exec sigmasight-postgres pg_dump -U sigmasight sigmasight_db > backup_before_cashflow_migration.sql
```

### Deployment Steps

#### Phase 1 Deployment:

```bash
# 1. Pull latest code
git pull origin main

# 2. Restart backend (code changes only, no migration)
docker-compose restart backend

# 3. Run batch processing manually to verify
cd backend
uv run python scripts/batch_processing/run_batch.py

# 4. Check equity values updated
uv run python scripts/testing/test_equity_flow.py

# 5. Monitor logs for errors
docker-compose logs -f backend
```

#### Phase 2 Deployment:

```bash
# 1. Backup database (REQUIRED)
docker exec sigmasight-postgres pg_dump -U sigmasight sigmasight_db > backup.sql

# 2. Pull latest code
git pull origin phase2-cashflow

# 3. Run Alembic migration
cd backend
uv run alembic upgrade head

# 4. Verify migration
uv run alembic current
uv run python -c "
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
import asyncio
async def check():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(PortfolioSnapshot).limit(1))
        snap = result.scalar_one()
        print(f'equity_inflow column exists: {hasattr(snap, \"equity_inflow\")}')
asyncio.run(check())
"

# 5. Restart backend
docker-compose restart backend

# 6. Deploy frontend
cd frontend
npm run build
# Deploy build to hosting service

# 7. Smoke test new features
# - Record a test deposit via API
# - Verify equity history endpoint works
# - Check frontend UI displays correctly
```

### Post-Deployment Validation

#### Phase 1 Checks:
```bash
# 1. Verify equity updates
psql -U sigmasight sigmasight_db -c "
SELECT name, equity_balance, updated_at
FROM portfolios
ORDER BY updated_at DESC;
"

# 2. Check snapshot consistency
psql -U sigmasight sigmasight_db -c "
SELECT p.name, ps.snapshot_date, ps.equity_balance, ps.daily_pnl
FROM portfolio_snapshots ps
JOIN portfolios p ON p.id = ps.portfolio_id
WHERE ps.snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY ps.snapshot_date DESC;
"

# 3. Verify frontend displays updated values
# Navigate to dashboard, check equity displays
```

#### Phase 2 Checks:
```bash
# 1. Test equity transaction API
curl -X POST http://localhost:8000/api/v1/analytics/portfolio/{id}/equity-transaction \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "transaction_date": "2025-10-16",
    "transaction_type": "deposit",
    "amount": 100000
  }'

# 2. Verify equity history endpoint
curl http://localhost:8000/api/v1/analytics/portfolio/{id}/equity-history \
  -H "Authorization: Bearer {token}"

# 3. Check cash flow columns populated
psql -U sigmasight sigmasight_db -c "
SELECT snapshot_date, equity_balance, equity_inflow, equity_outflow, daily_pnl
FROM portfolio_snapshots
WHERE equity_inflow > 0 OR equity_outflow > 0;
"
```

### Rollback Procedures

#### Phase 1 Rollback (Code only):
```bash
# 1. Revert code
git revert <commit-hash>

# 2. Restart backend
docker-compose restart backend

# No data loss - equity values will revert to previous calculation
```

#### Phase 2 Rollback (With migration):
```bash
# 1. Downgrade migration
cd backend
uv run alembic downgrade -1

# 2. Verify downgrade
uv run alembic current

# 3. Restore database from backup if needed
docker exec -i sigmasight-postgres psql -U sigmasight sigmasight_db < backup.sql

# 4. Revert code
git revert <commit-hash>

# 5. Restart services
docker-compose restart
```

---

## Risk Assessment

### Low Risk (Phase 1)
- **Code changes only**, no schema modifications
- Equity calculation logic change isolated to one function
- Existing snapshots remain intact
- Easy rollback (just revert code)

### Medium Risk (Phase 2)
- **Schema changes** require migration
- Database backup essential
- New columns have default values (safe for existing data)
- Rollback requires migration downgrade

### Mitigation Strategies
1. **Staging environment testing** before production
2. **Database backups** before Phase 2 deployment
3. **Gradual rollout**: Phase 1 first, Phase 2 after validation
4. **Monitoring**: Watch for calculation errors in logs
5. **Validation queries**: Verify equity consistency post-deployment

---

## Success Metrics

### Phase 1 Metrics
- ✅ Portfolio equity_balance updates daily (not frozen)
- ✅ Snapshot equity matches portfolio table
- ✅ Frontend displays dynamic equity values
- ✅ No batch processing errors
- ✅ Leverage calculations accurate

### Phase 2 Metrics
- ✅ Users can record deposits/withdrawals via UI
- ✅ Cash flows reflected in equity calculations
- ✅ Historical equity recalculates correctly
- ✅ Performance returns exclude cash flow effects
- ✅ Frontend charts display cash flow events

---

## Future Enhancements

### Advanced Features (Phase 3+)
1. **Time-weighted returns**: Calculate true investment performance
2. **Benchmark comparison**: Track equity vs S&P 500
3. **Multi-currency support**: Handle FX effects on equity
4. **Fee tracking**: Deduct management/performance fees
5. **Tax lot accounting**: Track cost basis per position
6. **Cash management**: Explicit cash positions vs equity
7. **Margin tracking**: Separate equity from borrowed capital

### Technical Improvements
1. **Event sourcing**: Full audit trail of equity changes
2. **Real-time updates**: WebSocket for live equity display
3. **Analytics dashboard**: Equity attribution analysis
4. **Export functionality**: Historical equity data to CSV
5. **API rate limiting**: Prevent abuse of transaction recording

---

## Appendix

### A. Related Documentation
- `backend/app/models/users.py` - Portfolio model definition
- `backend/app/models/snapshots.py` - PortfolioSnapshot model
- `backend/app/calculations/snapshots.py` - Snapshot calculation logic
- `backend/app/batch/batch_orchestrator_v2.py` - Batch processing orchestration

### B. Database Schema Diagrams

```
Portfolio Table:
+------------------+-----------------+
| Column           | Type            |
+------------------+-----------------+
| id               | UUID (PK)       |
| user_id          | UUID (FK)       |
| name             | VARCHAR(255)    |
| equity_balance   | NUMERIC(16,2)   | ← UPDATES DAILY (Phase 1)
| created_at       | TIMESTAMP       |
| updated_at       | TIMESTAMP       |
+------------------+-----------------+

PortfolioSnapshot Table:
+------------------+-----------------+
| Column           | Type            |
+------------------+-----------------+
| id               | UUID (PK)       |
| portfolio_id     | UUID (FK)       |
| snapshot_date    | DATE            |
| equity_balance   | NUMERIC(16,2)   | ← Calculated from previous + P&L
| total_value      | NUMERIC(16,2)   |
| daily_pnl        | NUMERIC(16,2)   |
| cumulative_pnl   | NUMERIC(16,2)   |
| equity_inflow    | NUMERIC(16,2)   | ← NEW (Phase 2)
| equity_outflow   | NUMERIC(16,2)   | ← NEW (Phase 2)
| created_at       | TIMESTAMP       |
+------------------+-----------------+
```

### C. Contact & Support
- **Questions**: Tag @backend-team in Slack
- **Issues**: Create ticket in issue tracker
- **Code reviews**: Pull requests require 1 approval
- **Documentation updates**: This file is authoritative source

---

**Document End**

Last Updated: 2025-10-16
Next Review: After Phase 1 completion
