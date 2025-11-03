# Position Management Feature - Implementation Plan

**Document Version**: 3.0 (FINAL)
**Updated**: November 3, 2025
**Status**: ✅ Planning Complete - All 13 Decisions Finalized - Implementation Starting
**Feature**: Full CRUD operations for portfolio positions with smart features
**Timeline**: 9.5-11.5 days (Week 1: Backend, Week 2: Frontend)

---

## ✅ Confirmed Decisions (ALL 13 QUESTIONS COMPLETE)

### UX Design
- ✅ **Location**: Command Center page enhancement (no separate page)
- ✅ **Organize page**: Will be deprecated in future, ignore for now
- ✅ **Inline editing**: Expandable rows with ">" caret (matches Research page)
- ✅ **Batch add**: Side panel via "Manage Positions" button
- ✅ **No checkboxes**: Side panel handles bulk add, expandable rows handle individual edits
- ✅ **Mobile-first**: Responsive design from day 1 (bottom sheet on mobile, side drawer on desktop)

### Editable Fields
- ✅ **Create (new positions)**: All fields (symbol, quantity, avg_cost, type, class, notes)
- ✅ **Update (existing)**: Quantity, avg_cost, position_type, notes only
- ✅ **Symbol editing**: Only within 5 minutes if no snapshots exist, otherwise delete + recreate
- ✅ **No editing**: Investment class (too risky for analytics)
- ✅ **Position notes**: TEXT column, nullable, editable inline

### Features
- ✅ **Phase 1**: Core CRUD + notes + duplicate detection + symbol validation + tag inheritance
- ✅ **Phase 2**: CSV import/export (deferred)
- ✅ **Soft delete**: Preserve all historical data (snapshots, target prices)
- ✅ **Batch operations**: Bulk add via single API call

### Smart Features
- ✅ **Duplicate detection**: Warn when adding existing symbol, prompt "Add as new lot?"
- ✅ **Tag inheritance**: New lots of existing symbol inherit tags automatically
- ✅ **Symbol validation**: Check market data API before saving to prevent invalid tickers
- ✅ **Quantity reduction**: Smart "Is this a sale?" prompt when user reduces quantity
- ✅ **Reverse Addition**: Hard delete if < 5 minutes, otherwise soft delete with "Sell" language
- ✅ **Multi-lot sales**: Lot-level sells only in Phase 1 (FIFO/LIFO in Phase 2)

### Technical
- ✅ **Recalculation**: Hybrid (auto for single changes, manual for bulk)
- ✅ **Historical snapshots**: Immutable (edits apply going forward only)
- ✅ **Target prices**: Symbol-level (preserved on position soft delete)
- ✅ **Permissions**: Users can only edit their own portfolios
- ✅ **Real-time sync**: Page refresh only (no WebSocket for MVP)
- ✅ **Frontend grouping**: Consolidate multiple lots by symbol in UI, separate in DB
- ✅ **HHI fix**: Aggregate by symbol before calculating concentration

### Action Language
- ✅ **"Sell" not "Delete"**: User-friendly terminology for removing positions
- ✅ **Sale recording**: Capture sale price and date for accounting
- ✅ **Mistake handling**: "Reverse Addition" for < 5 min, "Sell" for older positions

---

## Executive Summary

### What We're Building
Enhancement to the **Command Center page** that enables users to create, edit, and delete positions with full historical data preservation and intuitive inline/batch workflows.

### Current State
- Users can **VIEW** positions on Command Center, Public Positions, Private Positions, and Research pages
- Backend has **NO** create/update/delete endpoints for positions
- Position data is read-only, populated via manual seeding or batch processes

### Target State
- Users can **ADD** positions via side panel (single or batch)
- Users can **EDIT** existing positions inline (expandable rows)
- Users can **DELETE** positions with soft-delete (checkbox multi-select)
- Full audit trail of all position changes
- Zero duplication - all features integrated into existing Command Center page

### Strategic Value
- **User Empowerment**: Self-service portfolio management
- **Data Quality**: Users can correct errors immediately
- **Audit Compliance**: Complete historical record
- **UX Consistency**: Inline patterns match Research page

---

## UX Design (Command Center Enhancement)

### Visual Layout

```
Command Center                          [Manage Positions]
┌────────────────────────────────────────────────────────┐
│ Portfolio Metrics                                      │
│ Net Worth: $1.2M    P&L: +$50K                        │
├────────────────────────────────────────────────────────┤
│ Holdings                                               │
│                                                        │
│ ☐ > AAPL    100 shares   $150.00    +5.2%            │ ← Collapsed
│                                                        │
│ ☐ ∨ MSFT     50 shares   $320.00    -2.1%            │ ← Expanded
│     Quantity: [50____]  Avg Cost: [$320___]  Type: [LONG ▾]
│     [Cancel] [Save Changes] [Delete]                  │
│                                                        │
│ ☐ > TSLA     25 shares   $250.00   +10.3%            │
│                                                        │
│ [2 selected] [Delete Selected]                        │
└────────────────────────────────────────────────────────┘

Side Panel (when "Manage Positions" clicked):
┌────────────────────────┐
│ Add Positions          │
├────────────────────────┤
│ Position 1:            │
│ Symbol: [AAPL____]     │
│ Quantity: [100___]     │
│ Avg Cost: [$150__]     │
│ Type: [LONG ▾]         │
│ Class: [PUBLIC ▾]      │
│                        │
│ [+ Add Another]        │
│                        │
│ [Cancel] [Save All]    │
└────────────────────────┘
```

### Interaction Patterns

#### 1. Add Position(s) - Side Panel Batch Mode

**Trigger:** Click "Manage Positions" button (top-right of Command Center)

**Flow:**
1. Side panel slides in from right
2. User enters position details (symbol, quantity, cost, type, class)
3. Click "+ Add Another" to add more positions (repeatable form)
4. Click "Save All" → Single bulk POST API call
5. Panel closes, positions appear in table with success toast

**API Call:**
```javascript
POST /api/v1/positions/bulk
{
  "portfolio_id": "uuid",
  "positions": [
    {"symbol": "AAPL", "quantity": 100, "avg_cost": 150, "type": "LONG", "class": "PUBLIC"},
    {"symbol": "NVDA", "quantity": 25, "avg_cost": 450, "type": "LONG", "class": "PUBLIC"}
  ]
}
```

#### 2. Edit Position - Inline Expansion

**Trigger:** Click ">" caret to expand row

**Flow:**
1. Row expands to show edit fields
2. User modifies quantity, avg_cost, or type
3. Click "Save Changes" → Single PUT API call
4. Row collapses, shows updated values

**Special Case - Symbol Edit:**
- If position was created < 5 minutes ago AND has no snapshots: Allow symbol edit
- Otherwise: Show message "To change symbol, delete this position and create a new one"

**API Call:**
```javascript
PUT /api/v1/positions/{id}
{
  "quantity": 120,
  "avg_cost": 148,
  "position_type": "LONG"
}
```

#### 3. Delete Position(s) - Soft Delete

**Single Delete:**
1. Expand row → Click "Delete" button
2. Confirmation dialog appears
3. User confirms → Single DELETE API call
4. Position removed from table (soft deleted in database)

**Bulk Delete:**
1. Check boxes next to positions
2. "Delete Selected" button appears
3. Click → Confirmation dialog shows all positions
4. User confirms → Bulk DELETE API call
5. All positions removed from table

**API Calls:**
```javascript
// Single
DELETE /api/v1/positions/{id}

// Bulk
DELETE /api/v1/positions/bulk
{
  "position_ids": ["uuid1", "uuid2", "uuid3"]
}
```

---

## Backend Architecture

### New API Endpoints (6 total)

**Core CRUD:**
```
POST   /api/v1/positions              - Create single position
PUT    /api/v1/positions/{id}         - Update position (quantity, avg_cost, type)
DELETE /api/v1/positions/{id}         - Soft delete position (preserves history)
GET    /api/v1/positions/{id}         - Get single position details
```

**Bulk Operations:**
```
POST   /api/v1/positions/bulk         - Bulk create positions (Phase 1)
DELETE /api/v1/positions/bulk         - Bulk soft delete positions (Phase 1)
```

**Import/Export (Phase 2 - Deferred):**
```
POST   /api/v1/positions/import-csv   - Import from CSV with validation
GET    /api/v1/positions/export-csv   - Export to CSV
```

### Service Layer

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
        - No duplicate symbol in portfolio (allow if different type)

        Post-creation:
        - Trigger market data fetch for symbol
        - Queue for next batch analytics run (if auto-recalc enabled)
        """
        pass

    async def bulk_create_positions(
        self,
        portfolio_id: UUID,
        positions: List[CreatePositionData]
    ) -> List[Position]:
        """
        Bulk create positions in single transaction.

        Returns:
        - List of created positions
        - Rolls back all if any fail
        """
        pass

    async def update_position(
        self,
        position_id: UUID,
        quantity: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        position_type: Optional[PositionType] = None,
        symbol: Optional[str] = None,  # Only if < 5 min old and no snapshots
        allow_symbol_edit: bool = False
    ) -> Position:
        """
        Update position fields.

        Editable fields:
        - quantity (affects portfolio value)
        - avg_cost (affects unrealized P&L)
        - position_type (affects exposure calculations)
        - symbol (ONLY if created < 5 min AND no snapshots)

        Non-editable fields:
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
        """
        Bulk soft delete with transaction safety.

        Returns:
        {
            "deleted": True,
            "count": 3,
            "positions": ["AAPL", "MSFT", "TSLA"]
        }
        """
        pass

    async def can_edit_symbol(
        self,
        position_id: UUID
    ) -> tuple[bool, str]:
        """
        Check if symbol can be edited.

        Returns:
        - (True, "") if < 5 min old and no snapshots
        - (False, "reason") otherwise
        """
        pass
```

### Database Changes

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

    # Helper methods
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def can_edit_symbol(self) -> bool:
        """Check if symbol can be edited (< 5 min old, no snapshots)"""
        age = datetime.utcnow() - self.created_at
        return age.total_seconds() < 300 and len(self.snapshots) == 0

    def soft_delete(self):
        self.deleted_at = func.now()
```

**Migration Required:**
```bash
cd backend
alembic revision -m "add_soft_delete_to_positions"
alembic upgrade head
```

### Cascading Delete Logic

When position is soft-deleted:

| Related Data | Action | Rationale |
|--------------|--------|-----------|
| **PositionSnapshot** | ✅ Preserve (no delete) | Immutable audit trail |
| **TargetPrice** | ✅ Preserve (no delete) | Historical context |
| **PositionTag** | ⚠️ Soft delete (set deleted_at) | Tags no longer relevant |
| **PositionGreeks** | ⚠️ Soft delete | Greeks recalculated for active only |
| **PositionFactorExposure** | ⚠️ Soft delete | Factors recalculated for active only |

**Key Principle:** Historical snapshots are sacred. Everything else follows position lifecycle.

---

## Frontend Architecture

### Component Updates

#### 1. Command Center Page Enhancement

**File:** `app/portfolio/page.tsx` (existing)

**Changes:**
```typescript
'use client'
import { useState } from 'react'
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { PortfolioMetrics } from '@/components/portfolio/PortfolioMetrics'
import { PositionsTableWithCRUD } from '@/components/portfolio/PositionsTableWithCRUD' // NEW
import { AddPositionsSidePanel } from '@/components/portfolio/AddPositionsSidePanel' // NEW
import { Button } from '@/components/ui/button'

export default function CommandCenterPage() {
  const { positions, metrics, loading } = usePortfolioData()
  const [sidePanelOpen, setSidePanelOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1>Command Center</h1>
        <Button onClick={() => setSidePanelOpen(true)}>
          Manage Positions
        </Button>
      </div>

      <PortfolioMetrics metrics={metrics} />

      <PositionsTableWithCRUD
        positions={positions}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />

      <AddPositionsSidePanel
        open={sidePanelOpen}
        onClose={() => setSidePanelOpen(false)}
        onSave={handleBulkAdd}
      />
    </div>
  )
}
```

#### 2. New Component: PositionsTableWithCRUD

**File:** `src/components/portfolio/PositionsTableWithCRUD.tsx` (new)

**Features:**
- Checkbox column for multi-select
- ">" caret to expand rows
- Inline edit form when expanded
- Delete confirmation dialog
- Bulk delete button when items selected

```typescript
'use client'
import { useState } from 'react'
import { Position } from '@/lib/types'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

export function PositionsTableWithCRUD({ positions, onUpdate, onDelete }) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [editData, setEditData] = useState({})

  const handleExpand = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id)
  }

  const handleSave = async (id: string) => {
    await onUpdate(id, editData)
    setExpandedRow(null)
  }

  return (
    <div>
      <table>
        <thead>
          <tr>
            <th><Checkbox /></th>
            <th></th>
            <th>Symbol</th>
            <th>Quantity</th>
            <th>Avg Cost</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          {positions.map(position => (
            <>
              <tr key={position.id}>
                <td>
                  <Checkbox
                    checked={selectedIds.includes(position.id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedIds([...selectedIds, position.id])
                      } else {
                        setSelectedIds(selectedIds.filter(id => id !== position.id))
                      }
                    }}
                  />
                </td>
                <td>
                  <button onClick={() => handleExpand(position.id)}>
                    {expandedRow === position.id ? '∨' : '>'}
                  </button>
                </td>
                <td>{position.symbol}</td>
                <td>{position.quantity}</td>
                <td>${position.avg_cost}</td>
                <td className={position.unrealized_pnl > 0 ? 'text-green' : 'text-red'}>
                  {position.unrealized_pnl > 0 ? '+' : ''}{position.unrealized_pnl_pct}%
                </td>
              </tr>

              {expandedRow === position.id && (
                <tr>
                  <td colSpan={6} className="p-4 bg-gray-50">
                    <div className="flex gap-4 items-end">
                      <div>
                        <label>Quantity</label>
                        <Input
                          type="number"
                          defaultValue={position.quantity}
                          onChange={(e) => setEditData({...editData, quantity: e.target.value})}
                        />
                      </div>
                      <div>
                        <label>Avg Cost</label>
                        <Input
                          type="number"
                          defaultValue={position.avg_cost}
                          onChange={(e) => setEditData({...editData, avg_cost: e.target.value})}
                        />
                      </div>
                      <div>
                        <label>Type</label>
                        <Select
                          defaultValue={position.position_type}
                          onValueChange={(value) => setEditData({...editData, position_type: value})}
                        >
                          <option value="LONG">Long</option>
                          <option value="SHORT">Short</option>
                        </Select>
                      </div>
                      <Button variant="ghost" onClick={() => setExpandedRow(null)}>
                        Cancel
                      </Button>
                      <Button onClick={() => handleSave(position.id)}>
                        Save Changes
                      </Button>
                      <Button variant="destructive" onClick={() => onDelete(position.id)}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>

      {selectedIds.length > 0 && (
        <div className="mt-4 flex gap-2 items-center">
          <span>{selectedIds.length} selected</span>
          <Button variant="destructive" onClick={() => onDelete(selectedIds)}>
            Delete Selected
          </Button>
        </div>
      )}
    </div>
  )
}
```

#### 3. New Component: AddPositionsSidePanel

**File:** `src/components/portfolio/AddPositionsSidePanel.tsx` (new)

**Features:**
- Slide-in from right
- Repeatable position form
- "Add Another Position" button
- Bulk save (single API call)

```typescript
'use client'
import { useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

export function AddPositionsSidePanel({ open, onClose, onSave }) {
  const [positions, setPositions] = useState([createEmptyPosition()])

  const addAnother = () => {
    setPositions([...positions, createEmptyPosition()])
  }

  const handleSaveAll = async () => {
    await onSave(positions)
    setPositions([createEmptyPosition()])
    onClose()
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[400px]">
        <SheetHeader>
          <SheetTitle>Add Positions</SheetTitle>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          {positions.map((position, index) => (
            <div key={index} className="space-y-4 p-4 border rounded">
              <h4>Position {index + 1}</h4>

              <div>
                <label>Symbol *</label>
                <Input
                  placeholder="AAPL"
                  value={position.symbol}
                  onChange={(e) => updatePosition(index, 'symbol', e.target.value.toUpperCase())}
                />
              </div>

              <div>
                <label>Quantity *</label>
                <Input
                  type="number"
                  placeholder="100"
                  value={position.quantity}
                  onChange={(e) => updatePosition(index, 'quantity', e.target.value)}
                />
              </div>

              <div>
                <label>Avg Cost *</label>
                <Input
                  type="number"
                  placeholder="150.00"
                  value={position.avg_cost}
                  onChange={(e) => updatePosition(index, 'avg_cost', e.target.value)}
                />
              </div>

              <div>
                <label>Type *</label>
                <Select
                  value={position.position_type}
                  onValueChange={(value) => updatePosition(index, 'position_type', value)}
                >
                  <option value="LONG">Long</option>
                  <option value="SHORT">Short</option>
                  <option value="LC">Long Call</option>
                  <option value="LP">Long Put</option>
                  <option value="SC">Short Call</option>
                  <option value="SP">Short Put</option>
                </Select>
              </div>

              <div>
                <label>Class *</label>
                <Select
                  value={position.investment_class}
                  onValueChange={(value) => updatePosition(index, 'investment_class', value)}
                >
                  <option value="PUBLIC">Public</option>
                  <option value="OPTIONS">Options</option>
                  <option value="PRIVATE">Private</option>
                </Select>
              </div>
            </div>
          ))}

          <Button variant="outline" onClick={addAnother} className="w-full">
            + Add Another Position
          </Button>

          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button onClick={handleSaveAll} className="flex-1">
              Save All ({positions.length})
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function createEmptyPosition() {
  return {
    symbol: '',
    quantity: '',
    avg_cost: '',
    position_type: 'LONG',
    investment_class: 'PUBLIC'
  }
}
```

### Service Layer Updates

**Extend:** `src/services/positionApiService.ts`

```typescript
// src/services/positionApiService.ts

import { apiClient } from './apiClient'
import { Position, CreatePositionData, UpdatePositionData } from '@/lib/types'

const positionApiService = {
  // NEW: Create single position
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

  // NEW: Bulk create positions
  async bulkCreatePositions(
    portfolioId: string,
    positions: CreatePositionData[]
  ): Promise<Position[]> {
    const response = await apiClient.post('/api/v1/positions/bulk', {
      portfolio_id: portfolioId,
      positions
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

### State Management: Zustand Enhancement

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
  addPositions: (positions: Position[]) => void
  updatePosition: (id: string, data: Partial<Position>) => void
  removePosition: (id: string) => void
  removePositions: (ids: string[]) => void
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

      // Optimistic add single
      addPosition: (position) => set((state) => ({
        positions: [...state.positions, position]
      })),

      // Optimistic add multiple
      addPositions: (positions) => set((state) => ({
        positions: [...state.positions, ...positions]
      })),

      // Optimistic update
      updatePosition: (id, data) => set((state) => ({
        positions: state.positions.map(p =>
          p.id === id ? { ...p, ...data } : p
        )
      })),

      // Optimistic remove single
      removePosition: (id) => set((state) => ({
        positions: state.positions.filter(p => p.id !== id)
      })),

      // Optimistic remove multiple
      removePositions: (ids) => set((state) => ({
        positions: state.positions.filter(p => !ids.includes(p.id))
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

### Custom Hook: Position Management

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
    addPositions,
    updatePosition: updatePositionStore,
    removePosition,
    removePositions
  } = usePortfolioStore()

  const [loading, setLoading] = useState(false)

  const bulkCreatePositions = async (positionsData: CreatePositionData[]) => {
    if (!selectedPortfolioId) {
      toast.error('No portfolio selected')
      return
    }

    setLoading(true)
    try {
      // Optimistic update
      const tempPositions = positionsData.map(p => ({ ...p, id: 'temp-' + Math.random() }))
      addPositions(tempPositions)

      // API call
      const newPositions = await positionApiService.bulkCreatePositions(
        selectedPortfolioId,
        positionsData
      )

      // Replace temps with real
      tempPositions.forEach(temp => removePosition(temp.id))
      addPositions(newPositions)

      toast.success(`Added ${newPositions.length} position(s)`)
      return newPositions
    } catch (error) {
      // Rollback on error
      tempPositions.forEach(temp => removePosition(temp.id))
      toast.error(`Failed to add positions: ${error.message}`)
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
      removePositions(ids)

      // API call
      await positionApiService.bulkDeletePositions(ids)

      toast.success(`Deleted ${ids.length} position(s)`)
    } catch (error) {
      // Rollback on error
      addPositions(originals)
      toast.error(`Failed to delete positions: ${error.message}`)
      throw error
    } finally {
      setLoading(false)
    }
  }

  return {
    positions,
    loading,
    bulkCreatePositions,
    updatePosition,
    deletePosition,
    bulkDeletePositions
  }
}
```

---

## Implementation Roadmap

### Phase 1: Core CRUD + Smart Features (9.5-11.5 days)

#### Week 1: Backend Foundation (5-6 days)

**Day 1: Database Schema**
- [ ] Add `deleted_at` column to Position model (DateTime, nullable)
- [ ] Add `notes` column to Position model (TEXT, nullable)
- [ ] Add `can_edit_symbol()` helper method
- [ ] Create Alembic migration
- [ ] Test migration on local database
- [ ] Add index for performance: `idx_position_portfolio_active`

**Day 2: Service Layer - Core CRUD**
- [ ] Create `app/services/position_service.py`
- [ ] Implement `create_position()` with validation
- [ ] Implement `bulk_create_positions()` with transaction
- [ ] Implement `update_position()` with symbol edit logic
- [ ] Implement `soft_delete_position()` with cascading
- [ ] Write unit tests for core CRUD methods

**Day 3: Service Layer - Smart Features**
- [ ] Implement symbol validation (market data API check)
- [ ] Implement duplicate detection logic
- [ ] Implement tag inheritance for duplicate symbols
- [ ] Implement quantity reduction detection
- [ ] Add "Reverse Addition" logic (< 5 min = hard delete)
- [ ] Write unit tests for smart features

**Day 4: API Endpoints**
- [ ] Create `app/api/v1/positions.py` route file
- [ ] Implement POST `/positions` (create single with validation)
- [ ] Implement POST `/positions/bulk` (bulk create with validation)
- [ ] Implement PUT `/positions/{id}` (update with notes support)
- [ ] Implement DELETE `/positions/{id}` (soft/hard delete logic)
- [ ] Add authentication/authorization checks
- [ ] Test with Postman/Swagger

**Day 5: HHI Fix & Analytics**
- [ ] Fix HHI calculation in concentration service (aggregate by symbol)
- [ ] Fix correlation matrix calculation (aggregate by symbol)
- [ ] Test analytics with multi-lot portfolios
- [ ] Verify beta, factors, volatility work correctly (already symbol-level)
- [ ] Update analytics documentation

**Day 6: Integration Testing**
- [ ] Test all endpoints end-to-end
- [ ] Test cascading delete logic
- [ ] Test validation edge cases
- [ ] Test symbol edit restrictions (< 5 min, no snapshots)
- [ ] Test duplicate detection flow
- [ ] Update API documentation
- [ ] Deploy to Railway for staging test

#### Week 2: Frontend Implementation (4.5-5.5 days)

**Day 1: Service & State Layer**
- [ ] Extend `positionApiService.ts` with new methods (create, update, delete)
- [ ] Add position cache to `portfolioStore.ts` (Zustand)
- [ ] Create `usePositionManagement.ts` hook with optimistic updates
- [ ] Add smart features: duplicate detection, symbol validation
- [ ] Test service layer locally

**Day 2: Inline Editing Component**
- [ ] Create `PositionsTableWithCRUD.tsx` component
- [ ] Add ">" caret expansion (no checkbox column needed)
- [ ] Implement inline edit form (quantity, avg_cost, type, notes)
- [ ] Add quantity reduction detection UI ("Is this a sale?")
- [ ] Add delete button with "Sell" vs "Reverse Addition" logic
- [ ] Test inline editing flow

**Day 3: Side Panel Component**
- [ ] Create `AddPositionsSidePanel.tsx` component (responsive)
- [ ] Implement repeatable position form with notes field
- [ ] Add "+ Add Another Position" button
- [ ] Implement duplicate detection warning dialog
- [ ] Implement symbol validation before save
- [ ] Test side panel workflow

**Day 4: Mobile Responsiveness**
- [ ] Convert side panel to bottom sheet on mobile (< 768px)
- [ ] Make expandable rows touch-friendly (larger tap targets)
- [ ] Test on mobile viewport (Chrome DevTools)
- [ ] Adjust spacing and fonts for mobile
- [ ] Test on actual mobile device if possible

**Day 5: Polish & Integration**
- [ ] Implement "Save All" bulk API call with validation
- [ ] Add loading states and spinners
- [ ] Add error handling and toast notifications
- [ ] Implement sale recording dialog (price + date)
- [ ] Update Command Center page to integrate all components
- [ ] Test full workflow end-to-end (desktop + mobile)
- [ ] Update frontend documentation

### Phase 2: CSV Import/Export (2-3 days) - DEFERRED

Will be implemented after Phase 1 is complete and stable.

### Phase 3: Analytics Integration (1-2 days)

**Day 1: Batch Recalculation**
- [ ] Backend: Add recalculation trigger endpoint
- [ ] Frontend: Add "Recalculate" badge after bulk operations
- [ ] Show recalculation status
- [ ] Auto-trigger for single changes
- [ ] Manual trigger for bulk operations

### Phase 4: Polish & Production (1-2 days)

**Day 1: QA & Documentation**
- [ ] End-to-end testing
- [ ] Edge case testing
- [ ] Update user documentation
- [ ] Update `API_REFERENCE.md`
- [ ] Update `CLAUDE.md` files (frontend & backend)

---

## Testing Strategy

### Backend Tests

**Unit Tests:**
```python
# tests/services/test_position_service.py

@pytest.mark.asyncio
async def test_create_position_success():
    position = await position_service.create_position(...)
    assert position.symbol == "AAPL"

@pytest.mark.asyncio
async def test_bulk_create_positions():
    positions = await position_service.bulk_create_positions(
        portfolio_id,
        [
            {"symbol": "AAPL", "quantity": 100, ...},
            {"symbol": "MSFT", "quantity": 50, ...}
        ]
    )
    assert len(positions) == 2

@pytest.mark.asyncio
async def test_symbol_edit_restriction():
    # Create position > 5 min ago
    position = await create_old_position()

    # Try to edit symbol (should fail)
    with pytest.raises(ValidationError):
        await position_service.update_position(
            position.id,
            symbol="MSFT",
            allow_symbol_edit=True
        )

@pytest.mark.asyncio
async def test_soft_delete_preserves_snapshots():
    position = await create_test_position()
    await create_test_snapshots(position.id, count=10)

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

**Integration Tests:**
```python
# tests/api/test_positions_api.py

@pytest.mark.asyncio
async def test_bulk_create_endpoint(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/positions/bulk",
        headers=auth_headers,
        json={
            "portfolio_id": str(test_portfolio_id),
            "positions": [
                {"symbol": "AAPL", "quantity": 100, ...},
                {"symbol": "MSFT", "quantity": 50, ...}
            ]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2

@pytest.mark.asyncio
async def test_bulk_delete_endpoint(client: AsyncClient, auth_headers):
    # Create positions first
    positions = await create_test_positions(count=3)
    ids = [p.id for p in positions]

    # Bulk delete
    response = await client.delete(
        "/api/v1/positions/bulk",
        headers=auth_headers,
        json={"position_ids": ids}
    )
    assert response.status_code == 200

    # Verify all soft deleted
    for position_id in ids:
        position = await db.get(Position, position_id)
        assert position.deleted_at is not None
```

### Frontend Tests

```typescript
// src/hooks/__tests__/usePositionManagement.test.ts

describe('usePositionManagement', () => {
  it('bulk creates positions with optimistic update', async () => {
    const { result } = renderHook(() => usePositionManagement())

    await act(async () => {
      await result.current.bulkCreatePositions([
        { symbol: 'AAPL', quantity: 100, avg_cost: 150, type: 'LONG', class: 'PUBLIC' },
        { symbol: 'MSFT', quantity: 50, avg_cost: 320, type: 'LONG', class: 'PUBLIC' }
      ])
    })

    await waitFor(() => {
      expect(result.current.positions).toHaveLength(2)
    })
  })

  it('rolls back on bulk create error', async () => {
    const { result } = renderHook(() => usePositionManagement())
    const originalCount = result.current.positions.length

    // Mock API error
    jest.spyOn(positionApiService, 'bulkCreatePositions').mockRejectedValue(
      new Error('Network error')
    )

    await act(async () => {
      try {
        await result.current.bulkCreatePositions([...])
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

## Planning Survey Completion

All 13 planning questions have been answered and decisions finalized:

1. ✅ **Editable Fields**: Quantity, avg_cost, position_type, notes (+ symbol if < 5 min)
2. ✅ **CSV Import/Export**: Phase 2 (deferred)
3. ✅ **Page Layout**: Command Center enhancement (no separate page)
4. ✅ **UI Pattern**: Expandable rows + side panel (no checkboxes)
5. ✅ **Real-time Updates**: Page refresh only (Option C)
6. ✅ **Historical Snapshots**: Immutable (Option A)
7. ✅ **Batch Recalculation**: Hybrid (Option C)
8. ✅ **Duplicate Symbols**: Frontend grouping + DB normalization
9. ✅ **Action Language**: "Sell" not "Delete" + smart sale detection
10. ✅ **Multi-Select**: Not needed (side panel for bulk, expandable for individual)
11. ✅ **Mobile Experience**: Responsive-first design (Option C)
12. ✅ **Additional Features**: Notes, duplicate detection, symbol validation, tag inheritance
13. ✅ **Implementation Priority**: Approved (Week 1 backend, Week 2 frontend)

**Status**: ✅ Planning complete - Ready for implementation
**Next Step**: Begin Day 1 (Database Schema) - Backend foundation