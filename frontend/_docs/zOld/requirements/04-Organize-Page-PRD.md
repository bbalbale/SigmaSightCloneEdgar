# Product Requirements Document: Portfolio Organization Page

**Project**: SigmaSight Multi-Page Implementation  
**Feature**: Portfolio Organization (Organize Page)  
**Route**: `/organize`  
**Status**: Ready for Implementation  
**Created**: October 1, 2025

---

## Executive Summary

The Organize page enables users to group positions into strategies and apply tags for advanced portfolio organization. Users can combine multiple positions into synthetic strategies (e.g., pairs trades, spreads) and categorize them with custom tags for filtering and analysis across the application.

---

## Problem Statement

### Current State
- Users view all positions as individual line items
- No way to group related positions (e.g., long/short pairs, option spreads)
- No categorization system for portfolio segments
- Difficult to analyze themed investments or trading strategies

### Desired State
- Users can combine positions into named strategies
- Strategies can be tagged for categorization
- Tags enable filtering across all portfolio views
- Single positions act as default strategies
- Clear visualization of long/short/options/private segments

---

## Goals & Success Metrics

### Primary Goals
1. Enable position combination into strategies
2. Implement tagging system for categorization
3. Provide intuitive drag-and-drop interface
4. Separate display by investment class (PUBLIC LONG, PUBLIC SHORT, OPTIONS, PRIVATE)

### Success Metrics
- 70%+ of active users create at least one strategy within 30 days
- Average of 3-5 tags created per user
- 50%+ of strategies have at least one tag assigned
- Page load time < 2 seconds
- Zero data loss during strategy operations

---

## User Personas

### Primary: Active Trader
- **Profile**: Manages 20-50 positions across multiple strategies
- **Needs**: Quick position grouping, clear strategy visualization
- **Pain Points**: Manual tracking in spreadsheets, no synthetic P&L

### Secondary: Portfolio Manager
- **Profile**: Oversees institutional portfolio with 100+ positions
- **Needs**: Thematic organization, performance attribution
- **Pain Points**: Difficulty categorizing by investment thesis

### Tertiary: Casual Investor
- **Profile**: Long-term holder with 10-20 positions
- **Needs**: Simple organization by sector/theme
- **Pain Points**: Too many positions to track individually

---

## Functional Requirements

### FR-1: Investment Class Segmentation

#### FR-1.1: Four-Section Layout
**Priority**: P0 (Must Have)

Display positions grouped by investment class in separate sections:

1. **Long Positions** (PUBLIC, position_type = LONG)
   - Top-left quadrant
   - Show: Symbol, Company Name, Market Value, P&L
   - Sortable by: Symbol, Value, P&L
   
2. **Short Positions** (PUBLIC, position_type = SHORT)
   - Top-right quadrant
   - Show: Symbol, Company Name, Market Value, P&L
   - Sortable by: Symbol, Value, P&L

3. **Options Positions** (OPTIONS, all types: LC, LP, SC, SP)
   - Bottom-left quadrant
   - Sub-grouped into:
     - Long Options (LC, LP)
     - Short Options (SC, SP)
   - Show: Symbol, Strike, Expiry, Type, Market Value, P&L

4. **Private Positions** (PRIVATE)
   - Bottom-right quadrant
   - Show: Symbol, Description, Market Value, P&L
   - May have limited pricing data

**Acceptance Criteria**:
- [ ] All four sections render correctly
- [ ] Positions filter by investment_class and position_type
- [ ] Empty sections show "No positions" message
- [ ] Responsive layout (stacks on mobile)

#### FR-1.2: Position Selection
**Priority**: P0 (Must Have)

Each position displays a checkbox for selection:
- Single checkbox per position (left side)
- Visual feedback when selected (highlight background)
- Selection persists across scrolling
- Maximum 10 positions selectable at once
- Clear selection button when any position selected

**Acceptance Criteria**:
- [ ] Checkboxes appear on all positions
- [ ] Selected positions highlight
- [ ] Selection state persists during page interactions
- [ ] Clear selection button works correctly
- [ ] Error message if selecting > 10 positions

---

### FR-2: Strategy Creation

#### FR-2.1: Combine Positions Modal
**Priority**: P0 (Must Have)

When 2+ positions selected, show "Combine X items" button:
- Button appears at bottom of screen (fixed)
- Clicking opens "Create a Combined Position" modal
- Modal fields:
  - **Name** (required): Text input, e.g., "Tech Pairs Trade"
  - **Type** (required): Radio buttons (Long/Short)
  - **Description** (optional): Textarea, 500 char max
- Create button submits to backend
- Cancel button clears selection

**API Endpoint**: `POST /strategies/combine`
```json
{
  "portfolio_id": "uuid",
  "name": "Tech Pairs Trade",
  "strategy_type": "LONG",
  "description": "AAPL long vs GOOGL short",
  "position_ids": ["uuid1", "uuid2"]
}
```

**Response**:
```json
{
  "id": "strategy-uuid",
  "name": "Tech Pairs Trade",
  "strategy_type": "LONG",
  "positions": [...],
  "net_exposure": 25000,
  "total_cost_basis": 50000,
  "created_at": "2025-10-01T12:00:00Z"
}
```

**Acceptance Criteria**:
- [ ] Button appears when 2+ positions selected
- [ ] Button shows correct count ("Combine 2 items")
- [ ] Modal opens with correct fields
- [ ] Name field is required (validation)
- [ ] Type field is required (validation)
- [ ] Success creates strategy and refreshes view
- [ ] Error shows user-friendly message
- [ ] Cancel clears selection and closes modal

#### FR-2.2: Strategy Display
**Priority**: P0 (Must Have)

After creation, strategy appears as single line item:
- **Visual Indicator**: Icon showing it's a strategy (e.g., layers icon)
- **Name**: User-defined strategy name
- **Type Badge**: LONG or SHORT
- **Net Exposure**: Sum of position values
- **P&L**: Aggregated unrealized P&L
- **Expandable**: Click to see constituent positions
- **Tags**: Tag badges display below name

**Acceptance Criteria**:
- [ ] Strategy displays in appropriate section (by type)
- [ ] Visual indicator distinguishes from single positions
- [ ] Click to expand shows constituent positions
- [ ] Net exposure calculated correctly
- [ ] P&L aggregated correctly
- [ ] Tags display correctly

#### FR-2.3: Single Position Default Strategy
**Priority**: P0 (Must Have)

All positions that are NOT combined act as individual strategies:
- Same data structure as combined strategies
- strategy_type = position_type
- Single position in positions array
- Can be tagged like combined strategies
- Can be combined with other positions later

**Acceptance Criteria**:
- [ ] All non-combined positions treated as strategies
- [ ] Can apply tags to single positions
- [ ] Single positions can be selected for combining
- [ ] Backend returns consistent structure

---

### FR-3: Tagging System

#### FR-3.1: Tag Creation
**Priority**: P0 (Must Have)

At top of page, tag creation interface:
- Text input: "Create a new tag..."
- Color picker: Preset colors (8 options)
- "Add" button to create
- Tags appear as color-coded badges immediately

**API Endpoint**: `POST /tags/`
```json
{
  "name": "High Conviction",
  "color": "#3B82F6",
  "description": "Highest confidence ideas"
}
```

**Predefined Colors**:
- Core Holding: #3B82F6 (blue)
- High Conviction: #10B981 (green)
- Speculative: #F59E0B (yellow)
- Hedge: #8B5CF6 (purple)
- Tech: #6366F1 (indigo)
- Finance: #EC4899 (pink)
- Custom 1: #EF4444 (red)
- Custom 2: #14B8A6 (teal)

**Acceptance Criteria**:
- [ ] Input field accepts text (50 char max)
- [ ] Color picker shows 8 preset colors
- [ ] Add button creates tag
- [ ] New tag appears in tag list immediately
- [ ] Duplicate names show error
- [ ] Empty name shows validation error

#### FR-3.2: Tag Application via Drag-and-Drop
**Priority**: P0 (Must Have)

Users can drag tags onto strategies/positions:
- **Drag Source**: Tag badge at top of page
- **Drop Target**: Any position or strategy card
- **Visual Feedback**: 
  - Tag badge shows drag cursor
  - Drop target highlights on hover
  - Animation on successful drop
- **Multi-tag Support**: Single strategy can have multiple tags
- **Tag Display**: Tags appear as colored badges below position name

**Implementation**:
- Use HTML5 Drag and Drop API
- Draggable attribute on tag badges
- Drop zones on position/strategy cards
- Call API on successful drop

**API Endpoint**: `POST /strategies/{id}/tags`
```json
{
  "tag_ids": ["tag-uuid"]
}
```

**Acceptance Criteria**:
- [ ] Tags are draggable from top bar
- [ ] Position cards highlight as valid drop targets
- [ ] Drop adds tag to position/strategy
- [ ] Tag badge appears below position name
- [ ] Multiple tags can be applied
- [ ] Duplicate tags are prevented
- [ ] Drag works across all four sections

#### FR-3.3: Tag Management
**Priority**: P1 (Should Have)

Tag list at top of page shows all user tags:
- Display: Name, color badge, usage count
- Actions: Edit (rename, recolor), Delete (archive)
- Click tag to highlight all strategies with that tag
- Delete only archives (doesn't remove from strategies)

**API Endpoints**:
- `PATCH /tags/{id}` - Update name/color
- `DELETE /tags/{id}` - Archive tag
- `GET /tags/{id}/strategies` - Get strategies using tag

**Acceptance Criteria**:
- [ ] All tags display in list
- [ ] Usage count accurate
- [ ] Edit updates tag name/color
- [ ] Delete archives (doesn't permanently delete)
- [ ] Click highlights related strategies
- [ ] Changes propagate to all strategies

#### FR-3.4: Tag Filtering (Future)
**Priority**: P2 (Nice to Have)

_Note: This is a future enhancement for other pages_

On other pages (portfolio dashboard, position pages):
- Filter dropdown shows all tags
- Selecting tag filters to show only positions/strategies with that tag
- Multiple tag selection = OR logic
- "Clear filters" button resets

**Acceptance Criteria**:
- [ ] Filter dropdown available on other pages
- [ ] Selecting tag filters positions
- [ ] Multiple tags work with OR logic
- [ ] Clear filters resets view
- [ ] Filter state persists during session

---

### FR-4: Strategy Operations

#### FR-4.1: Edit Strategy
**Priority**: P1 (Should Have)

Users can edit existing strategies:
- Click edit icon on strategy card
- Opens modal with current values pre-filled
- Can update: Name, Description
- Cannot change: Type, Positions (must delete and recreate)

**API Endpoint**: `PATCH /strategies/{id}`
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Acceptance Criteria**:
- [ ] Edit icon appears on strategy cards
- [ ] Modal pre-fills current values
- [ ] Update saves successfully
- [ ] Changes reflect immediately
- [ ] Validation same as creation

#### FR-4.2: Delete Strategy
**Priority**: P1 (Should Have)

Users can delete strategies:
- Trash icon on strategy card
- Confirmation modal: "Delete this strategy?"
- Deleting strategy:
  - Removes strategy entity
  - Positions revert to individual strategies
  - Tags remain in system (just unlinked)
  - P&L calculations revert to individual

**API Endpoint**: `DELETE /strategies/{id}`

**Acceptance Criteria**:
- [ ] Delete icon appears on strategy cards
- [ ] Confirmation modal prevents accidental deletion
- [ ] Delete removes strategy successfully
- [ ] Positions reappear as individuals
- [ ] Tags persist (can be reused)
- [ ] Page refreshes to show updated state

#### FR-4.3: Expand/Collapse Strategy
**Priority**: P1 (Should Have)

Strategies can be expanded to show constituent positions:
- Click anywhere on strategy card to expand
- Shows nested list of positions
- Each position shows: Symbol, Quantity, Value, P&L
- Click again to collapse
- Expanded state doesn't persist (resets on refresh)

**Acceptance Criteria**:
- [ ] Click expands strategy
- [ ] Nested positions display correctly
- [ ] Position details accurate
- [ ] Click again collapses
- [ ] Expansion state visual feedback

---

### FR-5: Data Integration

#### FR-5.1: Backend API Integration
**Priority**: P0 (Must Have)

All operations use existing backend services:

**Services Used**:
- `strategiesApi.ts` - Strategy CRUD
- `tagsApi.ts` - Tag CRUD
- `apiClient.ts` - HTTP client
- `useAuth()` - Portfolio ID from context

**Key Endpoints**:
```typescript
// Strategies
GET    /strategies/                        // List all
GET    /data/portfolios/{id}/strategies    // Portfolio strategies
POST   /strategies/                        // Create
PATCH  /strategies/{id}                    // Update
DELETE /strategies/{id}                    // Delete
POST   /strategies/combine                 // Combine positions
POST   /strategies/{id}/positions          // Add positions
DELETE /strategies/{id}/positions          // Remove positions
POST   /strategies/{id}/tags               // Assign tags
DELETE /strategies/{id}/tags               // Remove tags

// Tags
GET    /tags/                              // List all
POST   /tags/                              // Create
PATCH  /tags/{id}                          // Update
DELETE /tags/{id}                          // Archive
POST   /tags/defaults                      // Create defaults
GET    /tags/{id}/strategies               // Get strategies using tag

// Positions
GET    /data/positions/details?portfolio_id={id}  // All positions
```

**Acceptance Criteria**:
- [ ] All API calls use existing services
- [ ] No direct fetch() calls
- [ ] Error handling on all requests
- [ ] Loading states during operations
- [ ] Optimistic UI updates where appropriate

#### FR-5.2: Position Data Structure
**Priority**: P0 (Must Have)

Position data includes investment_class for filtering:
```typescript
interface Position {
  id: string
  symbol: string
  investment_class: 'PUBLIC' | 'OPTIONS' | 'PRIVATE'
  position_type: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
  quantity: number
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
  // Options-specific
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}
```

**Strategy Data Structure**:
```typescript
interface Strategy {
  id: string
  portfolio_id: string
  name: string
  strategy_type: 'LONG' | 'SHORT'
  description?: string
  is_synthetic: boolean  // true if combined positions
  net_exposure: number
  total_cost_basis: number
  positions: Position[]
  tags?: Tag[]
  created_at: string
  updated_at: string
}
```

**Tag Data Structure**:
```typescript
interface Tag {
  id: string
  user_id: string
  name: string
  color: string
  description?: string
  usage_count: number
  created_at: string
}
```

**Acceptance Criteria**:
- [ ] Types match backend response
- [ ] investment_class field present
- [ ] Strategy structure consistent
- [ ] Tag structure matches API

---

## Non-Functional Requirements

### NFR-1: Performance
- Page load: < 2 seconds
- API response: < 500ms for all operations
- Drag-and-drop: < 100ms visual feedback
- No UI blocking during API calls
- Optimistic updates for better UX

### NFR-2: Usability
- Mobile responsive (stacks to single column)
- Keyboard navigation support
- Screen reader compatible
- Clear error messages
- Undo support for accidental operations (nice to have)

### NFR-3: Reliability
- No data loss during operations
- Graceful degradation if API fails
- Retry logic for transient failures
- Rollback on failed operations
- Error boundaries prevent page crashes

### NFR-4: Security
- Authentication required
- User can only see own positions
- Portfolio-scoped operations
- Input sanitization (XSS prevention)
- CSRF protection on mutations

---

## User Interface Specifications

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Portfolio Tagging & Grouping                               │
│  Drag tags, select & combine tickers, or click to rename   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Create new tag...] [🎨] [Add]  🗑️                        │
│                                                             │
│  [Core Holding] [High Conviction] [Speculative] [Hedge]    │
│  [Tech] [Finance]                                           │
│                                                             │
├──────────────────────────────┬──────────────────────────────┤
│  LONG POSITIONS              │  SHORT POSITIONS             │
├──────────────────────────────┼──────────────────────────────┤
│                              │                              │
│  ☐ NVDA                      │  ☐ TSLA                      │
│     NVIDIA Corporation       │     Tesla Inc.               │
│     $88,000                  │     -$40,000                 │
│     [Core Holding] [Tech]    │     [Hedge]                  │
│                              │                              │
│  ☐ META                      │  ☐ GME                       │
│     Meta Platforms Inc.      │     GameStop Corp.           │
│     $75,000                  │     -$15,000                 │
│     [Core Holding] [Tech]    │                              │
│                              │                              │
│  ...                         │  ...                         │
│                              │                              │
├──────────────────────────────┼──────────────────────────────┤
│  OPTIONS POSITIONS           │  PRIVATE POSITIONS           │
├──────────────────────────────┼──────────────────────────────┤
│  Long Options:               │                              │
│  ☐ AAPL 150C Oct25           │  ☐ Series A Investment       │
│     $5,000                   │     Startup XYZ              │
│                              │     $50,000                  │
│  Short Options:              │     [Speculative]            │
│  ☐ SPY 400P Nov25            │                              │
│     -$3,000                  │  ☐ Real Estate Fund          │
│     [Hedge]                  │     Commercial Properties    │
│                              │     $100,000                 │
│                              │     [High Conviction]        │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘

[Combine 2 items]  <-- Appears when 2+ selected
```

### Modal: Create Combined Position

```
┌────────────────────────────────────────────┐
│  Create a Combined Position                │
│  Select a name and whether it should be    │
│  long or short.                            │
├────────────────────────────────────────────┤
│                                            │
│  Name                                      │
│  [e.g. Tech Pairs Trade             ]     │
│                                            │
│  Type                                      │
│  ( ) Long    (•) Short                     │
│                                            │
│  Description (optional)                    │
│  [                                  ]      │
│  [                                  ]      │
│                                            │
│                                            │
│               [Cancel]  [Create]           │
│                                            │
└────────────────────────────────────────────┘
```

### Color Palette

**Primary Actions**:
- Add button: #000000 (black)
- Create button: #000000 (black)
- Success state: #10B981 (green)

**Tag Colors** (predefined):
- Core Holding: #3B82F6 (blue)
- High Conviction: #10B981 (green)
- Speculative: #F59E0B (yellow)
- Hedge: #8B5CF6 (purple)
- Tech: #6366F1 (indigo)
- Finance: #EC4899 (pink)

**Status Colors**:
- Positive P&L: #10B981 (green)
- Negative P&L: #EF4444 (red)
- Neutral: #6B7280 (gray)

**UI Elements**:
- Background: #FFFFFF (white)
- Card border: #E5E7EB (gray-200)
- Hover: #F9FAFB (gray-50)
- Selected: #EBF5FF (blue-50)

### Typography
- Page Title: 24px, Bold, #111827 (gray-900)
- Section Headers: 14px, Medium, #6B7280 (gray-500)
- Position Names: 14px, Medium, #111827 (gray-900)
- Values: 14px, Regular, #111827 (gray-900)
- Tag Labels: 12px, Medium, inherited from tag color

---

## Technical Architecture

### File Structure

```
app/organize/
└── page.tsx                           # Thin route wrapper (8 lines)

src/containers/
└── OrganizeContainer.tsx              # Main container (~200 lines)

src/components/organize/               # NEW folder
├── PositionSelectionGrid.tsx          # Four-section layout
├── LongPositionsList.tsx              # Long positions section
├── ShortPositionsList.tsx             # Short positions section
├── OptionsPositionsList.tsx           # Options section
├── PrivatePositionsList.tsx           # Private positions section
├── PositionCard.tsx                   # Individual position card
├── StrategyCard.tsx                   # Combined strategy card
├── CombinePositionsButton.tsx         # Fixed bottom button
├── CombineModal.tsx                   # Create strategy modal
├── TagCreator.tsx                     # Top tag creation UI
├── TagList.tsx                        # Tag display and management
└── TagBadge.tsx                       # Draggable tag badge

src/hooks/
├── usePositions.ts                    # Position data hook (exists)
├── useStrategies.ts                   # Strategy data hook (exists)
├── useTags.ts                         # Tag data hook (exists)
└── usePositionSelection.ts            # NEW: Selection state hook

src/services/
├── strategiesApi.ts                   # EXISTS - Strategy API
└── tagsApi.ts                         # EXISTS - Tag API
```

### Component Hierarchy

```
OrganizeContainer
├── TagCreator
│   └── TagList
│       └── TagBadge (draggable)
├── PositionSelectionGrid
│   ├── LongPositionsList
│   │   ├── PositionCard (with checkbox)
│   │   └── StrategyCard (expandable)
│   ├── ShortPositionsList
│   │   ├── PositionCard
│   │   └── StrategyCard
│   ├── OptionsPositionsList
│   │   ├── PositionCard (Long Options)
│   │   ├── PositionCard (Short Options)
│   │   └── StrategyCard
│   └── PrivatePositionsList
│       ├── PositionCard
│       └── StrategyCard
└── CombinePositionsButton (fixed)
    └── CombineModal
```

### State Management

**Local Component State**:
- Selected position IDs (Set<string>)
- Modal open/closed
- Drag-and-drop state
- Expanded strategies (Set<string>)

**Server State (via hooks)**:
- Positions data (usePositions)
- Strategies data (useStrategies)
- Tags data (useTags)
- Loading states
- Error states

**Derived State**:
- Filtered positions by investment_class
- Positions grouped by type
- Strategies with their positions
- Tag usage counts

### Custom Hook: usePositionSelection

```typescript
// src/hooks/usePositionSelection.ts
export function usePositionSelection() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  
  const toggleSelection = (id: string) => {
    const newSet = new Set(selectedIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      if (newSet.size >= 10) {
        throw new Error('Maximum 10 positions can be selected')
      }
      newSet.add(id)
    }
    setSelectedIds(newSet)
  }
  
  const clearSelection = () => setSelectedIds(new Set())
  
  const isSelected = (id: string) => selectedIds.has(id)
  
  return {
    selectedIds: Array.from(selectedIds),
    selectedCount: selectedIds.size,
    toggleSelection,
    clearSelection,
    isSelected,
  }
}
```

---

## Error Handling

### Error Scenarios

| Error | Cause | User Message | Action |
|-------|-------|--------------|--------|
| E1 | API timeout | "Failed to load positions. Please try again." | Retry button |
| E2 | Invalid strategy name | "Strategy name is required" | Form validation |
| E3 | Select < 2 positions | "Select at least 2 positions to combine" | Disable button |
| E4 | Select > 10 positions | "Maximum 10 positions can be combined" | Clear selection |
| E5 | Duplicate tag name | "A tag with this name already exists" | Form validation |
| E6 | Network error | "Connection lost. Changes may not be saved." | Toast notification |
| E7 | Strategy creation fails | "Failed to create strategy. Please try again." | Retry button |
| E8 | Tag creation fails | "Failed to create tag. Please try again." | Retry button |
| E9 | Unauthorized | "Session expired. Please log in again." | Redirect to login |

### Loading States

- **Initial Load**: Skeleton cards for all four sections
- **Strategy Creation**: Modal submit button shows spinner
- **Tag Creation**: Add button shows spinner
- **Drag-and-Drop**: Drop target shows loading indicator
- **Delete Strategy**: Card fades out before removal

---

## Testing Requirements

### Unit Tests

**Components**:
- [ ] PositionCard renders correctly
- [ ] StrategyCard expands/collapses
- [ ] TagBadge is draggable
- [ ] CombineModal validates input
- [ ] Selection limits enforced

**Hooks**:
- [ ] usePositionSelection manages state
- [ ] useStrategies fetches data
- [ ] useTags fetches data
- [ ] Error states handled

**Services**:
- [ ] strategiesApi.combine() works
- [ ] tagsApi.create() works
- [ ] API error handling works

### Integration Tests

- [ ] Select 2 positions → Combine button appears
- [ ] Create strategy → Strategy appears in list
- [ ] Drag tag → Tag applied to position
- [ ] Delete strategy → Positions revert
- [ ] Create tag → Tag appears in list
- [ ] Edit strategy name → Updates display
- [ ] Filter by investment_class works
- [ ] Expand strategy shows positions

### E2E Tests

**User Flow 1: Create Strategy**
1. Navigate to /organize
2. Select NVDA and META
3. Click "Combine 2 items"
4. Enter name "Tech Growth"
5. Select LONG type
6. Click Create
7. Verify strategy appears

**User Flow 2: Apply Tags**
1. Navigate to /organize
2. Create tag "High Conviction"
3. Drag tag to AAPL position
4. Verify tag badge appears

**User Flow 3: Delete Strategy**
1. Navigate to /organize
2. Click delete on existing strategy
3. Confirm deletion
4. Verify positions revert

---

## Accessibility Requirements

### WCAG 2.1 AA Compliance

**Keyboard Navigation**:
- Tab through all interactive elements
- Enter to open modals
- Escape to close modals
- Arrow keys to navigate lists
- Space to toggle checkboxes

**Screen Reader Support**:
- ARIA labels on all buttons
- ARIA descriptions for drag-and-drop
- ARIA live regions for status updates
- Semantic HTML (nav, main, section)
- Focus management in modals

**Visual Accessibility**:
- 4.5:1 contrast ratio for text
- 3:1 contrast ratio for UI elements
- Focus indicators on all interactive elements
- No color-only information
- Sufficient spacing (44x44px touch targets)

**Cognitive Accessibility**:
- Clear, concise labels
- Consistent patterns
- Confirmation for destructive actions
- Progress indicators
- Error messages near inputs

---

## Privacy & Security

### Data Privacy
- Strategies are user-scoped (portfolio_id)
- Tags are user-scoped (user_id)
- No PII collected beyond existing auth
- No analytics tracking without consent

### Security Measures
- Authentication required for all operations
- CSRF tokens on mutations
- Input sanitization (XSS prevention)
- SQL injection prevention (parameterized queries)
- Rate limiting on API endpoints

---

## Rollout Plan

### Phase 1: MVP (Weeks 1-2)
**Scope**: Core functionality only
- Four-section layout
- Position selection
- Strategy creation (combine)
- Basic tag creation and application
- NO drag-and-drop (use buttons)

**Success Criteria**:
- [ ] All positions display
- [ ] Can combine 2+ positions
- [ ] Can create tags
- [ ] Can apply tags via buttons
- [ ] Page loads < 2 seconds

### Phase 2: Enhanced UX (Week 3)
**Scope**: Improved interactions
- Drag-and-drop tag application
- Strategy expand/collapse
- Edit strategy modal
- Delete strategy confirmation
- Tag management (edit/delete)

**Success Criteria**:
- [ ] Drag-and-drop works smoothly
- [ ] Expand/collapse animations
- [ ] Edit/delete operations work
- [ ] Tag management functional

### Phase 3: Polish (Week 4)
**Scope**: Refinements and optimization
- Loading skeletons
- Error boundaries
- Optimistic updates
- Keyboard shortcuts
- Mobile responsive

**Success Criteria**:
- [ ] All loading states implemented
- [ ] Error handling comprehensive
- [ ] Mobile layout works
- [ ] Keyboard navigation works
- [ ] Performance metrics met

### Phase 4: Advanced Features (Future)
**Scope**: Nice-to-have features
- Undo/redo
- Strategy templates
- Bulk operations
- Advanced filtering
- Export strategies

---

## Dependencies

### Frontend Dependencies
- **Existing**: All UI components from shadcn/ui
- **Existing**: formatCurrency, formatNumber from lib/formatters
- **Existing**: apiClient, strategiesApi, tagsApi services
- **NEW**: HTML5 Drag and Drop API (browser native)

### Backend Dependencies
- **Existing**: `/strategies/*` endpoints (all implemented)
- **Existing**: `/tags/*` endpoints (all implemented)
- **Existing**: `/data/positions/details` endpoint
- **Required**: investment_class field in positions response

### Infrastructure
- Next.js 14+
- React 18+
- TypeScript 5+
- Tailwind CSS 3+

---

## Open Questions

### Technical
1. **Q**: Should strategies support nesting (strategy of strategies)?
   **A**: No, keep flat for MVP. Can add later if needed.

2. **Q**: How to handle strategy when constituent position is deleted?
   **A**: Auto-delete strategy or flag as invalid. TBD with backend team.

3. **Q**: Should tag order be persisted?
   **A**: Yes, use display_order field in tags table.

### UX
4. **Q**: What happens to tags when strategy is deleted?
   **A**: Tags remain in system, just unlinked from strategy.

5. **Q**: Can user change strategy type after creation?
   **A**: No for MVP, must delete and recreate.

6. **Q**: Should we show net delta for strategies with options?
   **A**: Yes, good enhancement for Phase 2+.

---

## Success Criteria

### Definition of Done

**Functional**:
- [ ] All FR-1 requirements met (Investment Class Segmentation)
- [ ] All FR-2 requirements met (Strategy Creation)
- [ ] All FR-3 requirements met (Tagging System)
- [ ] All API integrations working
- [ ] Error handling comprehensive

**Quality**:
- [ ] Unit test coverage > 80%
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] No console errors
- [ ] No accessibility violations

**Performance**:
- [ ] Page load < 2 seconds
- [ ] API calls < 500ms
- [ ] Drag-and-drop smooth (>30 FPS)
- [ ] No memory leaks

**Documentation**:
- [ ] Code comments on complex logic
- [ ] README updated
- [ ] Component Storybook stories
- [ ] API integration documented

---

## Appendix

### A. Example Use Cases

#### Use Case 1: Pairs Trade
**Actor**: Active Trader  
**Goal**: Create long/short equity pair

**Steps**:
1. Navigate to /organize
2. Select AAPL (long) and GOOGL (short)
3. Click "Combine 2 items"
4. Name: "Tech Pairs Trade"
5. Type: LONG (net position)
6. Create strategy
7. Drag "High Conviction" tag to strategy

**Result**: Strategy appears with both positions, net exposure calculated, tagged appropriately.

#### Use Case 2: Options Spread
**Actor**: Options Trader  
**Goal**: Create bull call spread

**Steps**:
1. Navigate to /organize
2. Select SPY 400C and SPY 410C (both long calls)
3. Click "Combine 2 items"
4. Name: "SPY Bull Spread Oct"
5. Type: LONG
6. Create strategy
7. Tag with "Hedge"

**Result**: Options spread tracked as single strategy.

#### Use Case 3: Thematic Portfolio
**Actor**: Portfolio Manager  
**Goal**: Tag all AI-related investments

**Steps**:
1. Navigate to /organize
2. Create tag "AI Theme" with purple color
3. Drag tag to NVDA
4. Drag tag to MSFT
5. Drag tag to GOOGL
6. Navigate to /portfolio
7. Filter by "AI Theme" tag

**Result**: All AI positions visible across views.

### B. Database Schema Reference

**strategies table**:
```sql
CREATE TABLE strategies (
  id UUID PRIMARY KEY,
  portfolio_id UUID REFERENCES portfolios(id),
  name VARCHAR(255) NOT NULL,
  strategy_type VARCHAR(10) NOT NULL,  -- LONG/SHORT
  description TEXT,
  is_synthetic BOOLEAN DEFAULT false,
  net_exposure DECIMAL(18, 2),
  total_cost_basis DECIMAL(18, 2),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  closed_at TIMESTAMP
);
```

**strategy_legs table**:
```sql
CREATE TABLE strategy_legs (
  id UUID PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id),
  position_id UUID REFERENCES positions(id),
  created_at TIMESTAMP
);
```

**tags_v2 table**:
```sql
CREATE TABLE tags_v2 (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name VARCHAR(100) NOT NULL,
  color VARCHAR(7) NOT NULL,  -- Hex color
  description TEXT,
  display_order INT,
  usage_count INT DEFAULT 0,
  is_archived BOOLEAN DEFAULT false,
  archived_at TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**strategy_tags table**:
```sql
CREATE TABLE strategy_tags (
  id UUID PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id),
  tag_id UUID REFERENCES tags_v2(id),
  assigned_at TIMESTAMP,
  assigned_by UUID REFERENCES users(id)
);
```

### C. API Response Examples

**GET /data/positions/details**:
```json
{
  "positions": [
    {
      "id": "pos-1",
      "symbol": "AAPL",
      "investment_class": "PUBLIC",
      "position_type": "LONG",
      "quantity": 100,
      "current_price": 150.00,
      "market_value": 15000.00,
      "cost_basis": 14000.00,
      "unrealized_pnl": 1000.00,
      "unrealized_pnl_percent": 7.14
    },
    {
      "id": "pos-2",
      "symbol": "TSLA",
      "investment_class": "PUBLIC",
      "position_type": "SHORT",
      "quantity": 50,
      "current_price": 800.00,
      "market_value": -40000.00,
      "cost_basis": -38000.00,
      "unrealized_pnl": -2000.00,
      "unrealized_pnl_percent": -5.26
    },
    {
      "id": "pos-3",
      "symbol": "SPY",
      "investment_class": "OPTIONS",
      "position_type": "LC",
      "quantity": 10,
      "current_price": 5.00,
      "market_value": 5000.00,
      "strike_price": 400.00,
      "expiration_date": "2025-10-15",
      "underlying_symbol": "SPY"
    }
  ]
}
```

**POST /strategies/combine**:
```json
// Request
{
  "portfolio_id": "pf-123",
  "name": "Tech Pairs",
  "strategy_type": "LONG",
  "description": "AAPL long vs GOOGL short",
  "position_ids": ["pos-1", "pos-2"]
}

// Response
{
  "id": "strat-456",
  "portfolio_id": "pf-123",
  "name": "Tech Pairs",
  "strategy_type": "LONG",
  "description": "AAPL long vs GOOGL short",
  "is_synthetic": true,
  "net_exposure": -25000.00,
  "total_cost_basis": 52000.00,
  "positions": [
    { "id": "pos-1", "symbol": "AAPL", ... },
    { "id": "pos-2", "symbol": "GOOGL", ... }
  ],
  "tags": [],
  "created_at": "2025-10-01T12:00:00Z"
}
```

**POST /strategies/{id}/tags**:
```json
// Request
{
  "tag_ids": ["tag-789"]
}

// Response - returns updated strategy with tags
{
  "id": "strat-456",
  "name": "Tech Pairs",
  "tags": [
    {
      "id": "tag-789",
      "name": "High Conviction",
      "color": "#10B981"
    }
  ],
  ...
}
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-01 | PRD Team | Initial draft based on mockups |
| 1.1 | 2025-10-01 | PRD Team | Added drag-and-drop specifications |
| 1.2 | 2025-10-01 | PRD Team | Clarified single positions as strategies |

---

**Document Status**: ✅ Ready for Development  
**Next Steps**: Review with development team, estimate timeline, begin Phase 1 implementation
