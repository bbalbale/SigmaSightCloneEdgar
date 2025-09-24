# SigmaSight UI Refactor - Product Requirements Document

**Version**: 1.0.0
**Date**: September 23, 2025
**Status**: Planning Phase
**Scope**: Complete UI refactor with navigation-based multi-page architecture

---

## Executive Summary

Complete refactor of the SigmaSight frontend from a single-page portfolio view to a comprehensive multi-page application with navigation, strategy management, tagging, and chat integration. The new architecture will leverage ShadCN components exclusively and follow established design principles while introducing a proper information architecture.

### Key Changes
- **From**: Single portfolio page → **To**: Multi-page navigation structure
- **From**: Basic position cards → **To**: Strategy-aware grouped positions with tagging
- **From**: Inline chat → **To**: Dedicated chat page with context awareness
- **New**: Strategy management UI with drag-and-drop
- **New**: Tag management system with visual organization
- **New**: Target price management interface

---

## 1. Information Architecture

### 1.1 Navigation Structure

```
SigmaSight App
├── 🏠 Home (Dashboard)
│   ├── Portfolio Metrics Summary
│   ├── Factor Exposure Cards
│   └── Position Overview Grid
│       ├── Public Positions Section
│       │   ├── Long Positions Row
│       │   ├── Short Positions Row
│       │   └── Options Row
│       └── Private Positions Section
│
├── 📈 Positions (Sub-menu)
│   ├── Long Positions
│   ├── Short Positions
│   ├── Options
│   └── Private Investments
│
├── 🎯 Strategies
│   ├── Strategy Overview
│   ├── Create/Combine
│   └── Pattern Detection
│
├── 🏷️ Tags
│   ├── Tag Manager
│   └── Tag Analytics
│
├── 💬 Chat
│   ├── Conversation View
│   └── Portfolio Context Panel
│
└── ⚙️ Settings
    ├── Portfolio Settings
    ├── Target Prices
    └── User Preferences
```

### 1.2 Page Hierarchy

**Primary Navigation** (Always visible sidebar):
- Home
- Positions (with sub-navigation)
- Strategies
- Tags
- Chat
- Settings

**Secondary Navigation** (Context-specific):
- Within Positions: Filter by tags, strategy type
- Within Strategies: View mode (list/grid/grouped)
- Within Chat: Conversation history, mode selector

---

## 2. Page Specifications

### 2.1 Home Dashboard Page

**Purpose**: High-level portfolio overview with quick access to all key metrics

**Layout Structure**:
```
┌─────────────────────────────────────────────────────────┐
│                    Top Navigation Bar                    │
│  [Logo] [Search] [Notifications] [User Menu] [Theme]    │
├───────────┬─────────────────────────────────────────────┤
│           │                                             │
│    Side   │         Portfolio Metrics Cards            │
│    Nav    │    [Total Value] [P&L] [Risk] [Exposure]  │
│           │                                             │
│  [Home]   ├─────────────────────────────────────────────┤
│  [Pos.]   │                                             │
│  [Strat.] │         Factor Exposure Cards              │
│  [Tags]   │    (Grid of 6-8 factor cards)              │
│  [Chat]   │                                             │
│  [Set.]   ├─────────────────────────────────────────────┤
│           │                                             │
│           │    Public Positions Overview               │
│           │    ┌─────────────────────────────┐        │
│           │    │ Long Positions (12 cards)    │        │
│           │    ├─────────────────────────────┤        │
│           │    │ Short Positions (4 cards)    │        │
│           │    ├─────────────────────────────┤        │
│           │    │ Options (8 cards)            │        │
│           │    └─────────────────────────────┘        │
│           │                                             │
│           │    Private Positions Overview              │
│           │    ┌─────────────────────────────┐        │
│           │    │ Alternative Investments      │        │
│           │    └─────────────────────────────┘        │
└───────────┴─────────────────────────────────────────────┘
```

**Components**:

#### Portfolio Metrics Cards
```tsx
<Card className="hover:shadow-lg transition-shadow">
  <CardHeader className="flex flex-row items-center justify-between pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">
      Total Portfolio Value
    </CardTitle>
    <TrendingUp className="h-4 w-4 text-green-500" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">$2,456,789</div>
    <p className="text-xs text-muted-foreground">
      +12.3% from last month
    </p>
  </CardContent>
</Card>
```

#### Position Overview Card
```tsx
<Card className="group hover:shadow-md transition-all cursor-pointer">
  <CardContent className="p-4">
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold">AAPL</h4>
          {strategy.is_synthetic && (
            <Badge variant="outline" className="text-xs">
              {strategy.type}
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">100 shares</p>
      </div>
      <div className="text-right">
        <p className="font-semibold text-green-600">+$15,420</p>
        <p className="text-xs text-muted-foreground">+18.5%</p>
      </div>
    </div>
    <div className="flex gap-1 mt-2">
      {tags.map(tag => (
        <Badge
          key={tag.id}
          style={{backgroundColor: tag.color}}
          className="text-xs"
        >
          {tag.name}
        </Badge>
      ))}
    </div>
  </CardContent>
</Card>
```

### 2.2 Positions Pages (Long/Short/Options/Private)

**Purpose**: Detailed view and management of specific position types

**Features**:
- List/Grid view toggle
- Filter by tags, date range, P&L
- Bulk actions (tag, combine into strategy)
- Target price management
- Export functionality

**Layout** (Long Positions Example):
```
┌─────────────────────────────────────────────────────────┐
│                 Long Positions                          │
│                                                         │
│  [Filter Tags ▼] [Date Range] [View: Grid/List] [Export]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Selected: 3 positions  [Add Tags] [Create Strategy]    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ □ AAPL - 100 shares                             │   │
│  │   Cost: $15,000 | Current: $18,500 | P&L: +23% │   │
│  │   Target: $195 | Tags: [tech] [growth]         │   │
│  │   [Edit Target] [Manage Tags] [View Details]    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ □ MSFT - 50 shares                              │   │
│  │   ...                                           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Position Detail View** (Modal/Sheet):
```tsx
<Sheet>
  <SheetContent className="w-[600px]">
    <SheetHeader>
      <SheetTitle>AAPL Position Details</SheetTitle>
    </SheetHeader>

    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="performance">Performance</TabsTrigger>
        <TabsTrigger value="strategy">Strategy</TabsTrigger>
        <TabsTrigger value="history">History</TabsTrigger>
      </TabsList>

      <TabsContent value="overview">
        {/* Position metrics, current value, P&L */}
      </TabsContent>

      <TabsContent value="strategy">
        {/* Strategy assignment, combination options */}
      </TabsContent>
    </Tabs>
  </SheetContent>
</Sheet>
```

### 2.3 Strategies Page

**Purpose**: Manage multi-leg strategies and virtual positions

**Features**:
- Strategy overview with expandable legs
- Pattern detection for uncombined positions
- Create custom strategies
- Strategy templates
- Performance analytics by strategy type

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│                    Strategies                           │
│                                                         │
│  [Create Strategy] [Detect Patterns] [Templates ▼]      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Suggested Strategies (Auto-detected)                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ⚡ Potential Iron Condor detected                │   │
│  │    SPY Options: 4 positions match pattern       │   │
│  │    [Review] [Create Strategy]                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Active Strategies                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ▼ Iron Condor SPY Dec        P&L: +$2,450      │   │
│  │   │ Net Delta: 0.02 | Theta: -45 | Max Loss: $5k│   │
│  │   ├── Short Call SPY 450 Dec                    │   │
│  │   ├── Long Call SPY 460 Dec                     │   │
│  │   ├── Short Put SPY 420 Dec                     │   │
│  │   └── Long Put SPY 410 Dec                      │   │
│  │   Tags: [income] [neutral] [options]            │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ ▶ Covered Call NVDA          P&L: +$890        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Strategy Creation Dialog**:
```tsx
<Dialog>
  <DialogContent className="max-w-2xl">
    <DialogHeader>
      <DialogTitle>Create Strategy</DialogTitle>
    </DialogHeader>

    <div className="space-y-4">
      <div>
        <Label>Strategy Type</Label>
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Select type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="covered_call">Covered Call</SelectItem>
            <SelectItem value="iron_condor">Iron Condor</SelectItem>
            <SelectItem value="custom">Custom</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>Select Positions</Label>
        <div className="border rounded-lg p-4">
          {/* Drag and drop area for positions */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border-2 border-dashed p-4">
              <p className="text-sm text-muted-foreground">
                Drag positions here
              </p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <Label>Strategy Name</Label>
        <Input placeholder="e.g., SPY Iron Condor Dec" />
      </div>
    </div>

    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button>Create Strategy</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### 2.4 Tags Page

**Purpose**: Organize and manage portfolio tags

**Features**:
- Tag creation and management
- Color customization
- Usage statistics
- Bulk tag operations
- Tag performance analytics

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│                      Tag Manager                        │
│                                                         │
│  [Create Tag] [Import] [Export]         Usage: 15/100   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Your Tags                                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🏷️ tech                                         │   │
│  │   Color: [#4A90E2] | Used: 12 positions         │   │
│  │   Performance: +18.5% avg                       │   │
│  │   [Edit] [Delete]                               │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 🏷️ defensive                                    │   │
│  │   Color: [#7C3AED] | Used: 5 positions          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Tag Analytics                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Performance by Tag (Chart)                      │   │
│  │ [Bar chart showing returns by tag]              │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.5 Chat Page

**Purpose**: AI-powered portfolio assistant with full context

**Features**:
- Conversation history
- Mode selection (4 modes as existing)
- Portfolio context panel
- Quick actions from chat responses
- Export conversation

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│                    Portfolio Assistant                   │
├─────────┬────────────────────────────────┬──────────────┤
│         │                                 │              │
│ History │      Conversation Area         │   Context    │
│         │                                 │              │
│ [Conv1] │ ┌─────────────────────────────┐│ Portfolio:   │
│ [Conv2] │ │ AI: How can I help you      ││ HNW          │
│ [Conv3] │ │     analyze your portfolio? ││              │
│ [+New]  │ ├─────────────────────────────┤│ Strategies:  │
│         │ │ You: What are my biggest    ││ 5 active     │
│         │ │      risks?                 ││              │
│         │ ├─────────────────────────────┤│ Top Holdings:│
│         │ │ AI: Based on your portfolio,││ AAPL 15%     │
│         │ │     your main risks are...  ││ MSFT 12%     │
│         │ └─────────────────────────────┘│ NVDA 10%     │
│         │                                 │              │
│         │ [Message input box]            │ Quick Stats: │
│         │ [Send] [Mode: Analytical ▼]    │ P&L: +18.5%  │
└─────────┴────────────────────────────────┴──────────────┘
```

---

## 3. Component Design System

### 3.1 Design Tokens

```typescript
// colors.ts
export const colors = {
  primary: {
    50: '#EFF6FF',
    500: '#3B82F6',  // Primary blue
    900: '#1E3A8A'
  },
  success: {
    50: '#F0FDF4',
    500: '#10B981',
    900: '#064E3B'
  },
  warning: {
    50: '#FFFBEB',
    500: '#F59E0B',
    900: '#78350F'
  },
  danger: {
    50: '#FEF2F2',
    500: '#EF4444',
    900: '#7F1D1D'
  },
  neutral: {
    50: '#FAFAFA',
    100: '#F4F4F5',
    200: '#E4E4E7',
    300: '#D4D4D8',
    400: '#A1A1AA',
    500: '#71717A',
    600: '#52525B',
    700: '#3F3F46',
    800: '#27272A',
    900: '#18181B'
  }
}

// spacing.ts
export const spacing = {
  xs: '0.5rem',   // 8px
  sm: '1rem',     // 16px
  md: '1.5rem',   // 24px
  lg: '2rem',     // 32px
  xl: '3rem',     // 48px
  '2xl': '4rem'   // 64px
}

// typography.ts
export const typography = {
  fonts: {
    sans: 'Inter, system-ui, sans-serif',
    mono: 'JetBrains Mono, monospace'
  },
  sizes: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '2rem',    // 32px
    '4xl': '2.5rem'   // 40px
  }
}
```

### 3.2 Core Components (ShadCN-based)

#### Strategy Card Component
```tsx
interface StrategyCardProps {
  strategy: Strategy
  tags: Tag[]
  expanded: boolean
  onToggle: () => void
  onTagClick: (tag: Tag) => void
}

export function StrategyCard({
  strategy,
  tags,
  expanded,
  onToggle,
  onTagClick
}: StrategyCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/50"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {expanded ? <ChevronDown /> : <ChevronRight />}
            <CardTitle className="text-lg">
              {strategy.name}
            </CardTitle>
            {strategy.is_synthetic && (
              <Badge variant="secondary">
                {strategy.legs.length} legs
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm text-muted-foreground">P&L</p>
              <p className={cn(
                "font-semibold",
                strategy.pnl >= 0 ? "text-green-600" : "text-red-600"
              )}>
                {formatCurrency(strategy.pnl)}
              </p>
            </div>
          </div>
        </div>
        <div className="flex gap-1 mt-2">
          {tags.map(tag => (
            <Badge
              key={tag.id}
              variant="outline"
              style={{borderColor: tag.color, color: tag.color}}
              className="cursor-pointer hover:bg-muted"
              onClick={(e) => {
                e.stopPropagation()
                onTagClick(tag)
              }}
            >
              {tag.name}
            </Badge>
          ))}
        </div>
      </CardHeader>

      {expanded && strategy.is_synthetic && (
        <CardContent>
          <div className="space-y-2 pl-6">
            {strategy.legs.map(leg => (
              <div key={leg.id} className="flex justify-between py-2 border-b last:border-0">
                <span className="text-sm">{leg.description}</span>
                <span className="text-sm font-medium">{formatCurrency(leg.value)}</span>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t">
            <div>
              <p className="text-xs text-muted-foreground">Net Delta</p>
              <p className="font-medium">{strategy.net_delta}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Theta</p>
              <p className="font-medium">{strategy.theta}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Profit</p>
              <p className="font-medium text-green-600">{formatCurrency(strategy.max_profit)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Loss</p>
              <p className="font-medium text-red-600">{formatCurrency(strategy.max_loss)}</p>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}
```

#### Tag Manager Component
```tsx
export function TagManager({
  tags,
  onCreateTag,
  onEditTag,
  onDeleteTag
}: TagManagerProps) {
  const [isCreating, setIsCreating] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Your Tags</h3>
        <Button
          onClick={() => setIsCreating(true)}
          size="sm"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Tag
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tags.map(tag => (
          <Card key={tag.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{backgroundColor: tag.color}}
                  />
                  <span className="font-medium">{tag.name}</span>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger>
                    <MoreHorizontal className="h-4 w-4" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => onEditTag(tag)}>
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => onDeleteTag(tag)}
                      className="text-red-600"
                    >
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <div className="mt-2 text-sm text-muted-foreground">
                Used in {tag.usage_count} strategies
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <TagCreationDialog
        open={isCreating}
        onClose={() => setIsCreating(false)}
        onCreate={onCreateTag}
      />
    </div>
  )
}
```

### 3.3 Drag and Drop System

```tsx
// Using @dnd-kit/sortable for drag and drop
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'

export function DraggablePositionGrid({
  positions,
  onDragEnd,
  onCombineIntoStrategy
}: DraggablePositionGridProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor)
  )

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {positions.map(position => (
          <DraggablePositionCard
            key={position.id}
            position={position}
          />
        ))}
      </div>

      <DropZone
        label="Drop here to create strategy"
        onDrop={onCombineIntoStrategy}
      />

      <DragOverlay>
        {/* Preview of dragged item */}
      </DragOverlay>
    </DndContext>
  )
}
```

---

## 4. Navigation Component

### 4.1 Sidebar Navigation

```tsx
export function AppSidebar() {
  const pathname = usePathname()

  const navItems = [
    {
      icon: Home,
      label: 'Home',
      href: '/dashboard',
      badge: null
    },
    {
      icon: TrendingUp,
      label: 'Positions',
      href: '/positions',
      badge: null,
      subItems: [
        { label: 'Long', href: '/positions/long' },
        { label: 'Short', href: '/positions/short' },
        { label: 'Options', href: '/positions/options' },
        { label: 'Private', href: '/positions/private' }
      ]
    },
    {
      icon: Layers,
      label: 'Strategies',
      href: '/strategies',
      badge: '5'
    },
    {
      icon: Tags,
      label: 'Tags',
      href: '/tags',
      badge: '15'
    },
    {
      icon: MessageSquare,
      label: 'Chat',
      href: '/chat',
      badge: null
    },
    {
      icon: Settings,
      label: 'Settings',
      href: '/settings',
      badge: null
    }
  ]

  return (
    <div className="flex h-screen w-64 flex-col fixed left-0 top-0 border-r bg-background">
      <div className="p-6">
        <h2 className="text-2xl font-bold">SigmaSight</h2>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {navItems.map(item => (
          <NavItem
            key={item.href}
            {...item}
            isActive={pathname.startsWith(item.href)}
          />
        ))}
      </nav>

      <div className="p-4 border-t">
        <Button variant="outline" className="w-full justify-start">
          <LogOut className="h-4 w-4 mr-2" />
          Logout
        </Button>
      </div>
    </div>
  )
}

function NavItem({ icon: Icon, label, href, badge, subItems, isActive }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div>
      <Link
        href={href}
        className={cn(
          "flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "hover:bg-muted"
        )}
        onClick={() => subItems && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Icon className="h-4 w-4" />
          <span>{label}</span>
        </div>
        {badge && (
          <Badge variant="secondary" className="ml-auto">
            {badge}
          </Badge>
        )}
        {subItems && (
          <ChevronRight className={cn(
            "h-4 w-4 transition-transform",
            expanded && "rotate-90"
          )} />
        )}
      </Link>

      {expanded && subItems && (
        <div className="ml-7 mt-1 space-y-1">
          {subItems.map(subItem => (
            <Link
              key={subItem.href}
              href={subItem.href}
              className="block rounded-lg px-3 py-1.5 text-sm hover:bg-muted"
            >
              {subItem.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## 5. Responsive Design Strategy

### 5.1 Breakpoints
```css
/* Tailwind default breakpoints */
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
2xl: 1536px /* Extra large */
```

### 5.2 Mobile Adaptations

**Mobile Navigation**:
- Sidebar becomes bottom tab bar
- Hamburger menu for secondary options
- Swipe gestures for page transitions

**Mobile Cards**:
- Stack vertically
- Swipeable actions (edit, delete)
- Expandable details

**Mobile Tables**:
- Horizontal scroll for wide tables
- Card view alternative for data

---

## 6. State Management

### 6.1 Store Structure

```typescript
// stores/strategyStore.ts
interface StrategyStore {
  strategies: Strategy[]
  selectedStrategies: string[]
  isCreatingStrategy: boolean

  // Actions
  loadStrategies: () => Promise<void>
  createStrategy: (data: CreateStrategyData) => Promise<void>
  combinePositions: (positionIds: string[], type: string) => Promise<void>
  detectPatterns: () => Promise<SuggestedStrategy[]>
  toggleStrategySelection: (id: string) => void
}

// stores/tagStore.ts
interface TagStore {
  tags: Tag[]
  selectedTags: string[]
  filterMode: 'AND' | 'OR'

  // Actions
  loadTags: () => Promise<void>
  createTag: (data: CreateTagData) => Promise<void>
  assignTags: (strategyIds: string[], tagIds: string[]) => Promise<void>
  filterByTags: (tagIds: string[]) => void
}

// stores/navigationStore.ts
interface NavigationStore {
  currentPage: string
  sidebarExpanded: boolean
  mobileMenuOpen: boolean

  // Actions
  navigateTo: (page: string) => void
  toggleSidebar: () => void
  toggleMobileMenu: () => void
}
```

---

## 7. API Integration Points

### 7.1 New Endpoints Required

```typescript
// Strategy APIs
GET    /api/v1/strategies
POST   /api/v1/strategies
PUT    /api/v1/strategies/{id}
DELETE /api/v1/strategies/{id}
POST   /api/v1/strategies/combine
POST   /api/v1/strategies/detect

// Tag APIs
GET    /api/v1/tags
POST   /api/v1/tags
PUT    /api/v1/tags/{id}
DELETE /api/v1/tags/{id}
POST   /api/v1/tags/bulk-assign

// Enhanced Position APIs
GET    /api/v1/positions?type={type}&tags={tags}
PUT    /api/v1/positions/{id}/target-price
POST   /api/v1/positions/bulk-action

// Portfolio Overview
GET    /api/v1/portfolios/{id}/dashboard
GET    /api/v1/portfolios/{id}/strategies
GET    /api/v1/portfolios/{id}/tags/analytics
```

### 7.2 Real-time Updates

```typescript
// WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws')

ws.on('strategy:created', (strategy) => {
  strategyStore.addStrategy(strategy)
})

ws.on('position:updated', (position) => {
  positionStore.updatePosition(position)
})

ws.on('market:update', (data) => {
  marketStore.updatePrices(data)
})
```

---

## 8. Performance Optimizations

### 8.1 Code Splitting
```typescript
// Lazy load pages
const StrategiesPage = lazy(() => import('./pages/Strategies'))
const ChatPage = lazy(() => import('./pages/Chat'))
const SettingsPage = lazy(() => import('./pages/Settings'))
```

### 8.2 Data Virtualization
```typescript
// Virtual scrolling for large lists
import { VirtualList } from '@tanstack/react-virtual'

// Use for position lists > 50 items
```

### 8.3 Caching Strategy
```typescript
// SWR for data fetching
import useSWR from 'swr'

const { data: strategies } = useSWR(
  '/api/v1/strategies',
  fetcher,
  {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    refreshInterval: 30000 // 30 seconds
  }
)
```

---

## 9. Accessibility Requirements

### 9.1 WCAG AA Compliance
- Color contrast ratios ≥ 4.5:1 for normal text
- Color contrast ratios ≥ 3:1 for large text
- All interactive elements keyboard accessible
- Focus indicators visible
- Screen reader announcements for dynamic content

### 9.2 Keyboard Navigation
```
Tab         - Navigate between elements
Shift+Tab   - Navigate backwards
Enter       - Activate buttons/links
Space       - Toggle checkboxes/expand
Arrow keys  - Navigate within components
Escape      - Close modals/dialogs
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
- Set up navigation structure
- Create layout components
- Implement routing
- Basic Home dashboard

### Phase 2: Core Pages (Week 2)
- Position pages (Long/Short/Options/Private)
- Basic CRUD operations
- Filter and search functionality

### Phase 3: Strategy System (Week 3)
- Strategy page implementation
- Drag and drop functionality
- Pattern detection UI
- Strategy creation flow

### Phase 4: Tag System (Week 4)
- Tag manager page
- Tag assignment UI
- Filter by tags
- Tag analytics

### Phase 5: Chat & Polish (Week 5)
- Chat page with context
- Settings pages
- Performance optimization
- Mobile responsive adjustments

### Phase 6: Testing & Launch (Week 6)
- End-to-end testing
- Performance testing
- Bug fixes
- Documentation

---

## 11. Success Metrics

### User Experience
- Page load time < 1s
- Time to complete common tasks reduced by 50%
- Mobile usability score > 95

### Technical
- Lighthouse score > 90
- Bundle size < 500KB
- 90% code coverage

### Business
- User engagement increase by 40%
- Feature adoption rate > 70%
- Support tickets reduced by 30%

---

## Document History

- **v1.0.0** (2025-09-23): Initial UI refactor PRD with comprehensive multi-page architecture