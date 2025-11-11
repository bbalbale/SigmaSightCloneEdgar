# Organize Page UI Component Refactoring Plan

**Author**: Claude Code
**Date**: 2025-10-01
**Status**: Planning - Awaiting Approval

---

## Executive Summary

Refactor the Organize page to use our new reusable position card architecture while adding organize-specific features: checkbox selection, tag display, and drag-drop functionality. **Key difference from Portfolio page**: No P&L display on Organize page.

---

## Current State Analysis

### Organize Page Structure
```
OrganizeContainer (container)
└── PositionSelectionGrid
    ├── LongPositionsList
    ├── ShortPositionsList
    ├── OptionsPositionsList
    └── PrivatePositionsList
        └── PositionCard (organize-specific, ~117 lines)
```

### Key Features (Must Preserve)
1. ✅ **Checkbox selection** - Combine positions into strategies
2. ✅ **Tag display** - Show tags associated with each position
3. ✅ **Drag & drop** - Apply tags to positions/strategies
4. ✅ **Strategy cards** - Display grouped positions
5. ✅ **Selection highlighting** - Blue border when selected
6. ❌ **No P&L display** - Different from Portfolio page

### Current Duplication Problem
- `src/components/organize/PositionCard.tsx` (~117 lines) duplicates styling from our new BasePositionCard
- Cannot reuse Portfolio page cards because they show P&L
- Tags are not displayed with positions currently

---

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Organize Page (Container)                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Position List Components                    │
│  (LongPositions, ShortPositions, Options, Private)       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│           SelectablePositionCard (NEW)                   │
│  • Checkbox (left side)                                  │
│  • Tag badges (below card)                               │
│  • Drag & drop handlers                                  │
│  • Selection highlighting                                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│      OrganizePositionCard (NEW - Adapter)                │
│  • Uses BasePositionCard                                 │
│  • NO P&L display                                        │
│  • Shows: Symbol, Name, Market Value only                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              BasePositionCard (Existing)                 │
│           Pure presentation component                    │
│         Uses design tokens from Tailwind                 │
└─────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. OrganizePositionCard (NEW Adapter)

**Purpose**: Transform position data for organize page (NO P&L)

**File**: `src/components/positions/OrganizePositionCard.tsx`

**Interface**:
```typescript
interface OrganizePositionCardProps {
  position: Position
  onClick?: () => void
}
```

**Transformation Logic**:
```typescript
// For stocks/ETFs
primaryText: position.symbol
secondaryText: position.company_name || 'Company'
primaryValue: formatCurrency(position.market_value)
secondaryValue: '' // NO P&L on organize page
secondaryValueColor: 'neutral' // Not used

// For options
primaryText: position.symbol
secondaryText: `${optionTypeLabel} • Strike: $${position.strike_price}`
primaryValue: formatCurrency(Math.abs(position.market_value))
secondaryValue: '' // NO P&L
secondaryValueColor: 'neutral'

// For private
primaryText: position.symbol
secondaryText: position.investment_subtype || 'Alternative Investment'
primaryValue: formatCurrency(Math.abs(position.market_value))
secondaryValue: '' // NO P&L
secondaryValueColor: 'neutral'
```

**Example Implementation**:
```typescript
import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'
import { Position } from '@/hooks/usePositions'

interface OrganizePositionCardProps {
  position: Position
  onClick?: () => void
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  'LC': 'Long Call', 'LP': 'Long Put',
  'SC': 'Short Call', 'SP': 'Short Put'
}

export function OrganizePositionCard({ position, onClick }: OrganizePositionCardProps) {
  // Determine card content based on investment class
  const getCardContent = () => {
    if (position.investment_class === 'OPTIONS') {
      const optionType = OPTION_TYPE_LABELS[position.position_type] || 'Option'
      return {
        primaryText: position.symbol,
        secondaryText: `${optionType} • Strike: $${position.strike_price} • Exp: ${position.expiration_date}`,
        primaryValue: formatCurrency(Math.abs(position.market_value)),
        secondaryValue: '', // NO P&L
        secondaryValueColor: 'neutral' as const
      }
    }

    if (position.investment_class === 'PRIVATE') {
      return {
        primaryText: position.symbol,
        secondaryText: position.investment_subtype || 'Alternative Investment',
        primaryValue: formatCurrency(Math.abs(position.market_value)),
        secondaryValue: '', // NO P&L
        secondaryValueColor: 'neutral' as const
      }
    }

    // PUBLIC (stocks/ETFs)
    return {
      primaryText: position.symbol,
      secondaryText: position.company_name || 'Company',
      primaryValue: formatCurrency(position.market_value),
      secondaryValue: '', // NO P&L
      secondaryValueColor: 'neutral' as const
    }
  }

  const content = getCardContent()

  return <BasePositionCard {...content} onClick={onClick} />
}
```

**Lines of Code**: ~60 lines (vs 117 in current PositionCard)

---

### 2. SelectablePositionCard (NEW Wrapper)

**Purpose**: Add organize-specific features (checkbox, tags, drag-drop)

**File**: `src/components/organize/SelectablePositionCard.tsx`

**Interface**:
```typescript
interface SelectablePositionCardProps {
  children: React.ReactNode  // OrganizePositionCard
  isSelected: boolean
  onToggleSelection: () => void
  tags?: TagItem[]  // NEW: Display tags
  onDropTag?: (tagId: string) => void
}
```

**Features**:
1. **Checkbox** - Left side, controls selection
2. **Tag Display** - Shows tags below the card
3. **Drag & Drop** - Accept tags via drag-drop
4. **Selection Highlighting** - Blue border when selected

**Example Implementation**:
```typescript
import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'

interface SelectablePositionCardProps {
  children: React.ReactNode
  isSelected: boolean
  onToggleSelection: () => void
  tags?: TagItem[]
  onDropTag?: (tagId: string) => void
}

export function SelectablePositionCard({
  children,
  isSelected,
  onToggleSelection,
  tags = [],
  onDropTag
}: SelectablePositionCardProps) {
  const { theme } = useTheme()

  // Drag & drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.add(
      theme === 'dark' ? 'bg-blue-900/20' : 'bg-blue-50'
    )
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId && onDropTag) {
      onDropTag(tagId)
    }
  }

  return (
    <div
      className={`relative transition-all ${
        isSelected
          ? 'ring-2 ring-blue-500 ring-offset-2'
          : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Checkbox + Card Layout */}
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelection}
          className="mt-4 h-4 w-4 cursor-pointer"
        />

        {/* Card Content */}
        <div className="flex-1">
          {children}

          {/* Tags Display */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {tags.map(tag => (
                <TagBadge key={tag.id} tag={tag} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

**Lines of Code**: ~70 lines

---

### 3. Update Position List Components

All 4 list components follow the same pattern. Here's the example for **LongPositionsList**:

**Before** (~84 lines):
```typescript
{longPositions.map(position => (
  <PositionCard
    key={position.id}
    position={position}
    isSelected={isSelected(position.id)}
    onToggleSelection={onToggleSelection}
    onDrop={onDropTag}
  />
))}
```

**After** (~15 lines):
```typescript
{longPositions.map(position => (
  <SelectablePositionCard
    key={position.id}
    isSelected={isSelected(position.id)}
    onToggleSelection={() => onToggleSelection(position.id)}
    tags={position.tags || []}  // NEW: Display tags
    onDropTag={(tagId) => onDropTag?.(position.id, tagId)}
  >
    <OrganizePositionCard position={position} />
  </SelectablePositionCard>
))}
```

**Files to Modify**:
1. `LongPositionsList.tsx` - Use SelectablePositionCard + OrganizePositionCard
2. `ShortPositionsList.tsx` - Use SelectablePositionCard + OrganizePositionCard
3. `OptionsPositionsList.tsx` - Use SelectablePositionCard + OrganizePositionCard
4. `PrivatePositionsList.tsx` - Use SelectablePositionCard + OrganizePositionCard

---

## Implementation Plan

### Phase 1: Create New Components

**Step 1.1**: Create OrganizePositionCard adapter
- File: `src/components/positions/OrganizePositionCard.tsx`
- Handles all 3 investment classes (PUBLIC, OPTIONS, PRIVATE)
- Uses BasePositionCard for presentation
- **NO P&L display** (key difference from Portfolio adapters)

**Step 1.2**: Create SelectablePositionCard wrapper
- File: `src/components/organize/SelectablePositionCard.tsx`
- Adds checkbox, tags, drag-drop, selection highlighting
- Generic wrapper that works with any position card type

**Testing**: Can test both components in isolation before integration

---

### Phase 2: Refactor Position Lists (One at a Time)

**Step 2.1**: Update LongPositionsList.tsx
- Replace PositionCard with SelectablePositionCard + OrganizePositionCard
- Add tags prop mapping
- Test: Long positions display correctly, selection works, tags show

**Step 2.2**: Update ShortPositionsList.tsx
- Same pattern as Step 2.1
- Test: Short positions display correctly

**Step 2.3**: Update OptionsPositionsList.tsx
- Same pattern, handles both long and short options
- Test: Options display correctly with strike/expiration

**Step 2.4**: Update PrivatePositionsList.tsx
- Same pattern
- Test: Private positions display correctly

---

### Phase 3: Cleanup

**Step 3.1**: Delete old PositionCard
- Remove `src/components/organize/PositionCard.tsx`
- Verify no imports remain

**Step 3.2**: Visual regression test
- Screenshot before/after comparison
- Verify checkbox, tags, selection, drag-drop all work

---

## Design Token Usage

All cards will use the same design tokens from `tailwind.config.js`:

**Card Background**:
- Light: `bg-card-bg` (white)
- Dark: `bg-card-bg-dark` (slate-800)

**Text Colors**:
- Primary: `text-card-text` / `text-card-text-dark`
- Secondary: `text-card-text-muted` / `text-card-text-muted-dark`

**Selection State** (NEW):
```javascript
// Add to tailwind.config.js
selection: {
  ring: 'hsl(217, 91%, 60%)',    // blue-500
  'ring-dark': 'hsl(217, 91%, 60%)' // Same in dark mode
}
```

**Tag Badges**:
- Use custom colors from tag.color property
- White text on colored background

---

## Data Flow

### Position with Tags
```typescript
interface Position {
  id: string
  symbol: string
  company_name?: string
  market_value: number
  // ... other fields
  tags?: TagItem[]  // NEW: Tags associated with position
}

interface TagItem {
  id: string
  name: string
  color: string
  // ... other fields
}
```

### Tag Assignment Flow
1. User drags tag from TagList
2. Drops on SelectablePositionCard
3. SelectablePositionCard calls `onDropTag(tagId)`
4. Parent handler applies tag to position
5. Position re-renders with new tag in tags array

---

## Benefits

### Code Quality
- ✅ **50% reduction** in organize card code (~117 lines → ~60 lines)
- ✅ **Single source of truth** for card styling
- ✅ **Design tokens** centralized in Tailwind config
- ✅ **Reusable wrapper** pattern for future pages

### UX Consistency
- ✅ **Same card design** across Portfolio and Organize pages
- ✅ **Consistent colors** and spacing via design tokens
- ✅ **Dark mode** works identically on both pages

### Maintainability
- ✅ **One place to update** card styling (BasePositionCard)
- ✅ **Clear separation** of concerns (presentation vs organize features)
- ✅ **Easy to extend** (add new organize features to wrapper only)

### Feature Additions
- ✅ **Tag display** now built into organize cards
- ✅ **Visual feedback** for drag-drop operations
- ✅ **Consistent selection** highlighting

---

## Testing Strategy

### Visual Tests
1. **Checkbox functionality** - Select/deselect positions
2. **Tag display** - Tags show below cards
3. **Drag & drop** - Visual feedback when dragging tags
4. **Selection highlighting** - Blue ring appears when selected
5. **Dark mode** - All features work in dark theme

### Functional Tests
1. **Combine positions** - Multi-select and create strategy
2. **Apply tags** - Drag tag onto position
3. **Strategy display** - Strategy cards show correctly
4. **Empty states** - Quadrants with no positions display correctly

### Regression Tests
- Compare screenshots before/after refactoring
- Verify all organize features still work
- Check performance (should be same or better)

---

## Migration Checklist

### Phase 1 Checklist
- [ ] Create OrganizePositionCard.tsx
- [ ] Create SelectablePositionCard.tsx
- [ ] Test both components in isolation
- [ ] Add selection design tokens to tailwind.config.js

### Phase 2 Checklist
- [ ] Update LongPositionsList.tsx
- [ ] Update ShortPositionsList.tsx
- [ ] Update OptionsPositionsList.tsx
- [ ] Update PrivatePositionsList.tsx
- [ ] Update Position interface to include tags?: TagItem[]

### Phase 3 Checklist
- [ ] Delete organize/PositionCard.tsx
- [ ] Verify no broken imports
- [ ] Visual regression test (screenshot comparison)
- [ ] Manual testing of all features
- [ ] Commit and push changes

---

## Comparison: Portfolio vs Organize

| Feature | Portfolio Page | Organize Page |
|---------|---------------|---------------|
| **Card Component** | StockPositionCard, OptionPositionCard, PrivatePositionCard | OrganizePositionCard (universal) |
| **P&L Display** | ✅ Yes (color-coded) | ❌ No |
| **Market Value** | ✅ Yes | ✅ Yes |
| **Checkboxes** | ❌ No | ✅ Yes |
| **Tag Display** | ❌ No | ✅ Yes |
| **Drag & Drop** | ❌ No | ✅ Yes |
| **Selection State** | ❌ No | ✅ Yes (blue ring) |
| **Strategy Cards** | ❌ No | ✅ Yes |
| **Base Component** | BasePositionCard | BasePositionCard (same!) |
| **Design Tokens** | ✅ Yes | ✅ Yes (same tokens) |

---

## Risk Assessment

### Low Risk
- ✅ BasePositionCard already proven on Portfolio page
- ✅ Wrapper pattern doesn't change existing behavior
- ✅ Can test each list component independently
- ✅ Easy rollback (keep old PositionCard until done)

### Medium Risk
- ⚠️ Tag display is new feature (not currently shown on organize page)
- ⚠️ Need to ensure Position interface has tags array

### Mitigation
- Test tag display thoroughly with real data
- Add fallback: `tags={position.tags || []}` to handle missing data
- Keep old PositionCard until all 4 lists are migrated

---

## Future Enhancements

### Phase 4 (Future)
1. **Bulk tag operations** - Apply tag to multiple selected positions at once
2. **Tag filtering** - Filter positions by tag
3. **Tag colors** - Auto-generate contrasting colors
4. **Tag autocomplete** - Suggest existing tags when creating new ones
5. **Position grouping** - Group by tag in UI

---

## Conclusion

This refactoring brings the Organize page into alignment with our new reusable component architecture while:
- **Eliminating code duplication** (~50% reduction)
- **Adding tag display** functionality
- **Maintaining all existing features** (checkboxes, drag-drop, strategies)
- **Using design tokens** for consistent styling
- **Setting up for future enhancements** (tag filtering, bulk operations)

**Estimated Timeline**: 3-4 hours
**Risk Level**: Low
**Impact**: High (benefits entire organize page, sets pattern for future pages)
