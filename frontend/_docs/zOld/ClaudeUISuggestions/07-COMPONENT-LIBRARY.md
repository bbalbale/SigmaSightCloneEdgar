# Component Library - Reusable UI Components

**Document Version**: 1.0
**Last Updated**: October 30, 2025

---

## Overview

This document specifies all new and modified components required for the frontend refactor. Components are organized by category and include TypeScript interfaces, props, and usage examples.

---

## Core Components

### 1. PortfolioHealthScore

**Purpose**: Composite metric showing overall portfolio status

```typescript
interface PortfolioHealthScoreProps {
  score: number  // 0-100
  beta: number
  volatility: number
  hhi: number
  loading?: boolean
  onDetailsClick?: () => void
}

<PortfolioHealthScore
  score={82}
  beta={1.15}
  volatility={0.18}
  hhi={0.08}
  onDetailsClick={() => console.log('Details clicked')}
/>
```

**Visual States**:
- 90-100: Excellent (green)
- 70-89: Good (blue)
- 50-69: Fair (yellow)
- <50: Poor (red)

---

### 2. ExposureGauge

**Purpose**: Visual representation of net exposure (-100% to +100%)

```typescript
interface ExposureGaugeProps {
  netExposure: number  // -1.0 to 1.0
  grossExposure: number
  longExposure: number
  shortExposure: number
  size?: 'small' | 'medium' | 'large'
}

<ExposureGauge
  netExposure={0.20}  // 20% net long
  grossExposure={500000}
  longExposure={300000}
  shortExposure={200000}
  size="large"
/>
```

---

### 3. MetricCard

**Purpose**: Reusable card for displaying key metrics

```typescript
interface MetricCardProps {
  title: string
  value: number | string
  change?: {
    amount: number
    percentage: number
    period: 'MTD' | 'YTD' | 'QTD'
  }
  sparkline?: number[]  // Historical values for trend chart
  footer?: ReactNode  // Optional footer content
  loading?: boolean
  onClick?: () => void
}

<MetricCard
  title="Net Worth"
  value={500000}
  change={{ amount: 12500, percentage: 2.5, period: 'MTD' }}
  sparkline={[480000, 485000, 490000, 495000, 500000]}
  onClick={() => navigate('/positions')}
/>
```

---

### 4. AIInsightCard

**Purpose**: Proactive AI-generated insight/alert

```typescript
interface AIInsightCardProps {
  type: 'warning' | 'info' | 'success' | 'suggestion'
  title: string
  summary: string
  actions: Array<{
    label: string
    onClick: () => void
    variant?: 'primary' | 'secondary'
  }>
  dismissible?: boolean
  onDismiss?: () => void
}

<AIInsightCard
  type="warning"
  title="Tech Concentration Alert"
  summary="Your tech exposure is 45%, +15% above S&P 500..."
  actions={[
    { label: 'AI Explain', onClick: openAI },
    { label: 'Suggest Rebalancing', onClick: rebalance }
  ]}
  dismissible
  onDismiss={() => console.log('Dismissed')}
/>
```

---

### 5. SectorExposureChart

**Purpose**: Bar chart showing sector weights vs benchmark

```typescript
interface SectorExposureChartProps {
  portfolioExposures: Record<string, number>  // { 'Technology': 0.45, ... }
  benchmarkExposures: Record<string, number>  // S&P 500 weights
  onClick?: (sector: string) => void
  maxSectors?: number  // Show top N sectors, default 10
}

<SectorExposureChart
  portfolioExposures={{ 'Technology': 0.45, 'Financials': 0.12, ... }}
  benchmarkExposures={{ 'Technology': 0.30, 'Financials': 0.13, ... }}
  onClick={(sector) => filterBySector(sector)}
  maxSectors={5}
/>
```

---

### 6. PositionCard

**Purpose**: Card displaying position details with quick actions

```typescript
interface PositionCardProps {
  position: {
    symbol: string
    name: string
    quantity: number
    avgCost: number
    currentPrice: number
    marketValue: number
    unrealizedPnL: number
    unrealizedPnLPct: number
    positionType: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
    sector?: string
    tags?: string[]
    beta?: number
  }
  selectable?: boolean
  selected?: boolean
  onSelect?: (symbol: string) => void
  onAnalyzeRisk?: () => void
  onAIExplain?: () => void
}

<PositionCard
  position={nvdaPosition}
  selectable
  selected={false}
  onSelect={(symbol) => toggleSelection(symbol)}
  onAnalyzeRisk={() => openSidePanel(nvdaPosition)}
  onAIExplain={() => explainPosition(nvdaPosition)}
/>
```

---

### 7. AIExplainButton

**Purpose**: Contextual "AI Explain" button

```typescript
interface AIExplainButtonProps {
  context: {
    type: 'position' | 'metric' | 'chart' | 'general'
    data: any
  }
  prompt?: string  // Custom prompt, or auto-generated from context
  size?: 'small' | 'medium' | 'large'
  variant?: 'primary' | 'secondary' | 'ghost'
}

<AIExplainButton
  context={{
    type: 'position',
    data: { symbol: 'NVDA', value: 88000, pnl_pct: 0.158 }
  }}
  prompt="Explain this position and whether I should trim"
  size="small"
  variant="ghost"
/>
```

---

### 8. AICopilotSidebar

**Purpose**: Persistent AI sidebar component

```typescript
interface AICopilotSidebarProps {
  isOpen: boolean
  context: AIContext  // Auto-injected page context
  conversationId?: string
  onClose: () => void
  onMessage?: (message: string) => void
}

<AICopilotSidebar
  isOpen={sidebarOpen}
  context={{ page: '/command-center', portfolio_id: '123' }}
  conversationId={currentConversationId}
  onClose={() => setSidebarOpen(false)}
  onMessage={(msg) => console.log('User sent:', msg)}
/>
```

**Internal Components**:
- `ChatInput`: Text input with send button
- `ChatMessage`: Individual message bubble (user/AI)
- `QuickActions`: Pre-defined prompt buttons
- `InsightsList`: Proactive insights/alerts
- `ConversationHistory`: Past conversations

---

## Navigation Components

### 9. TopNavigationBar

```typescript
interface TopNavigationBarProps {
  activeWorkspace: 'command-center' | 'positions' | 'risk' | 'organize'
  user: {
    name: string
    email: string
    avatar?: string
  }
  portfolioName?: string
  aiSidebarOpen: boolean
  onWorkspaceChange: (workspace: string) => void
  onAIToggle: () => void
  onLogout: () => void
}
```

---

### 10. WorkspaceTabs

```typescript
interface WorkspaceTabsProps {
  tabs: Array<{
    value: string
    label: string
    icon?: ReactNode
  }>
  activeTab: string
  onChange: (tab: string) => void
}

<WorkspaceTabs
  tabs={[
    { value: 'all', label: 'All' },
    { value: 'long', label: 'Long' },
    { value: 'short', label: 'Short' },
    { value: 'options', label: 'Options' },
    { value: 'private', label: 'Private' }
  ]}
  activeTab="long"
  onChange={(tab) => setActiveTab(tab)}
/>
```

---

### 11. BottomNavigation (Mobile)

```typescript
interface BottomNavigationProps {
  items: Array<{
    value: string
    label: string
    icon: ReactNode
    badge?: number
  }>
  activeValue: string
  onChange: (value: string) => void
}
```

---

## Data Display Components

### 12. CorrelationMatrix

```typescript
interface CorrelationMatrixProps {
  correlations: Record<string, Record<string, number>>
  symbols: string[]
  onClick?: (symbol1: string, symbol2: string) => void
  highlightThreshold?: number  // Highlight correlations > threshold
}
```

---

### 13. StressTestCard

```typescript
interface StressTestCardProps {
  scenario: {
    name: string
    description: string
    expectedImpact: number
    expectedImpactPct: number
  }
  onRunTest: () => void
  loading?: boolean
}
```

---

### 14. ActivityFeedItem

```typescript
interface ActivityFeedItemProps {
  activity: {
    type: 'price_change' | 'volatility_change' | 'sector_change' | 'insight'
    timestamp: Date
    description: string
    relatedEntity?: { type: 'position' | 'sector', value: string }
  }
  onClick?: () => void
}
```

---

## Form Components

### 15. TagInput

```typescript
interface TagInputProps {
  tags: string[]
  availableTags: Array<{ id: string; name: string; color: string }>
  onTagsChange: (tags: string[]) => void
  aiSuggestions?: string[]  // AI-suggested tags
  onAcceptAISuggestions?: () => void
}
```

---

### 16. TargetPriceModal

```typescript
interface TargetPriceModalProps {
  position: { symbol: string; currentPrice: number }
  existingTarget?: { price: number; date: string }
  isOpen: boolean
  onClose: () => void
  onSave: (target: { price: number; note?: string }) => void
}
```

---

## Utility Components

### 17. LoadingSkeleton

```typescript
interface LoadingSkeletonProps {
  variant: 'card' | 'table' | 'chart' | 'sidebar'
  count?: number  // Number of skeleton items
}

<LoadingSkeleton variant="card" count={3} />
```

---

### 18. EmptyState

```typescript
interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

<EmptyState
  icon={<ChartIcon />}
  title="No positions yet"
  description="Start by adding positions to your portfolio"
  action={{ label: 'Add Position', onClick: openAddModal }}
/>
```

---

## Component Design System

**Colors**:
- Primary: `#3B82F6` (Blue)
- Success: `#10B981` (Green)
- Warning: `#F59E0B` (Orange)
- Danger: `#EF4444` (Red)
- Neutral: `#6B7280` (Gray)

**Typography**:
- Heading: Inter Bold
- Body: Inter Regular
- Monospace: Roboto Mono (for numbers, tickers)

**Spacing**:
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px

**Border Radius**:
- sm: 4px
- md: 8px
- lg: 12px
- xl: 16px

**Shadows**:
- sm: `0 1px 2px rgba(0,0,0,0.05)`
- md: `0 4px 6px rgba(0,0,0,0.1)`
- lg: `0 10px 15px rgba(0,0,0,0.1)`

---

## Component File Structure

```
src/components/
├── core/
│   ├── PortfolioHealthScore/
│   │   ├── index.tsx
│   │   ├── types.ts
│   │   └── styles.ts
│   ├── ExposureGauge/
│   ├── MetricCard/
│   └── ...
├── ai/
│   ├── AICopilotSidebar/
│   ├── AIInsightCard/
│   ├── AIExplainButton/
│   └── ...
├── navigation/
│   ├── TopNavigationBar/
│   ├── WorkspaceTabs/
│   ├── BottomNavigation/
│   └── ...
├── positions/
│   ├── PositionCard/
│   ├── PositionTable/
│   ├── PositionSidePanel/
│   └── ...
├── risk/
│   ├── SectorExposureChart/
│   ├── CorrelationMatrix/
│   ├── StressTestCard/
│   └── ...
└── ui/
    ├── Button/
    ├── Input/
    ├── Modal/
    ├── LoadingSkeleton/
    └── ...
```

---

## Storybook Integration

All components should have Storybook stories for:
- Default state
- Loading state
- Error state
- Empty state
- Interactive variants

**Example Story**:
```typescript
// PortfolioHealthScore.stories.tsx
export default {
  title: 'Core/PortfolioHealthScore',
  component: PortfolioHealthScore
}

export const Excellent = {
  args: {
    score: 92,
    beta: 1.05,
    volatility: 0.12,
    hhi: 0.05
  }
}

export const Poor = {
  args: {
    score: 38,
    beta: 1.85,
    volatility: 0.35,
    hhi: 0.22
  }
}

export const Loading = {
  args: {
    score: 0,
    loading: true
  }
}
```

**Next**: See `08-MOBILE-RESPONSIVE-DESIGN.md` for mobile-specific patterns.
