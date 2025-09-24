# Portfolio Position Tagging System - Implementation Plan

**Date**: September 23, 2025
**Feature**: User-defined tags for portfolio positions
**Scope**: Database schema, API endpoints, business logic, and UI considerations

---

## Executive Summary

This plan outlines the implementation of a tagging system that allows users to organize and categorize positions within their portfolios. Each portfolio can have up to 10 custom tags, and each position can be assigned multiple tags to enable flexible portfolio views and analysis.

---

## Phase 1: Database Schema Design

### New Tables Required

#### 1. `portfolio_tags` Table
```sql
-- Stores tag definitions at the portfolio level
portfolio_tags:
  - id (UUID, PK)
  - portfolio_id (UUID, FK -> portfolios.id, NOT NULL)
  - name (VARCHAR(50), NOT NULL)
  - color (VARCHAR(7)) -- Hex color code for UI display
  - description (TEXT) -- Optional tag description
  - display_order (INTEGER) -- For consistent UI ordering
  - created_by (UUID, FK -> users.id)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

Constraints:
  - UNIQUE(portfolio_id, name) -- No duplicate tag names per portfolio
  - CHECK(color ~ '^#[0-9A-Fa-f]{6}$') -- Valid hex color
Indexes:
  - portfolio_id
  - (portfolio_id, display_order)
```

#### 2. `position_tags` Table (Junction Table)
```sql
-- Many-to-many relationship between positions and tags
position_tags:
  - id (UUID, PK)
  - position_id (UUID, FK -> positions.id, NOT NULL)
  - tag_id (UUID, FK -> portfolio_tags.id, NOT NULL)
  - created_by (UUID, FK -> users.id)
  - created_at (TIMESTAMP)

Constraints:
  - UNIQUE(position_id, tag_id) -- Prevent duplicate assignments
Indexes:
  - position_id
  - tag_id
  - (position_id, tag_id)
```

### Database Migrations
- Create Alembic migration for new tables
- Add cascade delete rules (when tag deleted, remove all position associations)
- Add database trigger to enforce 10-tag-per-portfolio limit

---

## Phase 2: API Endpoints Design

### Tag Management Endpoints

#### Portfolio Tag CRUD Operations
```
POST   /api/v1/tags/{portfolio_id}                    - Create new tag
GET    /api/v1/tags/{portfolio_id}                    - List all portfolio tags
GET    /api/v1/tags/{portfolio_id}/{tag_id}           - Get specific tag details
PUT    /api/v1/tags/{portfolio_id}/{tag_id}           - Update tag (name, color, description)
DELETE /api/v1/tags/{portfolio_id}/{tag_id}           - Delete tag (cascade to positions)
```

#### Position Tag Assignment
```
POST   /api/v1/tags/positions/{position_id}/assign    - Assign tags to position
DELETE /api/v1/tags/positions/{position_id}/remove    - Remove tags from position
GET    /api/v1/tags/positions/{position_id}           - Get all tags for a position
PUT    /api/v1/tags/positions/{position_id}/bulk      - Bulk update position tags
```

#### Tag-Based Queries
```
GET    /api/v1/data/portfolio/{id}/positions?tags={tag_ids}     - Filter positions by tags
GET    /api/v1/tags/{portfolio_id}/statistics                   - Tag usage statistics
GET    /api/v1/analytics/portfolio/{id}/by-tag                  - Analytics grouped by tag
POST   /api/v1/tags/{portfolio_id}/bulk-assign                  - Bulk tag assignment
```

### Request/Response Schemas

#### Tag Creation Request
```json
{
  "name": "Tech Stocks",
  "color": "#4A90E2",
  "description": "Technology sector positions"
}
```

#### Tag Assignment Request
```json
{
  "tag_ids": ["uuid1", "uuid2", "uuid3"]
}
```

#### Enhanced Position Response (with tags)
```json
{
  "id": "position_uuid",
  "symbol": "AAPL",
  "quantity": 100,
  "tags": [
    {
      "id": "tag_uuid",
      "name": "Tech Stocks",
      "color": "#4A90E2"
    }
  ]
}
```

---

## Phase 3: Business Logic Implementation

### Core Services Required

#### 1. `TagService` Class
- **Responsibilities**:
  - Tag CRUD operations
  - Enforce 10-tag limit per portfolio
  - Validate tag names (no special characters, length limits)
  - Handle color defaults if not provided
  - Ensure tag ownership matches portfolio ownership

#### 2. `PositionTagService` Class
- **Responsibilities**:
  - Assign/remove tags from positions
  - Bulk tag operations
  - Validate position belongs to same portfolio as tag
  - Generate tag-based analytics

### Business Rules

1. **Tag Limits**:
   - Maximum 10 tags per portfolio (enforced at DB and API level)
   - Tag names: 1-50 characters
   - No duplicate tag names within same portfolio

2. **Tag Naming**:
   - Alphanumeric + spaces only
   - Case-insensitive uniqueness check
   - Reserved names: "All", "Untagged", "System"

3. **Default Tags** (Optional):
   - Consider pre-populating common tags: "Core", "Satellite", "High Risk", "Income"
   - User can delete/modify defaults

4. **Tag Colors**:
   - Provide 10 default color options
   - Allow custom hex colors
   - Ensure contrast for accessibility

5. **Cascade Rules**:
   - Deleting tag removes all position associations
   - Deleting position removes all tag associations
   - Deleting portfolio deletes all tags

---

## Phase 4: Integration Points

### Enhanced Existing Endpoints

#### 1. Portfolio Complete Endpoint
```python
GET /api/v1/data/portfolio/{id}/complete

# Add to response:
"tags": [
  {
    "id": "uuid",
    "name": "Tech Stocks",
    "color": "#4A90E2",
    "position_count": 5,
    "total_value": 150000.00,
    "percentage_of_portfolio": 25.5
  }
]
```

#### 2. Position Details Endpoint
```python
GET /api/v1/data/positions/details

# Add tag information to each position
"positions": [
  {
    "existing_fields": "...",
    "tags": ["tag_id1", "tag_id2"]
  }
]
```

#### 3. Analytics Enhancements
- Add tag-based grouping to risk metrics
- Calculate returns by tag
- Generate tag-based correlation matrices
- Include tags in portfolio reports

### Batch Processing Integration
- Update portfolio snapshot calculations to include tag summaries
- Add tag-based performance metrics to batch jobs
- Generate tag allocation reports

---

## Phase 5: UI/UX Considerations

### Tag Management Interface
1. **Portfolio Settings Page**:
   - Tag creation/edit modal
   - Color picker with presets
   - Drag-to-reorder functionality
   - Usage count display

2. **Position Management**:
   - Multi-select tag assignment
   - Quick tag filters
   - Bulk operations toolbar

3. **Portfolio Views**:
   - Tag filter pills
   - Group by tag option
   - Tag-based pie charts
   - Color-coded position rows

### User Workflows

#### Workflow 1: Initial Tag Setup
1. User navigates to Portfolio Settings
2. Creates tags with names and colors
3. Optionally adds descriptions
4. System shows suggested tags based on portfolio type

#### Workflow 2: Tag Assignment
1. User selects positions (single or multiple)
2. Opens tag assignment modal
3. Selects applicable tags
4. Confirms assignment

#### Workflow 3: Tag-Based Analysis
1. User applies tag filters on portfolio view
2. Views analytics grouped by tags
3. Exports tag-based reports

---

## Phase 6: Implementation Sequence

### Sprint 1: Database & Core API (Week 1)
1. Create database migrations
2. Implement SQLAlchemy models
3. Create TagService class
4. Implement basic CRUD endpoints
5. Add authentication/authorization

### Sprint 2: Position Integration (Week 2)
1. Implement position-tag assignment endpoints
2. Enhance existing position endpoints
3. Add tag filtering to queries
4. Implement bulk operations

### Sprint 3: Analytics Integration (Week 3)
1. Add tag-based analytics endpoints
2. Integrate with batch processing
3. Update portfolio reports
4. Add tag statistics

### Sprint 4: Testing & Documentation (Week 4)
1. Comprehensive unit tests
2. Integration tests
3. API documentation update
4. Performance testing with max tags/positions

---

## Phase 7: Technical Considerations

### Performance Optimization
1. **Indexing Strategy**:
   - Index on portfolio_id for tag lookups
   - Composite index on position_tags junction table
   - Consider materialized views for tag statistics

2. **Query Optimization**:
   - Use eager loading for tags when fetching positions
   - Implement pagination for tag-filtered queries
   - Cache tag metadata at application level

3. **Scalability**:
   - Monitor performance with maximum tags (10) and positions
   - Consider denormalizing tag counts
   - Implement tag statistics as background job

### Security Considerations
1. **Authorization**:
   - Verify user owns portfolio before tag operations
   - Validate tag belongs to portfolio before assignment
   - Implement rate limiting on bulk operations

2. **Data Validation**:
   - Sanitize tag names to prevent injection
   - Validate color codes
   - Enforce character limits

---

## Phase 8: Migration & Rollback Plan

### Migration Strategy
1. Deploy database changes first (backward compatible)
2. Deploy API with feature flag
3. Enable for select users for testing
4. Gradual rollout to all users
5. Remove feature flag after stability confirmed

### Rollback Plan
1. Feature flag to disable tag endpoints
2. Keep database tables (no data loss)
3. Hide UI elements via frontend flag
4. Fix issues and re-deploy
5. Database rollback only as last resort

---

## Success Metrics

### Technical Metrics
- API response time < 200ms for tag operations
- Support 10 tags × 100 positions without degradation
- Zero data loss during tag operations

### User Adoption Metrics
- % of portfolios using tags
- Average tags per portfolio
- Tag usage in analytics views
- User feedback scores

---

## Risk Assessment

### Technical Risks
1. **Performance degradation** with complex tag queries
   - Mitigation: Proper indexing and query optimization

2. **Data consistency** during bulk operations
   - Mitigation: Transactional operations, validation

3. **UI complexity** with many tags
   - Mitigation: Progressive disclosure, smart defaults

### Business Risks
1. **Low adoption** if feature too complex
   - Mitigation: Simple onboarding, suggested tags

2. **Feature creep** (requests for more than 10 tags)
   - Mitigation: Clear documentation of limits, future roadmap

---

## Future Enhancements (Post-MVP)

1. **Smart Tagging**:
   - AI-suggested tags based on position characteristics
   - Auto-tagging rules based on criteria

2. **Tag Templates**:
   - Pre-defined tag sets for different strategies
   - Industry-standard categorizations

3. **Tag Sharing**:
   - Share tag structures between portfolios
   - Team/organization-level tags

4. **Advanced Analytics**:
   - Tag correlation analysis
   - Tag-based rebalancing suggestions
   - Historical tag performance tracking

5. **Tag Hierarchies**:
   - Parent-child tag relationships
   - Tag categories/groups

---

## Conclusion

This tagging system will provide users with a flexible way to organize and analyze their portfolios. The implementation is designed to be:
- **Scalable**: Handles growth in positions and usage
- **Performant**: Optimized queries and caching
- **User-friendly**: Simple interface with powerful capabilities
- **Extensible**: Foundation for future enhancements

The phased approach ensures we can deliver value incrementally while maintaining system stability.