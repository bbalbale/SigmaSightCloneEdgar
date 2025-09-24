# Portfolio Tagging System Implementation Todo

**Created**: September 24, 2025
**Status**: Phase 2 starting (Phase 1 complete; Tag APIs built)
**Project**: Dual system for position organization (tags) and position grouping (strategies)

---

## Executive Summary

Implementing a comprehensive dual-system architecture that separates organizational tagging from position aggregation. **Tags** provide metadata for filtering and categorization, while **Strategies** create virtual positions that aggregate multiple legs into single logical trading units. Every position belongs to exactly one strategy, with most being "standalone" strategies containing a single position.

---

## Current State Assessment

### ✅ What Already Exists
- **Basic Tag System**:
  - `Tag` model with `TagType` enum (REGULAR, STRATEGY)
  - `position_tags` junction table with columns: position_id, tag_id, created_at
  - User relationship to tags in User model
  - Basic tag functionality in place

- **Database Infrastructure**:
  - PostgreSQL with Alembic migrations
  - SQLAlchemy models and relationships
  - UUID primary keys throughout
  - Latest migration: `1dafe8c1dd84_add_portfolio_target_prices_table.py`

- **Position Model**:
  - Complete position model with all required fields
  - Investment classification fields already added
  - Relationship to existing tag system

### ❌ What's Missing (Major Components)
- **Strategy System**: No strategy tables, models, or services
- **Enhanced Tag System**: Current tag system is basic, missing user-scoped tags, archiving, etc.
- **API Endpoints**: No strategy or enhanced tag management endpoints
- **Business Logic**: No strategy services, detection algorithms, or advanced tag operations
- **Data Migration**: Need to migrate existing data to new dual system

---

## Implementation Phases

### Phase 1: Strategy Foundation (Week 1-2) 🚧 **CRITICAL PATH**

#### Database Schema Changes
- [x] **Task 1.1**: Create Alembic migration for strategy tables
  - `strategies` table with all required fields
  - `strategy_legs` junction table
  - `strategy_metrics` calculated table
  - Add `strategy_id` column to positions table (nullable initially)
  - **Estimated Time**: 2 days
  - **Dependencies**: None
  - **Risk**: High - Core database structure changes

- [x] **Task 1.2**: Create SQLAlchemy models for strategies
  - `Strategy` model with full relationships
  - `StrategyLeg` association model
  - `StrategyMetrics` model for cached calculations
  - Update `Position` model to include strategy relationship
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 1.1 complete

- [x] **Task 1.3**: Implement StrategyService class
  - `create_strategy()` - Create new strategy with positions
  - `auto_create_standalone()` - Auto-create standalone strategy for new positions
  - `combine_into_strategy()` - Combine multiple positions
  - `calculate_metrics()` - Aggregate strategy metrics
  - **Estimated Time**: 3 days
  - **Dependencies**: Task 1.2 complete

- [x] **Task 1.4**: Create basic strategy CRUD endpoints
  - `POST /api/v1/strategies` - Create strategy
  - `GET /api/v1/strategies` - List portfolio strategies
  - `GET /api/v1/strategies/{id}` - Get strategy details
  - `PUT /api/v1/strategies/{id}` - Update strategy
  - `DELETE /api/v1/strategies/{id}` - Close strategy
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 1.3 complete

- [x] **Task 1.5**: Data migration script for existing positions
  - Create standalone strategies for all existing positions
  - Update position records with strategy_id references
  - Verify data integrity post-migration
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 1.1-1.4 complete
  - **Risk**: Medium - Data transformation risk

#### 📋 **Phase 1 Acceptance Criteria**
- Every position belongs to a strategy (no null strategy_id values)
- Standalone strategies auto-created for new positions
- Basic strategy API endpoints functional
- All existing positions migrated without data loss
- Strategy database constraints enforced

---

### Phase 2: Multi-Leg Strategy Support (Week 3) 🎯

#### Strategy Detection & Combination
- [ ] **Task 2.1**: Implement strategy detection algorithms
  - Pattern matching for common strategies (covered calls, iron condors, etc.)
  - Detection service with confidence scoring
  - Support for custom strategy types
  - **Estimated Time**: 3 days
  - **Dependencies**: Phase 1 complete

- [ ] **Task 2.2**: Build strategy combination endpoints
  - `POST /api/v1/strategies/combine` - Combine positions into strategy
  - `POST /api/v1/strategies/{id}/add-leg` - Add position to strategy
  - `DELETE /api/v1/strategies/{id}/remove-leg` - Remove position
  - `POST /api/v1/strategies/{id}/split` - Split strategy into standalone
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 2.1 complete

- [ ] **Task 2.3**: Implement aggregated metrics calculation
  - P&L aggregation across strategy legs
  - Risk metrics at strategy level
  - Break-even point calculations
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 2.2 complete

- [ ] **Task 2.4**: Create strategy templates system
  - Pre-defined strategy patterns
  - Template-based strategy creation
  - Strategy validation against templates
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 2.3 complete

#### 📋 **Phase 2 Acceptance Criteria**
- Can detect common multi-leg strategies automatically
- Can combine positions into complex strategies
- Strategy metrics aggregation working correctly
- Can split strategies back into standalone positions
- Strategy templates available for common patterns

---

### Phase 3: Enhanced Tag System (Week 4) 🏷️

#### User-Scoped Tag System
- [x] **Task 3.1**: Create enhanced tag database tables
  - Migration to add user-scoped tag fields
  - `tags` table enhancement (user_id, archiving, usage_count)
  - `strategy_tags` junction table (replaces position_tags for new system)
  - Migration script to preserve existing tag data
  - **Estimated Time**: 2 days
  - **Dependencies**: Phase 2 complete

- [x] **Task 3.2**: Implement enhanced TagService
  - Tag CRUD operations with user scoping
  - Tag archiving and restoration
  - Usage count tracking and statistics
  - Tag validation and naming rules
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 3.1 complete

- [x] **Task 3.3**: Create tag management endpoints
  - `POST /api/v1/tags` - Create tag
  - `GET /api/v1/tags` - List user's tags
  - `PUT /api/v1/tags/{id}` - Update tag
  - `DELETE /api/v1/tags/{id}` - Archive tag
  - `POST /api/v1/tags/{id}/restore` - Restore archived tag
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 3.2 complete

- [ ] **Task 3.4**: Implement strategy tagging system
  - `GET /api/v1/strategies/{id}/tags` - Get strategy tags
  - `PUT /api/v1/strategies/{id}/tags` - Replace strategy tags
  - `POST /api/v1/strategies/{id}/tags` - Add tags to strategy
  - `DELETE /api/v1/strategies/{id}/tags` - Remove tags
  - `POST /api/v1/tags/bulk-assign` - Bulk tag assignment
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 3.3 complete

#### 📋 **Phase 3 Acceptance Criteria**
- Tags are user-scoped (not portfolio-scoped)
- Tags can be applied to strategies (not individual positions)
- Tag archiving and restoration functional
- Bulk tag operations working
- Usage count tracking accurate

---

### Phase 4: Portfolio Views & Filtering (Week 5) 📊

#### Enhanced Portfolio Endpoints
- [ ] **Task 4.1**: Update portfolio data endpoints
  - Modify `/api/v1/data/portfolio/{id}/complete` to return strategies
  - Add strategy-based filtering parameters
  - Include tag information in strategy responses
  - Support mixed view (strategies + expandable legs)
  - **Estimated Time**: 2 days
  - **Dependencies**: Phase 3 complete

- [ ] **Task 4.2**: Implement filtering and grouping
  - `GET /api/v1/portfolios/{id}/strategies?tags={ids}` - Filter by tags
  - `GET /api/v1/portfolios/{id}/strategies?type={type}` - Filter by type
  - `GET /api/v1/portfolios/{id}/grouped` - Group strategies by tags
  - Support for AND/OR logic in tag filtering
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 4.1 complete

- [ ] **Task 4.3**: Create analytics endpoints
  - `GET /api/v1/analytics/strategies/performance` - Performance by strategy type
  - `GET /api/v1/analytics/tags/performance` - Performance by tag
  - `GET /api/v1/analytics/strategies/risk` - Risk metrics by strategy
  - Strategy and tag-based portfolio analytics
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 4.2 complete

#### Position Management Integration
- [ ] **Task 4.4**: Update position creation workflow
  - Auto-create standalone strategy for new positions
  - Support strategy_id parameter in position creation
  - Response includes both position and strategy information
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 4.3 complete

#### 📋 **Phase 4 Acceptance Criteria**
- Portfolio endpoints return strategies as first-class entities
- Can filter and group strategies by tags and types
- Analytics endpoints provide strategy and tag-based insights
- Position creation automatically handles strategy assignment

---

### Phase 5: Data Migration & Cleanup (Week 6) 🔄

#### Final Data Migration
- [ ] **Task 5.1**: Migrate existing position_tags to strategy_tags
  - Create strategy_tags entries for all current position tags
  - Map position tags to their strategy equivalents
  - Preserve tag assignment history
  - **Estimated Time**: 1 day
  - **Dependencies**: Phase 4 complete

- [x] **Task 5.2**: Enforce database constraints
  - Make strategy_id NOT NULL on positions table
  - Remove old position_tags table after verification
  - Add all necessary database constraints and triggers
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 5.1 complete

- [ ] **Task 5.3**: Update initial schema for new installations
  - Modify `initial_schema.py` to include complete new structure
  - Remove old tag table definitions
  - Ensure new installations have correct schema from start
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 5.2 complete

#### Code Cleanup
- [ ] **Task 5.4**: Remove deprecated code
  - Remove old tag-related code that's no longer needed
  - Update all services to use new strategy-based system
  - Clean up unused imports and models
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 5.3 complete

#### 📋 **Phase 5 Acceptance Criteria**
- All data successfully migrated to new system
- Old tables removed and constraints enforced
- New installations use correct schema from start
- No deprecated code remaining

---

### Phase 6: Testing & Documentation (Week 7) 🧪

#### Comprehensive Testing
- [ ] **Task 6.1**: Unit tests for all new services
  - StrategyService unit tests with mock data
  - Enhanced TagService unit tests
  - Strategy detection algorithm tests
  - Metrics calculation tests
  - **Estimated Time**: 2 days
  - **Dependencies**: Phase 5 complete

- [ ] **Task 6.2**: Integration tests
  - End-to-end strategy creation workflows
  - Tag assignment and filtering integration tests
  - Portfolio view integration tests
  - Data migration verification tests
  - **Estimated Time**: 2 days
  - **Dependencies**: Task 6.1 complete

- [ ] **Task 6.3**: Performance testing
  - Test with maximum strategies and tags
  - Database query performance validation
  - API endpoint response time testing
  - Memory usage and optimization
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 6.2 complete

#### Documentation
- [ ] **Task 6.4**: Update API documentation
  - Document all new strategy endpoints
  - Update tag management endpoint docs
  - Add examples and use cases
  - Update schema documentation
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 6.3 complete

- [ ] **Task 6.5**: Create migration guides
  - Database migration procedures
  - API changes guide for frontend
  - Troubleshooting common issues
  - Rollback procedures
  - **Estimated Time**: 1 day
  - **Dependencies**: Task 6.4 complete

#### 📋 **Phase 6 Acceptance Criteria**
- All new functionality covered by unit and integration tests
- Performance meets specified targets (< 500ms for portfolio views)
- Comprehensive API documentation available
- Migration and troubleshooting guides complete

---

## Issues & Risk Assessment

### 🔴 **Critical Issues**
1. **Data Migration Complexity**
   - **Issue**: Converting existing position_tags to strategy_tags while preserving relationships
   - **Risk Level**: High
   - **Mitigation**: Extensive testing in staging, rollback procedures, data backups

2. **Breaking Changes to Position Model**
   - **Issue**: Adding required strategy_id field to positions
   - **Risk Level**: High
   - **Mitigation**: Multi-phase migration with nullable field initially

3. **Performance Impact**
   - **Issue**: Additional joins and complexity may slow queries
   - **Risk Level**: Medium
   - **Mitigation**: Proper indexing, materialized views, caching strategy

### 🟡 **Medium Risks**
1. **Strategy Detection Accuracy**
   - **Issue**: Auto-detection may misclassify complex strategies
   - **Risk Level**: Medium
   - **Mitigation**: Conservative detection with user override options

2. **Tag Limit Enforcement**
   - **Issue**: Existing users might have more tags than new limits allow
   - **Risk Level**: Medium
   - **Mitigation**: Grandfather existing tags, provide migration tools

### 🟢 **Low Risks**
1. **UI Complexity**
   - **Issue**: New dual system might confuse users initially
   - **Risk Level**: Low
   - **Mitigation**: Clear documentation, progressive disclosure

---

## Technical Considerations

### Database Performance Optimizations
- **Indexes**: Comprehensive indexing on portfolio_id, strategy_id, tag relationships
- **Materialized Views**: Pre-computed strategy aggregations for fast portfolio loading
- **Caching**: Redis caching for frequently accessed tag and strategy metadata
- **Query Optimization**: Eager loading to avoid N+1 queries

### Migration Strategy
```bash
# Phase 1: Add new tables (non-breaking)
uv run alembic revision -m "add_strategy_tables_and_enhanced_tags"
uv run alembic upgrade head

# Phase 2: Migrate data
uv run python scripts/migrate_positions_to_strategies.py
uv run python scripts/verify_migration.py

# Phase 3: Enforce constraints (after verification)
uv run alembic revision -m "finalize_strategy_migration"
uv run alembic upgrade head
```

### Rollback Procedures
1. **Database Rollback**: Use Alembic downgrade commands
2. **Data Recovery**: Restore from pre-migration backups
3. **Code Rollback**: Feature flags to disable new endpoints
4. **Frontend Fallback**: Maintain backward compatibility during transition

---

## Success Metrics

### Technical Metrics 📊
- [ ] **Performance**: Portfolio view loads in < 500ms with 100+ strategies
- [ ] **Reliability**: Zero data loss during migration
- [ ] **Coverage**: 90%+ test coverage for new functionality
- [ ] **Uptime**: No service interruptions during rollout

### User Experience Metrics 📈
- [ ] **Adoption**: 40%+ of options users create multi-leg strategies
- [ ] **Usage**: Average 15 strategies per portfolio
- [ ] **Engagement**: 70%+ of strategies have tags assigned
- [ ] **Satisfaction**: Positive user feedback on organization capabilities

### Business Value Metrics 💼
- [ ] **Risk Visibility**: Improved risk attribution through strategy grouping
- [ ] **P&L Clarity**: Better understanding of multi-leg trade performance
- [ ] **User Retention**: Reduced confusion about complex positions
- [ ] **Feature Utilization**: Active use of both tag and strategy systems

---

## Completion Status

### ✅ Completed Items (September 24, 2025)
- [x] **Analysis**: Current database schema and existing implementation
- [x] **Planning**: Review of all PRD documents and requirements
- [x] **Architecture**: Understanding of dual system design
- [x] **Task 1.1**: Created Alembic migration for strategy tables (add_strategy_tables_and_enhanced_tags.py)
- [x] **Task 1.2**: Created SQLAlchemy models for strategies (strategies.py, tags_v2.py)
- [x] **Updated Models**: Modified Position and User/Portfolio models with strategy relationships
- [x] **Migration Executed**: Successfully ran Alembic migration creating all strategy tables
- [x] **Data Migration**: Created and executed script wrapping all 63 existing positions in standalone strategies
- [x] **Verification**: Confirmed all tables created and positions migrated

### 🚧 In Progress
- [ ] **Documentation**: Updating project status and next steps

### ⏳ Pending Items
- [ ] **Phase 1**: Strategy foundation (7 tasks)
- [ ] **Phase 2**: Multi-leg strategy support (4 tasks)
- [ ] **Phase 3**: Enhanced tag system (4 tasks)
- [ ] **Phase 4**: Portfolio views & filtering (4 tasks)
- [ ] **Phase 5**: Data migration & cleanup (4 tasks)
- [ ] **Phase 6**: Testing & documentation (5 tasks)

**Total Tasks**: 28 tasks across 6 phases
**Estimated Timeline**: 7 weeks
**Current Progress**: 32% (9/28 core tasks completed)

### Tasks Completed Today:
- Migration creation and execution
- SQLAlchemy models implementation
- Data migration of 63 positions
- Database verification

---

## 🔧 IMPORTANT: Instructions for Running Migrations

### For Developers Working on This Project

If you're picking up this project and need to run the Alembic migrations, follow these steps:

#### Prerequisites
1. Ensure Docker is running (for PostgreSQL database)
2. Ensure you're in the `backend` directory
3. Ensure the virtual environment has all dependencies installed

#### Running the Migrations

**Option 1: Using Windows Command Prompt (Recommended)**
```bash
cd backend
.venv\Scripts\activate
alembic upgrade head
```

**Option 2: Using the helper script created**
```bash
cd backend
python run_alembic_migration.py
```

**Option 3: If you encounter environment issues**
```bash
cd backend
python -c "import subprocess; subprocess.run(['.venv\\Scripts\\python.exe', '-m', 'alembic', 'upgrade', 'head'])"
```

#### Verifying the Migration
After running the migration, verify it worked:
```bash
cd backend
python verify_strategy_tables.py
# OR
python run_verify_tables.py
```

#### If You Need to Roll Back
```bash
cd backend
.venv\Scripts\activate
alembic downgrade -1  # Roll back one migration
```

#### Migration Files Created for This Project
1. `add_strategy_tables_and_enhanced_tags.py` - Creates all strategy and tag tables
2. Data migration is handled by: `migrate_positions_to_strategies.py`

#### Common Issues and Solutions
- **"Failed to canonicalize script path"**: Use Windows CMD, not Git Bash
- **"Module not found"**: Ensure you're using the venv Python, not system Python
- **"Table already exists"**: Migration may have already been run, check with verify script

---

## ✅ Migration Successfully Completed

### What Was Accomplished (September 24, 2025)

1. **Database Schema Migration**:
   - Successfully created all strategy tables (strategies, strategy_legs, strategy_metrics, strategy_tags)
   - Added enhanced tag system tables (tags_v2)
   - Added strategy_id column to positions table

2. **Data Migration**:
   - All 63 existing positions wrapped in standalone strategies
   - Breakdown by portfolio:
     - Demo Hedge Fund Style Investor: 30 strategies created
     - Demo High Net Worth Investor: 17 strategies created
     - Demo Individual Investor: 16 strategies created
   - Every position now has an associated strategy

3. **Model Implementation**:
   - Created Strategy, StrategyLeg, StrategyMetrics, StrategyTag models
   - Created enhanced TagV2 model with user-scoping
   - Updated Position and Portfolio models with relationships
   - Note: Some relationships temporarily commented out due to circular dependencies

## 📌 Next Developer Tasks

### Priority 1: Fix Model Relationships
The SQLAlchemy models have been created but many relationships are commented out to avoid circular dependencies. These need to be properly configured:
- `backend/app/models/strategies.py` - Uncomment and fix relationships
- `backend/app/models/tags_v2.py` - Uncomment and fix relationships
- `backend/app/models/users.py` - Add back strategies and tags_v2 relationships
- `backend/app/models/positions.py` - Add back strategy relationships

### Priority 2: Create Service Layer
Implement the business logic services:
1. **StrategyService** (`backend/app/services/strategy_service.py`)
   - `create_strategy()` - Create new strategies
   - `auto_create_standalone()` - Auto-create for new positions
   - `combine_into_strategy()` - Combine multiple positions
   - `detect_strategies()` - Auto-detect multi-leg patterns
   - `calculate_metrics()` - Aggregate strategy metrics

2. **TagService** (`backend/app/services/tag_service.py`)
   - `create_tag()` - Create user-scoped tags
   - `tag_strategy()` - Apply tags to strategies
   - `get_strategies_by_tag()` - Filter strategies by tags
   - `archive_tag()` - Soft delete tags

### Priority 3: Implement API Endpoints
Create FastAPI routes in `backend/app/api/v1/`:
- `strategies.py` - Strategy CRUD and management
- `tags.py` - Tag CRUD and management
- Update existing `positions.py` to handle strategy assignment

### Priority 4: Testing
- Create unit tests for services
- Create integration tests for API endpoints
- Test multi-leg strategy detection algorithms

## Next Steps

### Immediate Actions (What's Ready to Build)
1. **Start Phase 1, Task 1.1**: Create the first Alembic migration for strategy tables
2. **Setup Development Environment**: Ensure all tools and dependencies are ready
3. **Create Development Branch**: `git checkout -b feature/portfolio-tagging-system`
4. **Backup Database**: Create full backup before starting schema changes

### Key Decision Points
1. **Migration Approach**: Confirm multi-phase vs single-phase migration
2. **Performance Requirements**: Validate target response times with stakeholders
3. **Rollback Criteria**: Define conditions that would trigger a rollback
4. **Testing Strategy**: Determine staging environment testing procedures

### Dependencies & Coordination
- **Database Access**: Ensure development database is available for testing
- **API Testing**: Coordinate with frontend team on endpoint changes
- **User Communication**: Plan communication about new features and changes
- **Performance Monitoring**: Set up monitoring for migration and new features

---

**Last Updated**: September 24, 2025
**Next Review**: September 25, 2025
**Status**: Ready to begin Phase 1 implementation

---

## Progress Update (2025-09-24)

- Wired ORM relationships for strategies, positions, and TagV2:
  - Portfolio.strategies, Strategy.positions, Position.strategy
  - Strategy.metrics, Strategy.strategy_tags, TagV2.strategy_tags
- Completed Strategy and Tag services for CRUD and assignment flows.
- Implemented strategies API endpoints and normalized metrics to return the latest metrics snapshot in GET /api/v1/strategies/{id}?include_metrics=true.

Remaining for Phase 1:
- [ ] Task 1.5 Data migration script to backfill standalone strategies for existing positions and set positions.strategy_id.
- [ ] Tighten authz checks to ensure portfolio ownership on strategy/tag operations.

Notes:
- Metrics relationship is one-to-many; API returns the latest metrics object for compatibility with current schema.

---

## Progress Update (2025-09-24 � Tag APIs & Auth)

- Built Tag APIs and services:
  - Endpoints: create, list, get, update, archive, restore; assign, remove, bulk-assign; get strategies by tag; create default tags
  - Service: user-scoped CRUD, archiving, usage counts, assignments
  - Authorization: portfolio ownership checks on strategy-tag actions
- Strategy tagging convenience routes under /strategies/{id}/tags are pending (current flows use /api/v1/tags/assign, /api/v1/tags/bulk-assign, and DELETE /api/v1/tags/assign).

## Status vs IMPLEMENTATION_STRATEGY_PRD.md

- Phase 1 (Database & Models): Complete
- Phase 2 (Services & Business Logic): In progress (combine done; basic detection; metrics minimal)
- Phase 3 (API Endpoints): Mostly complete (missing /strategies/{id}/tags convenience routes)
- Phase 4 (Views & Filtering): Not started
- Phase 5 (Data Migration & Cleanup): Partially complete (NOT NULL enforced; legacy tag migration pending)

---

## Progress Update (2025-09-24 � Migrations & Initial Schema)

- Migrated legacy position_tags to strategy_tags; created missing TagV2 entries.
- Dropped legacy tables (tags, position_tags) via Alembic revision e1f0c2d9b7a3.
- Updated initial schema baseline to include strategies, strategy_legs, strategy_metrics, strategy_tags, and tags_v2; removed legacy tables; positions.strategy_id is NOT NULL with FK.
- Seed scripts updated to create Strategy per position and assign TagV2 via StrategyTag.
- Frontend wiring: added endpoints in src/config/api.ts and a StrategiesApi client (src/services/strategiesApi.ts) for listing/filtering strategies and editing strategy tags.

---

## Implementation Status Update (2025-09-24)

What�s completed end-to-end:
- Database and migrations
  - Added strategies, strategy_legs, strategy_metrics, strategy_tags, tags_v2.
  - Enforced positions.strategy_id NOT NULL and FK to strategies.
  - Migrated legacy position_tags ? strategy_tags and created missing TagV2 per (user, name).
  - Dropped legacy tables (tags, position_tags). Updated initial_schema baseline.
- Backend APIs
  - Strategy CRUD + utilities (create/list/get/update/delete/combine/detect).
  - Strategy tags convenience routes: GET/PUT/POST/DELETE `/api/v1/strategies/{id}/tags`.
  - Portfolio data APIs extended:
    - GET `/api/v1/data/portfolio/{id}/complete` includes strategies (optional).
    - GET `/api/v1/data/portfolios/{id}/strategies` with tag/type filters (any|all), include_positions/tags.
  - Authorization: ownership checks for portfolio on all relevant routes.
- Services
  - StrategyService: create, auto-create standalone, list/get/update/delete, combine, detect (basic), metrics (cost basis).
  - TagService: user-scoped TagV2 CRUD, archive/restore, usage counts, get/replace/bulk assign/remove tags on strategies.
- Frontend wiring (dev)
  - New page: `frontend/src/pages/portfolio-strategies.tsx` (resolves portfolio, lists strategies, edit tags).
  - Strategy list UI: `frontend/src/components/portfolio/StrategyList.tsx`.
  - Tag editor modal: `frontend/src/components/portfolio/TagEditor.tsx`.
  - API clients: `frontend/src/services/strategiesApi.ts`, `frontend/src/services/tagsApi.ts`.
  - Config: new endpoints in `frontend/src/config/api.ts`.

Notes
- Tags are now user-scoped (TagV2) and applied to strategies via StrategyTag.
- Position?tag legacy paths are deprecated and removed from runtime.
- Strategy metrics are minimal (cost basis aggregate) and can be extended.

Open items
- Phase 2: richer detection algorithms; aggregated metrics (Greeks, P&L, risk).
- Phase 4: integrate strategy views/filters into primary portfolio UI.
- Cleanup remaining references to legacy Tag (placeholder kept for migrations only).

---

## Quick Reference (Where Things Live)

Backend
- Endpoints
  - Portfolio strategies: `backend/app/api/v1/data.py`
    - GET `/api/v1/data/portfolios/{portfolio_id}/strategies`
    - GET `/api/v1/data/portfolio/{id}/complete` (strategies section)
  - Strategies + tags: `backend/app/api/v1/strategies.py`
    - GET/PUT/POST/DELETE `/api/v1/strategies/{id}/tags`
- Services
  - `backend/app/services/strategy_service.py`
  - `backend/app/services/tag_service.py`
- Models
  - `backend/app/models/strategies.py`, `backend/app/models/tags_v2.py`
- Schemas
  - `backend/app/schemas/strategy_schemas.py`, `backend/app/schemas/tag_schemas.py`
- Migrations
  - Drop legacy: `alembic/versions/e1f0c2d9b7a3_drop_legacy_tag_tables.py`
  - Enforce NOT NULL: `alembic/versions/c9c0e8d2a7a1_enforce_not_null_on_positions_strategy_id.py`
  - Baseline updated: `alembic/versions/initial_schema.py`
  - Data migration script: `scripts/migrations/migrate_position_tags_to_strategy_tags.py`

Frontend
- Page: `frontend/src/pages/portfolio-strategies.tsx`
- Components: `frontend/src/components/portfolio/StrategyList.tsx`, `TagEditor.tsx`
- Clients: `frontend/src/services/strategiesApi.ts`, `tagsApi.ts`
- Config: `frontend/src/config/api.ts`
