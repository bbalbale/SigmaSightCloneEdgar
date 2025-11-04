# Phase 0: Realized P&L Tracking - Implementation Plan

**Feature**: Track Realized Gains/Losses from Position Closes
**Created**: November 3, 2025
**Status**: Planning Phase - **PREREQUISITE for Equity Changes**
**Priority**: Critical
**Estimated Effort**: 2-3 days

---

## Executive Summary

Fix critical gap in P&L tracking where realized gains/losses from closing positions are not recorded. Currently, the system only tracks unrealized (mark-to-market) P&L, ignoring actual profits/losses when positions are sold.

**Key Business Value:**
- Accurate profit/loss tracking when positions are closed
- Proper equity rollforward including realized gains
- Foundation for tax reporting (realized vs. unrealized)
- Prerequisite for equity changes tracking (Phase 1)

**Current State**:
- ✅ Database fields exist (`positions.realized_pnl`, `exit_price`, `exit_date`)
- ❌ Backend ignores exit fields from frontend
- ❌ No calculation logic for realized P&L
- ❌ P&L calculator only tracks unrealized changes

---

## Problem Statement

### What's Broken

When users close positions via `ManagePositionsSidePanel`:

```typescript
// Frontend sends (line 286-289 in ManagePositionsSidePanel.tsx)
await positionManagementService.updatePosition(lotId, {
  exit_price: parseFloat(sell.sale_price),
  exit_date: sell.sale_date,
  quantity: parseFloat(sell.sell_quantity)
})
```

**But the backend silently ignores `exit_price` and `exit_date`!**

**Backend schema** (`UpdatePositionRequest`):
```python
class UpdatePositionRequest(BaseModel):
    quantity: Optional[Decimal]
    avg_cost: Optional[Decimal]
    position_type: Optional[PositionType]
    notes: Optional[str]
    symbol: Optional[str]
    # Missing: exit_price, exit_date, entry_price
```

**Result**: Position closes are recorded (quantity reduced) but no realized P&L is calculated or stored.

### Impact

1. **Incomplete Equity Tracking**: Equity rollforward missing realized P&L component
2. **Incorrect Returns**: Returns don't reflect actual gains from closing positions
3. **No Tax Basis**: Can't track cost basis or realized gains for tax reporting
4. **Broken Partial Closes**: No way to track P&L on partial position exits

---

## Solution Architecture

### 3-Step Approach

1. **Accept Exit Fields**: Update backend to accept `exit_price`, `exit_date`, `entry_price`
2. **Calculate Realized P&L**: Compute gain/loss when position is closed
3. **Aggregate to Portfolio**: Track daily/cumulative realized P&L at snapshot level

---

## Implementation Details

### Step 1: Update Backend Schema

**File**: `backend/app/schemas/position_schemas.py`

**Changes**:
```python
class UpdatePositionRequest(BaseModel):
    """Payload for updating position fields."""

    # Existing fields
    quantity: Optional[Decimal] = Field(None, description="New quantity")
    avg_cost: Optional[Decimal] = Field(None, gt=0, description="New average cost")
    position_type: Optional[PositionType] = Field(None, description="New position type")
    notes: Optional[str] = Field(None, description="New notes")
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="New symbol (restricted)")

    # NEW: Exit fields for closing positions
    exit_price: Optional[Decimal] = Field(None, gt=0, description="Exit price when closing position")
    exit_date: Optional[date] = Field(None, description="Exit date when closing position")

    # NEW: Entry price correction (for averaging or fixing errors)
    entry_price: Optional[Decimal] = Field(None, gt=0, description="Entry price (for corrections)")

    @field_validator("exit_date")
    @classmethod
    def validate_exit_date(cls, value: Optional[date], info) -> Optional[date]:
        """Validate exit date is not in the future."""
        if value and value > date.today():
            raise ValueError("Exit date cannot be in the future")
        return value

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: Optional[str]) -> Optional[str]:
        """Ensure symbol is uppercase and trimmed if provided."""
        return value.upper().strip() if value else None
```

---

### Step 2: Calculate Realized P&L

**File**: `backend/app/services/position_service.py`

**Add to `update_position()` method** (~line 150+):

```python
async def update_position(
    self,
    position_id: UUID,
    user_id: UUID,
    quantity: Optional[Decimal] = None,
    avg_cost: Optional[Decimal] = None,
    position_type: Optional[PositionType] = None,
    notes: Optional[str] = None,
    symbol: Optional[str] = None,
    allow_symbol_edit: bool = False,
    # NEW parameters
    exit_price: Optional[Decimal] = None,
    exit_date: Optional[date] = None,
    entry_price: Optional[Decimal] = None,
) -> Position:
    """
    Update position fields.

    NEW: Calculates realized P&L when exit_price is set.
    """
    # ... existing code for loading position and permission checks ...

    # NEW: Update entry price if provided (for corrections)
    if entry_price is not None:
        position.entry_price = entry_price
        logger.info(f"Updated entry price to {entry_price}")

    # NEW: Handle position close (exit_price set)
    if exit_price is not None:
        position.exit_price = exit_price

        if exit_date is not None:
            position.exit_date = exit_date
        else:
            # Default to today if not specified
            position.exit_date = date.today()

        # Calculate realized P&L
        realized_pnl = self._calculate_realized_pnl(
            position=position,
            exit_price=exit_price
        )

        position.realized_pnl = realized_pnl

        logger.info(
            f"Position {position.symbol} closed: "
            f"Entry={position.entry_price}, Exit={exit_price}, "
            f"Quantity={position.quantity}, Realized P&L={realized_pnl}"
        )

    # ... rest of existing update logic ...

    await self.db.commit()
    await self.db.refresh(position)

    return position


def _calculate_realized_pnl(
    self,
    position: Position,
    exit_price: Decimal
) -> Decimal:
    """
    Calculate realized P&L when closing a position.

    Formula:
    - LONG positions: (exit_price - entry_price) × quantity × multiplier
    - SHORT positions: (entry_price - exit_price) × quantity × multiplier

    Multiplier:
    - Stocks: 1
    - Options: 100 (contracts represent 100 shares)

    Args:
        position: Position being closed
        exit_price: Exit price per share/contract

    Returns:
        Realized P&L as Decimal
    """
    from app.models.positions import PositionType

    # Determine multiplier (options have 100x multiplier)
    if position.position_type in [
        PositionType.LC,  # Long Call
        PositionType.LP,  # Long Put
        PositionType.SC,  # Short Call
        PositionType.SP   # Short Put
    ]:
        multiplier = Decimal('100')
    else:
        multiplier = Decimal('1')

    # Calculate P&L based on position direction
    if position.position_type in [PositionType.LONG, PositionType.LC, PositionType.LP]:
        # Long positions: profit when exit > entry
        price_diff = exit_price - position.entry_price
    else:  # SHORT, SC, SP
        # Short positions: profit when entry > exit
        price_diff = position.entry_price - exit_price

    realized_pnl = price_diff * position.quantity * multiplier

    return realized_pnl
```

---

### Step 3: Update API Endpoint

**File**: `backend/app/api/v1/positions.py`

**Update `update_position()` endpoint** (~line 177):

```python
@router.put("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID,
    request: UpdatePositionRequest,
    allow_symbol_edit: bool = Query(False, description="Allow symbol editing (< 5 min only)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update position fields.

    **Editable Fields (always):**
    - quantity (affects portfolio value)
    - avg_cost (affects unrealized P&L)
    - position_type (affects exposure calculations)
    - notes (user annotations)
    - exit_price (NEW: triggers realized P&L calculation)
    - exit_date (NEW: marks position close date)
    - entry_price (NEW: for corrections)

    **Conditional Edit:**
    - symbol (ONLY if allow_symbol_edit=true AND created < 5 min AND no snapshots)

    **Non-editable Fields:**
    - investment_class (use delete + create instead)
    - portfolio_id (cannot move positions between portfolios)

    **Realized P&L Calculation:**
    When exit_price is set, the system automatically calculates realized P&L:
    - LONG: (exit_price - entry_price) × quantity × multiplier
    - SHORT: (entry_price - exit_price) × quantity × multiplier

    **Permission Check:**
    - User must own the portfolio
    - Position must not be deleted

    **Returns:** Updated position with realized_pnl populated
    """
    service = PositionService(db)

    try:
        position = await service.update_position(
            position_id=position_id,
            user_id=current_user.id,
            quantity=request.quantity,
            avg_cost=request.avg_cost,
            position_type=request.position_type,
            notes=request.notes,
            symbol=request.symbol,
            allow_symbol_edit=allow_symbol_edit,
            # NEW: Pass exit fields
            exit_price=request.exit_price,
            exit_date=request.exit_date,
            entry_price=request.entry_price,
        )

        return PositionResponse.model_validate(position)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update position {position_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update position")
```

---

### Step 4: Add Snapshot Fields

**File**: `backend/app/models/snapshots.py`

**Add after line 35** (after `cumulative_pnl`):

```python
class PortfolioSnapshot(Base):
    """Portfolio snapshots - daily portfolio state for historical tracking"""
    __tablename__ = "portfolio_snapshots"

    # ... existing fields ...

    # P&L (existing)
    daily_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    daily_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6), nullable=True)
    cumulative_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)

    # NEW: Realized P&L tracking (Phase 0 - Nov 3, 2025)
    daily_realized_pnl: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(16, 2),
        nullable=True,
        comment="Realized P&L from closed positions on this date"
    )
    cumulative_realized_pnl: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(16, 2),
        nullable=True,
        comment="Running total of all realized P&L to date"
    )

    # ... rest of fields ...
```

**Database Migration**:

```bash
cd backend
alembic revision --autogenerate -m "add_realized_pnl_to_snapshots"
alembic upgrade head
```

---

### Step 5: Update P&L Calculator

**File**: `backend/app/batch/pnl_calculator.py`

**Modify `calculate_portfolio_pnl()` method** (~line 186-227):

```python
async def calculate_portfolio_pnl(
    self,
    portfolio_id: UUID,
    calculation_date: date,
    db: AsyncSession
) -> bool:
    """
    Calculate P&L for a single portfolio and create snapshot

    Steps:
    1. Check if trading day (skip if not)
    2. Get previous snapshot (for previous equity)
    3. Calculate position-level unrealized P&L (mark-to-market)
    4. Calculate realized P&L (from closed positions) [NEW]
    5. Aggregate to portfolio-level P&L
    6. Calculate new equity = previous_equity + unrealized_pnl + realized_pnl [UPDATED]
    7. Create snapshot with new equity

    Args:
        portfolio_id: Portfolio to process
        calculation_date: Date to calculate for
        db: Database session

    Returns:
        True if snapshot created successfully
    """
    # ... existing code for trading day check and previous snapshot ...

    # Calculate unrealized P&L (existing logic)
    daily_unrealized_pnl = await self._calculate_daily_pnl(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date,
        previous_snapshot=previous_snapshot
    )

    # NEW: Calculate realized P&L from closed positions
    daily_realized_pnl = await self._calculate_daily_realized_pnl(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date
    )

    # Total P&L = unrealized + realized
    total_daily_pnl = daily_unrealized_pnl + daily_realized_pnl

    # Calculate new equity
    new_equity = previous_equity + total_daily_pnl

    logger.info(
        f"    Daily Unrealized P&L: ${daily_unrealized_pnl:,.2f} | "
        f"Daily Realized P&L: ${daily_realized_pnl:,.2f} | "
        f"Total P&L: ${total_daily_pnl:,.2f} | "
        f"New Equity: ${new_equity:,.2f}"
    )

    # Create snapshot with skip_pnl_calculation=True
    snapshot_result = await create_portfolio_snapshot(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date,
        skip_pnl_calculation=True
    )

    if snapshot_result.get('success'):
        # Update the snapshot with our calculated values
        snapshot = snapshot_result.get('snapshot')
        if snapshot:
            snapshot.equity_balance = new_equity
            snapshot.daily_pnl = total_daily_pnl
            snapshot.daily_realized_pnl = daily_realized_pnl  # NEW
            snapshot.daily_return = (
                total_daily_pnl / previous_equity
            ) if previous_equity > 0 else Decimal('0')

            # Update cumulative P&L
            if previous_snapshot:
                snapshot.cumulative_pnl = (
                    (previous_snapshot.cumulative_pnl or Decimal('0'))
                    + total_daily_pnl
                )
                # NEW: Track cumulative realized P&L
                snapshot.cumulative_realized_pnl = (
                    (previous_snapshot.cumulative_realized_pnl or Decimal('0'))
                    + daily_realized_pnl
                )
            else:
                snapshot.cumulative_pnl = total_daily_pnl
                snapshot.cumulative_realized_pnl = daily_realized_pnl  # NEW

            await db.commit()

        logger.info(f"    ✓ Snapshot created")
        return True
    else:
        logger.warning(f"    ✗ Snapshot creation failed: {snapshot_result.get('message')}")
        return False


async def _calculate_daily_realized_pnl(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Decimal:
    """
    Calculate realized P&L from positions closed on calculation_date.

    Query positions where:
    - exit_date = calculation_date
    - realized_pnl is not null
    - deleted_at is null

    Args:
        db: Database session
        portfolio_id: Portfolio to calculate for
        calculation_date: Date to check for closed positions

    Returns:
        Sum of realized P&L for the day
    """
    from app.models.positions import Position

    # Query positions closed on this date
    query = select(func.sum(Position.realized_pnl)).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.exit_date == calculation_date,
            Position.realized_pnl.isnot(None),
            Position.deleted_at.is_(None)
        )
    )

    result = await db.execute(query)
    daily_realized_pnl = result.scalar() or Decimal('0')

    if daily_realized_pnl != Decimal('0'):
        logger.info(f"    Found realized P&L: ${daily_realized_pnl:,.2f}")

    return daily_realized_pnl
```

---

### Step 6: Backfill Historical Data (Optional)

**File**: `backend/scripts/backfill_realized_pnl.py` (new script)

```python
"""
Backfill realized P&L for positions that were closed before this feature was implemented.

This script:
1. Finds positions with exit_price and exit_date but null realized_pnl
2. Calculates realized P&L retroactively
3. Updates the position records
4. Marks with audit flag for tracking

Run: python scripts/backfill_realized_pnl.py
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_realized_pnl():
    """Backfill realized P&L for historical closed positions."""

    async with AsyncSessionLocal() as db:
        # Find positions with exit but no realized P&L
        query = select(Position).where(
            and_(
                Position.exit_price.isnot(None),
                Position.exit_date.isnot(None),
                Position.realized_pnl.is_(None),
                Position.deleted_at.is_(None)
            )
        )

        result = await db.execute(query)
        positions = result.scalars().all()

        logger.info(f"Found {len(positions)} positions to backfill")

        updated_count = 0

        for position in positions:
            try:
                # Calculate realized P&L
                realized_pnl = calculate_realized_pnl(position)

                # Update position
                position.realized_pnl = realized_pnl

                logger.info(
                    f"Backfilled {position.symbol}: "
                    f"Entry={position.entry_price}, Exit={position.exit_price}, "
                    f"Quantity={position.quantity}, P&L={realized_pnl}"
                )

                updated_count += 1

            except Exception as e:
                logger.error(f"Error backfilling {position.id}: {e}")

        await db.commit()
        logger.info(f"Backfilled {updated_count} positions")


def calculate_realized_pnl(position: Position) -> Decimal:
    """Calculate realized P&L for a position."""

    # Determine multiplier
    if position.position_type in [PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP]:
        multiplier = Decimal('100')
    else:
        multiplier = Decimal('1')

    # Calculate P&L based on direction
    if position.position_type in [PositionType.LONG, PositionType.LC, PositionType.LP]:
        price_diff = position.exit_price - position.entry_price
    else:  # SHORT, SC, SP
        price_diff = position.entry_price - position.exit_price

    realized_pnl = price_diff * position.quantity * multiplier

    return realized_pnl


if __name__ == "__main__":
    asyncio.run(backfill_realized_pnl())
```

---

## Testing Strategy

### Unit Tests

**File**: `backend/tests/services/test_position_service_realized_pnl.py`

```python
"""Unit tests for realized P&L calculations."""
import pytest
from decimal import Decimal
from datetime import date

from app.services.position_service import PositionService
from app.models.positions import Position, PositionType


@pytest.mark.asyncio
async def test_calculate_realized_pnl_long_stock_profit(db_session, sample_user, sample_portfolio):
    """Test realized P&L for profitable long stock position."""
    service = PositionService(db_session)

    # Create long stock position
    position = Position(
        portfolio_id=sample_portfolio.id,
        symbol="AAPL",
        position_type=PositionType.LONG,
        quantity=Decimal('100'),
        entry_price=Decimal('150.00'),
        entry_date=date(2025, 1, 1)
    )
    db_session.add(position)
    await db_session.commit()

    # Close position at profit
    updated = await service.update_position(
        position_id=position.id,
        user_id=sample_user.id,
        exit_price=Decimal('160.00'),
        exit_date=date(2025, 6, 1)
    )

    # Verify realized P&L
    assert updated.realized_pnl == Decimal('1000.00')  # ($160 - $150) * 100
    assert updated.exit_price == Decimal('160.00')
    assert updated.exit_date == date(2025, 6, 1)


@pytest.mark.asyncio
async def test_calculate_realized_pnl_short_stock_loss(db_session, sample_user, sample_portfolio):
    """Test realized P&L for unprofitable short stock position."""
    service = PositionService(db_session)

    # Create short stock position
    position = Position(
        portfolio_id=sample_portfolio.id,
        symbol="TSLA",
        position_type=PositionType.SHORT,
        quantity=Decimal('50'),
        entry_price=Decimal('200.00'),
        entry_date=date(2025, 1, 1)
    )
    db_session.add(position)
    await db_session.commit()

    # Close position at loss (cover at higher price)
    updated = await service.update_position(
        position_id=position.id,
        user_id=sample_user.id,
        exit_price=Decimal('220.00'),
        exit_date=date(2025, 6, 1)
    )

    # Verify realized P&L (loss)
    assert updated.realized_pnl == Decimal('-1000.00')  # ($200 - $220) * 50
    assert updated.exit_price == Decimal('220.00')


@pytest.mark.asyncio
async def test_calculate_realized_pnl_long_call_option(db_session, sample_user, sample_portfolio):
    """Test realized P&L for long call option (100x multiplier)."""
    service = PositionService(db_session)

    # Create long call option
    position = Position(
        portfolio_id=sample_portfolio.id,
        symbol="SPY",
        position_type=PositionType.LC,
        quantity=Decimal('1'),  # 1 contract
        entry_price=Decimal('5.00'),
        entry_date=date(2025, 1, 1)
    )
    db_session.add(position)
    await db_session.commit()

    # Close option at profit
    updated = await service.update_position(
        position_id=position.id,
        user_id=sample_user.id,
        exit_price=Decimal('7.50'),
        exit_date=date(2025, 3, 1)
    )

    # Verify realized P&L (accounts for 100x multiplier)
    assert updated.realized_pnl == Decimal('250.00')  # ($7.50 - $5.00) * 100
```

### Integration Tests

**File**: `backend/tests/batch/test_pnl_calculator_realized.py`

```python
"""Integration tests for P&L calculator with realized P&L."""
import pytest
from decimal import Decimal
from datetime import date

from app.batch.pnl_calculator import PnLCalculator


@pytest.mark.asyncio
async def test_pnl_calculator_includes_realized_pnl(
    db_session,
    sample_portfolio,
    sample_position
):
    """Test that batch calculator includes realized P&L in snapshots."""

    calculator = PnLCalculator()

    # Close position on specific date
    sample_position.exit_price = Decimal('160.00')
    sample_position.exit_date = date(2025, 6, 1)
    sample_position.realized_pnl = Decimal('1000.00')
    await db_session.commit()

    # Run calculator for that date
    result = await calculator.calculate_portfolio_pnl(
        portfolio_id=sample_portfolio.id,
        calculation_date=date(2025, 6, 1),
        db=db_session
    )

    assert result is True

    # Verify snapshot includes realized P&L
    from app.models.snapshots import PortfolioSnapshot
    from sqlalchemy import select

    query = select(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == sample_portfolio.id,
        PortfolioSnapshot.snapshot_date == date(2025, 6, 1)
    )
    snapshot_result = await db_session.execute(query)
    snapshot = snapshot_result.scalar_one()

    assert snapshot.daily_realized_pnl == Decimal('1000.00')
    assert snapshot.daily_pnl >= Decimal('1000.00')  # Includes unrealized + realized
```

---

## Implementation Checklist

### Backend Development (Days 1-2)

**Schema Updates**:
- [ ] Add `exit_price`, `exit_date`, `entry_price` to `UpdatePositionRequest` schema
- [ ] Add validation for exit_date (not in future)
- [ ] Add `daily_realized_pnl` and `cumulative_realized_pnl` to `PortfolioSnapshot` model
- [ ] Create Alembic migration for snapshot fields
- [ ] Run migration: `alembic upgrade head`

**Service Layer**:
- [ ] Add `_calculate_realized_pnl()` method to `PositionService`
- [ ] Update `update_position()` to accept new fields
- [ ] Add realized P&L calculation when exit_price is set
- [ ] Handle both full and partial closes
- [ ] Add logging for all realized P&L calculations

**API Layer**:
- [ ] Update `update_position()` endpoint to pass new fields to service
- [ ] Update API documentation with realized P&L behavior
- [ ] Test endpoint with Postman/curl

### Batch Calculator Enhancement (Day 3)

- [ ] Add `_calculate_daily_realized_pnl()` method to `PnLCalculator`
- [ ] Update `calculate_portfolio_pnl()` to include realized P&L
- [ ] Update snapshot creation to populate realized P&L fields
- [ ] Update logging to show unrealized vs. realized breakdown
- [ ] Test batch run with closed positions

### Testing (Days 4-5)

**Unit Tests**:
- [ ] Test long stock position close (profit)
- [ ] Test long stock position close (loss)
- [ ] Test short stock position close
- [ ] Test long call option close (100x multiplier)
- [ ] Test partial position close
- [ ] Test entry price correction

**Integration Tests**:
- [ ] Test batch calculator includes realized P&L
- [ ] Test snapshot fields populated correctly
- [ ] Test cumulative realized P&L rollup
- [ ] Test equity rollforward with realized P&L

**Manual Testing**:
- [ ] Close position via ManagePositionsSidePanel
- [ ] Verify realized_pnl appears in position record
- [ ] Run batch calculation manually
- [ ] Verify snapshot includes realized P&L
- [ ] Check equity balance updated correctly

### Optional: Historical Backfill

- [ ] Create `backfill_realized_pnl.py` script
- [ ] Test on local database copy first
- [ ] Run on Railway database if needed
- [ ] Verify backfilled values are correct

### Documentation

- [ ] Update backend CLAUDE.md with realized P&L patterns
- [ ] Update API_REFERENCE.md with new UpdatePositionRequest fields
- [ ] Add code comments explaining P&L calculation logic
- [ ] Document backfill script usage

---

## Success Criteria

### Functional Requirements ✅
- [ ] Closing a position via UI calculates realized P&L
- [ ] `positions.realized_pnl` is populated for closed positions
- [ ] Portfolio snapshots include `daily_realized_pnl` and `cumulative_realized_pnl`
- [ ] Batch calculator aggregates realized P&L from closed positions
- [ ] Equity rollforward includes realized P&L component
- [ ] Both full and partial closes are handled correctly

### Data Integrity ✅
- [ ] Realized P&L for LONG: `(exit_price - entry_price) × quantity × multiplier`
- [ ] Realized P&L for SHORT: `(entry_price - exit_price) × quantity × multiplier`
- [ ] Options use 100x multiplier correctly
- [ ] Cumulative realized P&L equals sum of daily realized P&L
- [ ] No double-counting between realized and unrealized P&L

### Performance ✅
- [ ] Position update endpoint < 500ms
- [ ] Batch calculation completes in existing time window
- [ ] No N+1 query issues when aggregating realized P&L

---

## Risk Assessment

### Technical Risks

**1. Partial Position Closes** (Medium)
- **Risk**: Complex logic for calculating P&L on partial quantity
- **Current Approach**: Update quantity, calculate P&L on exited portion
- **Mitigation**: Clear documentation, comprehensive tests

**2. Historical Data Gaps** (Low)
- **Risk**: Existing closed positions have no realized P&L
- **Mitigation**: Optional backfill script, clearly marked as estimated

**3. Calculation Errors** (Medium)
- **Risk**: Wrong P&L calculation for complex position types
- **Mitigation**: Unit tests for all position types, manual validation

### Business Risks

**1. User Confusion** (Low)
- **Risk**: Users don't understand realized vs. unrealized P&L
- **Mitigation**: Clear UI labels, tooltips, help documentation

---

## Example Calculations

### Long Stock Position - Profit
```
Entry: 100 shares @ $50.00
Exit:  100 shares @ $60.00
Realized P&L: ($60 - $50) × 100 = $1,000 gain
```

### Short Stock Position - Loss
```
Entry: -100 shares @ $50.00 (short sell)
Exit:  +100 shares @ $60.00 (cover)
Realized P&L: ($50 - $60) × 100 = -$1,000 loss
```

### Long Call Option - Profit
```
Entry: 1 contract @ $5.00 = $500 cost
Exit:  1 contract @ $8.00 = $800 proceeds
Realized P&L: ($8 - $5) × 100 = $300 gain
```

### Partial Close - Long Stock
```
Original: 1,000 shares @ $50
Sell 400:  400 shares @ $55

Realized P&L on closed portion:
($55 - $50) × 400 = $2,000 gain

Remaining position:
600 shares @ $50 (still has unrealized P&L)
```

---

## Next Steps

1. ✅ Review this plan with team
2. ✅ Approve for implementation
3. ⏳ Begin Day 1: Schema updates and migration
4. ⏳ Day 2: Service layer and API endpoint
5. ⏳ Day 3: Batch calculator enhancement
6. ⏳ Days 4-5: Testing and validation
7. ⏳ **Checkpoint**: Phase 0 complete → Proceed to Phase 1 (Equity Changes)

---

**Document End**

*This plan is a prerequisite for Phase 1: Equity Changes Tracking. Do not begin Phase 1 until Phase 0 is complete and validated.*
