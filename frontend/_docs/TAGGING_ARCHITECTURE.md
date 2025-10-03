# Tagging System Architecture Guide

**Last Updated**: October 3, 2025
**Status**: Production - Position Tagging System (Preferred)

---

## Executive Summary

The SigmaSight tagging system allows users to organize positions with custom tags. **This guide clarifies that our 3-file architecture is intentional and correct**, not technical debt from "different developers."

**Key Points**:
- ✅ **Position tagging** is the PREFERRED method (direct position-to-tag relationships)
- ⚠️ **Strategy tagging** is DEPRECATED (kept for backward compatibility)
- 📁 **3-file structure** is standard separation of concerns (API layer, service layer, data model)

---

## Architecture Overview

### The Three-Tier Structure (Intentional Design)

```
┌─────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                     │
│  ┌────────────────────┐      ┌──────────────────────────┐  │
│  │ position_tags.py   │      │     tags.py              │  │
│  │                    │      │                          │  │
│  │ Position-Tag       │      │ Tag Management           │  │
│  │ Relationships      │      │ + Reverse Lookups        │  │
│  └─────────┬──────────┘      └──────────┬───────────────┘  │
└────────────┼─────────────────────────────┼──────────────────┘
             │                             │
             ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌────────────────────┐      ┌──────────────────────────┐  │
│  │ PositionTagService │      │     TagService           │  │
│  │                    │      │                          │  │
│  │ • assign_tag       │      │ • create_tag             │  │
│  │ • remove_tag       │      │ • update_tag             │  │
│  │ • bulk_assign      │      │ • archive_tag            │  │
│  └─────────┬──────────┘      │ • get_positions_by_tag   │  │
└────────────┼─────────────────┴──────────┬───────────────────┘
             │                            │
             ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA MODEL LAYER                        │
│              ┌──────────────────────────┐                   │
│              │      tags_v2.py          │                   │
│              │                          │                   │
│              │  • TagV2 (main model)    │                   │
│              │  • PositionTag (junction)│                   │
│              │  • StrategyTag (legacy)  │                   │
│              └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**Why Three Files?**
1. **`position_tags.py`** - Handles position-tag relationship operations (assign/remove tags)
2. **`tags.py`** - Handles tag lifecycle (create/update/delete) + reverse lookups
3. **`tags_v2.py`** - Database models and relationships

This is **standard 3-tier architecture**, not redundant code!

---

## System Components

### 1. Position Tagging System (PREFERRED - NEW)

**Endpoints**: `/api/v1/positions/{position_id}/tags`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/positions/{id}/tags` | Add tags to position |
| GET | `/positions/{id}/tags` | Get position's tags |
| DELETE | `/positions/{id}/tags` | Remove tags from position |
| PATCH | `/positions/{id}/tags` | Replace all position tags |

**Service**: `PositionTagService` (app/services/position_tag_service.py)

**Database**: `position_tags` junction table (many-to-many)

**When to Use**:
- ✅ Organizing individual positions
- ✅ New frontend development
- ✅ All new features

### 2. Tag Management System

**Endpoints**: `/api/v1/tags/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/tags/` | Create new tag |
| GET | `/tags/` | List user's tags |
| GET | `/tags/{id}` | Get tag details |
| PATCH | `/tags/{id}` | Update tag |
| POST | `/tags/{id}/archive` | Archive tag |
| POST | `/tags/{id}/restore` | Restore archived tag |
| GET | `/tags/{id}/positions` | **Reverse lookup** - Find positions with this tag |

**Service**: `TagService` (app/services/tag_service.py)

**Database**: `tags_v2` table

**When to Use**:
- ✅ Creating/managing tags
- ✅ Getting all positions with a specific tag (reverse lookup)
- ✅ Tag lifecycle operations

### 3. Strategy Tagging (DEPRECATED - Legacy)

**Endpoints**: `/api/v1/tags/{id}/strategies` (in tags.py)

**Status**: ⚠️ Kept for backward compatibility only

**Migration Path**: Use position tagging instead

---

## Data Flow Diagrams

### Creating and Assigning a Tag (Complete Flow)

```
1. CREATE TAG
   Frontend (TagCreator)
        │
        ├── POST /api/v1/tags/
        │        └── tags.py::create_tag()
        │                 └── TagService.create_tag()
        │                          └── INSERT INTO tags_v2
        ▼
   Tag Created (returns TagItem)

2. ASSIGN TAG TO POSITION
   Frontend (drag-drop)
        │
        ├── POST /api/v1/positions/{id}/tags
        │        └── position_tags.py::assign_tags_to_position()
        │                 └── PositionTagService.bulk_assign_tags()
        │                          └── INSERT INTO position_tags
        ▼
   Position Tagged

3. GET POSITIONS BY TAG (Reverse Lookup)
   Frontend (filter by tag)
        │
        ├── GET /api/v1/tags/{id}/positions
        │        └── tags.py::get_positions_by_tag()
        │                 └── PositionTagService.get_positions_by_tag()
        │                          └── SELECT positions JOIN position_tags
        ▼
   Filtered Position List
```

### Why Reverse Lookup is in tags.py (Not position_tags.py)

**Question**: Why is `/tags/{id}/positions` in the tags router instead of position_tags router?

**Answer**: It's a **reverse lookup pattern**:
- **Position-centric endpoints** (position_tags.py): "What tags does THIS position have?"
- **Tag-centric endpoints** (tags.py): "What positions have THIS tag?"

This is a standard REST API design pattern for many-to-many relationships.

---

## Frontend Integration

### Services Architecture

**File**: `frontend/src/services/tagsApi.ts`

```typescript
// TAG MANAGEMENT (lines 10-62)
class TagsApi {
  async list()           // GET /api/v1/tags/
  async create()         // POST /api/v1/tags/
  async update()         // PATCH /api/v1/tags/{id}
  async delete()         // POST /api/v1/tags/{id}/archive

  // POSITION TAGGING (lines 69-130)
  async getPositionTags()     // GET /api/v1/positions/{id}/tags
  async addPositionTags()     // POST /api/v1/positions/{id}/tags
  async removePositionTags()  // POST /api/v1/positions/{id}/tags/remove
  async getPositionsByTag()   // GET /api/v1/tags/{id}/positions (reverse)
}
```

**This is ONE service with TWO responsibilities** - perfectly aligned with backend architecture!

### React Hooks

**File**: `frontend/src/hooks/useTags.ts`
- Tag lifecycle management (create, update, delete)

**File**: `frontend/src/hooks/usePositionTags.ts`
- Position-tag relationship management (add, remove)

### Organize Page Flow

```typescript
// frontend/src/containers/OrganizeContainer.tsx

1. useTags() → Fetches user's tags from /api/v1/tags/
2. usePortfolioData() → Fetches positions (includes tags array automatically)
3. usePositionTags() → Provides addTags/removeTags functions
4. User drags tag onto position → addTagsToPosition() → POST /api/v1/positions/{id}/tags
```

---

## Database Schema

### Tags Table (tags_v2)

```sql
CREATE TABLE tags_v2 (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(50),
    color VARCHAR(7),  -- Hex color code
    description TEXT,
    display_order INTEGER,
    usage_count INTEGER,
    is_archived BOOLEAN,
    UNIQUE(user_id, name, is_archived)
);
```

### Position-Tag Junction (position_tags) - NEW SYSTEM

```sql
CREATE TABLE position_tags (
    id UUID PRIMARY KEY,
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags_v2(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP,
    assigned_by UUID REFERENCES users(id),
    UNIQUE(position_id, tag_id)
);

CREATE INDEX ix_position_tags_position_id ON position_tags(position_id);
CREATE INDEX ix_position_tags_tag_id ON position_tags(tag_id);
```

### Strategy-Tag Junction (strategy_tags) - DEPRECATED

```sql
-- ⚠️ DEPRECATED - Kept for backward compatibility only
CREATE TABLE strategy_tags (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES strategies(id),
    tag_id UUID REFERENCES tags_v2(id),
    assigned_at TIMESTAMP,
    assigned_by UUID REFERENCES users(id)
);
```

---

## Common Use Cases

### Use Case 1: Create a New Tag

**Frontend**:
```typescript
import tagsApi from '@/services/tagsApi'

await tagsApi.create('High Conviction', '#10B981', 'Core holdings')
```

**Backend Flow**:
1. `POST /api/v1/tags/` → `tags.py::create_tag()`
2. `TagService.create_tag()` validates and creates
3. Returns `TagResponse` object

### Use Case 2: Tag a Position

**Frontend**:
```typescript
import tagsApi from '@/services/tagsApi'

await tagsApi.addPositionTags(positionId, [tagId1, tagId2], false)
```

**Backend Flow**:
1. `POST /api/v1/positions/{id}/tags` → `position_tags.py::assign_tags_to_position()`
2. `PositionTagService.bulk_assign_tags()` creates associations
3. Increments `tag.usage_count`

### Use Case 3: Get All Positions with a Tag (Reverse Lookup)

**Frontend**:
```typescript
import tagsApi from '@/services/tagsApi'

const positions = await tagsApi.getPositionsByTag(tagId)
```

**Backend Flow**:
1. `GET /api/v1/tags/{id}/positions` → `tags.py::get_positions_by_tag()`
2. `PositionTagService.get_positions_by_tag()` joins tables
3. Returns list of positions

### Use Case 4: Filter Organize Page by Tag

**Frontend** (already implemented):
```typescript
// OrganizeContainer.tsx
const filteredPositions = positions.filter(p =>
  p.tags?.some(tag => tag.id === selectedTagId)
)
```

**Backend**: No special endpoint needed - positions already include tags array!

---

## Migration Guide: Strategies → Position Tagging

### Why Deprecate Strategy Tagging?

**Old System** (Deprecated):
```
Position → Strategy → StrategyTag → Tag
(Indirect, complex)
```

**New System** (Preferred):
```
Position → PositionTag → Tag
(Direct, simple)
```

### Migration Steps (For Future Cleanup)

1. **Verify no frontend code uses strategy tagging**
   ```bash
   grep -r "strategiesApi.*tags" frontend/src
   grep -r "/strategies/.*/tags" frontend/src
   ```

2. **Mark strategy endpoints as deprecated** (already done)

3. **Add warning logs** to strategy tag endpoints

4. **Future: Remove strategy tag tables**
   - Drop `strategy_tags` table
   - Remove `StrategyTag` model
   - Remove strategy methods from `TagService`

---

## API Endpoint Reference

### Position Tagging Endpoints (PREFERRED)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/positions/{id}/tags` | `{ tag_ids: [uuid], replace_existing: bool }` | `{ assigned_count: int, tag_ids: [uuid] }` |
| GET | `/positions/{id}/tags` | - | `[{ id, name, color, description }]` |
| DELETE | `/positions/{id}/tags` | `?tag_ids=uuid,uuid` | `{ removed_count: int }` |
| PATCH | `/positions/{id}/tags` | `{ tag_ids: [uuid] }` | `{ assigned_count: int }` |

### Tag Management Endpoints

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/tags/` | `{ name, color?, description? }` | `TagResponse` |
| GET | `/tags/` | `?include_archived=bool` | `{ tags: [TagResponse], total: int }` |
| GET | `/tags/{id}` | - | `TagResponse` |
| PATCH | `/tags/{id}` | `{ name?, color?, description? }` | `TagResponse` |
| POST | `/tags/{id}/archive` | - | `{ message: string }` |
| GET | `/tags/{id}/positions` | `?portfolio_id=uuid` | `{ positions: [PositionSummary] }` |

---

## Troubleshooting

### Issue: Tags not showing on positions

**Check**:
1. Position has tags assigned: `GET /api/v1/positions/{id}/tags`
2. Tag is not archived: `tag.is_archived === false`
3. Frontend is fetching positions correctly: `usePortfolioData()`

### Issue: Can't assign tag to position

**Check**:
1. Tag exists and user owns it
2. Position exists and user has access
3. No existing assignment (unless `replace_existing: true`)
4. Tag is not archived

### Issue: Reverse lookup returns no positions

**Check**:
1. Tag ID is correct
2. Portfolio filter is correct (optional parameter)
3. Positions have the tag assigned
4. Positions are not soft-deleted

---

## Best Practices

### Frontend Development

✅ **DO**:
- Use `tagsApi.addPositionTags()` for position tagging
- Use `tagsApi.getPositionsByTag()` for reverse lookups
- Use `useTags()` hook for tag management
- Use `usePositionTags()` hook for position-tag operations

❌ **DON'T**:
- Don't use strategy tagging endpoints
- Don't bypass the service layer
- Don't create tags and assign in same operation (separate concerns)

### Backend Development

✅ **DO**:
- Use `PositionTagService` for position-tag operations
- Use `TagService` for tag CRUD
- Keep reverse lookups in `tags.py` (tag-centric endpoint)
- Maintain separation of concerns

❌ **DON'T**:
- Don't mix position and tag operations in same service method
- Don't add new strategy tagging features
- Don't move reverse lookup to position_tags.py (breaks REST conventions)

---

## FAQ

### Q: Why do we have 3 different files for tagging?

**A**: It's standard 3-tier architecture:
- **API layer** (`position_tags.py`, `tags.py`) - HTTP endpoints
- **Service layer** (`position_tag_service.py`, `tag_service.py`) - Business logic
- **Data layer** (`tags_v2.py`) - Database models

This is **intentional design**, not technical debt!

### Q: Why is `/tags/{id}/positions` in tags.py instead of position_tags.py?

**A**: It's a **reverse lookup** pattern:
- Position-centric: "Get tags for this position" → position_tags.py
- Tag-centric: "Get positions with this tag" → tags.py

This follows REST API best practices for many-to-many relationships.

### Q: Should I use strategy tagging or position tagging?

**A**: Always use **position tagging**. Strategy tagging is deprecated.

### Q: Can I delete the strategy tagging code?

**A**: Not yet. It's kept for backward compatibility. Verify no frontend code uses it first.

### Q: How do I know which endpoint to use?

**A**: Follow this decision tree:
```
Need to manage tags? → Use /api/v1/tags/
Need to tag positions? → Use /api/v1/positions/{id}/tags
Need to find positions by tag? → Use /api/v1/tags/{id}/positions
```

---

## Related Documentation

- **API Reference**: `frontend/_docs/API_AND_DATABASE_SUMMARY.md`
- **Backend Structure**: `backend/AI_AGENT_REFERENCE.md`
- **Frontend Services**: `frontend/_docs/requirements/07-Services-Reference.md`
- **Database Schema**: See "Database Schema" section above

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| Oct 3, 2025 | Created comprehensive architecture guide | Claude AI |
| Oct 2, 2025 | Position tagging system implemented | Dev Team |
| Sept 2025 | Strategy tagging marked deprecated | Dev Team |

---

**Need Help?** This is the authoritative guide for the tagging system. If something isn't clear, update this document!
