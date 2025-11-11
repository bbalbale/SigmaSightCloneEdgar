# Public Positions Page Implementation Guide - Enhanced

**Purpose**: Research-focused public positions page with comprehensive analysis metrics
**Route**: `/public-positions`
**Investment Class**: PUBLIC (regular equities, ETFs)
**Last Updated**: October 8, 2025

---

## Overview

This page displays all public equity and ETF positions with comprehensive research and target data:
- **Dual-section layout**: Longs (top) and Shorts (bottom)
- **Advanced filtering**: By tags, sector, industry within each section
- **Research metrics**: User targets, analyst targets, EPS estimates, revenue projections
- **Return calculations**: Expected returns for this year and next year
- **Aggregate analytics**: Portfolio-level expected returns for longs and shorts

---

## Data Architecture

### API Endpoints Used

```typescript
// 1. Position data with tags and current prices
GET /api/v1/data/positions/details?portfolio_id={id}

// 2. Company profiles with analyst data
GET /api/v1/data/company-profiles?portfolio_id={id}

// 3. User-generated target prices
GET /api/v1/target-prices/{portfolio_id}
```

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  usePublicPositions Hook                                │
│                                                         │
│  1. Fetch positions (/data/positions/details)          │
│  2. Fetch company profiles (/data/company-profiles)    │
│  3. Fetch user targets (/target-prices/{id})           │
│  4. Merge data by symbol                               │
│  5. Calculate expected returns                         │
│  6. Split into longs and shorts                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PublicPositionsContainer                               │
│                                                         │
│  ┌─────────────────────────────────────────┐           │
│  │  Longs Section                          │           │
│  │  - Filter/sort controls                 │           │
│  │  - Summary metrics (% return aggregate) │           │
│  │  - Enhanced table with 12+ columns      │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  ┌─────────────────────────────────────────┐           │
│  │  Shorts Section                         │           │
│  │  - Filter/sort controls                 │           │
│  │  - Summary metrics (% return aggregate) │           │
│  │  - Enhanced table with 12+ columns      │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## Column Design

### Table Columns (14 total)

| # | Column | Source | Calculation |
|---|--------|--------|-------------|
| 1 | Symbol | `/data/positions/details` | Direct |
| 2 | Company Name | `/data/company-profiles` | `company_name` |
| 3 | Tags | `/data/positions/details` | `tags[]` array |
| 4 | Sector | `/data/company-profiles` | `sector` |
| 5 | Industry | `/data/company-profiles` | `industry` |
| 6 | % of Equity | `/data/positions/details` | `market_value / portfolio_equity * 100` |
| 7 | Current Price | `/data/positions/details` | `current_price` |
| 8 | User Target EOY | `/target-prices/{id}` | `target_price_eoy` |
| 9 | User Target Next Yr | `/target-prices/{id}` | `target_price_next_year` |
| 10 | Analyst Target | `/data/company-profiles` | `target_mean_price` |
| 11 | EPS This Year | `/data/company-profiles` | `current_year_earnings_avg` |
| 12 | EPS Next Year | `/data/company-profiles` | `next_year_earnings_avg` |
| 13 | Revenue This Year | `/data/company-profiles` | `current_year_revenue_avg` |
| 14 | Revenue Next Year | `/data/company-profiles` | `next_year_revenue_avg` |
| 15 | Target Return EOY | Calculated | `(user_target_eoy - current_price) / current_price * 100` |
| 16 | Target Return Next Yr | Calculated | `(user_target_next - current_price) / current_price * 100` |

---

## Implementation Steps

### Step 1: Create Position Research Service

**File**: `src/services/positionResearchService.ts`

```typescript
// src/services/positionResearchService.ts
import { apiClient } from '@/services/apiClient'

export interface EnhancedPosition {
  // Position basics
  id: string
  symbol: string
  position_type: 'LONG' | 'SHORT'
  quantity: number
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number

  // Tags
  tags: Array<{ id: string; name: string; color: string }>

  // Company profile data
  company_name?: string
  sector?: string
  industry?: string

  // Analyst data
  target_mean_price?: number
  current_year_earnings_avg?: number
  next_year_earnings_avg?: number
  current_year_revenue_avg?: number
  next_year_revenue_avg?: number

  // User targets
  user_target_eoy?: number
  user_target_next_year?: number

  // Calculated fields
  percent_of_equity: number
  target_return_eoy?: number
  target_return_next_year?: number
}

interface FetchEnhancedPositionsParams {
  portfolioId: string
  investmentClass?: 'PUBLIC' | 'PRIVATE' | 'OPTIONS'
}

interface EnhancedPositionsResult {
  positions: EnhancedPosition[]
  longPositions: EnhancedPosition[]
  shortPositions: EnhancedPosition[]
  portfolioEquity: number
}

export const positionResearchService = {
  /**
   * Fetch and merge position data from multiple APIs
   * - Positions API: Basic position data, tags, prices
   * - Company Profiles API: Company info, analyst targets, estimates
   * - Target Prices API: User-defined target prices
   */
  async fetchEnhancedPositions({
    portfolioId,
    investmentClass
  }: FetchEnhancedPositionsParams): Promise<EnhancedPositionsResult> {
    // Fetch all data in parallel
    const [positionsRes, profilesRes, targetsRes] = await Promise.all([
      apiClient.get<{
        positions: any[]
        summary: { total_market_value: number }
      }>(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`),

      apiClient.get<{ profiles: any[] }>(
        `/api/v1/data/company-profiles?portfolio_id=${portfolioId}`
      ),

      apiClient.get<any[]>(`/api/v1/target-prices/${portfolioId}`)
    ])

    // Filter by investment class if specified
    let filteredPositions = positionsRes.positions
    if (investmentClass) {
      filteredPositions = filteredPositions.filter(
        p => p.investment_class === investmentClass
      )
    }

    // Get portfolio equity for % calculations
    const portfolioEquity = positionsRes.summary?.total_market_value || 0

    // Create lookup maps for O(1) access
    const profilesMap = new Map(
      profilesRes.profiles.map(p => [p.symbol, p])
    )
    const targetsMap = new Map(
      targetsRes.map(t => [t.symbol, t])
    )

    // Merge data and calculate derived fields
    const enhanced: EnhancedPosition[] = filteredPositions.map(pos => {
      const profile = profilesMap.get(pos.symbol)
      const target = targetsMap.get(pos.symbol)

      // Calculate % of portfolio equity
      const percent_of_equity = portfolioEquity > 0
        ? (pos.market_value / portfolioEquity) * 100
        : 0

      // Calculate target returns
      const target_return_eoy = target?.target_price_eoy && pos.current_price
        ? ((target.target_price_eoy - pos.current_price) / pos.current_price) * 100
        : undefined

      const target_return_next_year = target?.target_price_next_year && pos.current_price
        ? ((target.target_price_next_year - pos.current_price) / pos.current_price) * 100
        : undefined

      return {
        ...pos,
        // Company profile fields
        company_name: profile?.company_name,
        sector: profile?.sector,
        industry: profile?.industry,
        target_mean_price: profile?.target_mean_price,
        current_year_earnings_avg: profile?.current_year_earnings_avg,
        next_year_earnings_avg: profile?.next_year_earnings_avg,
        current_year_revenue_avg: profile?.current_year_revenue_avg,
        next_year_revenue_avg: profile?.next_year_revenue_avg,
        // User target fields
        user_target_eoy: target?.target_price_eoy,
        user_target_next_year: target?.target_price_next_year,
        // Calculated fields
        percent_of_equity,
        target_return_eoy,
        target_return_next_year
      }
    })

    // Split into longs and shorts
    const longPositions = enhanced.filter(p => p.position_type === 'LONG')
    const shortPositions = enhanced.filter(p => p.position_type === 'SHORT')

    return {
      positions: enhanced,
      longPositions,
      shortPositions,
      portfolioEquity
    }
  },

  /**
   * Calculate weighted aggregate return for a set of positions
   */
  calculateAggregateReturn(
    positions: EnhancedPosition[],
    returnField: 'target_return_eoy' | 'target_return_next_year'
  ): number {
    const totalWeight = positions.reduce((sum, p) => sum + p.percent_of_equity, 0)
    if (totalWeight === 0) return 0

    const weightedSum = positions.reduce((sum, p) => {
      const ret = p[returnField] || 0
      return sum + (ret * p.percent_of_equity)
    }, 0)

    return weightedSum / totalWeight
  }
}
```

**Key Features**:
- ✅ Centralized data fetching logic
- ✅ Reusable across the application
- ✅ Testable independently of React
- ✅ Clean separation of concerns
- ✅ O(1) lookup performance with Maps

---

### Step 2: Simplified Data Hook

**File**: `src/hooks/usePublicPositions.ts`

```typescript
// src/hooks/usePublicPositions.ts
'use client'

import { useState, useEffect, useMemo } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  positionResearchService,
  type EnhancedPosition
} from '@/services/positionResearchService'

interface UsePublicPositionsReturn {
  longPositions: EnhancedPosition[]
  shortPositions: EnhancedPosition[]
  loading: boolean
  error: string | null
  aggregateReturns: {
    longs_eoy: number
    longs_next_year: number
    shorts_eoy: number
    shorts_next_year: number
  }
  refetch: () => Promise<void>
}

export function usePublicPositions(): UsePublicPositionsReturn {
  const { portfolioId } = usePortfolioStore()
  const [longPositions, setLongPositions] = useState<EnhancedPosition[]>([])
  const [shortPositions, setShortPositions] = useState<EnhancedPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    if (!portfolioId) return

    setLoading(true)
    setError(null)

    try {
      // Use service to fetch and merge all data
      const result = await positionResearchService.fetchEnhancedPositions({
        portfolioId,
        investmentClass: 'PUBLIC'
      })

      setLongPositions(result.longPositions)
      setShortPositions(result.shortPositions)
    } catch (err) {
      console.error('Failed to fetch positions:', err)
      setError('Failed to load positions data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (portfolioId) {
      fetchData()
    }
  }, [portfolioId])

  // Calculate aggregate returns using service method
  const aggregateReturns = useMemo(() => ({
    longs_eoy: positionResearchService.calculateAggregateReturn(
      longPositions,
      'target_return_eoy'
    ),
    longs_next_year: positionResearchService.calculateAggregateReturn(
      longPositions,
      'target_return_next_year'
    ),
    shorts_eoy: positionResearchService.calculateAggregateReturn(
      shortPositions,
      'target_return_eoy'
    ),
    shorts_next_year: positionResearchService.calculateAggregateReturn(
      shortPositions,
      'target_return_next_year'
    )
  }), [longPositions, shortPositions])

  return {
    longPositions,
    shortPositions,
    loading,
    error,
    aggregateReturns,
    refetch: fetchData
  }
}
```

**Key Features**:
- ✅ Simple, focused on React state management
- ✅ Delegates data fetching to service layer
- ✅ Easy to test and maintain
- ✅ Includes refetch function for manual refresh

---

### Step 3: Research Position Card Component

**File**: `src/components/positions/ResearchPositionCard.tsx`

```typescript
// src/components/positions/ResearchPositionCard.tsx
'use client'

import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { TagBadge } from '@/components/organize/TagBadge'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'
import type { EnhancedPosition } from '@/services/positionResearchService'

interface ResearchPositionCardProps {
  position: EnhancedPosition
  onClick?: () => void
}

export function ResearchPositionCard({ position, onClick }: ResearchPositionCardProps) {
  const { theme } = useTheme()

  return (
    <div className="space-y-3">
      {/* Main Position Card */}
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={position.company_name || position.symbol}
        primaryValue={formatCurrency(position.market_value)}
        secondaryValue={`${formatNumber(position.percent_of_equity, 1)}% of portfolio`}
        secondaryValueColor="neutral"
        onClick={onClick}
      />

      {/* Tags Row */}
      {position.tags && position.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {position.tags.map(tag => (
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      )}

      {/* Research Data - Compact Grid */}
      <div className={`text-xs space-y-1.5 px-2 py-2 rounded-md transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800/50' : 'bg-gray-50'
      }`}>
        {/* Sector & Industry */}
        {(position.sector || position.industry) && (
          <div className={`flex justify-between transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            <span className="font-medium">Sector:</span>
            <span>{position.sector || '-'} • {position.industry || '-'}</span>
          </div>
        )}

        {/* Price & Targets */}
        <div className={`space-y-1 transition-colors duration-300 ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
          <div className="flex justify-between">
            <span className="font-medium">Current:</span>
            <span>{formatCurrency(position.current_price)}</span>
          </div>
          {position.user_target_eoy && (
            <div className="flex justify-between">
              <span className="font-medium">Target EOY:</span>
              <span className={position.target_return_eoy && position.target_return_eoy >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatCurrency(position.user_target_eoy)} ({position.target_return_eoy ? `${position.target_return_eoy >= 0 ? '+' : ''}${formatNumber(position.target_return_eoy, 1)}%` : '-'})
              </span>
            </div>
          )}
          {position.user_target_next_year && (
            <div className="flex justify-between">
              <span className="font-medium">Target Next Yr:</span>
              <span className={position.target_return_next_year && position.target_return_next_year >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatCurrency(position.user_target_next_year)} ({position.target_return_next_year ? `${position.target_return_next_year >= 0 ? '+' : ''}${formatNumber(position.target_return_next_year, 1)}%` : '-'})
              </span>
            </div>
          )}
          {position.target_mean_price && (
            <div className="flex justify-between">
              <span className="font-medium">Analyst Target:</span>
              <span>{formatCurrency(position.target_mean_price)}</span>
            </div>
          )}
        </div>

        {/* EPS & Revenue */}
        {(position.current_year_earnings_avg || position.next_year_earnings_avg) && (
          <div className={`space-y-1 pt-1 border-t transition-colors duration-300 ${
            theme === 'dark' ? 'border-slate-700 text-slate-400' : 'border-gray-200 text-gray-600'
          }`}>
            {position.current_year_earnings_avg && (
              <div className="flex justify-between">
                <span className="font-medium">EPS This Yr:</span>
                <span>{formatCurrency(position.current_year_earnings_avg)}</span>
              </div>
            )}
            {position.next_year_earnings_avg && (
              <div className="flex justify-between">
                <span className="font-medium">EPS Next Yr:</span>
                <span>{formatCurrency(position.next_year_earnings_avg)}</span>
              </div>
            )}
            {position.current_year_revenue_avg && (
              <div className="flex justify-between">
                <span className="font-medium">Rev This Yr:</span>
                <span>${(position.current_year_revenue_avg / 1e9).toFixed(2)}B</span>
              </div>
            )}
            {position.next_year_revenue_avg && (
              <div className="flex justify-between">
                <span className="font-medium">Rev Next Yr:</span>
                <span>${(position.next_year_revenue_avg / 1e9).toFixed(2)}B</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

---

### Step 4: Enhanced Positions Section Component

**File**: `src/components/positions/EnhancedPositionsSection.tsx`

```typescript
// src/components/positions/EnhancedPositionsSection.tsx
'use client'

import { useState, useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PositionList } from '@/components/common/PositionList'
import { ResearchPositionCard } from '@/components/positions/ResearchPositionCard'
import { formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'
import type { EnhancedPosition } from '@/services/positionResearchService'

interface EnhancedPositionsSectionProps {
  positions: EnhancedPosition[]
  title: string
  aggregateReturnEOY: number
  aggregateReturnNextYear: number
}

export function EnhancedPositionsSection({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear
}: EnhancedPositionsSectionProps) {
  const { theme } = useTheme()
  const [filterBy, setFilterBy] = useState<'all' | 'tag' | 'sector' | 'industry'>('all')
  const [filterValue, setFilterValue] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'percent_of_equity' | 'symbol' | 'target_return_eoy'>('percent_of_equity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Get unique values for filters
  const filterOptions = useMemo(() => {
    if (filterBy === 'tag') {
      const tags = new Set<string>()
      positions.forEach(p => p.tags?.forEach(t => tags.add(t.name)))
      return Array.from(tags).sort()
    }
    if (filterBy === 'sector') {
      return Array.from(new Set(positions.map(p => p.sector).filter(Boolean))).sort()
    }
    if (filterBy === 'industry') {
      return Array.from(new Set(positions.map(p => p.industry).filter(Boolean))).sort()
    }
    return []
  }, [positions, filterBy])

  // Filter positions
  const filteredPositions = useMemo(() => {
    if (filterBy === 'all' || filterValue === 'all') return positions

    return positions.filter(p => {
      if (filterBy === 'tag') {
        return p.tags?.some(t => t.name === filterValue)
      }
      if (filterBy === 'sector') {
        return p.sector === filterValue
      }
      if (filterBy === 'industry') {
        return p.industry === filterValue
      }
      return true
    })
  }, [positions, filterBy, filterValue])

  // Sort positions
  const sortedPositions = useMemo(() => {
    return [...filteredPositions].sort((a, b) => {
      const aValue = a[sortBy] as any
      const bValue = b[sortBy] as any

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
      }

      return sortOrder === 'asc'
        ? String(aValue || '').localeCompare(String(bValue || ''))
        : String(bValue || '').localeCompare(String(aValue || ''))
    })
  }, [filteredPositions, sortBy, sortOrder])

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className={`text-lg font-semibold transition-colors duration-300 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            {title}
          </h3>
          <Badge variant="secondary" className={`transition-colors duration-300 ${
            theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
          }`}>
            {filteredPositions.length}
          </Badge>
        </div>

        {/* Aggregate Returns */}
        <div className={`text-right text-sm transition-colors duration-300 ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
          <p className="font-medium mb-1">Expected Return (Weighted)</p>
          <div className="flex gap-4">
            <div>
              <span className="text-xs">EOY: </span>
              <span className={`font-semibold ${aggregateReturnEOY >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {aggregateReturnEOY >= 0 ? '+' : ''}{formatNumber(aggregateReturnEOY, 2)}%
              </span>
            </div>
            <div>
              <span className="text-xs">Next Yr: </span>
              <span className={`font-semibold ${aggregateReturnNextYear >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {aggregateReturnNextYear >= 0 ? '+' : ''}{formatNumber(aggregateReturnNextYear, 2)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Sort Controls */}
      <div className="flex gap-4 mb-4 flex-wrap">
        {/* Filter By */}
        <Select value={filterBy} onValueChange={(v: any) => { setFilterBy(v); setFilterValue('all') }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Positions</SelectItem>
            <SelectItem value="tag">Filter by Tag</SelectItem>
            <SelectItem value="sector">Filter by Sector</SelectItem>
            <SelectItem value="industry">Filter by Industry</SelectItem>
          </SelectContent>
        </Select>

        {/* Filter Value */}
        {filterBy !== 'all' && filterOptions.length > 0 && (
          <Select value={filterValue} onValueChange={setFilterValue}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder={`Select ${filterBy}...`} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All {filterBy}s</SelectItem>
              {filterOptions.map(option => (
                <SelectItem key={option} value={option}>{option}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Sort By */}
        <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Sort by..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="percent_of_equity">% of Portfolio</SelectItem>
            <SelectItem value="symbol">Symbol (A-Z)</SelectItem>
            <SelectItem value="target_return_eoy">Return EOY</SelectItem>
          </SelectContent>
        </Select>

        {/* Sort Order */}
        <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="desc">High to Low</SelectItem>
            <SelectItem value="asc">Low to High</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Position Cards */}
      <PositionList
        items={sortedPositions}
        renderItem={(position) => (
          <ResearchPositionCard
            key={position.id}
            position={position}
          />
        )}
        emptyMessage={`No ${title.toLowerCase()} found`}
      />
    </div>
  )
}
```

**Key Features**:
- ✅ Uses `BasePositionCard` for consistent styling with Organize page
- ✅ Uses `PositionList` for item rendering
- ✅ Card-based layout matching Organize page
- ✅ Filter by tags, sector, or industry
- ✅ Sort controls for different views
- ✅ Aggregate return display in header
- ✅ Theme-aware styling
- ✅ Compact research data below each card

---

### Step 5: Container Component

**File**: `src/containers/PublicPositionsContainer.tsx`

```typescript
// src/containers/PublicPositionsContainer.tsx
'use client'

import { usePublicPositions } from '@/hooks/usePublicPositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { useTheme } from '@/contexts/ThemeContext'

export function PublicPositionsContainer() {
  const { theme } = useTheme()
  const { longPositions, shortPositions, loading, error, aggregateReturns } = usePublicPositions()

  if (loading && !longPositions.length && !shortPositions.length) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-8">
          <div className="container mx-auto text-center">
            <p className={`text-lg transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Loading positions...
            </p>
          </div>
        </section>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-8">
          <div className="container mx-auto">
            <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Public Positions Research
            </h1>
            <p className={`text-red-600 mt-4`}>{error}</p>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            Public Positions Research
          </h1>
          <p className={`transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Comprehensive analysis with targets, analyst estimates, and EPS/revenue projections
          </p>
        </div>
      </section>

      {/* Longs Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-3">
              <EnhancedPositionsSection
                positions={longPositions}
                title="Long Positions"
                aggregateReturnEOY={aggregateReturns.longs_eoy}
                aggregateReturnNextYear={aggregateReturns.longs_next_year}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Shorts Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-3">
              <EnhancedPositionsSection
                positions={shortPositions}
                title="Short Positions"
                aggregateReturnEOY={aggregateReturns.shorts_eoy}
                aggregateReturnNextYear={aggregateReturns.shorts_next_year}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
```

**Key Features**:
- ✅ Matches Organize page layout (section-based)
- ✅ Theme-aware styling (dark mode support)
- ✅ Clean separation of longs and shorts
- ✅ Loading and error states with proper styling
- ✅ Container-based responsive layout

---

### Step 6: Page Route

**File**: `app/public-positions/page.tsx`

```typescript
// app/public-positions/page.tsx
'use client'

import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'

export default function PublicPositionsPage() {
  return <PublicPositionsContainer />
}
```

---

## File Creation Checklist

### New Files to Create
- [ ] `src/services/positionResearchService.ts` - ⭐ **NEW** Data fetching & merging service
- [ ] `src/hooks/usePublicPositions.ts` - Simplified React state hook
- [ ] `src/components/positions/ResearchPositionCard.tsx` - ⭐ **NEW** Card-based research display
- [ ] `src/components/positions/EnhancedPositionsSection.tsx` - ⭐ **NEW** Section with filters (matches Organize)
- [ ] `src/containers/PublicPositionsContainer.tsx` - Section-based container (matches Organize)
- [ ] `app/public-positions/page.tsx` - Route wrapper

### Existing Dependencies
- [x] `src/services/apiClient.ts` - HTTP client
- [x] `src/stores/portfolioStore.ts` - Portfolio ID from Zustand
- [x] `src/lib/formatters.ts` - formatCurrency, formatNumber
- [x] `src/components/ui/*` - ShadCN UI components (Card, Select, Badge)
- [x] `src/components/common/BasePositionCard.tsx` - ⭐ Reused from Organize page
- [x] `src/components/common/PositionList.tsx` - ⭐ Reused from Organize page
- [x] `src/components/organize/TagBadge.tsx` - ⭐ Reused from Organize page
- [x] `src/contexts/ThemeContext.tsx` - ⭐ Theme support (dark mode)

---

## API Integration Summary

### 1. Position Details API
```typescript
GET /api/v1/data/positions/details?portfolio_id={id}

Response: {
  positions: [{
    id, symbol, position_type, quantity, current_price,
    market_value, cost_basis, tags: [], ...
  }],
  summary: { total_market_value: number }
}
```

### 2. Company Profiles API
```typescript
GET /api/v1/data/company-profiles?portfolio_id={id}

Response: {
  profiles: [{
    symbol, company_name, sector, industry,
    target_mean_price,
    current_year_earnings_avg, next_year_earnings_avg,
    current_year_revenue_avg, next_year_revenue_avg,
    ... (53 total fields)
  }]
}
```

### 3. Target Prices API
```typescript
GET /api/v1/target-prices/{portfolio_id}

Response: [{
  symbol, position_type,
  target_price_eoy, target_price_next_year,
  downside_target_price, ...
}]
```

---

## Calculation Reference

### % of Equity
```typescript
percent_of_equity = (position.market_value / portfolio_total_equity) * 100
```

### Target Return %
```typescript
// For EOY
target_return_eoy = ((user_target_eoy - current_price) / current_price) * 100

// For Next Year
target_return_next_year = ((user_target_next - current_price) / current_price) * 100
```

### Aggregate Weighted Return
```typescript
// Calculate for longs or shorts
totalWeight = sum(position.percent_of_equity for all positions)
weightedSum = sum(position.target_return * position.percent_of_equity)
aggregateReturn = weightedSum / totalWeight
```

---

## Testing Steps

1. **Verify API responses**
   - Check `/data/positions/details` returns positions with tags
   - Check `/data/company-profiles` returns 53 fields
   - Check `/target-prices/{id}` returns user targets

2. **Test data merging**
   - Verify symbols match across all 3 APIs
   - Check missing data displays as "-"
   - Validate calculations (% equity, returns)

3. **Test filtering**
   - Filter by tags - should show only positions with selected tag
   - Filter by sector - should show only positions in sector
   - Filter by industry - should show only positions in industry

4. **Test sorting**
   - Sort by % equity (descending by default)
   - Sort by returns (ascending/descending toggle)
   - Sort by symbol (alphabetical)

5. **Test aggregate calculations**
   - Verify weighted returns match manual calculations
   - Check longs and shorts calculate separately

6. **Test edge cases**
   - No positions in portfolio
   - No user targets set
   - No company profile data available
   - All positions are longs (no shorts section)

---

## Performance Considerations

### Data Fetching
- ✅ **Parallel API calls**: All 3 APIs called with `Promise.all()`
- ✅ **Single request per API**: No N+1 queries
- ✅ **Map-based lookups**: O(1) time complexity for merging

### Expected Load Times
- 3 API calls in parallel: ~200-500ms
- Data merging: <50ms
- Rendering 50 positions: <100ms
- **Total**: ~350-650ms for full page load

### Optimization Opportunities
1. **Frontend caching**: Cache API responses for 30-60 seconds
2. **Incremental loading**: Load visible rows first, lazy-load rest
3. **Virtual scrolling**: For portfolios with 100+ positions
4. **Memoization**: Already implemented with `useMemo`

---

## Common Issues & Solutions

### Issue 1: Missing company profile data
**Symptom**: Company name, sector, industry show "-"
**Cause**: Symbol not in company_profiles table
**Solution**: Run company profile sync: `POST /admin/batch/trigger/company-profiles`

### Issue 2: Missing user targets
**Symptom**: User target columns show "-"
**Cause**: No target prices created for position
**Solution**: User must set target prices via target prices page/API

### Issue 3: Incorrect % of equity
**Symptom**: Percentages don't add to 100%
**Cause**: Calculated against total portfolio value, not just public positions
**Solution**: Working as designed - shows % of entire portfolio

### Issue 4: Aggregate return seems wrong
**Symptom**: Weighted return doesn't match expectations
**Cause**: Positions with no target prices have 0% return in calculation
**Solution**: Set target prices for all positions, or filter calculation to only include positions with targets

---

## Future Enhancements

### Phase 2: Interactive Features
- [ ] Click symbol to open detailed research modal
- [ ] Inline editing of user target prices
- [ ] Export to CSV/Excel functionality
- [ ] Add notes/commentary per position

### Phase 3: Advanced Analytics
- [ ] Compare user targets vs analyst targets
- [ ] Show historical accuracy of targets
- [ ] Add custom calculated fields
- [ ] Integration with chat AI for recommendations

### Phase 4: Visualization
- [ ] Chart of expected returns distribution
- [ ] Sector/industry allocation pie charts
- [ ] Timeline view of target price changes
- [ ] Heatmap of returns by sector

---

## Architecture Benefits

### Service Layer Pattern
```
┌─────────────────────────────────────────┐
│  React Hook (usePublicPositions)        │
│  - State management                     │
│  - useEffect for data fetching          │
│  - useMemo for derived calculations     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Service (positionResearchService)      │
│  - API calls (3 parallel requests)      │
│  - Data merging                         │
│  - Business logic                       │
│  - Calculation utilities                │
└─────────────────────────────────────────┘
```

**Benefits**:
1. ✅ **Testability**: Service can be unit tested without React
2. ✅ **Reusability**: Same service for exports, reports, other pages
3. ✅ **Maintainability**: Business logic separated from UI logic
4. ✅ **Performance**: Service handles optimization (Maps, parallel calls)
5. ✅ **Extensibility**: Easy to add caching, error retry, etc.

---

## Summary

**New Architecture**: Research-focused dual-section layout with service layer (matches Organize page)
**Data Sources**: 3 parallel API calls merged by symbol in dedicated service
**Display**: Card-based layout using `BasePositionCard` + research data panels
**Calculations**: Frontend-calculated returns and weighted aggregates
**Filtering**: By tags, sector, industry within each section
**Performance**: <650ms expected page load for 50 positions

**Key Improvements**:
1. **Service layer** (`positionResearchService`) handles all data fetching, merging, and business logic
2. **Consistent UI** - Reuses `BasePositionCard`, `PositionList`, `TagBadge` from Organize page
3. **Theme support** - Dark mode using ThemeContext (matches Organize)
4. **Section-based layout** - Same structure as Organize page for visual consistency

This design provides institutional-grade research capabilities while maintaining the exact same look and feel as the Organize page, with powerful filtering and comprehensive metrics for informed decision-making.
