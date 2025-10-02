# UI Component Strategy: Reusable Position Card System

**Author**: Claude Code
**Date**: 2025-10-01
**Last Updated**: 2025-10-01
**Status**: Implementation Complete ✅

## Recent Updates (October 1, 2025)

**Combination View Deployed**: The reusable position card system has been successfully extended to support strategies through the new Combination View toggle on the Portfolio page:
- `PortfolioStrategiesView.tsx` uses the same 3-column grid layout as position view
- `StrategyPositionList.tsx` wraps position cards to display strategy positions
- Same visual consistency maintained across both Position and Combination views
- View toggle allows seamless switching between positions and strategies

## Executive Summary

This document outlines the strategy for creating a reusable, maintainable component system for position cards in the SigmaSight frontend. The goal is to eliminate code duplication, ensure visual consistency, and enable easy reuse across multiple pages while maintaining the current UX exactly.

---

## Problem Statement

### Current State

We have three types of position cards displaying portfolio positions:

1. **PositionCard.tsx** - Stock/ETF positions (53 lines)
2. **OptionCard.tsx** - Options contracts (46 lines)
3. **PrivatePositions.tsx** - Private investments with inline rendering (75 lines)

### Key Issues

1. **Code Duplication**: ~40 lines of identical JSX repeated across components
2. **Inconsistency**: PrivatePositions renders cards inline while others use separate components
3. **Tight Coupling**: Presentation logic mixed with domain-specific business logic
4. **Non-Reusable**: Difficult to reuse on other pages without bringing along specific logic
5. **Maintenance Burden**: Styling changes require updates in 3+ places
6. **Extension Difficulty**: Adding new position types requires duplicating entire card structure

### Visual Pattern (Current)

All three card types follow this identical structure:

```tsx
<Card theme-classes cursor-pointer>
  <CardContent className="p-4">
    <div flex justify-between items-start>
      <div>                              {/* Left side */}
        <div font-semibold>Symbol</div>
        <div text-xs>Subtitle</div>
      </div>
      <div text-right>                   {/* Right side */}
        <div font-medium>Value</div>
        <div colored>P&L</div>
      </div>
    </div>
  </CardContent>
</Card>
```

The **only** differences are:
- Subtitle content (company name vs option type vs investment subtype)
- Formatting functions (formatNumber vs formatCurrency)
- Data extraction logic

---

## Proposed Solution: Layered Component Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Pages Layer                              │
│  (Portfolio, Organize, Public Positions, Private Positions)     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Container Layer                              │
│        (PublicPositions, OptionsPositions, etc.)                │
└──────────────────────┬──────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Adapter Layer                          │
│   StockPositionCard │ OptionPositionCard │ Private...   │
│   (Domain-specific logic & data transformation)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Presentation Layer                       │
│              BasePositionCard.tsx                       │
│            (Pure visual component)                      │
└─────────────────────────────────────────────────────────┘
```

### Component Hierarchy

#### 1. Presentation Layer (New)

**BasePositionCard.tsx** - Pure presentation component
- No business logic
- Accepts fully-formatted strings as props
- Handles theme and hover states
- ~30 lines total

```typescript
interface BasePositionCardProps {
  primaryText: string      // "AAPL" or "NVDA251017C00800000"
  secondaryText: string    // "Apple Inc." or "Long Call"
  primaryValue: string     // "$382.7K" (pre-formatted)
  secondaryValue: string   // "+$45.2K" (pre-formatted with color class)
  secondaryValueColor: 'positive' | 'negative' | 'neutral'
  onClick?: () => void
}
```

**PositionSectionHeader.tsx** - Reusable section header
- Title + count badge
- Theme-aware styling
- ~15 lines

**PositionList.tsx** - Generic list container
- Maps array of items to cards
- Handles empty state
- Spacing between cards
- ~20 lines

#### 2. Adapter Layer (New)

These components transform domain data into BasePositionCard props:

**StockPositionCard.tsx**
```typescript
interface StockPosition {
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: 'LONG' | 'SHORT'
}

// Transforms to BasePositionCardProps:
// - Looks up company name
// - Formats numbers with formatNumber()
// - Determines color from positive flag
```

**OptionPositionCard.tsx**
```typescript
interface OptionPosition {
  symbol: string
  type: 'LC' | 'LP' | 'SC' | 'SP'
  marketValue: number
  pnl: number
}

// Transforms to BasePositionCardProps:
// - Maps type to label ("LC" → "Long Call")
// - Formats numbers with formatCurrency()
// - Determines color from pnl value
```

**PrivatePositionCard.tsx**
```typescript
interface PrivatePosition {
  symbol: string
  investment_subtype?: string
  marketValue: number
  pnl: number
}

// Transforms to BasePositionCardProps:
// - Uses investment_subtype as secondary
// - Formats numbers with formatCurrency()
// - Determines color from pnl value
```

#### 3. Container Layer (Existing, to be refactored)

**PublicPositions.tsx**
- Maps array of positions to StockPositionCard
- Uses PositionList for layout

**OptionsPositions.tsx**
- Maps array of positions to OptionPositionCard
- Uses PositionList for layout

**PrivatePositions.tsx**
- Groups by subtype
- Maps to PrivatePositionCard
- Uses PositionList for layout

#### 4. Layout Layer (Existing)

**PortfolioPositions.tsx**
- Orchestrates layout (grid, sections)
- Filters positions by type
- Uses PositionSectionHeader
- No changes needed to this component

---

## Design Token Strategy

### Why Design Tokens Over CSS Files?

The current implementation uses hardcoded Tailwind utility classes (e.g., `bg-slate-800`, `text-emerald-400`) directly in JSX. While this works, it has several issues:

**Problems with Hardcoded Classes:**
1. **No single source of truth** - Color changes require find/replace across multiple files
2. **Inconsistency risk** - Easy to use `emerald-400` in one place and `emerald-500` elsewhere
3. **Theme coupling** - Colors are tied to specific Tailwind values rather than semantic meaning
4. **Maintainability** - Changing "positive P&L color" requires updating 6+ files

**Benefits of Design Tokens:**
1. **Single source of truth** - All position card colors defined once in Tailwind config
2. **Semantic naming** - `position-card-positive` instead of `emerald-400`
3. **Easy theming** - Change one value, affects entire app
4. **Type safety** - TypeScript can autocomplete token names
5. **Better with existing theme** - Integrates with current `sigmasight` color palette

### Current Tailwind Configuration

The project already has design token infrastructure in `tailwind.config.js`:

```javascript
// Existing config with CSS variables
module.exports = {
  theme: {
    extend: {
      colors: {
        sigmasight: {
          primary: 'hsl(var(--sigmasight-primary))',
          secondary: 'hsl(var(--sigmasight-secondary))',
          // ... more colors
        }
      }
    }
  }
}
```

This pattern uses CSS variables for theming, which is perfect for adding position card tokens.

### Proposed Design Token Additions

Add position-specific design tokens to `tailwind.config.js`:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        sigmasight: {
          // ... existing colors ...

          // Position Card Tokens
          'position-card': {
            // Background colors
            'bg-light': 'hsl(0, 0%, 100%)',           // White
            'bg-dark': 'hsl(215, 28%, 17%)',          // slate-800
            'bg-hover-light': 'hsl(210, 20%, 98%)',   // gray-50
            'bg-hover-dark': 'hsl(215, 25%, 20%)',    // slate-750

            // Border colors
            'border-light': 'hsl(214, 32%, 91%)',     // gray-200
            'border-dark': 'hsl(215, 20%, 35%)',      // slate-700

            // Text colors (primary)
            'text-primary-light': 'hsl(222, 47%, 11%)', // gray-900
            'text-primary-dark': 'hsl(0, 0%, 100%)',    // white

            // Text colors (secondary/muted)
            'text-secondary-light': 'hsl(215, 16%, 47%)', // gray-600
            'text-secondary-dark': 'hsl(215, 20%, 65%)',  // slate-400

            // P&L colors (semantic - work in both themes)
            'pnl-positive': 'hsl(158, 64%, 52%)',     // emerald-400
            'pnl-negative': 'hsl(0, 72%, 51%)',       // red-400
            'pnl-neutral': 'hsl(215, 20%, 65%)',      // slate-400
          }
        }
      },

      // Empty state colors
      colors: {
        'empty-state': {
          'bg-light': 'hsl(210, 20%, 98%)',          // gray-50
          'bg-dark': 'hsla(215, 28%, 17%, 0.5)',     // slate-800/50
          'text-light': 'hsl(210, 13%, 50%)',        // gray-500
          'text-dark': 'hsl(215, 20%, 65%)',         // slate-400
          'border-light': 'hsl(214, 32%, 91%)',      // gray-200
          'border-dark': 'hsl(215, 20%, 35%)',       // slate-700
        }
      }
    }
  }
}
```

### Code Migration: Before & After

#### Before (Hardcoded Classes)

```typescript
// BasePositionCard.tsx - BEFORE
export function BasePositionCard({ ... }: BasePositionCardProps) {
  const { theme } = useTheme()

  return (
    <Card className={`transition-colors cursor-pointer ${
      theme === 'dark'
        ? 'bg-slate-800 border-slate-700 hover:bg-slate-750'
        : 'bg-white border-gray-200 hover:bg-gray-50'
    }`}>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <div className={`font-semibold text-sm ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {primaryText}
            </div>
            <div className={`text-xs ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              {secondaryText}
            </div>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {primaryValue}
            </div>
            <div className={`text-sm font-medium ${
              secondaryValueColor === 'positive' ? 'text-emerald-400' :
              secondaryValueColor === 'negative' ? 'text-red-400' :
              'text-slate-400'
            }`}>
              {secondaryValue}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### After (Design Tokens)

```typescript
// BasePositionCard.tsx - AFTER
export function BasePositionCard({ ... }: BasePositionCardProps) {
  const { theme } = useTheme()

  return (
    <Card className={`transition-colors cursor-pointer ${
      theme === 'dark'
        ? 'bg-sigmasight-position-card-bg-dark border-sigmasight-position-card-border-dark hover:bg-sigmasight-position-card-bg-hover-dark'
        : 'bg-sigmasight-position-card-bg-light border-sigmasight-position-card-border-light hover:bg-sigmasight-position-card-bg-hover-light'
    }`}>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <div className={`font-semibold text-sm transition-colors duration-300 ${
              theme === 'dark'
                ? 'text-sigmasight-position-card-text-primary-dark'
                : 'text-sigmasight-position-card-text-primary-light'
            }`}>
              {primaryText}
            </div>
            <div className={`text-xs transition-colors duration-300 ${
              theme === 'dark'
                ? 'text-sigmasight-position-card-text-secondary-dark'
                : 'text-sigmasight-position-card-text-secondary-light'
            }`}>
              {secondaryText}
            </div>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark'
                ? 'text-sigmasight-position-card-text-primary-dark'
                : 'text-sigmasight-position-card-text-primary-light'
            }`}>
              {primaryValue}
            </div>
            <div className={`text-sm font-medium ${
              secondaryValueColor === 'positive' ? 'text-sigmasight-position-card-pnl-positive' :
              secondaryValueColor === 'negative' ? 'text-sigmasight-position-card-pnl-negative' :
              'text-sigmasight-position-card-pnl-neutral'
            }`}>
              {secondaryValue}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Alternative: Shorter Token Names (Recommended)

For better readability, we can use a shorter namespace:

```javascript
// tailwind.config.js - Shorter namespace
module.exports = {
  theme: {
    extend: {
      colors: {
        'card': {
          // Backgrounds
          'bg': 'hsl(0, 0%, 100%)',
          'bg-dark': 'hsl(215, 28%, 17%)',
          'bg-hover': 'hsl(210, 20%, 98%)',
          'bg-hover-dark': 'hsl(215, 25%, 20%)',

          // Borders
          'border': 'hsl(214, 32%, 91%)',
          'border-dark': 'hsl(215, 20%, 35%)',

          // Text
          'text': 'hsl(222, 47%, 11%)',
          'text-dark': 'hsl(0, 0%, 100%)',
          'text-muted': 'hsl(215, 16%, 47%)',
          'text-muted-dark': 'hsl(215, 20%, 65%)',

          // Semantic colors
          'positive': 'hsl(158, 64%, 52%)',
          'negative': 'hsl(0, 72%, 51%)',
          'neutral': 'hsl(215, 20%, 65%)',
        }
      }
    }
  }
}
```

Then usage becomes cleaner:

```typescript
// Much cleaner JSX
<Card className={`transition-colors cursor-pointer ${
  theme === 'dark'
    ? 'bg-card-bg-dark border-card-border-dark hover:bg-card-bg-hover-dark'
    : 'bg-card-bg border-card-border hover:bg-card-bg-hover'
}`}>
```

### Implementation Impact

**Files to Update After Token Setup:**

1. `tailwind.config.js` - Add design tokens
2. `src/components/common/BasePositionCard.tsx` - Use tokens
3. `src/components/common/PositionSectionHeader.tsx` - Use tokens for badge
4. `src/components/common/PositionList.tsx` - Use tokens for empty state

**Total Changes**: 4 files (one-time setup)

**Future Benefit**: All position cards automatically use consistent colors. Changing theme = update 1 config file instead of 20+ components.

### Migration Strategy

1. **Phase 0a**: Add design tokens to `tailwind.config.js`
2. **Phase 0b**: Update `BasePositionCard` to use tokens
3. **Phase 0c**: Update `PositionSectionHeader` to use tokens
4. **Phase 0d**: Update `PositionList` empty state to use tokens
5. **Verify**: All existing cards look identical to before
6. **Proceed**: Continue with Phase 1 implementation

### Design Token Naming Convention

**Pattern**: `{component}-{element}-{state?}`

Examples:
- `card-bg` - Default background
- `card-bg-dark` - Dark theme background
- `card-bg-hover` - Hover state background
- `card-text-muted` - Secondary/muted text
- `card-positive` - Positive P&L color (semantic, theme-agnostic)

**Semantic Colors** (no light/dark variants needed):
- `card-positive` - Always emerald-400 (works in both themes)
- `card-negative` - Always red-400 (works in both themes)
- `card-neutral` - Slate-400 (works in both themes)

---

## Implementation Plan

### Phase 0: Design Token Setup (Foundation)

**Goal**: Establish design token system before creating components

#### Step 0.1: Add Design Tokens to Tailwind Config
**File**: `tailwind.config.js`

Add the shorter namespace tokens (recommended for readability):

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // Position card design tokens
        'card': {
          // Backgrounds
          'bg': 'hsl(0, 0%, 100%)',              // White (light theme)
          'bg-dark': 'hsl(215, 28%, 17%)',       // slate-800 (dark theme)
          'bg-hover': 'hsl(210, 20%, 98%)',      // gray-50 (light hover)
          'bg-hover-dark': 'hsl(215, 25%, 20%)', // slate-750 (dark hover)

          // Borders
          'border': 'hsl(214, 32%, 91%)',        // gray-200 (light)
          'border-dark': 'hsl(215, 20%, 35%)',   // slate-700 (dark)

          // Text (primary)
          'text': 'hsl(222, 47%, 11%)',          // gray-900 (light)
          'text-dark': 'hsl(0, 0%, 100%)',       // white (dark)

          // Text (secondary/muted)
          'text-muted': 'hsl(215, 16%, 47%)',    // gray-600 (light)
          'text-muted-dark': 'hsl(215, 20%, 65%)', // slate-400 (dark)

          // Semantic P&L colors (theme-agnostic)
          'positive': 'hsl(158, 64%, 52%)',      // emerald-400
          'negative': 'hsl(0, 72%, 51%)',        // red-400
          'neutral': 'hsl(215, 20%, 65%)',       // slate-400
        },

        // Empty state design tokens
        'empty': {
          'bg': 'hsl(210, 20%, 98%)',            // gray-50 (light)
          'bg-dark': 'hsla(215, 28%, 17%, 0.5)', // slate-800/50 (dark)
          'text': 'hsl(210, 13%, 50%)',          // gray-500 (light)
          'text-dark': 'hsl(215, 20%, 65%)',     // slate-400 (dark)
          'border': 'hsl(214, 32%, 91%)',        // gray-200 (light)
          'border-dark': 'hsl(215, 20%, 35%)',   // slate-700 (dark)
        },

        // Badge design tokens (for section headers)
        'badge': {
          'bg': 'hsl(214, 32%, 91%)',            // gray-200 (light)
          'bg-dark': 'hsl(215, 20%, 35%)',       // slate-700 (dark)
          'text': 'hsl(215, 16%, 47%)',          // gray-700 (light)
          'text-dark': 'hsl(215, 20%, 65%)',     // slate-300 (dark)
        }
      }
    }
  },
  plugins: [],
}
```

**Testing**:
1. Restart dev server after config change
2. Verify no build errors
3. Check Tailwind IntelliSense recognizes new tokens

**Output**: Design token system ready for use

---

### Phase 1: Foundation Components (No Breaking Changes)

**Goal**: Create base components that can coexist with existing code

#### Step 1.1: Create BasePositionCard
**File**: `src/components/common/BasePositionCard.tsx`

```typescript
import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

interface BasePositionCardProps {
  primaryText: string
  secondaryText: string
  primaryValue: string
  secondaryValue: string
  secondaryValueColor: 'positive' | 'negative' | 'neutral'
  onClick?: () => void
}

export function BasePositionCard({
  primaryText,
  secondaryText,
  primaryValue,
  secondaryValue,
  secondaryValueColor,
  onClick
}: BasePositionCardProps) {
  const { theme } = useTheme()

  // Map semantic color to design token class
  const getSecondaryValueClass = () => {
    if (secondaryValueColor === 'neutral') return 'text-card-neutral'
    if (secondaryValueColor === 'positive') return 'text-card-positive'
    return 'text-card-negative'
  }

  return (
    <Card
      className={`transition-colors ${onClick ? 'cursor-pointer' : ''} ${
        theme === 'dark'
          ? 'bg-card-bg-dark border-card-border-dark hover:bg-card-bg-hover-dark'
          : 'bg-card-bg border-card-border hover:bg-card-bg-hover'
      }`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <div className={`font-semibold text-sm transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
            }`}>
              {primaryText}
            </div>
            <div className={`text-xs transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
            }`}>
              {secondaryText}
            </div>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
            }`}>
              {primaryValue}
            </div>
            <div className={`text-sm font-medium ${getSecondaryValueClass()}`}>
              {secondaryValue}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Key Changes from Current Implementation**:
- Uses `text-card-positive/negative/neutral` instead of `text-emerald-400/red-400/slate-400`
- Uses `bg-card-bg/bg-card-bg-dark` instead of `bg-white/bg-slate-800`
- Uses `text-card-text/text-card-text-dark` instead of `text-gray-900/text-white`
- All colors now centralized in Tailwind config

**Testing**: Can be tested in isolation with hardcoded props

#### Step 1.2: Create PositionSectionHeader
**File**: `src/components/common/PositionSectionHeader.tsx`

```typescript
import React from 'react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'

interface PositionSectionHeaderProps {
  title: string
  count: number
}

export function PositionSectionHeader({ title, count }: PositionSectionHeaderProps) {
  const { theme } = useTheme()

  return (
    <div className="flex items-center gap-2 mb-4">
      <h3 className={`text-lg font-semibold transition-colors duration-300 ${
        theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
      }`}>
        {title}
      </h3>
      <Badge variant="secondary" className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-badge-bg-dark text-badge-text-dark' : 'bg-badge-bg text-badge-text'
      }`}>
        {count}
      </Badge>
    </div>
  )
}
```

**Key Changes**:
- Title uses `text-card-text/text-card-text-dark` design tokens
- Badge uses `bg-badge-bg/text-badge-text` design tokens

#### Step 1.3: Create PositionList
**File**: `src/components/common/PositionList.tsx`

```typescript
import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'

interface PositionListProps<T> {
  items: T[]
  renderItem: (item: T, index: number) => React.ReactNode
  emptyMessage?: string
}

export function PositionList<T>({
  items,
  renderItem,
  emptyMessage = 'No positions'
}: PositionListProps<T>) {
  const { theme } = useTheme()

  if (items.length === 0) {
    return (
      <div className={`text-sm p-3 rounded-lg border ${
        theme === 'dark'
          ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
          : 'text-empty-text bg-empty-bg border-empty-border'
      }`}>
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map(renderItem)}
    </div>
  )
}
```

**Key Changes**:
- Empty state uses `text-empty-text/bg-empty-bg/border-empty-border` design tokens
- All empty state styling centralized in Tailwind config

**Output**: Three foundation components that can be tested independently

---

### Phase 2: Domain Adapter Components

**Goal**: Create adapters that transform domain data to BasePositionCard props

#### Step 2.1: Create StockPositionCard
**File**: `src/components/positions/StockPositionCard.tsx`

```typescript
import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'

interface StockPosition {
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
}

interface StockPositionCardProps {
  position: StockPosition
  onClick?: () => void
}

// Company name mappings (moved from old PositionCard)
const COMPANY_NAMES: Record<string, string> = {
  'AAPL': 'Apple Inc.',
  'MSFT': 'Microsoft Corporation',
  'GOOGL': 'Alphabet Inc.',
  'NVDA': 'NVIDIA Corporation',
  'AMZN': 'Amazon.com, Inc.',
  'META': 'Meta Platforms Inc.',
  'TSLA': 'Tesla, Inc.',
  'JPM': 'JPMorgan Chase & Co.',
  'JNJ': 'Johnson & Johnson',
  'V': 'Visa Inc.',
  'PG': 'Procter & Gamble Co.',
  'UNH': 'UnitedHealth Group Inc.',
  'HD': 'The Home Depot, Inc.',
  'MA': 'Mastercard Inc.',
  'DIS': 'The Walt Disney Company',
  'BAC': 'Bank of America Corp.',
  'ADBE': 'Adobe Inc.',
  'NFLX': 'Netflix, Inc.',
  'CRM': 'Salesforce, Inc.',
  'PFE': 'Pfizer Inc.'
}

export function StockPositionCard({ position, onClick }: StockPositionCardProps) {
  const companyName = position.name || COMPANY_NAMES[position.symbol] || 'Company'

  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={companyName}
      primaryValue={formatNumber(position.marketValue)}
      secondaryValue={
        position.pnl === 0
          ? '—'
          : `${position.positive ? '+' : ''}${formatNumber(position.pnl)}`
      }
      secondaryValueColor={
        position.pnl === 0
          ? 'neutral'
          : position.positive
            ? 'positive'
            : 'negative'
      }
      onClick={onClick}
    />
  )
}
```

#### Step 2.2: Create OptionPositionCard
**File**: `src/components/positions/OptionPositionCard.tsx`

```typescript
import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  marketValue: number
  pnl: number
}

interface OptionPositionCardProps {
  position: OptionPosition
  onClick?: () => void
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  'LC': 'Long Call',
  'LP': 'Long Put',
  'SC': 'Short Call',
  'SP': 'Short Put'
}

export function OptionPositionCard({ position, onClick }: OptionPositionCardProps) {
  const optionTypeLabel = OPTION_TYPE_LABELS[position.type || ''] || 'Option'

  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={optionTypeLabel}
      primaryValue={formatCurrency(Math.abs(position.marketValue))}
      secondaryValue={
        position.pnl === 0
          ? '—'
          : `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}`
      }
      secondaryValueColor={
        position.pnl === 0
          ? 'neutral'
          : position.pnl >= 0
            ? 'positive'
            : 'negative'
      }
      onClick={onClick}
    />
  )
}
```

#### Step 2.3: Create PrivatePositionCard
**File**: `src/components/positions/PrivatePositionCard.tsx`

```typescript
import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'

interface PrivatePosition {
  id?: string
  symbol: string
  investment_subtype?: string
  marketValue: number
  pnl: number
}

interface PrivatePositionCardProps {
  position: PrivatePosition
  onClick?: () => void
}

export function PrivatePositionCard({ position, onClick }: PrivatePositionCardProps) {
  const subtype = position.investment_subtype || 'Alternative Investment'

  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={subtype}
      primaryValue={formatCurrency(Math.abs(position.marketValue))}
      secondaryValue={
        position.pnl === 0
          ? '—'
          : `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}`
      }
      secondaryValueColor={
        position.pnl === 0
          ? 'neutral'
          : position.pnl >= 0
            ? 'positive'
            : 'negative'
      }
      onClick={onClick}
    />
  )
}
```

**Output**: Three adapter components ready to replace existing card components

---

### Phase 3: Refactor Container Components (One at a Time)

**Goal**: Update existing container components to use new adapters

#### Step 3.1: Refactor PublicPositions.tsx

**Before** (24 lines):
```typescript
export function PublicPositions({ positions }: PublicPositionsProps) {
  const { theme } = useTheme()

  return (
    <div className="space-y-2">
      {positions.map((position, index) => (
        <PositionCard
          key={position.id || `public-${index}`}
          position={{
            ...position,
            marketValue: position.type === 'SHORT' ? -Math.abs(position.marketValue) : position.marketValue
          }}
        />
      ))}
      {positions.length === 0 && (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800/50 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No positions
        </div>
      )}
    </div>
  )
}
```

**After** (~10 lines):
```typescript
import { PositionList } from '@/components/common/PositionList'
import { StockPositionCard } from '@/components/positions/StockPositionCard'

export function PublicPositions({ positions }: PublicPositionsProps) {
  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <StockPositionCard
          key={position.id || `public-${index}`}
          position={{
            ...position,
            marketValue: position.type === 'SHORT' ? -Math.abs(position.marketValue) : position.marketValue
          }}
        />
      )}
      emptyMessage="No positions"
    />
  )
}
```

**Testing**:
1. Visual comparison with before state
2. Ensure SHORT positions show negative values
3. Empty state displays correctly

#### Step 3.2: Refactor OptionsPositions.tsx

**After**:
```typescript
import { PositionList } from '@/components/common/PositionList'
import { OptionPositionCard } from '@/components/positions/OptionPositionCard'

export function OptionsPositions({ positions }: OptionsPositionsProps) {
  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <OptionPositionCard
          key={position.id || `option-${index}`}
          position={position}
        />
      )}
      emptyMessage="No options positions"
    />
  )
}
```

#### Step 3.3: Refactor PrivatePositions.tsx

**Before** (105 lines with grouping logic)

**After** (~35 lines):
```typescript
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'
import { PrivatePositionCard } from '@/components/positions/PrivatePositionCard'

export function PrivatePositions({ positions }: PrivatePositionsProps) {
  const { theme } = useTheme()

  // Group by investment subtype
  const groupedPositions = positions.reduce((acc, position) => {
    const subtype = position.investment_subtype || 'Alternative Investment'
    if (!acc[subtype]) acc[subtype] = []
    acc[subtype].push(position)
    return acc
  }, {} as Record<string, PrivatePosition[]>)

  if (positions.length === 0) {
    return (
      <div className={`text-sm p-3 rounded-lg border ${
        theme === 'dark'
          ? 'text-slate-400 bg-slate-800/50 border-slate-700'
          : 'text-gray-500 bg-gray-50 border-gray-200'
      }`}>
        No private or alternative investments
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {Object.entries(groupedPositions).map(([subtype, subtypePositions]) => (
        <div key={subtype}>
          <div className="flex items-center gap-2 mb-3">
            <h4 className={`text-sm font-medium ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
            }`}>{subtype}</h4>
            <Badge variant="outline" className="text-xs">
              {subtypePositions.length}
            </Badge>
          </div>
          <div className="space-y-2">
            {subtypePositions.map((position, index) => (
              <PrivatePositionCard
                key={position.id || `private-${subtype}-${index}`}
                position={position}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

**Note**: Private positions have grouping logic, so can't use PositionList directly

---

### Phase 4: Cleanup

#### Step 4.1: Remove Old Components
- Delete `src/components/portfolio/PositionCard.tsx`
- Delete `src/components/portfolio/OptionCard.tsx`

#### Step 4.2: Update PortfolioPositions.tsx
Replace section header code with:
```typescript
import { PositionSectionHeader } from '@/components/common/PositionSectionHeader'

// Instead of inline header JSX:
<PositionSectionHeader title="Longs" count={publicLongs.length} />
```

#### Step 4.3: Document New Patterns
Update `frontend/_docs/project-structure.md` with new component locations

---

## Usage Examples

### On Portfolio Page (Current)
```typescript
import { PortfolioPositions } from '@/components/portfolio/PortfolioPositions'

// Works exactly as before, no changes needed
<PortfolioPositions
  publicPositions={publicPositions}
  optionsPositions={optionsPositions}
  privatePositions={privatePositions}
/>
```

### On New "Public Positions" Page
```typescript
import { StockPositionCard } from '@/components/positions/StockPositionCard'
import { PositionList } from '@/components/common/PositionList'
import { PositionSectionHeader } from '@/components/common/PositionSectionHeader'

function PublicPositionsPage() {
  const { positions } = usePublicPositions()

  return (
    <div>
      <PositionSectionHeader title="All Public Positions" count={positions.length} />
      <PositionList
        items={positions}
        renderItem={(pos, idx) => (
          <StockPositionCard key={pos.id} position={pos} />
        )}
      />
    </div>
  )
}
```

### On "Private Positions" Page
```typescript
import { PrivatePositionCard } from '@/components/positions/PrivatePositionCard'
import { PositionList } from '@/components/common/PositionList'
import { PositionSectionHeader } from '@/components/common/PositionSectionHeader'

function PrivatePositionsPage() {
  const { privatePositions } = usePrivatePositions()

  return (
    <div>
      <PositionSectionHeader title="Private & Alternative Investments" count={privatePositions.length} />
      <PositionList
        items={privatePositions}
        renderItem={(pos, idx) => (
          <PrivatePositionCard
            key={pos.id}
            position={pos}
            onClick={() => handlePositionDetails(pos)}
          />
        )}
        emptyMessage="No private or alternative investments"
      />
    </div>
  )
}
```

### On "Organize" Page (Filtered View)
```typescript
import { StockPositionCard } from '@/components/positions/StockPositionCard'
import { PositionList } from '@/components/common/PositionList'

function OrganizePage() {
  const { techPositions, financePositions } = usePositionsByStrategy()

  return (
    <div>
      <h2>Tech Strategy</h2>
      <PositionList
        items={techPositions}
        renderItem={(pos, idx) => (
          <StockPositionCard
            key={pos.id}
            position={pos}
            onClick={() => handlePositionClick(pos)}
          />
        )}
      />

      <h2>Finance Strategy</h2>
      <PositionList
        items={financePositions}
        renderItem={(pos, idx) => (
          <StockPositionCard key={pos.id} position={pos} />
        )}
      />
    </div>
  )
}
```

---

## Benefits Analysis

### Before Refactoring
- **Total Lines**: ~174 lines across 3 card components + containers
- **Code Duplication**: ~120 lines of duplicated JSX
- **Styling Changes**: Requires updates in 3 files
- **New Position Type**: ~50 lines of duplicated code
- **Reusability**: Low - must copy entire components

### After Refactoring
- **Total Lines**: ~150 lines (15% reduction)
- **Code Duplication**: ~0 lines (presentation in one place)
- **Styling Changes**: Update 1 file (BasePositionCard)
- **New Position Type**: ~20 lines (just adapter logic)
- **Reusability**: High - import and use anywhere

### Specific Benefits

1. **Single Source of Truth**
   - All card styling defined once in BasePositionCard
   - Theme changes propagate automatically
   - Hover states consistent across all types

2. **Improved Maintainability**
   - Presentation layer changes: 1 file
   - Business logic changes: Adapter layer only
   - Clear separation of concerns

3. **Enhanced Testability**
   - BasePositionCard: Test with mock props
   - Adapters: Test data transformation
   - Containers: Test layout logic
   - Each layer independently testable

4. **Easy Extension**
   - Add new position type: Create new adapter (~20 lines)
   - No changes to presentation layer
   - Guaranteed visual consistency

5. **Reusability Across Pages**
   - Import adapter + PositionList
   - Works on any page
   - No page-specific dependencies

---

## Migration Strategy

### Risk Mitigation

1. **No Breaking Changes in Phase 1**
   - New components coexist with old
   - Can test thoroughly before migration

2. **One Component at a Time**
   - Refactor PublicPositions first
   - Test thoroughly
   - Move to next component
   - Rollback easy if issues arise

3. **Visual Regression Testing**
   - Take screenshots before refactoring
   - Compare after each component migration
   - Ensure pixel-perfect match

4. **Gradual Rollout**
   - Can ship Phase 1 & 2 without touching existing code
   - Phase 3 can be done incrementally
   - Each step can be a separate commit

### Rollback Plan

If issues arise during Phase 3:
1. Revert the specific container component
2. Old components still exist
3. No impact on other components

---

## Testing Strategy

### Unit Tests

**BasePositionCard**:
- Renders all props correctly
- Applies theme classes
- Handles click events
- Displays color states correctly

**Adapters**:
- Transforms data correctly
- Handles edge cases (null values, zero P&L)
- Applies correct formatting functions

**Containers**:
- Maps arrays correctly
- Handles empty states
- Applies filters correctly

### Integration Tests

- Load portfolio page
- Verify all position types display
- Test theme switching
- Test responsive layout

### Visual Regression Tests

- Screenshot comparison before/after
- All three position types
- Empty states
- Dark/light themes

---

## Performance Considerations

### Bundle Size Impact
- **Before**: 3 similar components = ~3x code
- **After**: 1 base + 3 small adapters = smaller bundle
- **Estimated savings**: ~2-3 KB gzipped

### Runtime Performance
- No performance degradation
- Same number of components rendered
- Slightly faster due to shared code paths

### Code Splitting
- Base components in common chunk
- Adapters can be lazy-loaded per page
- Better code splitting opportunities

---

## Future Enhancements

### Phase 5: Advanced Features (Future)

1. **Virtualization for Large Lists**
   ```typescript
   <VirtualizedPositionList items={positions} />
   ```

2. **Sorting and Filtering**
   ```typescript
   <PositionList
     items={positions}
     sortBy="marketValue"
     filterBy={(pos) => pos.marketValue > 1000}
   />
   ```

3. **Bulk Actions**
   ```typescript
   <BasePositionCard
     selectable
     selected={selected}
     onSelect={handleSelect}
   />
   ```

4. **Expanded Detail View**
   ```typescript
   <BasePositionCard
     expandable
     renderDetails={(position) => <DetailView {...position} />}
   />
   ```

5. **Drag and Drop**
   ```typescript
   <DraggablePositionCard
     position={position}
     onDragEnd={handleDragEnd}
   />
   ```

---

## Conclusion

This refactoring creates a solid foundation for position cards that:
- Eliminates code duplication
- Ensures visual consistency
- Enables easy reuse across pages
- Simplifies maintenance
- Facilitates future enhancements

The layered architecture (Presentation → Adapter → Container → Page) provides clear separation of concerns and makes the codebase more maintainable and scalable.

**Estimated Timeline**: 5-7 hours total
**Risk Level**: Low (incremental, reversible changes)
**Impact**: High (benefits entire application)

---

## References

- Current components: `src/components/portfolio/*`
- Foundation: `@/components/ui/card`, `@/components/ui/badge`
- Theme system: `@/contexts/ThemeContext`
- Formatters: `@/lib/formatters`

---

## Implementation Status: Organize Page (2025-10-01)

### Overview

Successfully implemented the reusable position card architecture on the Organize page with key differences from the Portfolio page to support organize-specific features. The implementation demonstrates the flexibility of the layered architecture.

### What Was Implemented

#### 1. OrganizePositionCard Adapter (70 lines)
**File**: `src/components/positions/OrganizePositionCard.tsx`

**Purpose**: Universal adapter for all investment types on the Organize page

**Key Differences from Portfolio Adapters**:
```typescript
// Portfolio Page - Shows P&L
<BasePositionCard
  primaryValue={formatCurrency(Math.abs(position.market_value))}
  secondaryValue={`${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}`}
  secondaryValueColor={position.pnl >= 0 ? 'positive' : 'negative'}
/>

// Organize Page - NO P&L
<BasePositionCard
  primaryValue={formatCurrency(Math.abs(position.market_value))}
  secondaryValue=""  // EMPTY - no P&L display
  secondaryValueColor="neutral"
/>
```

**Why No P&L on Organize Page**:
- Organize page focuses on grouping positions into strategies
- Users are categorizing, not analyzing performance
- Cleaner visual focus on position selection and tagging

**Features**:
- Handles all investment classes (PUBLIC, OPTIONS, PRIVATE)
- Maps option types (LC/LP/SC/SP) to labels
- Extracts strike prices and expiration dates
- Uses design tokens for consistent theming
- Reuses BasePositionCard foundation

#### 2. SelectablePositionCard Wrapper (85 lines)
**File**: `src/components/organize/SelectablePositionCard.tsx`

**Purpose**: Adds organize-specific features without modifying the base card

**Features**:
1. **Checkbox Selection**
   ```typescript
   <input
     type="checkbox"
     checked={isSelected}
     onChange={onToggleSelection}
     className="mt-4 h-4 w-4 cursor-pointer"
   />
   ```

2. **Tag Display**
   ```typescript
   {tags.length > 0 && (
     <div className="flex flex-wrap gap-1 mt-2">
       {tags.map(tag => <TagBadge key={tag.id} tag={tag} />)}
     </div>
   )}
   ```

3. **Drag-Drop Support**
   ```typescript
   const handleDrop = (e: React.DragEvent) => {
     const tagId = e.dataTransfer.getData('tagId')
     if (tagId && onDropTag) {
       onDropTag(tagId)
     }
   }
   ```

4. **Visual Selection State**
   ```typescript
   className={`${isSelected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}`}
   ```

**Architecture Pattern**:
```
SelectablePositionCard (wrapper)
  ├── Checkbox for selection
  ├── OrganizePositionCard (adapter)
  │   └── BasePositionCard (foundation)
  └── Tags display below card
```

#### 3. Refactored Position Lists (4 files)

**Files Updated**:
- `LongPositionsList.tsx` (~80 lines)
- `ShortPositionsList.tsx` (~80 lines)
- `OptionsPositionsList.tsx` (~120 lines)
- `PrivatePositionsList.tsx` (~85 lines)

**Before** (with Card backgrounds):
```typescript
<Card className="bg-slate-800">
  <CardHeader>
    <CardTitle>Long Positions</CardTitle>
  </CardHeader>
  <CardContent>
    {positions.map(position => (
      <PositionCard position={position} />
    ))}
  </CardContent>
</Card>
```

**After** (no Card backgrounds):
```typescript
<div>
  <h3 className="text-base font-semibold mb-3">Long Positions</h3>
  {positions.length === 0 ? (
    <div className="text-sm p-3 rounded-lg border">
      No long positions
    </div>
  ) : (
    <div className="space-y-2">
      {positions.map(position => (
        <SelectablePositionCard
          isSelected={isSelected(position.id)}
          onToggleSelection={() => onToggleSelection(position.id)}
          tags={position.tags || []}
          onDropTag={(tagId) => onDropTag?.(position.id, tagId)}
        >
          <OrganizePositionCard position={position} />
        </SelectablePositionCard>
      ))}
    </div>
  )}
</div>
```

**Key Changes**:
1. **Removed Card wrappers** - No more Card/CardHeader/CardContent components
2. **Added h3 headings** - Section titles now simple h3 elements
3. **Matched Portfolio styling** - Same visual consistency across pages
4. **Preserved functionality** - All selection, tagging, and drag-drop features intact
5. **Design tokens** - Empty states use centralized color tokens

### Implementation Metrics

**Components Created**:
- OrganizePositionCard.tsx - 70 lines
- SelectablePositionCard.tsx - 85 lines

**Components Refactored**:
- LongPositionsList.tsx - Updated
- ShortPositionsList.tsx - Updated
- OptionsPositionsList.tsx - Updated
- PrivatePositionsList.tsx - Updated

**Components Deleted**:
- organize/PositionCard.tsx (legacy, replaced by new architecture)

**Net Code Change**: -12 lines (cleaner codebase)

### Architecture Benefits Demonstrated

#### 1. Foundation Reuse
- BasePositionCard used by both Portfolio and Organize pages
- Same visual consistency without code duplication
- Theme support automatic across both pages

#### 2. Adapter Flexibility
- Created OrganizePositionCard for no-P&L variant
- Only 70 lines to support all investment types
- Reuses BasePositionCard infrastructure

#### 3. Wrapper Pattern
- SelectablePositionCard adds features without modifying adapter
- Clean separation: selection logic vs display logic
- Easy to add more wrappers for other pages

#### 4. Design Token Power
- Changed to simple div/h3 structure
- Design tokens ensure visual consistency
- Single config change affects all cards

### Lessons Learned

#### What Worked Well

1. **Layered Architecture**
   - Easy to create organize-specific variant
   - No changes needed to BasePositionCard
   - Clear separation of concerns

2. **Wrapper Pattern**
   - SelectablePositionCard cleanly adds checkbox/tags
   - Doesn't pollute OrganizePositionCard with UI logic
   - Composable for future features

3. **Design Tokens**
   - Made Card removal straightforward
   - Consistent empty states automatically
   - Theme support seamless

#### Areas for Consideration

1. **Wrapper Complexity**
   - SelectablePositionCard has multiple responsibilities
   - Could split into smaller components if needed
   - Works well for current requirements

2. **Adapter Variations**
   - OrganizePositionCard very similar to other adapters
   - Could potentially unify with feature flags
   - Current approach (separate adapter) clearer for now

### Comparison: Portfolio vs Organize

| Feature | Portfolio Page | Organize Page |
|---------|---------------|---------------|
| **P&L Display** | ✅ Shows P&L with colors | ❌ Hidden (not relevant) |
| **Checkboxes** | ❌ None | ✅ For selection |
| **Tag Display** | ❌ None | ✅ Shows tags below card |
| **Drag-Drop** | ❌ None | ✅ Drag tags to positions |
| **Section Headers** | Simple h3 | Simple h3 |
| **Card Backgrounds** | No Card wrappers | No Card wrappers |
| **Theme Support** | ✅ Dark/Light | ✅ Dark/Light |
| **Foundation** | BasePositionCard | BasePositionCard |

### Usage Pattern Established

```typescript
// Pattern for future pages with different requirements:

// 1. Create page-specific adapter (if needed)
export function MyPagePositionCard({ position }: Props) {
  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={getCustomText(position)}
      primaryValue={formatValue(position)}
      secondaryValue={getCustomValue(position)}  // Customize as needed
      secondaryValueColor="neutral"
    />
  )
}

// 2. Create page-specific wrapper (if needed)
export function MyPageWrapper({ children, ...props }: Props) {
  return (
    <div className="custom-wrapper">
      {/* Add page-specific features */}
      {children}
    </div>
  )
}

// 3. Use in page component
<MyPageWrapper {...wrapperProps}>
  <MyPagePositionCard position={position} />
</MyPageWrapper>
```

### Next Steps

This implementation provides a proven pattern for:
1. **Public Positions Page** - Can reuse StockPositionCard directly
2. **Private Positions Page** - Can reuse PrivatePositionCard directly
3. **Settings Page** - Can create new adapter if position display needed
4. **AI Chat Page** - Can create compact variant for chat context

The architecture has proven flexible enough to handle significantly different requirements (P&L vs no P&L, interactive vs static) while maintaining code reuse and visual consistency.
