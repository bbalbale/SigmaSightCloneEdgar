# Mobile Implementation Plan

**Document Version**: 1.0
**Last Updated**: November 1, 2025
**Status**: Ready for implementation

---

## Overview

This document provides a detailed, phased implementation plan for making SigmaSight mobile-responsive. The plan prioritizes foundational work (navigation, utilities) before component-specific enhancements.

**Timeline**: 3-4 weeks (part-time development)
**Priority**: Foundation → Core Pages → Enhancements

---

## Phase 1: Foundation & Navigation (Week 1)

**Goal**: Get basic mobile navigation working with proper layout structure.

### 1.1 Update Layout Structure (1-2 hours)

**Files to modify**:
- `frontend/app/layout.tsx`
- `frontend/src/components/navigation/TopNavigationBar.tsx`

**Tasks**:

1. **Hide TopNavigationBar on mobile**:
   ```tsx
   // TopNavigationBar.tsx - Line 24
   <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 hidden md:flex">
   ```
   - Add `hidden md:flex` to header element
   - Test: TopNav disappears on mobile (<768px)

2. **Update main content padding** in layout.tsx:
   ```tsx
   // layout.tsx - Line 32
   <main className="flex-1 pb-16 md:pb-0">
     {children}
   </main>
   ```
   - Add `pb-16` for mobile (space for bottom nav)
   - Add `md:pb-0` for desktop (no bottom nav)

**Acceptance Criteria**:
- ✅ Top nav hidden on mobile (<768px)
- ✅ Top nav visible on desktop (≥768px)
- ✅ Content has bottom padding on mobile

---

### 1.2 Create BottomNavigation Component (3-4 hours)

**File**: `frontend/src/components/navigation/BottomNavigation.tsx`

**Implementation**:

```typescript
'use client'

import React, { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Command, Search, TrendingUp, Sparkles, User } from 'lucide-react'
import { UserDropdown } from './UserDropdown'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/command-center', icon: Command, label: 'Command Center' },
  { href: '/research-and-analyze', icon: Search, label: 'Research' },
  { href: '/risk-metrics', icon: TrendingUp, label: 'Risk' },
  { href: '/sigmasight-ai', icon: Sparkles, label: 'AI' },
]

interface NavItemProps {
  href?: string
  icon: React.ElementType
  label: string
  isActive: boolean
  onClick?: () => void
}

function NavItem({ href, icon: Icon, label, isActive, onClick }: NavItemProps) {
  const [showLabel, setShowLabel] = useState(false)
  const timeoutRef = useRef<NodeJS.Timeout>()

  const handleTouchStart = () => {
    timeoutRef.current = setTimeout(() => {
      setShowLabel(true)
    }, 500) // 500ms long-press
  }

  const handleTouchEnd = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setShowLabel(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const content = (
    <div className="relative">
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-1',
          'h-14 px-3 rounded-lg transition-colors duration-200',
          isActive
            ? 'text-accent font-semibold'
            : 'text-muted-foreground hover:text-foreground'
        )}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onMouseLeave={() => setShowLabel(false)}
      >
        <Icon className={cn('h-6 w-6', isActive && 'text-accent')} />
        {/* Active indicator */}
        {isActive && (
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-8 h-1 rounded-full bg-accent" />
        )}
      </div>

      {/* Tooltip on long-press */}
      {showLabel && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-lg whitespace-nowrap border">
          {label}
        </div>
      )}
    </div>
  )

  if (href) {
    return (
      <Link href={href} className="flex-1 min-w-0">
        {content}
      </Link>
    )
  }

  return (
    <button onClick={onClick} className="flex-1 min-w-0">
      {content}
    </button>
  )
}

export function BottomNavigation({ className }: { className?: string }) {
  const pathname = usePathname()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <nav
      className={cn(
        'fixed bottom-0 left-0 right-0 z-50',
        'border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        'pb-safe', // iOS safe area support
        className
      )}
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex items-center justify-around h-14">
        {/* 4 Main Navigation Items */}
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <NavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              isActive={isActive}
            />
          )
        })}

        {/* 5th Item: User Dropdown */}
        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <div className="flex-1 min-w-0">
              <NavItem
                icon={User}
                label="Profile"
                isActive={false}
                onClick={() => setDropdownOpen(true)}
              />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-56 mb-2"
            align="end"
            side="top"
          >
            <UserDropdown />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  )
}
```

**Key Features**:
- 5 items (4 nav + 1 user dropdown)
- Long-press (500ms) shows label tooltip
- Active page indicator (top bar + color)
- iOS safe area support
- Responsive tap targets (56px height)

**Acceptance Criteria**:
- ✅ Displays on mobile only (`md:hidden`)
- ✅ Fixed at bottom of screen
- ✅ Active page highlighted
- ✅ Long-press shows label
- ✅ User dropdown works
- ✅ iOS safe area respected

---

### 1.3 Update UserDropdown for Bottom Nav (1 hour)

**File**: `frontend/src/components/navigation/UserDropdown.tsx`

**Changes needed**:

Currently, `UserDropdown` renders the trigger button AND the menu content. For BottomNavigation, we need to use it as **content only** (no trigger).

**Option 1: Extract content to separate component** (Recommended):

```tsx
// UserDropdown.tsx

// Add new export for content only
export function UserDropdownContent() {
  const { user, logout } = useAuth()
  const portfolioName = usePortfolioName()

  const handleLogout = async () => {
    await logout()
  }

  return (
    <>
      {/* User info section */}
      {user && (
        <>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">{user.fullName}</p>
              <p className="text-xs leading-none text-muted-foreground">
                {user.email}
              </p>
              {portfolioName && (
                <p className="text-xs leading-none text-muted-foreground mt-1">
                  Portfolio: {portfolioName}
                </p>
              )}
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
        </>
      )}

      {/* Settings */}
      <DropdownMenuItem asChild>
        <Link href="/settings" className="flex items-center cursor-pointer">
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </Link>
      </DropdownMenuItem>

      {/* Logout */}
      <DropdownMenuSeparator />
      <DropdownMenuItem
        onClick={handleLogout}
        className="text-red-600 dark:text-red-400 cursor-pointer"
      >
        <LogOut className="mr-2 h-4 w-4" />
        <span>Logout</span>
      </DropdownMenuItem>
    </>
  )
}

// Keep existing UserDropdown for desktop top nav
export function UserDropdown() {
  const { user } = useAuth()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          <User className="h-4 w-4" />
          <span className="hidden sm:inline-block">{user?.fullName || 'User'}</span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end">
        <UserDropdownContent />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

**Then update BottomNavigation** to use content directly:

```tsx
// BottomNavigation.tsx
import { UserDropdownContent } from './UserDropdown'

// ...

<DropdownMenuContent className="w-56 mb-2" align="end" side="top">
  <UserDropdownContent />
</DropdownMenuContent>
```

**Acceptance Criteria**:
- ✅ Desktop top nav still works (UserDropdown component)
- ✅ Mobile bottom nav uses same menu content
- ✅ Settings link works
- ✅ Logout works

---

### 1.4 Add BottomNavigation to Layout (30 minutes)

**File**: `frontend/app/layout.tsx`

**Changes**:

```tsx
import { ConditionalNavigationHeader } from '@/components/navigation/ConditionalNavigationHeader'
import { BottomNavigation } from '@/components/navigation/BottomNavigation'

// ...

<div className="flex min-h-screen flex-col">
  <ConditionalNavigationHeader />
  <main className="flex-1 pb-16 md:pb-0">
    {children}
  </main>
  <BottomNavigation className="md:hidden" />
</div>
```

**Acceptance Criteria**:
- ✅ Bottom nav visible on all authenticated pages (mobile only)
- ✅ Bottom nav respects ConditionalNavigationHeader logic (no bottom nav on login/landing)

---

### 1.5 Testing Phase 1 (1 hour)

**Test on**:
- [ ] iPhone 14 (375px) - Safari
- [ ] Samsung Galaxy S23 (360px) - Chrome
- [ ] iPad Air (820px) - Should show desktop nav

**Test scenarios**:
1. Navigate between all 4 pages
2. Verify active page highlight
3. Long-press each icon to see label
4. Open user dropdown, navigate to settings
5. Logout and verify navigation disappears

**Bug fixes and polish** as needed.

---

**Phase 1 Total Time**: ~8-10 hours

**Deliverables**:
- ✅ Bottom navigation component (5 icons)
- ✅ Top nav hidden on mobile
- ✅ Layout updated with proper padding
- ✅ Tested on mobile devices

---

## Phase 2: Utility Hooks & Helpers (Week 1-2)

**Goal**: Create reusable hooks and utilities for responsive behavior.

### 2.1 Create useMediaQuery Hook (30 minutes)

**File**: `frontend/src/hooks/useMediaQuery.ts`

```typescript
'use client'

import { useState, useEffect } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const media = window.matchMedia(query)

    // Set initial value
    setMatches(media.matches)

    // Listen for changes
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches)
    media.addEventListener('change', listener)

    return () => media.removeEventListener('change', listener)
  }, [query])

  return matches
}

// Convenience hooks
export function useIsMobile() {
  return useMediaQuery('(max-width: 767px)')
}

export function useIsDesktop() {
  return useMediaQuery('(min-width: 768px)')
}

export function useIsTablet() {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)')
}
```

**Usage**:
```tsx
import { useIsMobile } from '@/hooks/useMediaQuery'

const isMobile = useIsMobile()

return isMobile ? <MobileView /> : <DesktopView />
```

---

### 2.2 Add Mobile-Specific CSS Variables (30 minutes)

**File**: `frontend/src/styles/globals.css`

**Add to `:root` section**:

```css
:root {
  /* Existing variables ... */

  /* Mobile-specific variables */
  --tap-target-min: 44px;
  --bottom-nav-height: 56px;
  --spacing-mobile: 12px;
  --spacing-desktop: 24px;
  --text-mobile-sm: 12px;
  --text-mobile-base: 14px;
}

/* iOS safe area support */
@supports (padding: env(safe-area-inset-bottom)) {
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom);
  }
}
```

---

**Phase 2 Total Time**: ~1-2 hours

**Deliverables**:
- ✅ `useMediaQuery` hook
- ✅ Convenience hooks (`useIsMobile`, `useIsDesktop`)
- ✅ Mobile CSS variables

---

## Phase 3: Command Center Mobile (Week 2)

**Goal**: Make Command Center fully mobile-responsive.

### 3.1 HeroMetricsRow - Mobile Grid (Current Approach) ✅

**File**: `frontend/src/components/command-center/HeroMetricsRow.tsx`

**Current implementation**:
```tsx
<div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
```

**Status**: Already works on mobile (stacks vertically). No changes needed for Phase 3.

**Future Enhancement (Phase 5)**: Add swipeable carousel option.

---

### 3.2 HoldingsTable - Responsive Wrapper (3-4 hours)

**File**: `frontend/src/components/command-center/HoldingsTable.tsx`

**Strategy**: Conditional rendering (table on desktop, cards on mobile)

**Implementation**:

```tsx
'use client'

import React from 'react'
import { useIsMobile } from '@/hooks/useMediaQuery'
import { HoldingsTableDesktop } from './HoldingsTableDesktop' // Rename current component
import { HoldingsTableMobile } from './HoldingsTableMobile' // New component

export function HoldingsTable({ holdings, loading }: HoldingsTableProps) {
  const isMobile = useIsMobile()

  // Preferred: CSS-based (better performance)
  return (
    <>
      <div className="hidden md:block">
        <HoldingsTableDesktop holdings={holdings} loading={loading} />
      </div>
      <div className="md:hidden">
        <HoldingsTableMobile holdings={holdings} loading={loading} />
      </div>
    </>
  )
}
```

**New file**: `frontend/src/components/command-center/HoldingsTableMobile.tsx`

```tsx
'use client'

import React from 'react'
import { type Holding } from '@/hooks/useCommandCenterData'

interface HoldingsTableMobileProps {
  holdings: Holding[]
  loading: boolean
}

export function HoldingsTableMobile({ holdings, loading }: HoldingsTableMobileProps) {
  if (loading) {
    return <div className="space-y-3 p-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="animate-pulse rounded-lg p-4 bg-secondary h-24" />
      ))}
    </div>
  }

  return (
    <section className="px-4 pb-8">
      <div className="container mx-auto">
        <h2 className="text-lg font-semibold mb-4">Holdings ({holdings.length})</h2>
        <div className="space-y-3">
          {holdings.map((holding) => (
            <HoldingCard key={holding.position_id} holding={holding} />
          ))}
        </div>
      </div>
    </section>
  )
}

function HoldingCard({ holding }: { holding: Holding }) {
  const isProfitable = holding.total_pnl_percent >= 0

  return (
    <div
      className="rounded-lg p-4 transition-all duration-200 border"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      {/* Header row: Symbol + Type */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-bold text-base" style={{ color: 'var(--text-primary)' }}>
            {holding.symbol}
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: holding.position_type === 'LONG' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              color: holding.position_type === 'LONG' ? 'var(--color-success)' : 'var(--color-error)'
            }}
          >
            {holding.position_type}
          </span>
        </div>
        {/* Sector tag */}
        {holding.sector && (
          <span className="text-xs px-2 py-0.5 rounded bg-tertiary text-secondary">
            {holding.sector}
          </span>
        )}
      </div>

      {/* Value row */}
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-sm text-secondary">Market Value</span>
        <span className="text-lg font-bold tabular-nums" style={{ color: 'var(--text-primary)' }}>
          ${holding.market_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
        </span>
      </div>

      {/* P&L row */}
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-secondary">Total P&L</span>
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-medium tabular-nums"
            style={{ color: isProfitable ? 'var(--color-success)' : 'var(--color-error)' }}
          >
            ${holding.total_pnl.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </span>
          <span
            className="text-sm font-bold tabular-nums"
            style={{ color: isProfitable ? 'var(--color-success)' : 'var(--color-error)' }}
          >
            ({isProfitable ? '+' : ''}{holding.total_pnl_percent.toFixed(1)}%)
          </span>
        </div>
      </div>

      {/* Tap to expand indicator (future enhancement) */}
      {/* <button className="text-xs text-accent mt-2">Tap to expand ▼</button> */}
    </div>
  )
}
```

**Acceptance Criteria**:
- ✅ Table shows on desktop
- ✅ Compact cards show on mobile
- ✅ All holdings displayed
- ✅ Cards show: symbol, type, value, P&L
- ✅ Color coding for long/short and profit/loss

---

### 3.3 RiskMetricsRow - Already Responsive ✅

**File**: `frontend/src/components/command-center/RiskMetricsRow.tsx`

**Current implementation**: Already stacks on mobile. No changes needed.

**Future Enhancement (Phase 5)**: Add collapse/expand functionality.

---

**Phase 3 Total Time**: ~4-5 hours

**Deliverables**:
- ✅ HoldingsTable responsive (table on desktop, cards on mobile)
- ✅ Command Center fully functional on mobile

---

## Phase 4: Research & Analyze Mobile (Week 2-3)

**Goal**: Make Research & Analyze mobile-friendly with collapsible tag bar and responsive tables.

### 4.1 Sticky Tag Bar - Collapsible on Mobile (2-3 hours)

**File**: `frontend/src/components/research-and-analyze/StickyTagBar.tsx`

**Create new wrapper component**:

```tsx
'use client'

import React, { useState } from 'react'
import { useIsMobile } from '@/hooks/useMediaQuery'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { TagList } from '@/components/organize/TagList'

interface StickyTagBarProps {
  tags: Tag[]
  onCreate: (name: string, color: string) => Promise<void>
  onDelete: (tagId: string) => Promise<void>
  onRestoreTags: () => Promise<void>
  restoringTags: boolean
  tagsLoading: boolean
}

export function StickyTagBar({
  tags,
  onCreate,
  onDelete,
  onRestoreTags,
  restoringTags,
  tagsLoading
}: StickyTagBarProps) {
  const isMobile = useIsMobile()
  const [isExpanded, setIsExpanded] = useState(false)

  // Desktop: Always show full tag bar
  if (!isMobile) {
    return (
      <section
        className="sticky top-14 z-40 transition-colors duration-300 border-b"
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderColor: 'var(--border-primary)'
        }}
      >
        <div className="container mx-auto py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <TagList tags={tags} onCreate={onCreate} onDelete={onDelete} />
            </div>
            <button
              onClick={onRestoreTags}
              disabled={restoringTags || tagsLoading}
              className="px-4 py-2 rounded-md font-medium transition-all duration-200 disabled:cursor-not-allowed flex-shrink-0"
              style={{
                backgroundColor: restoringTags || tagsLoading ? 'var(--bg-tertiary)' : 'var(--color-accent)',
                color: restoringTags || tagsLoading ? 'var(--text-tertiary)' : '#ffffff'
              }}
            >
              {restoringTags ? 'Restoring...' : 'Restore Sector Tags'}
            </button>
          </div>
        </div>
      </section>
    )
  }

  // Mobile: Collapsible tag bar
  return (
    <section
      className="sticky top-0 z-40 transition-colors duration-300 border-b"
      style={{
        backgroundColor: 'var(--bg-primary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      <div className="container mx-auto">
        {/* Collapsed view */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full py-3 px-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
              Tags
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-secondary text-secondary">
              {tags.length}
            </span>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-secondary" />
          ) : (
            <ChevronDown className="h-4 w-4 text-secondary" />
          )}
        </button>

        {/* Expanded view */}
        {isExpanded && (
          <div className="border-t px-4 pb-4 pt-3" style={{ borderColor: 'var(--border-primary)' }}>
            <div className="space-y-3">
              <div className="overflow-x-auto">
                <TagList tags={tags} onCreate={onCreate} onDelete={onDelete} />
              </div>
              <button
                onClick={onRestoreTags}
                disabled={restoringTags || tagsLoading}
                className="w-full px-4 py-2 rounded-md font-medium transition-all duration-200 disabled:cursor-not-allowed"
                style={{
                  backgroundColor: restoringTags || tagsLoading ? 'var(--bg-tertiary)' : 'var(--color-accent)',
                  color: restoringTags || tagsLoading ? 'var(--text-tertiary)' : '#ffffff'
                }}
              >
                {restoringTags ? 'Restoring...' : 'Restore Sector Tags'}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
```

**Update ResearchAndAnalyzeContainer** to use new component instead of inline tag bar.

**Acceptance Criteria**:
- ✅ Desktop: Full tag bar (current behavior)
- ✅ Mobile: Collapsed by default, shows "Tags (8)"
- ✅ Mobile: Tap to expand shows full tag list + restore button
- ✅ Tags list scrolls horizontally if needed

---

### 4.2 ResearchTableView - Responsive Wrapper (3-4 hours)

**File**: `frontend/src/components/research-and-analyze/ResearchTableView.tsx`

**Strategy**: Similar to HoldingsTable - table on desktop, cards on mobile.

**Implementation**:

```tsx
'use client'

import React from 'react'
import { useIsMobile } from '@/hooks/useMediaQuery'
import { ResearchTableDesktop } from './ResearchTableDesktop' // Rename current
import { ResearchTableMobile } from './ResearchTableMobile' // New

export function ResearchTableView({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate,
  onTagDrop,
  onRemoveTag
}: ResearchTableViewProps) {
  return (
    <>
      <div className="hidden md:block">
        <ResearchTableDesktop
          positions={positions}
          title={title}
          aggregateReturnEOY={aggregateReturnEOY}
          aggregateReturnNextYear={aggregateReturnNextYear}
          onTargetPriceUpdate={onTargetPriceUpdate}
          onTagDrop={onTagDrop}
          onRemoveTag={onRemoveTag}
        />
      </div>
      <div className="md:hidden">
        <ResearchTableMobile
          positions={positions}
          title={title}
          aggregateReturnEOY={aggregateReturnEOY}
          aggregateReturnNextYear={aggregateReturnNextYear}
          onTargetPriceUpdate={onTargetPriceUpdate}
          onTagDrop={onTagDrop}
          onRemoveTag={onRemoveTag}
        />
      </div>
    </>
  )
}
```

**New file**: `frontend/src/components/research-and-analyze/ResearchTableMobile.tsx`

```tsx
'use client'

import React from 'react'
import { type EnhancedPosition } from '@/services/positionResearchService'

// ... (similar structure to HoldingsTableMobile, but includes target price display)

function ResearchPositionCard({ position, onTagDrop, onRemoveTag }: any) {
  const hasTarget = position.target_price_eoy !== null
  const targetReturn = position.target_return_eoy || 0
  const isProfitable = targetReturn >= 0

  return (
    <div
      className="rounded-lg p-4 transition-all duration-200 border"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      {/* Header: Symbol + Type */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-bold text-base">{position.symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-tertiary text-secondary">
            {position.position_type}
          </span>
        </div>
      </div>

      {/* Price row */}
      <div className="flex items-center justify-between mb-2 text-sm">
        <span className="text-secondary">Current Price</span>
        <span className="font-mono">${position.current_price?.toFixed(2) || 'N/A'}</span>
      </div>

      {/* Target row */}
      {hasTarget && (
        <>
          <div className="flex items-center justify-between mb-2 text-sm">
            <span className="text-secondary">Target EOY</span>
            <span className="font-mono">${position.target_price_eoy?.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Target Return</span>
            <span
              className="text-base font-bold tabular-nums"
              style={{ color: isProfitable ? 'var(--color-success)' : 'var(--color-error)' }}
            >
              {isProfitable ? '+' : ''}{targetReturn.toFixed(1)}%
            </span>
          </div>
        </>
      )}

      {/* Tags */}
      {position.tags && position.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {position.tags.map((tag: any) => (
            <span
              key={tag.id}
              className="text-xs px-2 py-1 rounded-full"
              style={{
                backgroundColor: tag.color + '20',
                color: tag.color
              }}
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-3 pt-3 border-t" style={{ borderColor: 'var(--border-primary)' }}>
        <button className="flex-1 text-sm px-3 py-1.5 rounded bg-tertiary text-secondary">
          Edit Target
        </button>
        <button className="flex-1 text-sm px-3 py-1.5 rounded bg-tertiary text-secondary">
          Add Tag
        </button>
      </div>
    </div>
  )
}
```

**Acceptance Criteria**:
- ✅ Table shows on desktop
- ✅ Cards show on mobile
- ✅ Cards display: symbol, current price, target, return, tags
- ✅ Color-coded returns
- ✅ Action buttons (Edit Target, Add Tag)

---

**Phase 4 Total Time**: ~5-7 hours

**Deliverables**:
- ✅ Collapsible tag bar on mobile
- ✅ Research table responsive (cards on mobile)
- ✅ Research & Analyze fully functional on mobile

---

## Phase 5: Risk Metrics & AI Mobile (Week 3)

**Goal**: Ensure Risk Metrics and AI pages work well on mobile.

### 5.1 Risk Components - Collapsible Sections (2-3 hours)

**Files**: Various risk component files

**Strategy**: Wrap each section in a collapsible accordion.

**Create wrapper**: `frontend/src/components/risk-metrics/CollapsibleSection.tsx`

```tsx
'use client'

import React, { useState } from 'react'
import { useIsMobile } from '@/hooks/useMediaQuery'
import { ChevronDown, ChevronUp } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  defaultExpanded?: boolean
  children: React.ReactNode
}

export function CollapsibleSection({
  title,
  defaultExpanded = false,
  children
}: CollapsibleSectionProps) {
  const isMobile = useIsMobile()
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || !isMobile)

  // Desktop: Always expanded
  if (!isMobile) {
    return <>{children}</>
  }

  // Mobile: Collapsible
  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between"
      >
        <h3 className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>
          {title}
        </h3>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-secondary" />
        ) : (
          <ChevronDown className="h-5 w-5 text-secondary" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  )
}
```

**Update RiskMetricsContainer**:

```tsx
<CollapsibleSection title="Volatility Analysis">
  <VolatilityMetrics {...} />
</CollapsibleSection>

<CollapsibleSection title="Sector Exposure">
  <SectorExposure {...} />
</CollapsibleSection>

<CollapsibleSection title="Concentration Metrics">
  <ConcentrationMetrics {...} />
</CollapsibleSection>

// etc.
```

**Acceptance Criteria**:
- ✅ Desktop: All sections expanded (current behavior)
- ✅ Mobile: Sections collapsed by default
- ✅ Mobile: Tap to expand shows content

---

### 5.2 AI Chat - Mobile Optimization (1-2 hours)

**File**: `frontend/src/components/claude-insights/ClaudeChatInterface.tsx`

**Changes**:
- Ensure input area is properly sized for mobile keyboards
- Add mobile-specific padding
- Test on actual mobile devices

**Minor CSS adjustments** (likely already responsive).

---

**Phase 5 Total Time**: ~3-5 hours

**Deliverables**:
- ✅ Risk components collapsible on mobile
- ✅ AI chat optimized for mobile
- ✅ All 4 core pages fully mobile-responsive

---

## Phase 6: Enhancements & Polish (Week 3-4)

**Optional enhancements** (can be deferred):

### 6.1 Swipeable Hero Metrics Carousel (4-6 hours)

Use Embla Carousel to create swipeable metric cards on mobile.

**Library**: `npm install embla-carousel-react`

---

### 6.2 Pull-to-Refresh (2-3 hours)

Add pull-to-refresh on mobile for data reload.

**Library**: `npm install react-pull-to-refresh` or custom hook.

---

### 6.3 Bottom Sheets for Details (3-4 hours)

Use bottom sheets instead of inline expansion for position details.

**Library**: `npm install vaul` (React bottom sheet)

---

### 6.4 Swipe-to-Tag Gestures (4-6 hours)

Add drag-and-drop tag functionality on mobile.

**Library**: `@dnd-kit/core` (already have React DnD?)

---

**Phase 6 Total Time**: ~13-19 hours (optional)

---

## Testing Plan

### Manual Testing

**Devices**:
- iPhone 14 (375px width)
- Samsung Galaxy S23 (360px width)
- iPad Air (820px width)

**Test Matrix**:

| Feature | Mobile (<768px) | Desktop (≥768px) |
|---------|----------------|------------------|
| Navigation | Bottom nav (5 icons) | Top nav bar |
| Command Center | Cards stack | Grid layout |
| Holdings | Position cards | Table |
| Research | Position cards | Table |
| Tag Bar | Collapsible | Always visible |
| Risk Metrics | Collapsible sections | Expanded sections |
| AI Chat | Full width | Split layout |

### Accessibility Testing

- [ ] VoiceOver (iOS) navigation works
- [ ] TalkBack (Android) navigation works
- [ ] Focus indicators visible
- [ ] Tap targets ≥44px
- [ ] Color contrast ≥4.5:1

### Performance Testing

- [ ] Lighthouse Mobile score ≥90
- [ ] First Contentful Paint <2s on 4G
- [ ] Cumulative Layout Shift <0.1
- [ ] No horizontal scroll on mobile

---

## Dependencies

**New npm packages needed**:

**Phase 1-5 (Required)**:
- None! All features use existing libraries.

**Phase 6 (Optional)**:
```bash
npm install embla-carousel-react          # Swipeable carousel
npm install vaul                          # Bottom sheets
npm install react-pull-to-refresh         # Pull to refresh (or custom)
```

---

## Rollout Plan

### Week 1
- ✅ Phase 1: Foundation & Navigation
- ✅ Phase 2: Utility Hooks

### Week 2
- ✅ Phase 3: Command Center Mobile
- ✅ Phase 4: Research & Analyze Mobile (start)

### Week 3
- ✅ Phase 4: Research & Analyze Mobile (finish)
- ✅ Phase 5: Risk Metrics & AI Mobile
- ✅ Testing & bug fixes

### Week 4 (Optional)
- ✅ Phase 6: Enhancements (carousel, pull-to-refresh, etc.)
- ✅ Final polish and QA

---

## Success Criteria

**Definition of Done**:
- [ ] All 4 core pages functional on mobile (<768px)
- [ ] Bottom navigation works on mobile
- [ ] Top navigation hidden on mobile
- [ ] Tables convert to cards on mobile
- [ ] Tag bar collapsible on mobile
- [ ] Risk sections collapsible on mobile
- [ ] User can navigate, view data, and perform actions on mobile
- [ ] Lighthouse Mobile score ≥85
- [ ] No accessibility violations
- [ ] Tested on iPhone and Android

**Future Work** (post-Phase 6):
- Settings page mobile optimization
- Advanced gestures (swipe-to-delete, etc.)
- Offline support
- Mobile-specific animations

---

## Summary

This plan provides a clear, phased approach to making SigmaSight mobile-responsive:

**Core Work (3 weeks)**:
- Phase 1-5: Navigation, utilities, and all 4 core pages
- ~20-25 hours total

**Optional Enhancements (1 week)**:
- Phase 6: Carousel, pull-to-refresh, bottom sheets, gestures
- ~13-19 hours additional

**Total Effort**: 30-45 hours (part-time over 3-4 weeks)

All work builds on existing architecture (ThemeContext, Container pattern) with minimal disruption to desktop experience.
