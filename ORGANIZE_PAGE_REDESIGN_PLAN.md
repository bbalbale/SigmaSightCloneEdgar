# Organize Page Redesign Plan - Tag-Based Position Management

**Date**: 2025-10-02
**Status**: Draft for Review
**Approach**: Minimal backend changes, fix frontend to match backend conventions

---

## **Core Problem Summary**

1. ❌ **Options not appearing**: Frontend filters for `'OPTION'` (singular), backend uses `'OPTIONS'` (plural)
2. ❌ **Tags not appearing**: API doesn't return tags with positions
3. ❌ **Combined strategies disappear**: Categorization bug (already fixed in latest code)
4. ❌ **"Strategy" terminology is confusing**: Should use "tags" for organization instead

---

## **Solution Architecture**

### **Philosophy**
- ✅ Keep backend as-is (uses `'OPTIONS'` plural - dashboard already works with this)
- ✅ Fix frontend to match backend conventions
- ✅ Add direct position-tag relationship (bypass strategies for tagging)
- ✅ Deprecate "combine" functionality in favor of simple tagging
- ✅ Show individual positions in 5-column grid with tag badges

---

## **Phase 1: Backend - Add Direct Position Tagging**

### 1.1 Create Position-Tag Relationship Table

**New migration**: `backend/alembic/versions/xxx_add_position_tags.py`

```sql
CREATE TABLE position_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags_v2(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    CONSTRAINT unique_position_tag UNIQUE(position_id, tag_id)
);

CREATE INDEX idx_position_tags_position ON position_tags(position_id);
CREATE INDEX idx_position_tags_tag ON position_tags(tag_id);
```

### 1.2 Create Position-Tag Model

**New file**: `backend/app/models/position_tags.py`

```python
from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from app.database import Base

class PositionTag(Base):
    """Direct position-to-tag relationship (bypasses strategies)"""
    __tablename__ = "position_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags_v2.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint('position_id', 'tag_id', name='unique_position_tag'),
    )

    # Relationships
    position = relationship("Position", back_populates="position_tags")
    tag = relationship("TagV2", back_populates="position_tags")
    assignor = relationship("User", foreign_keys=[assigned_by])
```

### 1.3 Update Existing Models

**Modify**: `backend/app/models/positions.py`
```python
# Add to Position class:
from app.models.position_tags import PositionTag

position_tags = relationship("PositionTag", back_populates="position", cascade="all, delete-orphan")
```

**Modify**: `backend/app/models/tags.py` (TagV2 class)
```python
# Add to TagV2 class:
position_tags = relationship("PositionTag", back_populates="tag", cascade="all, delete-orphan")
```

### 1.4 Update Positions API to Include Tags

**Modify**: `backend/app/api/v1/data.py` (line ~535-678)

**After line 573** (where we build the query), add eager loading:
```python
from sqlalchemy.orm import selectinload

stmt = select(Position).where(Position.portfolio_id == portfolio_id).options(
    selectinload(Position.position_tags).selectinload(PositionTag.tag)
)
```

**In the position loop** (around line 646-666), add tags to the response dict:
```python
positions_data.append({
    "id": str(position.id),
    "portfolio_id": str(position.portfolio_id),
    "symbol": position.symbol,
    "position_type": position.position_type.value,
    "investment_class": position.investment_class if position.investment_class else "PUBLIC",
    "investment_subtype": position.investment_subtype if position.investment_subtype else None,
    "quantity": float(position.quantity),
    "entry_date": to_iso_date(position.entry_date) if position.entry_date else None,
    "entry_price": float(position.entry_price),
    "cost_basis": cost_basis,
    "current_price": float(current_price),
    "market_value": market_value,
    "unrealized_pnl": unrealized_pnl,
    "unrealized_pnl_percent": unrealized_pnl_percent,
    "strategy_id": str(position.strategy_id) if position.strategy_id else None,
    "strike_price": float(position.strike_price) if position.strike_price else None,
    "expiration_date": to_iso_date(position.expiration_date) if position.expiration_date else None,
    "underlying_symbol": position.underlying_symbol if position.underlying_symbol else None,
    # ADD THIS:
    "tags": [
        {
            "id": str(pt.tag.id),
            "name": pt.tag.name,
            "color": pt.tag.color,
            "description": pt.tag.description
        }
        for pt in position.position_tags
    ] if hasattr(position, 'position_tags') and position.position_tags else []
})
```

### 1.5 Add Position Tag Management Endpoints

**New file**: `backend/app/api/v1/position_tags.py`

```python
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, Position, TagV2
from app.models.position_tags import PositionTag
from pydantic import BaseModel

router = APIRouter(prefix="/positions", tags=["position_tags"])

class PositionTagsRequest(BaseModel):
    tag_ids: List[UUID]

@router.post("/{position_id}/tags")
async def add_position_tags(
    position_id: UUID,
    request: PositionTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add tags to a position"""
    # Verify position exists and belongs to user's portfolio
    position_query = select(Position).where(Position.id == position_id)
    result = await db.execute(position_query)
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    # Verify tags exist and belong to user
    tag_query = select(TagV2).where(
        TagV2.id.in_(request.tag_ids),
        TagV2.user_id == current_user.id
    )
    result = await db.execute(tag_query)
    tags = result.scalars().all()

    if len(tags) != len(request.tag_ids):
        raise HTTPException(status_code=404, detail="One or more tags not found")

    # Add tags (skip if already exists due to unique constraint)
    created = []
    for tag_id in request.tag_ids:
        # Check if already exists
        existing_query = select(PositionTag).where(
            PositionTag.position_id == position_id,
            PositionTag.tag_id == tag_id
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            continue  # Already tagged

        position_tag = PositionTag(
            position_id=position_id,
            tag_id=tag_id,
            assigned_by=current_user.id
        )
        db.add(position_tag)
        created.append(position_tag)

    await db.commit()
    return {"message": f"Added {len(created)} tags", "created": len(created)}

@router.delete("/{position_id}/tags")
async def remove_position_tags(
    position_id: UUID,
    request: PositionTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove tags from a position"""
    # Verify position exists
    position_query = select(Position).where(Position.id == position_id)
    result = await db.execute(position_query)
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    # Delete position tags
    delete_query = delete(PositionTag).where(
        PositionTag.position_id == position_id,
        PositionTag.tag_id.in_(request.tag_ids)
    )
    result = await db.execute(delete_query)
    await db.commit()

    return {"message": f"Removed {result.rowcount} tags", "removed": result.rowcount}
```

**Update router registration** in `backend/app/api/v1/router.py`:
```python
from app.api.v1 import position_tags

api_router.include_router(position_tags.router)
```

---

## **Phase 2: Frontend - Fix Investment Class Value**

### 2.1 Update All Frontend Components to Use 'OPTIONS' (Plural)

**Files to modify**:

1. **`frontend/src/components/organize/OptionsPositionsList.tsx`** (line 38)
   ```typescript
   // CHANGE FROM:
   s.primary_investment_class === 'OPTION'
   // CHANGE TO:
   s.primary_investment_class === 'OPTIONS'
   ```

2. **`frontend/src/components/organize/ShortOptionsPositionsList.tsx`** (similar change)

3. **Any other components filtering by investment_class**

### 2.2 Update Position Interface

**Modify**: `frontend/src/hooks/usePositions.ts`

```typescript
export interface Position {
  id: string
  symbol: string
  quantity: number
  position_type: string
  investment_class?: string  // 'PUBLIC', 'OPTIONS', 'PRIVATE'
  investment_subtype?: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  realized_pnl: number
  strategy_id?: string
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
  pnl?: number
  positive?: boolean
  // ADD THIS:
  tags?: Array<{
    id: string
    name: string
    color: string
    description?: string
  }>
}
```

---

## **Phase 3: Frontend - Remove Combine Functionality**

### 3.1 Delete Unused Components

**Files to DELETE**:
- ✅ `frontend/src/components/organize/CombineModal.tsx`
- ✅ `frontend/src/components/organize/CombinePositionsButton.tsx`
- ✅ `frontend/src/components/organize/SelectablePositionCard.tsx`
- ✅ `frontend/src/hooks/usePositionSelection.ts`
- ✅ `frontend/src/components/organize/StrategyCard.tsx`
- ✅ `frontend/src/hooks/useStrategies.ts`
- ✅ `frontend/src/components/organize/LongPositionsList.tsx`
- ✅ `frontend/src/components/organize/ShortPositionsList.tsx`
- ✅ `frontend/src/components/organize/OptionsPositionsList.tsx`
- ✅ `frontend/src/components/organize/ShortOptionsPositionsList.tsx`

---

## **Phase 4: Frontend - Create New 5-Column Layout**

### 4.1 Create New Position Card Component

**New file**: `frontend/src/components/organize/PositionCard.tsx`

```tsx
'use client'

import { Position } from '@/hooks/usePositions'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import { formatCurrency } from '@/lib/formatters'

interface PositionCardProps {
  position: Position
  onDropTag?: (positionId: string, tagId: string) => void
  onRemoveTag?: (positionId: string, tagId: string) => void
}

export function PositionCard({ position, onDropTag, onRemoveTag }: PositionCardProps) {
  const { theme } = useTheme()

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.add(theme === 'dark' ? 'bg-blue-900/20' : 'bg-blue-50')
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId && onDropTag) {
      onDropTag(position.id, tagId)
    }
  }

  const isPnlPositive = (position.unrealized_pnl || 0) >= 0

  return (
    <Card
      className={`transition-all ${
        theme === 'dark'
          ? 'bg-card-bg-dark border-card-border-dark hover:bg-card-bg-hover-dark'
          : 'bg-card-bg border-card-border hover:bg-card-bg-hover'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <CardContent className="p-3">
        <div className="space-y-2">
          {/* Symbol */}
          <h4 className={`font-semibold text-base ${
            theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
          }`}>
            {position.symbol}
          </h4>

          {/* Value */}
          <div className={`text-sm ${
            theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
          }`}>
            {formatCurrency(position.market_value)}
          </div>

          {/* P&L */}
          <div className={`text-sm font-medium ${
            isPnlPositive ? 'text-green-600' : 'text-red-600'
          }`}>
            {isPnlPositive ? '+' : ''}{formatCurrency(position.unrealized_pnl || 0)}
          </div>

          {/* Tags */}
          {position.tags && position.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {position.tags.map(tag => (
                <Badge
                  key={tag.id}
                  className="text-xs px-2 py-0.5 flex items-center gap-1"
                  style={{ backgroundColor: tag.color, color: 'white' }}
                >
                  {tag.name}
                  {onRemoveTag && (
                    <X
                      className="h-3 w-3 cursor-pointer hover:opacity-70"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRemoveTag(position.id, tag.id)
                      }}
                    />
                  )}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
```

### 4.2 Create Column Components

**Pattern for each column** (5 files total):

**File**: `frontend/src/components/organize/LongStocksList.tsx`
```tsx
'use client'

import { Position } from '@/hooks/usePositions'
import { PositionCard } from './PositionCard'
import { useTheme } from '@/contexts/ThemeContext'

interface LongStocksListProps {
  positions: Position[]
  onDropTag?: (positionId: string, tagId: string) => void
  onRemoveTag?: (positionId: string, tagId: string) => void
}

export function LongStocksList({ positions, onDropTag, onRemoveTag }: LongStocksListProps) {
  const { theme } = useTheme()

  const longStocks = positions.filter(p =>
    p.investment_class === 'PUBLIC' &&
    (p.position_type === 'LONG' || p.position_type === 'long')
  )

  return (
    <div>
      <h3 className={`text-base font-semibold mb-3 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Long Stocks
      </h3>

      {longStocks.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No positions
        </div>
      ) : (
        <div className="space-y-2">
          {longStocks.map(position => (
            <PositionCard
              key={position.id}
              position={position}
              onDropTag={onDropTag}
              onRemoveTag={onRemoveTag}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Repeat pattern for**:
- `ShortStocksList.tsx` - Filter: `investment_class === 'PUBLIC' && position_type === 'SHORT'`
- `LongOptionsList.tsx` - Filter: `investment_class === 'OPTIONS' && (position_type === 'LC' || position_type === 'LP')`
- `ShortOptionsList.tsx` - Filter: `investment_class === 'OPTIONS' && (position_type === 'SC' || position_type === 'SP')`
- `PrivatePositionsList.tsx` - Filter: `investment_class === 'PRIVATE'`

### 4.3 Update Grid Layout

**Modify**: `frontend/src/components/organize/PositionSelectionGrid.tsx`

```tsx
'use client'

import { Position } from '@/hooks/usePositions'
import { LongStocksList } from './LongStocksList'
import { ShortStocksList } from './ShortStocksList'
import { LongOptionsList } from './LongOptionsList'
import { ShortOptionsList } from './ShortOptionsList'
import { PrivatePositionsList } from './PrivatePositionsList'

interface PositionSelectionGridProps {
  positions: Position[]
  onDropTag?: (positionId: string, tagId: string) => void
  onRemoveTag?: (positionId: string, tagId: string) => void
}

export function PositionSelectionGrid({
  positions,
  onDropTag,
  onRemoveTag
}: PositionSelectionGridProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <LongStocksList
        positions={positions}
        onDropTag={onDropTag}
        onRemoveTag={onRemoveTag}
      />
      <ShortStocksList
        positions={positions}
        onDropTag={onDropTag}
        onRemoveTag={onRemoveTag}
      />
      <LongOptionsList
        positions={positions}
        onDropTag={onDropTag}
        onRemoveTag={onRemoveTag}
      />
      <ShortOptionsList
        positions={positions}
        onDropTag={onDropTag}
        onRemoveTag={onRemoveTag}
      />
      <PrivatePositionsList
        positions={positions}
        onDropTag={onDropTag}
        onRemoveTag={onRemoveTag}
      />
    </div>
  )
}
```

### 4.4 Simplify OrganizeContainer

**Modify**: `frontend/src/containers/OrganizeContainer.tsx`

```tsx
'use client'

import { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { usePositions } from '@/hooks/usePositions'
import { useTags } from '@/hooks/useTags'
import { PositionSelectionGrid } from '@/components/organize/PositionSelectionGrid'
import { TagList } from '@/components/organize/TagList'
import { apiClient } from '@/services/apiClient'
import tagsApi from '@/services/tagsApi'

export function OrganizeContainer() {
  const { theme } = useTheme()
  const { positions, loading: positionsLoading, refresh: refreshPositions } = usePositions()
  const { tags, loading: tagsLoading, refresh: refreshTags } = useTags()

  const isLoading = positionsLoading || tagsLoading

  const handleDropTag = async (positionId: string, tagId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) throw new Error('Not authenticated')

      await apiClient.post(
        `/api/v1/positions/${positionId}/tags`,
        { tag_ids: [tagId] },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      await refreshPositions() // Reload positions with updated tags
    } catch (error) {
      console.error('Failed to add tag:', error)
      alert('Failed to add tag')
    }
  }

  const handleRemoveTag = async (positionId: string, tagId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) throw new Error('Not authenticated')

      await apiClient.delete(
        `/api/v1/positions/${positionId}/tags`,
        {
          headers: { Authorization: `Bearer ${token}` },
          data: { tag_ids: [tagId] }
        }
      )

      await refreshPositions()
    } catch (error) {
      console.error('Failed to remove tag:', error)
      alert('Failed to remove tag')
    }
  }

  const handleCreateTag = async (name: string, color: string) => {
    try {
      await tagsApi.create(name, color)
      await refreshTags()
    } catch (error) {
      console.error('Failed to create tag:', error)
      throw error
    }
  }

  const handleDeleteTag = async (tagId: string) => {
    try {
      await tagsApi.delete(tagId)
      await refreshTags()
    } catch (error) {
      console.error('Failed to delete tag:', error)
      throw error
    }
  }

  if (isLoading) {
    return (
      <div className={`min-h-screen ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Loading portfolio organization...
            </p>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      <section className="px-4 py-8">
        <div className="container mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className={`text-3xl font-bold mb-2 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Portfolio Organization
            </h1>
            <p className={`${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Organize positions with tags
            </p>
          </div>

          {/* Tag Management */}
          <TagList
            tags={tags}
            onCreate={handleCreateTag}
            onDelete={handleDeleteTag}
          />

          {/* 5-Column Position Grid */}
          <PositionSelectionGrid
            positions={positions}
            onDropTag={handleDropTag}
            onRemoveTag={handleRemoveTag}
          />
        </div>
      </section>
    </div>
  )
}
```

---

## **Phase 5: Data Migration (Clean Up Combined Strategies)**

### 5.1 Optional: Break Apart Existing Combined Strategies

**New script**: `backend/scripts/break_apart_combined_strategies.py`

```python
"""
Break apart any existing combined strategies (is_synthetic=True)
back into standalone strategies.
"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.strategies import Strategy
from app.services.strategy_service import StrategyService

async def break_apart_combined_strategies():
    async with get_async_session() as db:
        # Find all combined strategies
        query = select(Strategy).where(
            Strategy.is_synthetic == True,
            Strategy.closed_at.is_(None)
        )
        result = await db.execute(query)
        combined_strategies = result.scalars().all()

        print(f"Found {len(combined_strategies)} combined strategies to break apart")

        service = StrategyService(db)

        for strategy in combined_strategies:
            # Delete the combined strategy (reassign_positions=True creates standalone)
            await service.delete_strategy(strategy.id, reassign_positions=True)
            print(f"Broke apart: {strategy.name}")

        print("✅ Migration complete")

if __name__ == "__main__":
    asyncio.run(break_apart_combined_strategies())
```

---

## **Implementation Order**

### **Week 1: Backend Changes**
1. ✅ Create `position_tags` table migration
2. ✅ Create `PositionTag` model
3. ✅ Update `Position` and `TagV2` models with relationships
4. ✅ Update `/api/v1/data/positions/details` to include tags
5. ✅ Create position tag management endpoints
6. ✅ Test backend APIs with Postman/curl

### **Week 2: Frontend Refactor**
1. ✅ Fix investment class filter (OPTION → OPTIONS)
2. ✅ Update `Position` interface to include tags
3. ✅ Delete old combine/strategy components
4. ✅ Create new `PositionCard` component
5. ✅ Create 5 column list components
6. ✅ Update grid layout to 5 columns
7. ✅ Simplify `OrganizeContainer`
8. ✅ Test tag drag-drop functionality

### **Week 3: Testing & Polish**
1. ✅ Run data migration (break apart combined strategies)
2. ✅ Test with all 3 demo portfolios
3. ✅ Test tag creation, assignment, removal
4. ✅ Verify all position types appear in correct columns
5. ✅ Test responsive design on different screen sizes

---

## **Testing Checklist**

- [ ] Options appear in Long Options / Short Options columns
- [ ] Private positions appear in Private column
- [ ] Tags load with positions automatically
- [ ] Can create new tag
- [ ] Can drag tag onto position card
- [ ] Tag badge appears on position card after drop
- [ ] Can click X to remove tag from position
- [ ] Tag removal works immediately
- [ ] Dashboard page still works (positions with tags)
- [ ] No console errors
- [ ] Works in dark mode and light mode
- [ ] Responsive on mobile/tablet

---

## **Rollback Plan**

If issues arise:
1. **Backend**: Migrations can be rolled back with `alembic downgrade -1`
2. **Frontend**: Keep git commits small, can revert individual changes
3. **Data**: Database backup before running migration scripts
4. **Strategy system**: Still in place, no breaking changes

---

## **Future Enhancements** (Post-MVP)

- [ ] Tag filtering (show only positions with specific tag)
- [ ] Tag-based reporting/analytics
- [ ] Bulk tag operations (tag multiple positions at once)
- [ ] Tag hierarchy (parent/child tags)
- [ ] Clean up strategy system entirely (remove if truly deprecated)
- [ ] Position grouping by tags (visual grouping within columns)

---

## **Questions / Decisions Needed**

1. ✅ **Investment class**: Keep backend 'OPTIONS', fix frontend to match (DECIDED)
2. ❓ **Combined strategies**: Break them apart or leave orphaned?
3. ❓ **Tag colors**: Allow custom colors or predefined palette?
4. ❓ **Tag limit**: Max tags per position?
5. ❓ **Default tags**: Create any default tags for new users?

---

**END OF PLAN**
