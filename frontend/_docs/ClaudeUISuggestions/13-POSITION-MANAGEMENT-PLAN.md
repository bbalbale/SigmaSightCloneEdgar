# Position Management Feature - Implementation Plan

**Document Version**: 1.0
**Created**: November 3, 2025
**Status**: Planning - Awaiting Final Decisions
**Feature**: Full CRUD operations for portfolio positions

---

## Executive Summary

### What We're Building
A dedicated **Position Management** page that enables users to create, edit, and delete positions in their portfolio with full historical data preservation and audit trail capabilities.

### Current State
- Users can **VIEW** positions across multiple pages (portfolio, public-positions, private-positions, organize)
- Backend has **NO** create/update/delete endpoints for positions
- Position data is read-only, populated via manual seeding or batch processes

### Target State
- Users can **CREATE** new positions through intuitive UI
- Users can **EDIT** existing positions (quantity, cost, type)
- Users can **DELETE** positions with soft-delete (historical preservation)
- Full audit trail of all position changes
- Bulk operations (multi-select delete, CSV import/export)
- Automatic analytics recalculation for immediate feedback

### Strategic Value
- **User Empowerment**: Users can manage their portfolios independently
- **Data Quality**: Users can correct errors and update holdings
- **Audit Compliance**: Complete historical record of all changes
- **Operational Efficiency**: Reduces manual data entry burden

---

## Architecture Overview

### Backend Architecture

#### New API Endpoints (7 total)

**Core CRUD:**
```
POST   /api/v1/positions              - Create single position
PUT    /api/v1/positions/{id}         - Update position (quantity, avg_cost, type)
DELETE /api/v1/positions/{id}         - Soft delete position (preserves history)
GET    /api/v1/positions/{id}         - Get single position details
```

**Bulk Operations:**
```
POST   /api/v1/positions/bulk         - Bulk create positions
DELETE /api/v1/positions/bulk         - Bulk soft delete positions
```

**Import/Export (Phase 2):**
```
POST   /api/v1/positions/import-csv   - Import from CSV with validation
GET    /api/v1/positions/export-csv   - Export to CSV
```

#### Service Layer

**New File:** `app/services/position_service.py`

```python
class PositionService:
    """Position CRUD operations with validation and cascading logic"""

    async def create_position(
        self,
        portfolio_id: UUID,
        symbol: str,
        quantity: Decimal,
        avg_cost: Decimal,
        position_type: PositionType,
        investment_class: str
    ) -> Position:
        """
        Create new position with validation.

        Validation:
        - User owns portfolio
        - Symbol is valid format (1-5 uppercase chars)
        - Quantity > 0 (or < 0 for SHORT positions)
        - Avg cost > 0
        - Position type matches investment class
        - No duplicate symbol in portfolio (unless different type)

        Post-creation:
        - Trigger market data fetch for symbol
        - Queue for next batch analytics run (if auto-recalc enabled)
        """
        pass

    async def update_position(
        self,
        position_id: UUID,
        quantity: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        position_type: Optional[PositionType] = None
    ) -> Position:
        """
        Update position fields.

        Editable fields:
        - quantity (affects portfolio value)
        - avg_cost (affects unrealized P&L)
        - position_type (affects exposure calculations)

        Non-editable fields:
        - symbol (use delete + create instead)
        - investment_class (use delete + create instead)
        - portfolio_id (cannot move positions between portfolios)

        Historical Impact:
        - Snapshots remain unchanged (immutable audit trail)
        - Future calculations use new values
        - Target prices preserved
        """
        pass

    async def soft_delete_position(
        self,
        position_id: UUID,
        user_id: UUID
    ) -> dict:
        """
        Soft delete position (sets deleted_at timestamp).

        Preserves:
        - Position record (deleted_at field set)
        - All historical snapshots (immutable)
        - Target price (linked to deleted position)
        - Position tags (soft deleted via cascade)

        Impact:
        - Position excluded from active portfolio calculations
        - Historical analytics include deleted positions in date range
        - Batch orchestrator skips deleted positions
        - UI hides by default (show in audit view)

        Returns:
        {
            "deleted": True,
            "position_id": "uuid",
            "symbol": "AAPL",
            "preserved_snapshots": 90,
            "preserved_target_price": True
        }
        """
        pass

    async def bulk_delete_positions(
        self,
        position_ids: List[UUID],
        user_id: UUID
    ) -> dict:
        """Bulk soft delete with transaction safety"""
        pass

    async def validate_position_data(
        self,
        symbol: str,
        quantity: Decimal,
        position_type: PositionType,
        investment_class: str
    ) -> tuple[bool, Optional[str]]:
        """Validate position data before create/update"""
        pass
```

#### Database Changes

**Add Soft Delete Column to Position Model:**

```python
# app/models/positions.py

class Position(Base):
    __tablename__ = "positions"

    # Existing fields...
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"))
    symbol = Column(String(10), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    avg_cost = Column(Numeric(20, 8), nullable=False)
    position_type = Column(Enum(PositionType), nullable=False)
    investment_class = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # NEW: Soft delete support
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    # Add index for performance
    __table_args__ = (
        Index('idx_position_portfolio_active', 'portfolio_id', 'deleted_at'),
    )
```

**Migration Required:**
```bash
alembic revision -m "add_soft_delete_to_positions"
```

#### Cascading Delete Logic

When position is soft-deleted, what happens to related data?

| Related Data | Action | Rationale |
|--------------|--------|-----------|
| **PositionSnapshot** | ✅ Preserve (no delete) | Immutable audit trail |
| **TargetPrice** | ✅ Preserve (no delete) | Historical context ("Why did I hold this?") |
| **PositionTag** | ⚠️ Soft delete (set deleted_at) | Tags no longer relevant for active positions |
| **PositionGreeks** | ⚠️ Soft delete | Greeks recalculated for active positions only |
| **PositionFactorExposure** | ⚠️ Soft delete | Factors recalculated for active positions only |

**Key Principle:** Historical snapshots are sacred. Everything else follows position lifecycle.

#### Batch Orchestrator Integration

**Hybrid Recalculation Strategy:**

```python
# app/batch/batch_orchestrator_v3.py

async def trigger_recalculation(
    self,
    portfolio_id: UUID,
    trigger_type: str  # "auto" or "manual"
) -> dict:
    """
    Trigger analytics recalculation after position changes.

    Auto-triggered (single position change):
    - Market data fetch for new/changed symbol
    - P&L calculation for portfolio
    - Position market value updates
    - Factor exposure updates (fast)

    Manual-triggered (bulk operations):
    - User clicks "Recalculate" button
    - Full Phase 3 analytics run
    - Correlation matrices
    - Volatility forecasting
    - Stress testing

    Returns:
    {
        "job_id": "uuid",
        "status": "running",
        "estimated_completion": "2025-11-03T12:05:00Z"
    }
    """
    pass
```

**UI Indicator:**
```
After bulk delete:
┌─────────────────────────────────────────┐
│ ⚠️ Portfolio analytics need update      │
│ 5 positions deleted                      │
│ [Recalculate Now] [Later]               │
└─────────────────────────────────────────┘
```

---

### Frontend Architecture

#### New Page: Position Management

**Route:** `/manage-positions`

**Navigation Update:**
```typescript
// components/navigation/NavigationDropdown.tsx

const pages = [
  { name: 'Dashboard', href: '/portfolio' },
  { name: 'Manage Positions', href: '/manage-positions' }, // NEW
  { name: 'Public Positions', href: '/public-positions' },
  { name: 'Private Positions', href: '/private-positions' },
  { name: 'Organize', href: '/organize' },
  { name: 'AI Chat', href: '/ai-chat' },
  { name: 'Settings', href: '/settings' }
]
```

#### Page Layout: Split View (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│ Manage Positions                    [Add Position] [Import] │
├─────────────────────┬───────────────────────────────────────┤
│ Position List       │ Position Form                         │
│ (60% width)         │ (40% width)                           │
│                     │                                       │
│ [Filter: All ▾]     │ ┌───────────────────────────────┐    │
│ [Search...]         │ │ Symbol: [AAPL___]             │    │
│                     │ │ Quantity: [100___]            │    │
│ ☐ AAPL    [Edit]    │ │ Avg Cost: [$150.00___]        │    │
│   100 shares        │ │ Type: [LONG ▾]                │    │
│   $150.00 avg       │ │ Class: [PUBLIC ▾]             │    │
│                     │ │                                │    │
│ ☐ MSFT    [Edit]    │ │ [Cancel] [Save Position]      │    │
│   50 shares         │ └───────────────────────────────┘    │
│   $320.00 avg       │                                       │
│                     │ Recently Added:                       │
│ ☐ TSLA    [Edit]    │ • NVDA - 25 shares (2 min ago)       │
│   25 shares         │ • GOOGL - 30 shares (1 hour ago)     │
│   $250.00 avg       │                                       │
│                     │                                       │
│ [2 selected]        │                                       │
│ [Bulk Delete]       │                                       │
└─────────────────────┴───────────────────────────────────────┘
```

**Why Split View?**
- No modal popups (faster workflow)
- Form always visible (less clicking)
- See position list while editing
- Better for desktop power users
- Can add responsive mobile layout later

#### Component Architecture

```
ManagePositionsContainer.tsx (new page container)
├── PositionListPanel (left side)
│   ├── PositionFilterBar
│   ├── PositionSearchBox
│   ├── PositionTable
│   │   └── PositionRow (with checkbox, edit button)
│   └── BulkActionsBar (appears when items selected)
│
└── PositionFormPanel (right side)
    ├── PositionForm
    │   ├── SymbolInput (auto-uppercase)
    │   ├── QuantityInput (numeric only)
    │   ├── AvgCostInput (currency format)
    │   ├── TypeSelect (dropdown)
    │   └── ClassSelect (dropdown)
    ├── FormActions (Cancel/Save buttons)
    └── RecentActivityFeed
```

#### New Components Needed (7 total)

**1. ManagePositionsContainer.tsx** (~300 lines)
```typescript
'use client'
import { useState } from 'react'
import { usePositions } from '@/hooks/usePositions'
import { PositionListPanel } from '@/components/positions/PositionListPanel'
import { PositionFormPanel } from '@/components/positions/PositionFormPanel'

export function ManagePositionsContainer() {
  const { positions, loading, createPosition, updatePosition, deletePosition } = usePositions()
  const [selectedPositions, setSelectedPositions] = useState<string[]>([])
  const [editingPosition, setEditingPosition] = useState<Position | null>(null)

  return (
    <div className="grid grid-cols-[60%_40%] gap-6">
      <PositionListPanel
        positions={positions}
        selectedPositions={selectedPositions}
        onSelect={setSelectedPositions}
        onEdit={setEditingPosition}
      />
      <PositionFormPanel
        position={editingPosition}
        onCreate={createPosition}
        onUpdate={updatePosition}
        onCancel={() => setEditingPosition(null)}
      />
    </div>
  )
}
```

**2. PositionFormPanel.tsx** (~250 lines)
- Symbol input with auto-uppercase
- Quantity input with numeric validation
- Avg cost input with currency formatting
- Position type dropdown (LONG/SHORT/LC/LP/SC/SP)
- Investment class dropdown (PUBLIC/OPTIONS/PRIVATE)
- Real-time validation feedback
- Submit/Cancel buttons
- Recent activity feed

**3. PositionListPanel.tsx** (~200 lines)
- Position table with checkboxes
- Filter dropdown (All/Public/Options/Private)
- Search box (symbol, name)
- Edit/Delete actions per row
- Multi-select support

**4. BulkActionsBar.tsx** (~100 lines)
- Appears when 1+ positions selected
- Shows count: "3 positions selected"
- Bulk delete button
- Clear selection button

**5. PositionDeleteDialog.tsx** (~150 lines)
- Confirmation modal
- Shows position details
- Lists cascading impacts (target prices, tags)
- Confirm/Cancel buttons

**6. RecalculationBadge.tsx** (~80 lines)
- Shows after bulk operations
- "Portfolio analytics need update"
- "Recalculate Now" button
- Dismissible

**7. PositionImportModal.tsx** (~300 lines) - Phase 2
- CSV file upload
- Preview table with validation
- Error display
- Import confirmation

#### Service Layer Updates

**Extend:** `src/services/positionApiService.ts`

```typescript
// src/services/positionApiService.ts

import { apiClient } from './apiClient'
import { Position, CreatePositionData, UpdatePositionData } from '@/lib/types'

const positionApiService = {
  // NEW: Create position
  async createPosition(
    portfolioId: string,
    data: CreatePositionData
  ): Promise<Position> {
    const response = await apiClient.post('/api/v1/positions', {
      portfolio_id: portfolioId,
      ...data
    })
    return response.data
  },

  // NEW: Update position
  async updatePosition(
    positionId: string,
    data: UpdatePositionData
  ): Promise<Position> {
    const response = await apiClient.put(`/api/v1/positions/${positionId}`, data)
    return response.data
  },

  // NEW: Delete position (soft delete)
  async deletePosition(positionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/positions/${positionId}`)
  },

  // NEW: Bulk delete
  async bulkDeletePositions(positionIds: string[]): Promise<void> {
    await apiClient.delete('/api/v1/positions/bulk', {
      data: { position_ids: positionIds }
    })
  },

  // Existing methods...
  async getPositions(portfolioId: string): Promise<Position[]> {
    const response = await apiClient.get(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`)
    return response.data.positions
  }
}

export default positionApiService
```

#### State Management: Zustand Enhancement

**Extend:** `src/stores/portfolioStore.ts`

```typescript
// src/stores/portfolioStore.ts

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import positionApiService from '@/services/positionApiService'

interface PortfolioStore {
  // Existing...
  portfolios: Portfolio[]
  selectedPortfolioId: string | null

  // NEW: Position cache
  positions: Position[]
  positionsLoading: boolean
  positionsError: string | null

  // NEW: Position mutations
  addPosition: (position: Position) => void
  updatePosition: (id: string, data: Partial<Position>) => void
  removePosition: (id: string) => void
  setPositions: (positions: Position[]) => void

  // NEW: Fetch positions
  fetchPositions: () => Promise<void>
}

export const usePortfolioStore = create<PortfolioStore>()(
  persist(
    (set, get) => ({
      portfolios: [],
      selectedPortfolioId: null,
      positions: [],
      positionsLoading: false,
      positionsError: null,

      // Optimistic add
      addPosition: (position) => set((state) => ({
        positions: [...state.positions, position]
      })),

      // Optimistic update
      updatePosition: (id, data) => set((state) => ({
        positions: state.positions.map(p =>
          p.id === id ? { ...p, ...data } : p
        )
      })),

      // Optimistic remove
      removePosition: (id) => set((state) => ({
        positions: state.positions.filter(p => p.id !== id)
      })),

      setPositions: (positions) => set({ positions }),

      // Fetch from API
      fetchPositions: async () => {
        const portfolioId = get().selectedPortfolioId
        if (!portfolioId) return

        set({ positionsLoading: true, positionsError: null })
        try {
          const positions = await positionApiService.getPositions(portfolioId)
          set({ positions, positionsLoading: false })
        } catch (error) {
          set({ positionsError: error.message, positionsLoading: false })
        }
      }
    }),
    {
      name: 'portfolio-store',
      partialPersist: (state) => ({
        selectedPortfolioId: state.selectedPortfolioId
        // Don't persist positions (fetch fresh)
      })
    }
  )
)
```

#### Custom Hook: Position Management

**New File:** `src/hooks/usePositionManagement.ts`

```typescript
// src/hooks/usePositionManagement.ts

import { useState } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import positionApiService from '@/services/positionApiService'
import { toast } from 'sonner'

export function usePositionManagement() {
  const {
    selectedPortfolioId,
    positions,
    addPosition,
    updatePosition: updatePositionStore,
    removePosition
  } = usePortfolioStore()

  const [loading, setLoading] = useState(false)

  const createPosition = async (data: CreatePositionData) => {
    if (!selectedPortfolioId) {
      toast.error('No portfolio selected')
      return
    }

    setLoading(true)
    try {
      // Optimistic update
      const tempPosition = { ...data, id: 'temp-' + Date.now() }
      addPosition(tempPosition)

      // API call
      const newPosition = await positionApiService.createPosition(
        selectedPortfolioId,
        data
      )

      // Replace temp with real
      removePosition(tempPosition.id)
      addPosition(newPosition)

      toast.success(`Added ${data.symbol}`)
      return newPosition
    } catch (error) {
      // Rollback on error
      removePosition('temp-' + Date.now())
      toast.error(`Failed to add position: ${error.message}`)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const updatePosition = async (id: string, data: UpdatePositionData) => {
    setLoading(true)

    // Store original for rollback
    const original = positions.find(p => p.id === id)

    try {
      // Optimistic update
      updatePositionStore(id, data)

      // API call
      const updated = await positionApiService.updatePosition(id, data)

      // Confirm with server response
      updatePositionStore(id, updated)

      toast.success('Position updated')
      return updated
    } catch (error) {
      // Rollback on error
      if (original) updatePositionStore(id, original)
      toast.error(`Failed to update position: ${error.message}`)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const deletePosition = async (id: string) => {
    setLoading(true)

    // Store original for rollback
    const original = positions.find(p => p.id === id)

    try {
      // Optimistic delete
      removePosition(id)

      // API call
      await positionApiService.deletePosition(id)

      toast.success('Position deleted')
    } catch (error) {
      // Rollback on error
      if (original) addPosition(original)
      toast.error(`Failed to delete position: ${error.message}`)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const bulkDeletePositions = async (ids: string[]) => {
    setLoading(true)

    // Store originals for rollback
    const originals = positions.filter(p => ids.includes(p.id))

    try {
      // Optimistic delete
      ids.forEach(removePosition)

      // API call
      await positionApiService.bulkDeletePositions(ids)

      toast.success(`Deleted ${ids.length} positions`)
    } catch (error) {
      // Rollback on error
      originals.forEach(addPosition)
      toast.error(`Failed to delete positions: ${error.message}`)
      throw error
    } finally {
      setLoading(false)
    }
  }

  return {
    positions,
    loading,
    createPosition,
    updatePosition,
    deletePosition,
    bulkDeletePositions
  }
}
```

---

## User Experience Design

### Form Validation

**Client-side Validation (Instant Feedback):**

| Field | Validation Rules | Error Message |
|-------|------------------|---------------|
| Symbol | Required, 1-5 uppercase chars, alphanumeric | "Symbol must be 1-5 uppercase letters" |
| Quantity | Required, numeric, > 0 (or < 0 for SHORT) | "Quantity must be greater than 0" |
| Avg Cost | Required, numeric, > 0 | "Avg cost must be greater than 0" |
| Position Type | Required, must match investment class | "Options must use LC/LP/SC/SP types" |
| Investment Class | Required | "Please select investment class" |

**Server-side Validation (Security):**
- User owns portfolio
- Symbol format valid
- No SQL injection
- Duplicate symbol check (same type in portfolio)
- Position type matches investment class

### Delete Confirmation Dialog

```
┌─────────────────────────────────────────┐
│ ⚠️  Delete Position?                    │
├─────────────────────────────────────────┤
│                                          │
│ AAPL - 100 shares @ $150.00             │
│ Apple Inc.                               │
│                                          │
│ This position will be archived.          │
│ Historical data will be preserved:       │
│                                          │
│ ✓ 90 historical snapshots                │
│ ✓ Target price ($250.00)                │
│ ✓ 2 tags (Tech, Core Holdings)          │
│                                          │
│ The position will no longer appear in    │
│ your active portfolio but can be viewed  │
│ in historical reports.                   │
│                                          │
│ [Cancel]  [Archive Position]            │
└─────────────────────────────────────────┘
```

**Note:** Using "Archive" instead of "Delete" to communicate preservation.

### Loading States

**Creating Position:**
```
[Add Position] → [Adding...] → ✓ Success toast
```

**Form State:**
```
Symbol: [AAPL___]
Quantity: [100___]
Avg Cost: [$150.00___]
Type: [LONG ▾]
Class: [PUBLIC ▾]

[Cancel] [Adding Position...] ← Disabled, spinner
```

**Optimistic Update:**
```
Position appears immediately in list with:
• Faded opacity (0.6)
• Spinner icon
• "Saving..." label

On success: Full opacity, spinner removed
On error: Red flash, removed from list, error toast
```

### Error Handling

**Types of Errors:**

1. **Validation Error (400)**
   - Show inline field error
   - Keep form open
   - User can correct

2. **Permission Error (403)**
   - Toast: "You don't have permission to modify this portfolio"
   - Close form
   - Redirect to view-only mode

3. **Network Error (500)**
   - Toast: "Failed to save position. Please try again."
   - Keep form open with data
   - Retry button

4. **Conflict Error (409)**
   - Toast: "Position with symbol AAPL already exists"
   - Highlight symbol field
   - Suggest editing existing instead

**Error Recovery:**
- Optimistic updates rolled back
- Original state restored
- User can retry immediately

---

## Implementation Roadmap

### Phase 1: Core CRUD (5-7 days)

#### Backend (3-4 days)
**Day 1: Database & Models**
- [ ] Add `deleted_at` column to Position model
- [ ] Create Alembic migration
- [ ] Test migration on local database
- [ ] Update Position model with soft delete methods

**Day 2: Service Layer**
- [ ] Create `app/services/position_service.py`
- [ ] Implement `create_position()` with validation
- [ ] Implement `update_position()` with field restrictions
- [ ] Implement `soft_delete_position()` with cascading
- [ ] Write unit tests for service methods

**Day 3: API Endpoints**
- [ ] Create `app/api/v1/positions.py` route file
- [ ] Implement POST `/positions` (create)
- [ ] Implement PUT `/positions/{id}` (update)
- [ ] Implement DELETE `/positions/{id}` (soft delete)
- [ ] Implement GET `/positions/{id}` (single position)
- [ ] Add authentication/authorization checks

**Day 4: Integration & Testing**
- [ ] Test all endpoints with Postman/Swagger
- [ ] Test cascading delete logic
- [ ] Test validation edge cases
- [ ] Update API documentation
- [ ] Deploy to Railway for staging test

#### Frontend (3-4 days)
**Day 1: Service & State**
- [ ] Extend `positionApiService.ts` with new methods
- [ ] Add position cache to `portfolioStore.ts`
- [ ] Create `usePositionManagement.ts` hook
- [ ] Test optimistic updates locally

**Day 2: Core Components**
- [ ] Create `ManagePositionsContainer.tsx` (page container)
- [ ] Create `PositionFormPanel.tsx` (form UI)
- [ ] Create `PositionListPanel.tsx` (table UI)
- [ ] Add to navigation dropdown

**Day 3: Form Features**
- [ ] Implement form validation (client-side)
- [ ] Add auto-uppercase for symbol
- [ ] Add currency formatting for avg_cost
- [ ] Add position type/class dropdowns
- [ ] Create/Edit mode switching

**Day 4: Delete & Polish**
- [ ] Create `PositionDeleteDialog.tsx`
- [ ] Implement delete confirmation flow
- [ ] Add loading states and spinners
- [ ] Add error handling and toasts
- [ ] Test full workflow end-to-end

### Phase 2: Bulk Operations (2-3 days)

#### Backend (1 day)
**Day 5: Bulk APIs**
- [ ] Implement POST `/positions/bulk` (bulk create)
- [ ] Implement DELETE `/positions/bulk` (bulk delete)
- [ ] Add transaction safety (all or nothing)
- [ ] Test bulk operations with large datasets

#### Frontend (2 days)
**Day 6: Multi-select UI**
- [ ] Add checkbox column to PositionTable
- [ ] Create `BulkActionsBar.tsx`
- [ ] Implement multi-select logic
- [ ] Add "Select All" checkbox

**Day 7: Bulk Delete**
- [ ] Implement bulk delete confirmation
- [ ] Add progress indicator for bulk operations
- [ ] Create `RecalculationBadge.tsx`
- [ ] Test bulk operations

### Phase 3: CSV Import/Export (2-3 days) - Optional

#### Backend (1 day)
**Day 8: CSV Endpoints**
- [ ] Implement POST `/positions/import-csv`
- [ ] Implement GET `/positions/export-csv`
- [ ] Add CSV validation and error reporting

#### Frontend (2 days)
**Day 9-10: Import/Export UI**
- [ ] Create `PositionImportModal.tsx`
- [ ] CSV file upload with drag-drop
- [ ] Preview table with validation errors
- [ ] Export button with download

### Phase 4: Analytics Integration (1-2 days)

**Day 11: Batch Recalculation**
- [ ] Backend: Add recalculation trigger endpoint
- [ ] Frontend: Add "Recalculate" button
- [ ] Show recalculation status
- [ ] Auto-trigger for single changes
- [ ] Manual trigger for bulk operations

### Phase 5: Polish & Production (1-2 days)

**Day 12: QA & Documentation**
- [ ] End-to-end testing
- [ ] Edge case testing
- [ ] Update user documentation
- [ ] Update `API_REFERENCE.md`
- [ ] Update `CLAUDE.md` files

---

## Data Model Details

### Position Model (Enhanced)

```python
# app/models/positions.py

from sqlalchemy import Column, String, Numeric, Enum, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

class PositionType(str, enum.Enum):
    LONG = "LONG"      # Long equity
    SHORT = "SHORT"    # Short equity
    LC = "LC"          # Long call
    LP = "LP"          # Long put
    SC = "SC"          # Short call
    SP = "SP"          # Short put

class Position(Base):
    __tablename__ = "positions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)

    # Position data
    symbol = Column(String(10), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    avg_cost = Column(Numeric(20, 8), nullable=False)
    position_type = Column(Enum(PositionType), nullable=False)
    investment_class = Column(String(20), nullable=False)  # PUBLIC, OPTIONS, PRIVATE

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)  # NEW

    # Relationships (existing)
    portfolio = relationship("Portfolio", back_populates="positions")
    target_price = relationship("TargetPrice", back_populates="position", uselist=False)
    tags = relationship("PositionTag", back_populates="position")
    greeks = relationship("PositionGreeks", back_populates="position")
    factor_exposures = relationship("PositionFactorExposure", back_populates="position")
    snapshots = relationship("PositionSnapshot", back_populates="position")

    # Indexes
    __table_args__ = (
        Index('idx_position_portfolio', 'portfolio_id'),
        Index('idx_position_symbol', 'symbol'),
        Index('idx_position_portfolio_active', 'portfolio_id', 'deleted_at'),  # NEW
    )

    # Methods
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = func.now()

    def restore(self):
        self.deleted_at = None
```

### Alembic Migration

```python
# alembic/versions/XXXXXX_add_soft_delete_to_positions.py

"""add soft delete to positions

Revision ID: XXXXXX
Revises: YYYYYY
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add deleted_at column
    op.add_column('positions',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add index for performance
    op.create_index(
        'idx_position_portfolio_active',
        'positions',
        ['portfolio_id', 'deleted_at']
    )

def downgrade():
    op.drop_index('idx_position_portfolio_active', table_name='positions')
    op.drop_column('positions', 'deleted_at')
```

---

## Security Considerations

### Authorization Checks

**Every position mutation must verify:**
1. User is authenticated (JWT token valid)
2. User owns the portfolio containing the position
3. User has permission to modify portfolio

**Implementation:**

```python
# app/api/v1/positions.py

@router.post("/positions")
async def create_position(
    position_data: CreatePositionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Verify user owns portfolio
    portfolio = await db.get(Portfolio, position_data.portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this portfolio")

    # Create position
    position = await position_service.create_position(...)
    return position
```

### Input Validation

**SQL Injection Prevention:**
- Use SQLAlchemy ORM (parameterized queries)
- Never concatenate user input into SQL

**XSS Prevention:**
- Sanitize symbol input (uppercase, alphanumeric only)
- Limit field lengths

**CSRF Prevention:**
- JWT tokens in Authorization header
- No cookies for mutations

### Rate Limiting

**Prevent abuse:**
- Max 10 position creates per minute per user
- Max 50 bulk operations per hour per user
- Max 5 CSV imports per hour per user

---

## Testing Strategy

### Unit Tests (Backend)

**Test File:** `tests/services/test_position_service.py`

```python
import pytest
from app.services.position_service import PositionService

@pytest.mark.asyncio
async def test_create_position_success():
    """Test successful position creation"""
    position = await position_service.create_position(
        portfolio_id=test_portfolio_id,
        symbol="AAPL",
        quantity=100,
        avg_cost=150.00,
        position_type=PositionType.LONG,
        investment_class="PUBLIC"
    )
    assert position.symbol == "AAPL"
    assert position.quantity == 100

@pytest.mark.asyncio
async def test_create_position_invalid_symbol():
    """Test validation fails for invalid symbol"""
    with pytest.raises(ValidationError):
        await position_service.create_position(
            portfolio_id=test_portfolio_id,
            symbol="TOOLONG",  # Too long
            quantity=100,
            avg_cost=150.00,
            position_type=PositionType.LONG,
            investment_class="PUBLIC"
        )

@pytest.mark.asyncio
async def test_soft_delete_preserves_snapshots():
    """Test soft delete preserves historical data"""
    # Create position with snapshots
    position = await create_test_position()
    await create_test_snapshots(position.id, count=10)

    # Soft delete
    await position_service.soft_delete_position(position.id, user_id)

    # Verify position is deleted
    position = await db.get(Position, position.id)
    assert position.deleted_at is not None

    # Verify snapshots remain
    snapshots = await db.execute(
        select(PositionSnapshot).where(PositionSnapshot.position_id == position.id)
    )
    assert len(snapshots.all()) == 10
```

### Integration Tests (API)

**Test File:** `tests/api/test_positions_api.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_position_endpoint(client: AsyncClient, auth_headers):
    """Test POST /api/v1/positions"""
    response = await client.post(
        "/api/v1/positions",
        headers=auth_headers,
        json={
            "portfolio_id": str(test_portfolio_id),
            "symbol": "AAPL",
            "quantity": 100,
            "avg_cost": 150.00,
            "position_type": "LONG",
            "investment_class": "PUBLIC"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"

@pytest.mark.asyncio
async def test_delete_position_unauthorized(client: AsyncClient, auth_headers):
    """Test DELETE requires authorization"""
    # Create position owned by different user
    other_position = await create_position_for_other_user()

    # Try to delete (should fail)
    response = await client.delete(
        f"/api/v1/positions/{other_position.id}",
        headers=auth_headers
    )
    assert response.status_code == 403
```

### Frontend Tests

**Test File:** `src/hooks/__tests__/usePositionManagement.test.ts`

```typescript
import { renderHook, act, waitFor } from '@testing-library/react'
import { usePositionManagement } from '@/hooks/usePositionManagement'

describe('usePositionManagement', () => {
  it('creates position with optimistic update', async () => {
    const { result } = renderHook(() => usePositionManagement())

    await act(async () => {
      await result.current.createPosition({
        symbol: 'AAPL',
        quantity: 100,
        avg_cost: 150.00,
        position_type: 'LONG',
        investment_class: 'PUBLIC'
      })
    })

    await waitFor(() => {
      expect(result.current.positions).toContainEqual(
        expect.objectContaining({ symbol: 'AAPL' })
      )
    })
  })

  it('rolls back on error', async () => {
    const { result } = renderHook(() => usePositionManagement())
    const originalCount = result.current.positions.length

    // Mock API error
    jest.spyOn(positionApiService, 'createPosition').mockRejectedValue(
      new Error('Network error')
    )

    await act(async () => {
      try {
        await result.current.createPosition({ /* ... */ })
      } catch (error) {
        // Expected error
      }
    })

    // Verify rollback
    expect(result.current.positions).toHaveLength(originalCount)
  })
})
```

---

## Performance Considerations

### Backend Performance

**Database Queries:**
- Use indexes on `portfolio_id` and `deleted_at`
- Eager load relationships when needed
- Pagination for large position lists

**Batch Operations:**
- Use database transactions for bulk deletes
- Process in chunks (100 positions per transaction)
- Return job ID for async processing if > 500 positions

**Caching:**
- Cache position data for 5 minutes
- Invalidate cache on mutations
- Use Redis for shared cache across instances

### Frontend Performance

**Optimistic Updates:**
- Instant feedback without waiting for API
- Rollback on error (seamless UX)
- Show loading states during reconciliation

**Component Optimization:**
- Memo position rows (prevent unnecessary re-renders)
- Virtual scrolling for large position lists (>100 items)
- Debounce search input (300ms)

**Bundle Size:**
- Code split position management page
- Lazy load form validation library
- Tree-shake unused UI components

---

## Monitoring & Analytics

### Metrics to Track

**Backend Metrics:**
- Position create/update/delete counts per day
- API error rates by endpoint
- Average response times
- Bulk operation sizes

**Frontend Metrics:**
- Form completion rate
- Form abandonment rate
- Time to complete position add
- Error rate by validation rule

**Business Metrics:**
- Active users managing positions
- Positions created per user per month
- Bulk operation usage vs single operations
- CSV import adoption rate

### Logging

**Audit Log:**
```json
{
  "timestamp": "2025-11-03T12:00:00Z",
  "user_id": "uuid",
  "action": "position_created",
  "position_id": "uuid",
  "data": {
    "symbol": "AAPL",
    "quantity": 100,
    "avg_cost": 150.00
  }
}
```

**Error Log:**
```json
{
  "timestamp": "2025-11-03T12:00:00Z",
  "user_id": "uuid",
  "action": "position_create_failed",
  "error": "Validation error: Symbol too long",
  "data": {
    "symbol": "TOOLONGSYMBOL"
  }
}
```

---

## Open Questions & Decisions Needed

### Decision Matrix

| # | Question | Options | Recommended | Your Choice |
|---|----------|---------|-------------|-------------|
| 1 | Editable fields | Symbol / No symbol | **No symbol** (breaks history) | _______ |
| 2 | Editable fields | Investment class / No | **No** (breaks analytics) | _______ |
| 3 | Import/Export | Phase 1 / Phase 2 | **Phase 2** (get CRUD working first) | _______ |
| 4 | Page name | "Manage Positions" / "Positions" | **"Manage Positions"** (clearer intent) | _______ |
| 5 | Layout | Split view / Modal | **Split view** (power users) | _______ |
| 6 | Real-time sync | WebSocket / Poll / None | **None** (simplest for MVP) | _______ |
| 7 | Historical edit | Immutable / Recalculate | **Immutable** (audit trail) | _______ |
| 8 | Recalculation | Auto / Manual / Hybrid | **Hybrid** (auto single, manual bulk) | _______ |
| 9 | Duplicate symbol | Allow / Prevent | **Allow** (different times/types) | _______ |
| 10 | Delete verb | "Delete" / "Archive" | **"Archive"** (communicates preservation) | _______ |

### Critical Path Decisions (Need Answer Before Coding)

**Must Decide Now:**
1. [ ] Which fields are editable? (symbol, quantity, avg_cost, type, class)
2. [ ] Include CSV import/export in Phase 1 or defer?
3. [ ] Split view or modal-based form?

**Can Decide Later:**
4. [ ] Real-time sync strategy
5. [ ] Recalculation UX details
6. [ ] Mobile layout approach

---

## Success Criteria

### MVP Success (Phase 1)
- [ ] Users can create positions through UI
- [ ] Users can edit position quantity, avg_cost, type
- [ ] Users can delete positions (soft delete)
- [ ] All mutations have optimistic updates
- [ ] Form validation prevents invalid data
- [ ] Authorization prevents unauthorized modifications
- [ ] Historical data preserved on delete
- [ ] Batch recalculation triggered appropriately

### Full Feature Success (Phase 2+)
- [ ] All MVP criteria met
- [ ] Bulk operations (multi-select delete)
- [ ] CSV import with preview
- [ ] CSV export functionality
- [ ] Real-time recalculation status
- [ ] Mobile-responsive layout
- [ ] Comprehensive error handling
- [ ] Analytics dashboard integration

### Production Readiness
- [ ] 95% test coverage (unit + integration)
- [ ] Load tested with 1000+ positions
- [ ] Error monitoring in place
- [ ] User documentation complete
- [ ] API documentation updated
- [ ] Security audit passed
- [ ] Performance benchmarks met (<500ms API response)

---

## Risk Mitigation

### High Risk: Data Integrity

**Risk:** User deletes position, loses historical data

**Mitigation:**
- ✅ Soft delete by default
- ✅ Clear "Archive" language in UI
- ✅ Show what will be preserved in confirmation
- ✅ Admin panel to restore archived positions (future)

### Medium Risk: Analytics Stale

**Risk:** User adds position, analytics not updated, user confused

**Mitigation:**
- ✅ Hybrid recalculation (auto for single, manual for bulk)
- ✅ "Recalculation needed" badge
- ✅ Estimated completion time shown
- ✅ Real-time progress indicator

### Medium Risk: Form Validation Complexity

**Risk:** Position type doesn't match investment class, breaks analytics

**Mitigation:**
- ✅ Client-side validation with clear error messages
- ✅ Server-side validation as backup
- ✅ Conditional type dropdown (OPTIONS → show only LC/LP/SC/SP)
- ✅ Visual examples in form

### Low Risk: Optimistic Update Failures

**Risk:** Optimistic update succeeds, API fails, user sees wrong state

**Mitigation:**
- ✅ Rollback on error
- ✅ Clear error toast
- ✅ Retry mechanism
- ✅ Temporary position ID vs real ID tracking

---

## Documentation Updates Required

### Files to Update

1. **`backend/CLAUDE.md`**
   - Add position CRUD endpoints to API list
   - Document soft delete strategy
   - Update batch orchestrator section

2. **`backend/_docs/reference/API_REFERENCE_V1.4.7.md`** (new version)
   - Document 7 new endpoints
   - Add request/response examples
   - Add error codes

3. **`frontend/CLAUDE.md`**
   - Add new "Manage Positions" page to navigation list
   - Document `usePositionManagement` hook
   - Update service layer section

4. **`frontend/_docs/requirements/README.md`**
   - Add Phase 9: Position Management
   - Link to implementation guide

5. **`frontend/_docs/requirements/09-PositionManagement-Implementation.md`** (new)
   - Step-by-step implementation guide
   - Component architecture
   - Service usage examples

6. **`frontend/_docs/project-structure.md`**
   - Add new components
   - Add new hooks
   - Add new page

---

## Appendix: Wire frames

### Desktop Layout: Split View

```
┌────────────────────────────────────────────────────────────────┐
│ SigmaSight                                [User Menu ▾]         │
├────────────────────────────────────────────────────────────────┤
│ Manage Positions                [Add Position] [Import CSV]    │
├─────────────────────────┬──────────────────────────────────────┤
│ POSITION LIST (60%)     │ POSITION FORM (40%)                  │
│                         │                                      │
│ Filters:                │ ┌──────────────────────────────────┐ │
│ [All Classes ▾] [🔍]    │ │ Add New Position                 │ │
│                         │ ├──────────────────────────────────┤ │
│ ☐ Symbol  Qty    Cost   │ │ Symbol *                         │ │
│ ☐ AAPL    100  $150.00  │ │ [AAPL_______________]            │ │
│ ☐ MSFT     50  $320.00  │ │                                  │ │
│ ☐ GOOGL    30  $145.00  │ │ Quantity *                       │ │
│ ☐ TSLA     25  $250.00  │ │ [100_________________]           │ │
│ ☐ NVDA     40  $450.00  │ │                                  │ │
│                         │ │ Avg Cost *                       │ │
│ Showing 5 of 5          │ │ [$150.00_____________]           │ │
│                         │ │                                  │ │
│ [2 selected]            │ │ Position Type *                  │ │
│ [Bulk Delete]           │ │ [LONG ▾]                         │ │
│                         │ │                                  │ │
│                         │ │ Investment Class *               │ │
│                         │ │ [PUBLIC ▾]                       │ │
│                         │ │                                  │ │
│                         │ │ [Cancel] [Add Position]          │ │
│                         │ └──────────────────────────────────┘ │
│                         │                                      │
│                         │ Recently Added:                      │
│                         │ • NVDA - 40 @ $450 (2 min ago)      │
│                         │ • AMZN - 15 @ $175 (1 hour ago)     │
└─────────────────────────┴──────────────────────────────────────┘
```

### Mobile Layout: Stacked View

```
┌─────────────────────────┐
│ ☰  Manage Positions  👤 │
├─────────────────────────┤
│                         │
│ [+] Add Position        │
│                         │
│ [Search positions...]   │
│ [All Classes ▾]         │
│                         │
│ ┌─────────────────────┐ │
│ │ AAPL                │ │
│ │ 100 shares          │ │
│ │ $150.00 avg         │ │
│ │ [Edit] [Delete]     │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ MSFT                │ │
│ │ 50 shares           │ │
│ │ $320.00 avg         │ │
│ │ [Edit] [Delete]     │ │
│ └─────────────────────┘ │
│                         │
│ [Load More...]          │
└─────────────────────────┘
```

---

## Appendix: API Specifications

### POST /api/v1/positions

**Request:**
```json
{
  "portfolio_id": "uuid",
  "symbol": "AAPL",
  "quantity": 100,
  "avg_cost": 150.00,
  "position_type": "LONG",
  "investment_class": "PUBLIC"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "portfolio_id": "uuid",
  "symbol": "AAPL",
  "quantity": 100,
  "avg_cost": 150.00,
  "position_type": "LONG",
  "investment_class": "PUBLIC",
  "created_at": "2025-11-03T12:00:00Z",
  "updated_at": "2025-11-03T12:00:00Z",
  "deleted_at": null
}
```

**Errors:**
- `400` - Validation error
- `403` - Not authorized
- `409` - Duplicate position

### PUT /api/v1/positions/{id}

**Request:**
```json
{
  "quantity": 120,
  "avg_cost": 145.00,
  "position_type": "LONG"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "symbol": "AAPL",
  "quantity": 120,
  "avg_cost": 145.00,
  "position_type": "LONG",
  "updated_at": "2025-11-03T12:05:00Z"
}
```

### DELETE /api/v1/positions/{id}

**Response (200 OK):**
```json
{
  "deleted": true,
  "position_id": "uuid",
  "symbol": "AAPL",
  "preserved_snapshots": 90,
  "preserved_target_price": true,
  "deleted_at": "2025-11-03T12:10:00Z"
}
```

---

**Document End**

This comprehensive plan provides a complete roadmap for implementing position management functionality. Review the decision matrix above and provide your preferences so we can proceed to implementation.
