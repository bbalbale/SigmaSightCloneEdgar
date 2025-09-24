# Portfolio Tagging & Strategy Management System - Product Requirements & Implementation Plan

**Version**: 2.1.0
**Date**: September 23, 2025
**Status**: Planning Phase
**Feature**: Dual system for position organization (tags) and position grouping (strategies)

---

## Executive Summary

A dual-system architecture that separates organizational tagging from position aggregation. **Tags** provide metadata for filtering and categorization, while **Strategies** create virtual positions that aggregate multiple legs into single logical trading units. Every position belongs to exactly one strategy, with most being "standalone" strategies containing a single position.

### Key Architectural Decision
- **Tags**: Organizational metadata (labels for filtering/grouping)
- **Strategies**: Virtual positions (containers that hold 1+ actual positions)
- **Every position** must belong to a strategy (defaulting to "standalone")

### Key Capabilities
- User-scoped tags for organization across all portfolios
- Strategy system that treats multi-leg trades as single positions
- Automatic "standalone" strategy creation for individual positions
- AI-powered tag suggestions
- Drag-and-drop interface for organization
- Unified portfolio view mixing real and virtual positions

---

## 1. System Architecture

### 1.1 Two Distinct Systems

#### System 1: Tags (Organizational Metadata)
- **Purpose**: Filter, categorize, and organize strategies/positions
- **Examples**: "tech", "defensive", "income", "high-risk", "momentum"
- **Scope**: User-level (shared across all portfolios)
- **Application**: Can be applied to strategies (not individual positions)
- **Limit**: 100 tags per user, 20 tags per strategy

#### System 2: Strategies (Position Containers)
- **Purpose**: Group related positions into logical trading units
- **Types**:
  - `standalone` (DEFAULT - single position)
  - `covered_call` (stock + short call)
  - `protective_put` (stock + long put)
  - `iron_condor` (4 option legs)
  - `straddle` (call + put same strike)
  - `pairs_trade` (long + short correlated assets)
  - Custom user-defined strategies
- **Behavior**: Displayed as single rows with expandable legs
- **Metrics**: Aggregated P&L, net Greeks, combined risk

### 1.2 Fundamental Rules

1. **Every position belongs to exactly ONE strategy**
2. **Most strategies are "standalone" (single position)**
3. **Tags are applied to strategies, not individual positions**
4. **Strategies are first-class portfolio entities**
5. **Virtual positions (multi-leg) show aggregated metrics**

### 1.3 System Limits
- **Tags per user**: 100 maximum
- **Tags per strategy**: 20 maximum
- **Positions per strategy**: Unlimited (typically 1-6)
- **Tag name length**: 50 characters
- **Strategy name length**: 200 characters
- **Archived items retention**: 90 days

---

## 2. Database Schema Design

### 2.1 Strategy Tables (Primary System)

#### `strategies` Table
```sql
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    strategy_type VARCHAR(50) DEFAULT 'standalone',
    name VARCHAR(200) NOT NULL,
    is_synthetic BOOLEAN DEFAULT FALSE, -- true for multi-leg strategies
    net_exposure DECIMAL(20, 2), -- calculated field
    total_cost_basis DECIMAL(20, 2), -- sum of leg cost basis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP, -- when strategy is closed
    created_by UUID REFERENCES users(id),

    CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN (
            'standalone', 'covered_call', 'protective_put',
            'iron_condor', 'straddle', 'strangle', 'butterfly',
            'pairs_trade', 'custom'
        )
    )
);

CREATE INDEX idx_strategies_portfolio ON strategies(portfolio_id);
CREATE INDEX idx_strategies_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_synthetic ON strategies(is_synthetic);
```

#### `positions` Table (Modified)
```sql
-- Add strategy reference to existing positions table
ALTER TABLE positions
ADD COLUMN strategy_id UUID REFERENCES strategies(id) ON DELETE RESTRICT;

-- Make nullable initially for migration, then NOT NULL after data migration
-- Create index for foreign key
CREATE INDEX idx_positions_strategy ON positions(strategy_id);
```

#### `strategy_legs` Table
```sql
CREATE TABLE strategy_legs (
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    position_id UUID NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    leg_type VARCHAR(50) NOT NULL, -- 'single', 'long_leg', 'short_leg', 'protective', etc.
    leg_order INTEGER DEFAULT 0, -- display ordering

    PRIMARY KEY (strategy_id, position_id)
);

CREATE INDEX idx_strategy_legs_position ON strategy_legs(position_id);
```

### 2.2 Tag Tables (Organizational System)

#### `tags` Table
```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#4A90E2',
    description TEXT,
    display_order INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    archived_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_active_tag_name UNIQUE (user_id, name, is_archived),
    CONSTRAINT valid_hex_color CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    CONSTRAINT valid_tag_name CHECK (name ~ '^[a-zA-Z0-9_\-\s]+$')
);

CREATE INDEX idx_tags_user_active ON tags(user_id) WHERE is_archived = FALSE;
CREATE INDEX idx_tags_display_order ON tags(user_id, display_order);
```

#### `strategy_tags` Table (Replaces position_tags)
```sql
CREATE TABLE strategy_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id),

    CONSTRAINT unique_strategy_tag UNIQUE (strategy_id, tag_id)
);

CREATE INDEX idx_strategy_tags_strategy ON strategy_tags(strategy_id);
CREATE INDEX idx_strategy_tags_tag ON strategy_tags(tag_id);
```

### 2.3 Supporting Tables

#### `strategy_metrics` Table (Calculated/Cached)
```sql
CREATE TABLE strategy_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    calculation_date DATE NOT NULL,
    net_delta DECIMAL(10, 4),
    net_gamma DECIMAL(10, 6),
    net_theta DECIMAL(20, 2),
    net_vega DECIMAL(20, 2),
    total_pnl DECIMAL(20, 2),
    max_profit DECIMAL(20, 2),
    max_loss DECIMAL(20, 2),
    break_even_points JSONB, -- array of prices
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_strategy_date UNIQUE (strategy_id, calculation_date)
);
```

---

## 3. API Endpoints

### 3.1 Strategy Management

```yaml
# Core Strategy Operations
POST   /api/v1/strategies                    # Create new strategy
GET    /api/v1/strategies                    # List portfolio strategies
GET    /api/v1/strategies/{id}               # Get strategy details with legs
PUT    /api/v1/strategies/{id}               # Update strategy (name, type)
DELETE /api/v1/strategies/{id}               # Close/archive strategy
POST   /api/v1/strategies/{id}/add-leg       # Add position to strategy
DELETE /api/v1/strategies/{id}/remove-leg    # Remove position from strategy

# Strategy Analysis
GET    /api/v1/strategies/{id}/metrics       # Get aggregated metrics
GET    /api/v1/strategies/{id}/timeline      # Historical performance
POST   /api/v1/strategies/detect             # Auto-detect multi-leg strategies
GET    /api/v1/strategies/templates          # Get strategy templates

# Bulk Operations
POST   /api/v1/strategies/combine            # Combine positions into strategy
POST   /api/v1/strategies/{id}/split         # Split strategy into standalone
```

### 3.2 Tag Management (Applied to Strategies)

```yaml
# Core Tag Operations
POST   /api/v1/tags                          # Create new tag
GET    /api/v1/tags                          # List user's tags
GET    /api/v1/tags/{id}                     # Get tag details
PUT    /api/v1/tags/{id}                     # Update tag
DELETE /api/v1/tags/{id}                     # Archive tag (soft delete)
POST   /api/v1/tags/{id}/restore             # Restore archived tag

# Strategy Tagging
GET    /api/v1/strategies/{id}/tags          # Get strategy's tags
PUT    /api/v1/strategies/{id}/tags          # Replace strategy's tags
POST   /api/v1/strategies/{id}/tags          # Add tags to strategy
DELETE /api/v1/strategies/{id}/tags          # Remove tags from strategy

# Bulk Operations
POST   /api/v1/tags/bulk-assign              # Assign tags to multiple strategies
```

### 3.3 Portfolio Views & Filtering

```yaml
# Enhanced Portfolio Endpoints
GET    /api/v1/portfolios/{id}/strategies    # Get all strategies (virtual positions)
GET    /api/v1/portfolios/{id}/strategies?tags={tag_ids}  # Filter by tags
GET    /api/v1/portfolios/{id}/strategies?type={type}     # Filter by strategy type
GET    /api/v1/portfolios/{id}/grouped       # Group strategies by tags

# Analytics
GET    /api/v1/analytics/strategies/performance  # Performance by strategy type
GET    /api/v1/analytics/tags/performance        # Performance by tag
GET    /api/v1/analytics/strategies/risk         # Risk metrics by strategy
```

### 3.4 Position Management (Auto-Strategy Creation)

```yaml
# Position Creation (Auto-creates standalone strategy)
POST   /api/v1/positions
{
    "symbol": "AAPL",
    "quantity": 100,
    "position_type": "LONG",
    "strategy_id": null  # If null, creates standalone strategy
}

# Response includes strategy assignment
{
    "position": {...},
    "strategy": {
        "id": "uuid",
        "strategy_type": "standalone",
        "name": "Long AAPL",
        "is_synthetic": false
    }
}
```

---

## 4. Business Logic & Services

### 4.1 Core Services

#### StrategyService
```python
class StrategyService:
    async def create_strategy(
        portfolio_id: UUID,
        strategy_type: str = "standalone",
        name: Optional[str] = None,
        position_ids: List[UUID] = []
    ) -> Strategy:
        """Create new strategy, optionally with initial positions"""

    async def auto_create_standalone(
        position: Position
    ) -> Strategy:
        """Auto-create standalone strategy for new position"""
        strategy_name = f"{position.position_type} {position.symbol}"

    async def combine_into_strategy(
        position_ids: List[UUID],
        strategy_type: str,
        name: str
    ) -> Strategy:
        """Combine multiple positions into multi-leg strategy"""

    async def detect_strategies(
        portfolio_id: UUID
    ) -> List[StrategyDetection]:
        """Detect potential multi-leg strategies in portfolio"""

    async def calculate_metrics(
        strategy_id: UUID
    ) -> StrategyMetrics:
        """Calculate aggregated metrics for strategy"""
```

#### TagService (Applied to Strategies)
```python
class TagService:
    async def tag_strategy(
        strategy_id: UUID,
        tag_ids: List[UUID]
    ) -> None:
        """Apply tags to strategy (not individual positions)"""

    async def get_strategies_by_tag(
        user_id: UUID,
        tag_ids: List[UUID]
    ) -> List[Strategy]:
        """Get all strategies with specified tags"""
```

### 4.2 Strategy Detection Patterns

```python
STRATEGY_PATTERNS = {
    "covered_call": {
        "description": "Long stock + short call",
        "required_legs": 2,
        "detection": lambda legs: (
            len(legs) == 2 and
            any(l.position_type == "LONG" for l in legs) and
            any(l.position_type == "SC" for l in legs) and
            same_underlying(legs)
        )
    },
    "iron_condor": {
        "description": "Bull put spread + bear call spread",
        "required_legs": 4,
        "detection": lambda legs: (
            len(legs) == 4 and
            count_by_type(legs, "SC") == 1 and
            count_by_type(legs, "LC") == 1 and
            count_by_type(legs, "SP") == 1 and
            count_by_type(legs, "LP") == 1 and
            same_underlying(legs) and
            same_expiration(legs)
        )
    },
    "pairs_trade": {
        "description": "Long + short correlated assets",
        "required_legs": 2,
        "detection": lambda legs: (
            len(legs) == 2 and
            any(l.position_type == "LONG" for l in legs) and
            any(l.position_type == "SHORT" for l in legs) and
            high_correlation(legs)
        )
    }
}
```

### 4.3 Auto-Creation Flow

```python
async def create_position_with_strategy(position_data: dict):
    """
    Every position creation automatically creates or assigns a strategy
    """
    # Check if strategy_id provided
    if position_data.get('strategy_id'):
        # Validate strategy exists and add position
        strategy = await get_strategy(position_data['strategy_id'])
        position = await create_position(position_data)
        await add_position_to_strategy(position.id, strategy.id)
    else:
        # Auto-create standalone strategy
        position = await create_position(position_data)
        strategy = await create_standalone_strategy(position)

    return {
        "position": position,
        "strategy": strategy
    }
```

---

## 5. User Interface Design

### 5.1 Portfolio View (Mixed Real & Virtual Positions)

```
Portfolio Holdings
├── [▼] Iron Condor SPY Dec (4 legs) [$2,450 profit]        [tech] [income]
│   ├── Short Call SPY 450 Dec
│   ├── Long Call SPY 460 Dec
│   ├── Short Put SPY 420 Dec
│   └── Long Put SPY 410 Dec
├── [−] Long AAPL - 100 shares [$15,420 profit]              [tech] [growth]
├── [−] Long MSFT - 50 shares [$3,210 profit]                [tech] [defensive]
├── [▼] Covered Call NVDA (2 legs) [$890 profit]             [tech] [income]
│   ├── Long NVDA - 100 shares
│   └── Short Call NVDA 850 Jan
└── [−] Private Investment Fund X [$50,000 value]            [alternative]

Filters: [tech ✓] [income ✓] [growth ] [defensive ]
Group by: [None ▼] [Tags] [Strategy Type] [Sector]
```

### 5.2 Tag Assignment (To Strategies Only)

```python
# UI shows tags on strategy level
Strategy: "Iron Condor SPY Dec"
Tags: [income] [hedged] [options] [+]

# Individual legs don't have separate tags
# Tags apply to the entire strategy unit
```

### 5.3 Drag-and-Drop Behaviors

#### Scenario 1: Dragging Tags
- **Source**: Tag from sidebar
- **Target**: Strategy row (not individual legs)
- **Action**: Assigns tag to entire strategy

#### Scenario 2: Dragging into Tag Groups
- **Source**: Strategy (entire unit)
- **Target**: Tag group/bucket
- **Action**: Assigns that tag to strategy

#### Scenario 3: Combining into Strategy
- **Source**: Multiple selected positions
- **Target**: "Create Strategy" drop zone
- **Action**: Opens strategy creation dialog

### 5.4 Strategy Creation Dialog

```
Create Multi-Leg Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━
Selected Positions:
• Long AAPL 100 shares
• Short Call AAPL 180 Jan

Detected Pattern: ✓ Covered Call

Strategy Name: [Covered Call AAPL Jan    ]
Strategy Type: [Covered Call     ▼]

[Cancel] [Create Strategy]
```

---

## 6. Implementation Plan

### Phase 1: Strategy Foundation (Week 1-2)
**Goal**: Implement strategy system as position containers

**Tasks**:
1. Create strategy database tables via Alembic
2. Modify positions table to include strategy_id
3. Build StrategyService class
4. Implement auto-creation of standalone strategies
5. Create strategy CRUD endpoints
6. Migration script for existing positions (create standalone strategies)

**Deliverables**:
- Every position belongs to a strategy
- Standalone strategies auto-created
- Basic strategy API working

### Phase 2: Multi-Leg Strategies (Week 3)
**Goal**: Support combining positions into strategies

**Tasks**:
1. Implement strategy detection algorithms
2. Build combination/split endpoints
3. Calculate aggregated metrics
4. Create strategy templates
5. Test multi-leg scenarios

**Deliverables**:
- Can combine positions into strategies
- Strategy metrics aggregation working
- Pattern detection functional

### Phase 3: Tag System (Week 4)
**Goal**: Implement organizational tagging for strategies

**Tasks**:
1. Create tag database tables via Alembic
2. Build TagService class
3. Implement tag CRUD endpoints
4. Connect tags to strategies (not positions)
5. Build filtering/grouping logic

**Deliverables**:
- Tags can be applied to strategies
- Filter portfolio by tags
- Tag-based grouping working

### Phase 4: UI Implementation (Week 5-6)
**Goal**: Frontend for strategy management

**Tasks**:
1. Mixed portfolio view (strategies + expandable legs)
2. Strategy creation dialog
3. Drag-and-drop for combinations
4. Tag assignment to strategies
5. Performance metrics display

**Deliverables**:
- Portfolio shows virtual positions
- Can create/manage strategies via UI
- Tags visible and manageable

### Phase 5: Analytics & Optimization (Week 7)
**Goal**: Performance and analytics

**Tasks**:
1. Strategy performance analytics
2. Risk metrics by strategy type
3. Performance optimization
4. Caching layer for metrics
5. Testing and bug fixes

**Deliverables**:
- Analytics by strategy type
- Performance validated
- Production ready

---

## 7. Alembic Migration Strategy

### 7.1 Migration Approach

We'll use a **multi-step migration** approach to safely transform the existing schema:

1. **Phase 1**: Add new tables without breaking existing code
2. **Phase 2**: Migrate data from old structure to new
3. **Phase 3**: Clean up old tables and enforce constraints

### 7.2 Migration Files Required

#### Migration 1: Add Strategy Tables (Non-Breaking)
`alembic revision -m "add_strategy_tables_and_new_tag_system"`

```python
"""add_strategy_tables_and_new_tag_system

Revision ID: xxx
Revises: 1dafe8c1dd84
Create Date: 2025-09-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create strategies table
    op.create_table('strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_type', sa.String(50), nullable=False, server_default='standalone'),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('net_exposure', sa.Numeric(20, 2), nullable=True),
        sa.Column('total_cost_basis', sa.Numeric(20, 2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('closed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_strategies_portfolio', 'strategies', ['portfolio_id'])
    op.create_index('idx_strategies_type', 'strategies', ['strategy_type'])
    op.create_index('idx_strategies_synthetic', 'strategies', ['is_synthetic'])

    # Add strategy_id to positions (nullable initially)
    op.add_column('positions',
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_positions_strategy',
        'positions', 'strategies',
        ['strategy_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('idx_positions_strategy', 'positions', ['strategy_id'])

    # Create strategy_legs junction table
    op.create_table('strategy_legs',
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leg_type', sa.String(50), nullable=False, server_default='single'),
        sa.Column('leg_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('strategy_id', 'position_id')
    )
    op.create_index('idx_strategy_legs_position', 'strategy_legs', ['position_id'])

    # Create new tags table (user-scoped, not portfolio-scoped)
    # Note: We're NOT dropping the old tags table yet
    op.create_table('tags_v2',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('color', sa.String(7), nullable=True, server_default='#4A90E2'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('archived_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('archived_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['archived_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', 'is_archived', name='unique_active_tag_name_v2')
    )
    op.create_index('idx_tags_v2_user_active', 'tags_v2', ['user_id'],
                    postgresql_where=sa.text('is_archived = false'))
    op.create_index('idx_tags_v2_display_order', 'tags_v2', ['user_id', 'display_order'])

    # Create strategy_tags junction table
    op.create_table('strategy_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags_v2.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id', 'tag_id', name='unique_strategy_tag')
    )
    op.create_index('idx_strategy_tags_strategy', 'strategy_tags', ['strategy_id'])
    op.create_index('idx_strategy_tags_tag', 'strategy_tags', ['tag_id'])

    # Create strategy_metrics table for cached calculations
    op.create_table('strategy_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('net_delta', sa.Numeric(10, 4), nullable=True),
        sa.Column('net_gamma', sa.Numeric(10, 6), nullable=True),
        sa.Column('net_theta', sa.Numeric(20, 2), nullable=True),
        sa.Column('net_vega', sa.Numeric(20, 2), nullable=True),
        sa.Column('total_pnl', sa.Numeric(20, 2), nullable=True),
        sa.Column('max_profit', sa.Numeric(20, 2), nullable=True),
        sa.Column('max_loss', sa.Numeric(20, 2), nullable=True),
        sa.Column('break_even_points', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id', 'calculation_date', name='unique_strategy_date')
    )

def downgrade():
    op.drop_table('strategy_metrics')
    op.drop_table('strategy_tags')
    op.drop_table('tags_v2')
    op.drop_table('strategy_legs')
    op.drop_constraint('fk_positions_strategy', 'positions', type_='foreignkey')
    op.drop_index('idx_positions_strategy', 'positions')
    op.drop_column('positions', 'strategy_id')
    op.drop_table('strategies')
```

#### Migration 2: Data Migration
`alembic revision -m "migrate_positions_to_strategies"`

```python
"""migrate_positions_to_strategies

Revision ID: yyy
Revises: xxx
Create Date: 2025-09-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

def upgrade():
    # Create standalone strategies for all existing positions
    op.execute(text("""
        DO $$
        DECLARE
            pos RECORD;
            new_strategy_id UUID;
        BEGIN
            FOR pos IN
                SELECT p.*, port.user_id
                FROM positions p
                JOIN portfolios port ON p.portfolio_id = port.id
                WHERE p.strategy_id IS NULL
            LOOP
                -- Generate new UUID for strategy
                new_strategy_id := gen_random_uuid();

                -- Create standalone strategy
                INSERT INTO strategies (
                    id,
                    portfolio_id,
                    strategy_type,
                    name,
                    is_synthetic,
                    total_cost_basis,
                    created_at,
                    updated_at,
                    created_by
                ) VALUES (
                    new_strategy_id,
                    pos.portfolio_id,
                    'standalone',
                    CONCAT(
                        CASE pos.position_type
                            WHEN 'LONG' THEN 'Long '
                            WHEN 'SHORT' THEN 'Short '
                            WHEN 'LC' THEN 'Long Call '
                            WHEN 'LP' THEN 'Long Put '
                            WHEN 'SC' THEN 'Short Call '
                            WHEN 'SP' THEN 'Short Put '
                        END,
                        pos.symbol
                    ),
                    FALSE,
                    pos.cost_basis,
                    pos.created_at,
                    pos.updated_at,
                    pos.user_id
                );

                -- Update position with strategy_id
                UPDATE positions
                SET strategy_id = new_strategy_id
                WHERE id = pos.id;

                -- Create strategy_legs entry
                INSERT INTO strategy_legs (
                    strategy_id,
                    position_id,
                    leg_type,
                    leg_order
                ) VALUES (
                    new_strategy_id,
                    pos.id,
                    'single',
                    0
                );
            END LOOP;
        END $$;
    """))

    # Migrate existing tags from old system to new
    op.execute(text("""
        INSERT INTO tags_v2 (id, user_id, name, color, description, created_at, updated_at)
        SELECT
            t.id,
            t.user_id,
            t.name,
            t.color,
            t.description,
            t.created_at,
            t.updated_at
        FROM tags t
        WHERE t.tag_type = 'REGULAR'
        ON CONFLICT DO NOTHING;
    """))

    # Migrate position_tags to strategy_tags
    op.execute(text("""
        INSERT INTO strategy_tags (strategy_id, tag_id, assigned_at)
        SELECT DISTINCT
            p.strategy_id,
            pt.tag_id,
            pt.created_at
        FROM position_tags pt
        JOIN positions p ON pt.position_id = p.id
        WHERE p.strategy_id IS NOT NULL
        AND EXISTS (SELECT 1 FROM tags_v2 WHERE id = pt.tag_id)
        ON CONFLICT DO NOTHING;
    """))

def downgrade():
    # Remove strategy_id from positions
    op.execute(text("""
        UPDATE positions SET strategy_id = NULL;
    """))

    # Delete all created strategies
    op.execute(text("""
        DELETE FROM strategies WHERE strategy_type = 'standalone';
    """))
```

#### Migration 3: Enforce Constraints & Cleanup
`alembic revision -m "finalize_strategy_migration"`

```python
"""finalize_strategy_migration

Revision ID: zzz
Revises: yyy
Create Date: 2025-09-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Make strategy_id NOT NULL now that all positions have strategies
    op.alter_column('positions', 'strategy_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)

    # Drop old tag tables (after confirming migration success)
    op.drop_table('position_tags')
    op.drop_table('tags')

    # Rename tags_v2 to tags
    op.rename_table('tags_v2', 'tags')

    # Update indexes and constraints with new names
    op.drop_index('idx_tags_v2_user_active', 'tags')
    op.drop_index('idx_tags_v2_display_order', 'tags')
    op.create_index('idx_tags_user_active', 'tags', ['user_id'],
                    postgresql_where=sa.text('is_archived = false'))
    op.create_index('idx_tags_display_order', 'tags', ['user_id', 'display_order'])

    # Add check constraint for strategy types
    op.execute("""
        ALTER TABLE strategies
        ADD CONSTRAINT valid_strategy_type CHECK (
            strategy_type IN (
                'standalone', 'covered_call', 'protective_put',
                'iron_condor', 'straddle', 'strangle', 'butterfly',
                'pairs_trade', 'custom'
            )
        );
    """)

    # Add triggers for tag usage count
    op.execute("""
        CREATE OR REPLACE FUNCTION update_tag_usage_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE tags SET usage_count = usage_count + 1
                WHERE id = NEW.tag_id;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE tags SET usage_count = usage_count - 1
                WHERE id = OLD.tag_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER update_tag_count
        AFTER INSERT OR DELETE ON strategy_tags
        FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();
    """)

def downgrade():
    # This migration is difficult to reverse
    # Would need to recreate old tag structure
    raise NotImplementedError("Cannot downgrade after finalizing strategy migration")
```

### 7.3 Migration Execution Plan

```bash
# Step 1: Backup database
pg_dump sigmasight > backup_before_migration.sql

# Step 2: Run migrations in sequence
cd backend
uv run alembic revision -m "add_strategy_tables_and_new_tag_system"
# Edit the generated file with content from Migration 1
uv run alembic upgrade head

# Step 3: Verify phase 1
uv run python scripts/verify_migration_phase1.py

# Step 4: Data migration
uv run alembic revision -m "migrate_positions_to_strategies"
# Edit with Migration 2 content
uv run alembic upgrade head

# Step 5: Verify data migration
uv run python scripts/verify_migration_phase2.py

# Step 6: Finalize (only after thorough testing)
uv run alembic revision -m "finalize_strategy_migration"
# Edit with Migration 3 content
uv run alembic upgrade head
```

### 7.4 Rollback Strategy

```bash
# If issues in Phase 1
uv run alembic downgrade -1

# If issues in Phase 2 (data migration)
uv run alembic downgrade -2
# Restore from backup if needed

# If issues after finalization
# Must restore from backup
pg_restore -d sigmasight backup_before_migration.sql
```

### 7.5 Update to Initial Schema

For new installations, update `initial_schema.py` to include the complete structure:

```python
# In initial_schema.py, REMOVE the old tag tables and ADD:

# Create strategies table
op.create_table('strategies',
    # ... full schema from Migration 1
)

# Positions table should include strategy_id from the start
sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id']),

# Create new tag structure
op.create_table('tags',
    # ... schema from tags_v2 in Migration 1
)

# Create strategy_tags instead of position_tags
op.create_table('strategy_tags',
    # ... schema from Migration 1
)
```

---

## 8. Performance Considerations

### 8.1 Query Optimization

```sql
-- Materialized view for portfolio strategy view
CREATE MATERIALIZED VIEW portfolio_strategy_view AS
SELECT
    s.id as strategy_id,
    s.name as strategy_name,
    s.strategy_type,
    s.is_synthetic,
    COUNT(sl.position_id) as leg_count,
    SUM(p.current_value) as total_value,
    SUM(p.unrealized_pnl) as total_pnl,
    ARRAY_AGG(st.tag_id) as tag_ids
FROM strategies s
LEFT JOIN strategy_legs sl ON s.id = sl.strategy_id
LEFT JOIN positions p ON sl.position_id = p.id
LEFT JOIN strategy_tags st ON s.id = st.strategy_id
WHERE s.closed_at IS NULL
GROUP BY s.id;

-- Refresh on data changes
CREATE OR REPLACE FUNCTION refresh_strategy_view()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY portfolio_strategy_view;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### 8.2 Caching Strategy

- Cache strategy metrics for 5 minutes
- Cache tag assignments for 10 minutes
- Invalidate on position/strategy updates
- Pre-calculate common aggregations

### 8.3 Performance Targets

- Strategy list view: < 100ms
- Expand strategy legs: < 50ms
- Combine into strategy: < 500ms
- Strategy detection: < 1s for 100 positions
- Tag filtering: < 200ms

---

## 9. Testing Strategy

### 9.1 Migration Testing

```python
# scripts/verify_migration_phase1.py
"""Verify Phase 1: Tables exist, no data loss"""

# scripts/verify_migration_phase2.py
"""Verify Phase 2: All positions have strategies"""

# scripts/verify_migration_phase3.py
"""Verify Phase 3: Constraints enforced, old tables removed"""
```

### 9.2 Integration Testing

- Test strategy creation with new positions
- Test combining positions into strategies
- Test tag assignment to strategies
- Test filtering and grouping
- Test performance with large datasets

---

## 10. Success Metrics

### 10.1 Adoption Metrics
- % of multi-position strategies created (target: 40% of options users)
- Average strategies per portfolio (target: 15)
- % of strategies with tags (target: 70%)

### 10.2 User Experience Metrics
- Time to create strategy (target: < 30s)
- Strategy detection accuracy (target: 90%)
- Portfolio view load time (target: < 500ms)

### 10.3 Business Value Metrics
- Improved risk visibility (survey)
- Better P&L attribution (survey)
- Reduced confusion about multi-leg positions

---

## 11. Key Decision Summary

### Why Separate Strategies from Tags?

1. **Conceptual Clarity**:
   - Tags = organizational metadata
   - Strategies = position containers/virtual positions

2. **Better UX**:
   - Iron condor shows as ONE line with net P&L
   - No confusion about individual leg performance
   - Clean portfolio view

3. **Accurate Analytics**:
   - Strategy-level P&L and risk metrics
   - No double-counting in portfolio totals
   - Proper attribution of multi-leg trades

4. **Flexibility**:
   - Strategies can be tagged like any position
   - Can convert between standalone and multi-leg
   - Supports future complex strategies

### Why "Standalone" Default?

1. **Uniform Data Model**: Everything follows same pattern
2. **Simpler Code**: No special cases for single positions
3. **Future Flexibility**: Easy to combine later
4. **Clean Architecture**: One way to handle all positions

### Why Alembic Migrations?

1. **Safety**: Reversible changes with proper rollback
2. **Tracking**: Clear history of schema evolution
3. **Testing**: Can test migrations in staging first
4. **Team Coordination**: Everyone stays in sync
5. **Production Ready**: Standard practice for production systems

---

## Document History

- **v2.1.0** (2025-09-23): Added comprehensive Alembic migration strategy
- **v2.0.0** (2025-09-23): Complete redesign separating strategies from tags
- **v1.5.0** (2025-09-23): Combined plan with increased limits
- **v1.4.1**: Original PRD with strategy tags
- **v1.0.0**: Initial portfolio-level tagging proposal