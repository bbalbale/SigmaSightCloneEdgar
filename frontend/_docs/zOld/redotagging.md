# Implementation Plan: Position-Based Tagging System

## Overview
Migrate from strategy-based tagging to direct position tagging, allowing users to tag individual positions for filtering and organization. Strategy tables will remain in database but become orphaned.

## 🎯 Progress Tracker

### ✅ Completed (Backend Infrastructure)
- **Phase 2: Database Schema** - 100% Complete
  - ✅ PositionTag model created
  - ✅ Position & TagV2 models updated with relationships
  - ✅ Alembic migration created and applied
  - ✅ Database table `position_tags` exists with indexes

- **Phase 3: Backend API Layer** - 100% Complete
  - ✅ Pydantic schemas created (position_tag_schemas.py)
  - ✅ PositionTagService created with 7 methods
  - ✅ Position Tag API endpoints created (5 endpoints)
  - ✅ Router registered in main API
  - ✅ GET /api/v1/tags/{id}/positions endpoint added
  - ✅ positions/details endpoint includes tags array (batch fetched to avoid N+1)

- **Phase 4: Data Migration** - 100% Complete
  - ✅ Migration script created (migrate_strategy_tags_to_positions.py)
  - ✅ Migration executed successfully (all strategy tags copied to positions)

### ✅ Completed (Frontend Infrastructure)
- **Phase 5: Frontend Infrastructure** - 100% Complete
  - ✅ Update API config with position tag endpoints
  - ✅ Update tagsApi service with position methods (5 new methods)
  - ✅ Create usePositionTags hook
  - ✅ Update project-structure.md documentation
  - ✅ Update API_AND_DATABASE_SUMMARY.md documentation

### ⏸️ Pending (UI Implementation)
- **Phase 5: Frontend UI** - Not Started
  - ⏳ Update OrganizeContainer to use position tags
  - ⏳ Position card tag display
  - ⏳ Drag-drop tag assignment
  - ⏳ Filter by tags functionality

- **Phase 6: Deprecation & Cleanup** - Not Started
  - ⏳ Add deprecation warnings to strategy APIs

- **Phase 7: Testing & Verification** - Not Started

---

## **PHASE 1: Documentation Updates**

### Update `frontend/_docs/project-structure.md`
- Add section documenting position tagging system
- Update organize page component descriptions to reflect position tagging
- Add note about deprecated strategy system
- Update service layer section to show position tagging endpoints

### Update `frontend/_docs/API_AND_DATABASE_SUMMARY.md`
- Add new "Position Tagging" endpoint section
- Mark strategy endpoints as deprecated
- Update database schema ASCII diagram to show `position_tags` junction table
- Update relationships section to include Position → Tags many-to-many
- Update position details response schema to include `tags` array

---

## **PHASE 2: Database Schema (Backend)**

### **2.1 Create PositionTag Model**
**File**: `backend/app/models/position_tags.py` (new file)

Create junction table model:
```python
class PositionTag(Base):
    __tablename__ = "position_tags"

    id = Column(UUID, primary_key=True, default=uuid4)
    position_id = Column(UUID, ForeignKey("positions.id", ondelete="CASCADE"))
    tag_id = Column(UUID, ForeignKey("tags_v2.id", ondelete="CASCADE"))
    assigned_at = Column(DateTime, server_default=func.now())
    assigned_by = Column(UUID, ForeignKey("users.id"), nullable=True)

    # Relationships
    position = relationship("Position", back_populates="position_tags")
    tag = relationship("TagV2", back_populates="position_tags")
    assignor = relationship("User", foreign_keys=[assigned_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint('position_id', 'tag_id', name='unique_position_tag'),
        Index('ix_position_tags_position_id', 'position_id'),
        Index('ix_position_tags_tag_id', 'tag_id'),
    )
```

### **2.2 Update Existing Models**
**Files to modify**:
- `backend/app/models/positions.py` - Add `position_tags` relationship
- `backend/app/models/tags_v2.py` - Add `position_tags` relationship

### **2.3 Create Alembic Migration**
**File**: `backend/alembic/versions/XXXX_add_position_tags.py` (auto-generated)

Run: `uv run alembic revision --autogenerate -m "add position_tags junction table"`

---

## **PHASE 3: Backend API Layer**

### **3.1 Create PositionTagService**
**File**: `backend/app/services/position_tag_service.py` (new file)

Implement methods:
- `assign_tag_to_position(position_id, tag_id, assigned_by)` - Assign single tag
- `remove_tag_from_position(position_id, tag_id)` - Remove single tag
- `get_tags_for_position(position_id)` - Get all tags for a position
- `get_positions_by_tag(tag_id, portfolio_id)` - Get positions with specific tag
- `bulk_assign_tags(position_id, tag_ids, assigned_by, replace_existing)` - Bulk assign
- `bulk_remove_tags(position_id, tag_ids)` - Bulk remove
- `replace_tags_for_position(position_id, tag_ids, assigned_by)` - Replace all tags

### **3.2 Create Position Tag API Endpoints**
**File**: `backend/app/api/v1/position_tags.py` (new file)

Implement endpoints:
- `POST /api/v1/positions/{id}/tags` - Add tags to position
- `DELETE /api/v1/positions/{id}/tags` - Remove tags from position (query params: tag_ids)
- `GET /api/v1/positions/{id}/tags` - Get tags for position
- `PATCH /api/v1/positions/{id}/tags` - Bulk update position tags
- `GET /api/v1/tags/{id}/positions` - Get positions with tag

### **3.3 Update Positions Details Endpoint**
**File**: `backend/app/api/v1/data.py`

Modify `GET /api/v1/data/positions/details` response to include:
```python
{
    "id": "...",
    "symbol": "AAPL",
    # ... existing fields ...
    "tags": [  # NEW FIELD
        {
            "id": "tag-uuid",
            "name": "growth",
            "color": "#2196F3"
        }
    ]
}
```

### **3.4 Register Router**
**File**: `backend/app/api/v1/router.py`

Add: `router.include_router(position_tags.router, prefix="/positions")`

---

## **PHASE 4: Data Migration Script**

### **4.1 Create Migration Script**
**File**: `backend/scripts/migrate_strategy_tags_to_positions.py` (new file)

Script logic:
1. Get all strategies with tags
2. For each strategy:
   - Get all positions in that strategy
   - Get all tags assigned to the strategy
   - For each position × tag combination:
     - Create position_tag entry
3. Log migration results (X strategies, Y positions, Z tag assignments created)
4. **DO NOT DELETE** strategy or strategy_tag data

Run after deployment: `uv run python scripts/migrate_strategy_tags_to_positions.py`

---

## **PHASE 5: Frontend Updates**

### **5.1 Update Tag Service**
**File**: `frontend/src/services/tagsApi.ts`

Add new methods:
```typescript
async addPositionTags(positionId: string, tagIds: string[]): Promise<void>
async removePositionTags(positionId: string, tagIds: string[]): Promise<void>
async getPositionTags(positionId: string): Promise<TagItem[]>
async getPositionsByTag(tagId: string): Promise<Position[]>
async replacePositionTags(positionId: string, tagIds: string[]): Promise<void>
```

Change `getStrategies()` to `getPositions()` to work with positions instead

### **5.2 Create Position Tags Hook**
**File**: `frontend/src/hooks/usePositionTags.ts` (new file)

Create React hook for:
- Fetching tags for positions
- Adding/removing tags from positions
- Filtering positions by tags
- Tag assignment state management

### **5.3 Update Organize Container**
**File**: `frontend/src/containers/OrganizeContainer.tsx`

Changes:
- Remove strategy-related state and handlers
- Add position tag handlers
- Update tag drop handler to call position tag APIs
- Update tag display to show position tags
- Remove strategy combination modal and logic

### **5.4 Update Position Components**
**Files**:
- `frontend/src/components/positions/OrganizePositionCard.tsx` - Display tags on card
- `frontend/src/components/organize/SelectablePositionCard.tsx` - Update tag drop logic

### **5.5 Update Position Data Hook**
**File**: `frontend/src/hooks/usePortfolioData.ts`

Update to include tags in position data (already returned from updated API)

### **5.6 Mark Strategy APIs as Deprecated**
**File**: `frontend/src/services/strategiesApi.ts`

Add deprecation comments at top:
```typescript
/**
 * @deprecated Strategies are deprecated in favor of position-based tagging.
 * This service remains for legacy compatibility only.
 * Use position tagging via tagsApi instead.
 */
```

---

## **PHASE 6: Deprecation & Cleanup**

### **6.1 Add Deprecation Warnings**
**Backend**: Add deprecation headers to strategy endpoints
```python
@router.post("/strategies/", deprecated=True)
```

**Frontend**: Add console warnings when strategy APIs are called

### **6.2 Remove Strategy UI Components**
Delete or archive:
- `frontend/src/components/strategies/*` - All strategy display components
- `frontend/src/hooks/useStrategies.ts` - Strategy data hook
- `frontend/src/hooks/useStrategyFiltering.ts` - Strategy filtering hook
- Portfolio page "Combination View" toggle
- `frontend/src/components/portfolio/PortfolioStrategiesView.tsx`

### **6.3 Update Navigation/UI**
Remove strategy-related:
- Organize page strategy combination features
- Portfolio page strategy view toggle
- Any strategy-related filter options

---

## **PHASE 7: Testing & Verification**

### **7.1 Backend Testing**
Test endpoints:
- Assign tags to positions
- Remove tags from positions
- Get positions by tag
- Verify tag permissions (user ownership)
- Verify position ownership (portfolio access)

### **7.2 Frontend Testing**
- Tag display on position cards
- Drag-drop tag assignment
- Filter positions by tags
- Tag CRUD operations
- Organize page functionality

### **7.3 Data Migration Verification**
- Run migration script
- Verify all tags migrated correctly
- Verify no data loss
- Check tag counts match

---

## **Files to Create**

### Backend (7 files)
1. `backend/app/models/position_tags.py`
2. `backend/app/services/position_tag_service.py`
3. `backend/app/api/v1/position_tags.py`
4. `backend/alembic/versions/XXXX_add_position_tags.py` (auto-generated)
5. `backend/scripts/migrate_strategy_tags_to_positions.py`
6. `backend/tests/test_position_tags.py` (optional)
7. `backend/app/schemas/position_tag_schemas.py` (Pydantic schemas)

### Frontend (2 files)
1. `frontend/src/hooks/usePositionTags.ts`
2. Documentation updates (2 existing files)

---

## **Files to Modify**

### Backend (5 files)
1. `backend/app/models/positions.py` - Add position_tags relationship
2. `backend/app/models/tags_v2.py` - Add position_tags relationship
3. `backend/app/api/v1/data.py` - Update positions/details response
4. `backend/app/api/v1/router.py` - Register position_tags router
5. `backend/app/api/v1/strategies.py` - Add deprecation markers

### Frontend (6 files)
1. `frontend/src/services/tagsApi.ts` - Add position tagging methods
2. `frontend/src/containers/OrganizeContainer.tsx` - Update to use position tags
3. `frontend/src/hooks/usePortfolioData.ts` - Include tags in position data
4. `frontend/src/components/organize/SelectablePositionCard.tsx` - Update tag logic
5. `frontend/src/services/strategiesApi.ts` - Add deprecation warning
6. `frontend/_docs/project-structure.md` - Document changes
7. `frontend/_docs/API_AND_DATABASE_SUMMARY.md` - Update API docs

---

## **Rollout Strategy**

1. **Deploy backend** with new position tag endpoints (backward compatible)
2. **Run migration script** to copy tag associations
3. **Deploy frontend** with position tagging enabled
4. **Monitor** for 1-2 weeks to ensure stability
5. **Add deprecation warnings** to strategy endpoints
6. **Remove strategy UI** after migration proven successful
7. **Keep strategy tables** in database (orphaned, no cleanup needed per user request)

---

## **Success Criteria**

✅ Users can assign multiple tags to any position
✅ Users can filter positions by tags
✅ Tag drag-drop works on position cards
✅ All existing tags migrated without data loss
✅ Strategy APIs marked deprecated but still functional
✅ Documentation updated
✅ No breaking changes to existing data
