# Public Positions Page Implementation Guide

**Purpose**: Step-by-step guide to create the Public Positions page  
**Route**: `/public-positions`  
**Investment Class**: PUBLIC (regular equities, ETFs)  
**Last Updated**: September 29, 2025

---

## Overview

This page displays all public equity and ETF positions with:
- Summary metrics (total value, cost basis, P&L, return %)
- Sortable table of positions
- Long/Short position grouping
- Real-time P&L calculations

---

## Service Dependencies

### Services Used (Already Exist)
```typescript
import { apiClient } from '@/services/apiClient'          // HTTP client
import { portfolioResolver } from '@/services/portfolioResolver'  // Portfolio ID
import { useAuth } from '@/app/providers'                // Auth context
```

### API Endpoint Used
```
GET /api/v1/data/positions/details?portfolio_id={id}
```

### Response Format
```typescript
{
  positions: [
    {
      id: string
      symbol: string
      investment_class: 'PUBLIC'
      position_type: 'LONG' | 'SHORT'
      quantity: number
      current_price: number
      market_value: number
      cost_basis: number
      unrealized_pnl: number
      unrealized_pnl_percent: number
    }
  ]
}
```

---

## Implementation Steps

### Step 1: Create Custom Hook

**File**: `src/hooks/usePositions.ts`

```typescript
// src/hooks/usePositions.ts
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/app/providers'
import { apiClient } from '@/services/apiClient'

interface Position {
  id: string
  symbol: string
  quantity: number
  position_type: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
  investment_class: 'PUBLIC' | 'PRIVATE' | 'OPTIONS'
}

export function usePositions(investmentClass?: 'PUBLIC' | 'PRIVATE' | 'OPTIONS') {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { portfolioId } = useAuth()
  
  useEffect(() => {
    if (portfolioId) {
      fetchPositions()
    }
  }, [portfolioId, investmentClass])
  
  const fetchPositions = async () => {
    if (!portfolioId) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Use existing apiClient service
      const endpoint = `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
      const response = await apiClient.get<{ positions: Position[] }>(endpoint)
      
      // Filter by investment class if specified
      let filteredPositions = response.positions || []
      
      if (investmentClass) {
        filteredPositions = filteredPositions.filter(
          p => p.investment_class === investmentClass
        )
      }
      
      setPositions(filteredPositions)
    } catch (err) {
      console.error('Failed to fetch positions:', err)
      setError('Failed to load positions')
    } finally {
      setLoading(false)
    }
  }
  
  return {
    positions,
    loading,
    error,
    refetch: fetchPositions
  }
}
```

**Key Points**:
- ✅ Uses existing `apiClient` service
- ✅ Uses existing `useAuth` hook for portfolioId
- ✅ Filters positions by investment_class
- ✅ Handles loading and error states
- ✅ Provides refetch function

---

### Step 2: Create UI Components

#### Component A: Position Summary Cards

**File**: `src/components/positions/PositionSummary.tsx`

```typescript
// src/components/positions/PositionSummary.tsx
'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency } from '@/lib/formatters'

interface Position {
  market_value: number
  cost_basis: number
  unrealized_pnl: number
}

interface PositionSummaryProps {
  positions: Position[]
}

export function PositionSummary({ positions }: PositionSummaryProps) {
  const summary = useMemo(() => {
    const totalMarketValue = positions.reduce((sum, p) => sum + p.market_value, 0)
    const totalCostBasis = positions.reduce((sum, p) => sum + p.cost_basis, 0)
    const totalPnL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0)
    const totalReturn = totalCostBasis > 0 ? (totalPnL / totalCostBasis) * 100 : 0
    
    return { totalMarketValue, totalCostBasis, totalPnL, totalReturn }
  }, [positions])
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-600">
            Market Value
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatCurrency(summary.totalMarketValue)}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-600">
            Cost Basis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatCurrency(summary.totalCostBasis)}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-600">
            Unrealized P&L
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${
            summary.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatCurrency(summary.totalPnL)}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-600">
            Total Return
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${
            summary.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {summary.totalReturn >= 0 ? '+' : ''}
            {summary.totalReturn.toFixed(2)}%
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

**Key Points**:
- ✅ Uses existing `formatCurrency` from `/src/lib/formatters.ts`
- ✅ Calculates summary metrics from positions array
- ✅ Color-codes positive/negative P&L
- ✅ Responsive grid layout

#### Component B: Positions Table

**File**: `src/components/positions/PositionsTable.tsx`

```typescript
// src/components/positions/PositionsTable.tsx
'use client'

import { useState, useMemo } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/formatters'

interface Position {
  id: string
  symbol: string
  quantity: number
  position_type: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
}

interface PositionsTableProps {
  positions: Position[]
}

export function PositionsTable({ positions }: PositionsTableProps) {
  const [sortBy, setSortBy] = useState<keyof Position>('market_value')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  
  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aValue = a[sortBy]
      const bValue = b[sortBy]
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
      }
      
      return sortOrder === 'asc' 
        ? String(aValue).localeCompare(String(bValue))
        : String(bValue).localeCompare(String(aValue))
    })
  }, [positions, sortBy, sortOrder])
  
  const handleSort = (column: keyof Position) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }
  
  if (positions.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-gray-500">No public positions found</p>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('quantity')}
                >
                  Quantity
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('current_price')}
                >
                  Price
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('market_value')}
                >
                  Market Value
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('cost_basis')}
                >
                  Cost Basis
                </TableHead>
                <TableHead 
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('unrealized_pnl')}
                >
                  Unrealized P&L
                </TableHead>
                <TableHead>Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPositions.map((position) => (
                <TableRow key={position.id}>
                  <TableCell className="font-medium">
                    {position.symbol}
                  </TableCell>
                  <TableCell>
                    {formatNumber(position.quantity, 0)}
                  </TableCell>
                  <TableCell>
                    {formatCurrency(position.current_price)}
                  </TableCell>
                  <TableCell>
                    {formatCurrency(position.market_value)}
                  </TableCell>
                  <TableCell>
                    {formatCurrency(position.cost_basis)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <span className={
                        position.unrealized_pnl >= 0 
                          ? 'text-green-600' 
                          : 'text-red-600'
                      }>
                        {formatCurrency(position.unrealized_pnl)}
                      </span>
                      <Badge 
                        variant={
                          position.unrealized_pnl >= 0 
                            ? 'default' 
                            : 'destructive'
                        }
                        className="text-xs"
                      >
                        {position.unrealized_pnl >= 0 ? '+' : ''}
                        {formatNumber(position.unrealized_pnl_percent, 2)}%
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {position.position_type}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Key Points**:
- ✅ Uses existing UI components from `/src/components/ui/`
- ✅ Uses existing formatters from `/src/lib/formatters.ts`
- ✅ Sortable columns
- ✅ Empty state handling
- ✅ Responsive table with overflow

---

### Step 3: Create Container Component

**File**: `src/containers/PublicPositionsContainer.tsx`

```typescript
// src/containers/PublicPositionsContainer.tsx
'use client'

import { usePositions } from '@/hooks/usePositions'
import { PositionsTable } from '@/components/positions/PositionsTable'
import { PositionSummary } from '@/components/positions/PositionSummary'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function PublicPositionsContainer() {
  const { positions, loading, error } = usePositions('PUBLIC')
  
  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Public Positions</h1>
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-red-600">{error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Public Positions
        </h1>
        <p className="text-gray-600 mt-1">
          {positions.length} position{positions.length !== 1 ? 's' : ''}
        </p>
      </div>
      
      <PositionSummary positions={positions} />
      <PositionsTable positions={positions} />
    </div>
  )
}
```

**Key Points**:
- ✅ Uses custom hook for data
- ✅ Handles loading state with skeletons
- ✅ Handles error state
- ✅ Composes UI components
- ✅ ~40 lines total

---

### Step 4: Create Thin Page Route

**File**: `app/public-positions/page.tsx`

```typescript
// app/public-positions/page.tsx
'use client'

import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'

export default function PublicPositionsPage() {
  return <PublicPositionsContainer />
}
```

**Key Points**:
- ✅ Only 8 lines
- ✅ Just imports and renders container
- ✅ No business logic
- ✅ Client component

---

## File Creation Checklist

### Files to Create
- [ ] `src/hooks/usePositions.ts` - Custom data hook
- [ ] `src/components/positions/PositionSummary.tsx` - Summary cards
- [ ] `src/components/positions/PositionsTable.tsx` - Data table
- [ ] `src/containers/PublicPositionsContainer.tsx` - Page container
- [ ] `app/public-positions/page.tsx` - Thin route wrapper

### Dependencies (Already Exist)
- [x] `src/services/apiClient.ts` - HTTP client
- [x] `src/services/portfolioResolver.ts` - Portfolio ID
- [x] `app/providers.tsx` - Auth context (create separately)
- [x] `src/lib/formatters.ts` - Number formatting
- [x] `src/components/ui/*` - ShadCN UI components

---

## Testing Steps

1. **Create files** in order: Hook → Components → Container → Page
2. **Test hook** - Verify data fetching works
3. **Test components** - Check UI rendering
4. **Test container** - Verify composition
5. **Test page** - Navigate to `/public-positions`
6. **Test filtering** - Verify only PUBLIC positions show
7. **Test sorting** - Click table headers
8. **Test loading** - Check skeleton display
9. **Test errors** - Handle API failures gracefully

---

## Common Issues & Solutions

### Issue 1: Portfolio ID not found
**Symptom**: Hook doesn't fetch data  
**Cause**: portfolioId is null  
**Solution**: Ensure user is authenticated and portfolioResolver has loaded

### Issue 2: Empty positions array
**Symptom**: "No public positions found" shows  
**Cause**: Investment class filter too strict or no data  
**Solution**: Check database has positions with investment_class='PUBLIC'

### Issue 3: API call fails
**Symptom**: Error state displays  
**Cause**: Backend not running or proxy misconfigured  
**Solution**: Verify backend is running, check proxy configuration

---

## Next Steps

After implementing Public Positions:
1. Use same pattern for Private Positions (change filter to 'PRIVATE')
2. Reuse `usePositions` hook
3. Reuse `PositionsTable` and `PositionSummary` components
4. Create thin container and page files

---

## Summary

**Pattern**: Hook → Components → Container → Page  
**Services Used**: apiClient, portfolioResolver, useAuth  
**New Files**: 5 total (1 hook, 2 components, 1 container, 1 page)  
**Reusable**: Hook and components work for all position types
