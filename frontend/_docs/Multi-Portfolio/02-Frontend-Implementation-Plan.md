# Frontend Implementation Plan: Multi-Account Aggregation

**Feature:** Multi-Account Portfolio Aggregation
**Created:** 2025-11-01
**Status:** Planning Phase
**Estimated Effort:** 3-4 weeks (frontend only)

---

## Overview

This document details the frontend implementation plan for displaying multiple portfolios (accounts) with aggregated analytics across all accounts.

**Core UX Approach:**
- **Default view:** Aggregate (all accounts combined)
- **Optional filtering:** User can filter to single account
- **Clear breakdown:** Show which positions are in which account
- **Seamless experience:** No page reloads when filtering

---

## Phase 1: State Management

### Update Portfolio Store

**File:** `frontend/src/stores/portfolioStore.ts`

**Current Implementation:**
```typescript
interface PortfolioStore {
  // Single portfolio
  portfolioId: string | null
  portfolioName: string | null

  setPortfolio: (id: string, name?: string | null) => void
  clearPortfolio: () => void
  hasPortfolio: () => boolean
}
```

**New Implementation:**
```typescript
interface PortfolioListItem {
  id: string
  account_name: string
  account_type: string
  total_value: number
  position_count: number
  is_active: boolean
}

interface PortfolioStore {
  // Multiple portfolios
  portfolios: PortfolioListItem[]

  // Selected filter (null = show all accounts aggregated)
  selectedPortfolioId: string | null

  // Actions
  setPortfolios: (portfolios: PortfolioListItem[]) => void
  setSelectedPortfolio: (id: string | null) => void
  addPortfolio: (portfolio: PortfolioListItem) => void
  updatePortfolio: (id: string, updates: Partial<PortfolioListItem>) => void
  removePortfolio: (id: string) => void
  clearAll: () => void

  // Computed getters
  getTotalValue: () => number
  getPortfolioCount: () => number
  getActivePortfolios: () => PortfolioListItem[]
  getSelectedPortfolio: () => PortfolioListItem | null
  isAggregateView: () => boolean
}

export const usePortfolioStore = create<PortfolioStore>()(
  persist(
    (set, get) => ({
      // Initial state
      portfolios: [],
      selectedPortfolioId: null,  // null = aggregate view

      // Actions
      setPortfolios: (portfolios) => set({ portfolios }),

      setSelectedPortfolio: (id) => set({ selectedPortfolioId: id }),

      addPortfolio: (portfolio) => set((state) => ({
        portfolios: [...state.portfolios, portfolio]
      })),

      updatePortfolio: (id, updates) => set((state) => ({
        portfolios: state.portfolios.map(p =>
          p.id === id ? { ...p, ...updates } : p
        )
      })),

      removePortfolio: (id) => set((state) => ({
        portfolios: state.portfolios.filter(p => p.id !== id),
        // If removing selected portfolio, reset to aggregate view
        selectedPortfolioId: state.selectedPortfolioId === id
          ? null
          : state.selectedPortfolioId
      })),

      clearAll: () => set({
        portfolios: [],
        selectedPortfolioId: null
      }),

      // Computed getters
      getTotalValue: () => {
        const { portfolios } = get()
        return portfolios.reduce((sum, p) => sum + p.total_value, 0)
      },

      getPortfolioCount: () => {
        const { portfolios } = get()
        return portfolios.length
      },

      getActivePortfolios: () => {
        const { portfolios, selectedPortfolioId } = get()
        if (selectedPortfolioId) {
          return portfolios.filter(p => p.id === selectedPortfolioId)
        }
        return portfolios
      },

      getSelectedPortfolio: () => {
        const { portfolios, selectedPortfolioId } = get()
        if (!selectedPortfolioId) return null
        return portfolios.find(p => p.id === selectedPortfolioId) || null
      },

      isAggregateView: () => {
        const { selectedPortfolioId } = get()
        return selectedPortfolioId === null
      }
    }),
    {
      name: 'portfolio-storage',
      version: 3,  // Increment version for migration
      migrate: (persistedState: any, version: number) => {
        if (version < 3) {
          // Migrate from old single-portfolio store
          return {
            portfolios: persistedState.portfolioId ? [{
              id: persistedState.portfolioId,
              account_name: persistedState.portfolioName || 'Main Portfolio',
              account_type: 'taxable',
              total_value: 0,
              position_count: 0,
              is_active: true
            }] : [],
            selectedPortfolioId: null  // Default to aggregate view
          }
        }
        return persistedState
      }
    }
  )
)
```

**Migration Notes:**
- Increment storage version from 2 → 3
- Migrate existing `portfolioId` to `portfolios` array
- Default `selectedPortfolioId` to `null` (aggregate view)

---

## Phase 2: Service Layer Updates

### Portfolio API Service

**File:** `frontend/src/services/portfolioApi.ts`

**Add New Methods:**

```typescript
// portfolioApi.ts

export interface CreatePortfolioRequest {
  account_name: string
  account_type: 'taxable' | 'ira' | 'roth_ira' | '401k' | 'sep_ira' | 'simple_ira' | 'hsa' | '529'
  description?: string
}

export interface PortfolioResponse {
  id: string
  user_id: string
  name: string
  account_name: string
  account_type: string
  description?: string
  total_value: number
  is_active: boolean
  created_at: string
}

const portfolioApi = {
  // Existing method (no changes)
  async getPortfolios(): Promise<PortfolioListItem[]> {
    const response = await apiClient.get<ApiListResponse<PortfolioListItem>>(
      API_ENDPOINTS.PORTFOLIOS.LIST,
      REQUEST_CONFIGS.STANDARD
    )
    return response.data || []
  },

  // NEW: Create portfolio
  async createPortfolio(data: CreatePortfolioRequest): Promise<PortfolioResponse> {
    const response = await apiClient.post<PortfolioResponse>(
      '/api/v1/portfolios',
      data,
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  },

  // NEW: Update portfolio
  async updatePortfolio(
    portfolioId: string,
    data: CreatePortfolioRequest
  ): Promise<PortfolioResponse> {
    const response = await apiClient.put<PortfolioResponse>(
      `/api/v1/portfolios/${portfolioId}`,
      data,
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  },

  // NEW: Delete portfolio
  async deletePortfolio(portfolioId: string): Promise<void> {
    await apiClient.delete(
      `/api/v1/portfolios/${portfolioId}`,
      REQUEST_CONFIGS.STANDARD
    )
  },

  // NEW: Get aggregate analytics
  async getAggregateAnalytics(): Promise<AggregateAnalytics> {
    const response = await apiClient.get<AggregateAnalytics>(
      '/api/v1/analytics/aggregate',
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  },

  // NEW: Get portfolio breakdown
  async getPortfolioBreakdown(): Promise<PortfolioBreakdown[]> {
    const response = await apiClient.get<PortfolioBreakdown[]>(
      '/api/v1/analytics/portfolio-breakdown',
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  }
}

export default portfolioApi
```

### Update Analytics Service

**File:** `frontend/src/services/analyticsApi.ts`

**Modify Existing Methods to Support Filtering:**

```typescript
// analyticsApi.ts

const analyticsApi = {
  // UPDATED: Support optional portfolio_id parameter
  async getPortfolioOverview(portfolioId?: string): Promise<PortfolioOverview> {
    const url = portfolioId
      ? `/api/v1/analytics/overview?portfolio_id=${portfolioId}`
      : `/api/v1/analytics/overview`  // Aggregate view

    const response = await apiClient.get<PortfolioOverview>(
      url,
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  },

  // UPDATED: Support optional portfolio_id parameter
  async getSectorExposure(portfolioId?: string): Promise<SectorExposure> {
    const url = portfolioId
      ? `/api/v1/analytics/sector-exposure?portfolio_id=${portfolioId}`
      : `/api/v1/analytics/sector-exposure`

    const response = await apiClient.get<SectorExposure>(
      url,
      REQUEST_CONFIGS.STANDARD
    )
    return response.data
  },

  // Apply same pattern to ALL analytics methods
  async getConcentration(portfolioId?: string): Promise<Concentration> { ... },
  async getVolatility(portfolioId?: string): Promise<Volatility> { ... },
  async getFactorExposures(portfolioId?: string): Promise<FactorExposures> { ... },
  // etc.
}

export default analyticsApi
```

---

## Phase 3: React Query Integration

### Custom Hooks for Multi-Portfolio

**File:** `frontend/src/hooks/usePortfolioData.ts`

**Add New Hooks:**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import portfolioApi from '@/services/portfolioApi'
import { usePortfolioStore } from '@/stores/portfolioStore'

// Hook to load all portfolios on mount
export function usePortfolios() {
  const setPortfolios = usePortfolioStore(state => state.setPortfolios)

  return useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const portfolios = await portfolioApi.getPortfolios()
      setPortfolios(portfolios)  // Update Zustand store
      return portfolios
    },
    staleTime: 5 * 60 * 1000,  // 5 minutes
    refetchOnWindowFocus: true
  })
}

// Hook for aggregate analytics
export function useAggregateAnalytics() {
  const isAggregateView = usePortfolioStore(state => state.isAggregateView())

  return useQuery({
    queryKey: ['analytics', 'aggregate'],
    queryFn: portfolioApi.getAggregateAnalytics,
    enabled: isAggregateView,  // Only fetch when in aggregate view
    staleTime: 5 * 60 * 1000
  })
}

// Hook for portfolio breakdown
export function usePortfolioBreakdown() {
  return useQuery({
    queryKey: ['portfolios', 'breakdown'],
    queryFn: portfolioApi.getPortfolioBreakdown,
    staleTime: 5 * 60 * 1000
  })
}

// Hook to create portfolio
export function useCreatePortfolio() {
  const queryClient = useQueryClient()
  const addPortfolio = usePortfolioStore(state => state.addPortfolio)

  return useMutation({
    mutationFn: portfolioApi.createPortfolio,
    onSuccess: (newPortfolio) => {
      // Update Zustand store
      addPortfolio({
        id: newPortfolio.id,
        account_name: newPortfolio.account_name,
        account_type: newPortfolio.account_type,
        total_value: newPortfolio.total_value,
        position_count: 0,
        is_active: newPortfolio.is_active
      })

      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    }
  })
}

// Hook to update portfolio
export function useUpdatePortfolio() {
  const queryClient = useQueryClient()
  const updatePortfolio = usePortfolioStore(state => state.updatePortfolio)

  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: CreatePortfolioRequest }) =>
      portfolioApi.updatePortfolio(id, data),
    onSuccess: (updatedPortfolio) => {
      updatePortfolio(updatedPortfolio.id, {
        account_name: updatedPortfolio.account_name,
        account_type: updatedPortfolio.account_type
      })

      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    }
  })
}

// Hook to delete portfolio
export function useDeletePortfolio() {
  const queryClient = useQueryClient()
  const removePortfolio = usePortfolioStore(state => state.removePortfolio)

  return useMutation({
    mutationFn: portfolioApi.deletePortfolio,
    onSuccess: (_, portfolioId) => {
      removePortfolio(portfolioId)

      // Invalidate all portfolio-related queries
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
    }
  })
}

// UPDATED: Use selectedPortfolioId from store
export function usePortfolioAnalytics() {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const isAggregateView = usePortfolioStore(state => state.isAggregateView())

  return useQuery({
    queryKey: ['analytics', 'overview', selectedPortfolioId],
    queryFn: () => analyticsApi.getPortfolioOverview(selectedPortfolioId || undefined),
    enabled: !isAggregateView,  // Only fetch when viewing single portfolio
    staleTime: 5 * 60 * 1000
  })
}
```

---

## Phase 4: UI Components

### 1. Account Summary Card

**File:** `frontend/src/components/portfolio/AccountSummaryCard.tsx`

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePortfolioBreakdown } from '@/hooks/usePortfolioData'
import { formatCurrency } from '@/lib/formatters'
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react'

export function AccountSummaryCard() {
  const { data: breakdown, isLoading } = usePortfolioBreakdown()

  if (isLoading || !breakdown) {
    return <Card className="animate-pulse"><CardContent>Loading...</CardContent></Card>
  }

  const totalValue = breakdown.reduce((sum, p) => sum + p.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wallet className="h-5 w-5" />
          Total Portfolio Value
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Total Value */}
          <div>
            <div className="text-3xl font-bold">
              {formatCurrency(totalValue)}
            </div>
            <div className="text-sm text-muted-foreground">
              Across {breakdown.length} account{breakdown.length !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Account Breakdown */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">
              Account Breakdown
            </h3>

            {breakdown.map((portfolio) => (
              <div
                key={portfolio.portfolio_id}
                className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
              >
                <div className="flex flex-col">
                  <span className="font-medium">{portfolio.account_name}</span>
                  <span className="text-xs text-muted-foreground capitalize">
                    {portfolio.account_type.replace('_', ' ')}
                  </span>
                </div>

                <div className="flex flex-col items-end">
                  <span className="font-semibold">
                    {formatCurrency(portfolio.value)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {portfolio.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### 2. Account Filter Dropdown

**File:** `frontend/src/components/portfolio/AccountFilter.tsx`

```typescript
'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { formatCurrency } from '@/lib/formatters'
import { Building2, Layers } from 'lucide-react'

export function AccountFilter() {
  const portfolios = usePortfolioStore(state => state.portfolios)
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const setSelectedPortfolio = usePortfolioStore(state => state.setSelectedPortfolio)
  const getTotalValue = usePortfolioStore(state => state.getTotalValue())

  const handleChange = (value: string) => {
    if (value === 'all') {
      setSelectedPortfolio(null)  // Aggregate view
    } else {
      setSelectedPortfolio(value)
    }
  }

  return (
    <Select
      value={selectedPortfolioId || 'all'}
      onValueChange={handleChange}
    >
      <SelectTrigger className="w-[280px]">
        <SelectValue placeholder="Select account" />
      </SelectTrigger>
      <SelectContent>
        {/* Aggregate option */}
        <SelectItem value="all">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            <div className="flex flex-col">
              <span className="font-medium">All Accounts</span>
              <span className="text-xs text-muted-foreground">
                {formatCurrency(getTotalValue)}
              </span>
            </div>
          </div>
        </SelectItem>

        {/* Individual portfolios */}
        {portfolios.map((portfolio) => (
          <SelectItem key={portfolio.id} value={portfolio.id}>
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              <div className="flex flex-col">
                <span className="font-medium">{portfolio.account_name}</span>
                <span className="text-xs text-muted-foreground">
                  {formatCurrency(portfolio.total_value)}
                </span>
              </div>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

### 3. Updated Positions Table

**File:** `frontend/src/components/portfolio/PositionsTable.tsx`

**Add Account Column:**

```typescript
'use client'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePortfolioStore } from '@/stores/portfolioStore'

interface Position {
  id: string
  symbol: string
  portfolio_id: string
  portfolio_name: string  // NEW: Account name
  quantity: number
  current_value: number
  weight_in_portfolio: number
  weight_in_total: number  // NEW: Weight across all accounts
}

export function PositionsTable({ positions }: { positions: Position[] }) {
  const isAggregateView = usePortfolioStore(state => state.isAggregateView())

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          {isAggregateView && <TableHead>Account</TableHead>}  {/* Conditional */}
          <TableHead className="text-right">Quantity</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead className="text-right">Weight</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => (
          <TableRow key={position.id}>
            <TableCell className="font-medium">{position.symbol}</TableCell>

            {isAggregateView && (
              <TableCell className="text-sm text-muted-foreground">
                {position.portfolio_name}
              </TableCell>
            )}

            <TableCell className="text-right">
              {position.quantity.toLocaleString()}
            </TableCell>

            <TableCell className="text-right">
              {formatCurrency(position.current_value)}
            </TableCell>

            <TableCell className="text-right">
              {isAggregateView
                ? `${position.weight_in_total.toFixed(2)}%`
                : `${position.weight_in_portfolio.toFixed(2)}%`
              }
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### 4. Account Management Page

**File:** `frontend/app/account-management/page.tsx` (or integrate into /settings page)

**Note:** Consider integrating into existing Settings page rather than creating separate route.



```typescript
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useCreatePortfolio, useUpdatePortfolio, useDeletePortfolio } from '@/hooks/usePortfolioData'
import { Plus, Edit, Trash2, Save, X } from 'lucide-react'

export default function AccountManagementPage() {
  const portfolios = usePortfolioStore(state => state.portfolios)
  const createMutation = useCreatePortfolio()
  const updateMutation = useUpdatePortfolio()
  const deleteMutation = useDeletePortfolio()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [formData, setFormData] = useState({
    account_name: '',
    account_type: 'taxable' as const
  })

  const handleCreate = async () => {
    await createMutation.mutateAsync(formData)
    setFormData({ account_name: '', account_type: 'taxable' })
    setShowCreate(false)
  }

  const handleUpdate = async (id: string) => {
    await updateMutation.mutateAsync({ id, data: formData })
    setEditingId(null)
  }

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this account?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Account Management</h1>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Account
        </Button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="account_name">Account Name</Label>
              <Input
                id="account_name"
                value={formData.account_name}
                onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                placeholder="Fidelity, Schwab IRA, etc."
              />
            </div>

            <div>
              <Label htmlFor="account_type">Account Type</Label>
              <Select
                value={formData.account_type}
                onValueChange={(value) => setFormData({ ...formData, account_type: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="taxable">Taxable</SelectItem>
                  <SelectItem value="ira">Traditional IRA</SelectItem>
                  <SelectItem value="roth_ira">Roth IRA</SelectItem>
                  <SelectItem value="401k">401(k)</SelectItem>
                  <SelectItem value="sep_ira">SEP IRA</SelectItem>
                  <SelectItem value="simple_ira">SIMPLE IRA</SelectItem>
                  <SelectItem value="hsa">HSA</SelectItem>
                  <SelectItem value="529">529 Plan</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleCreate}>
                <Save className="mr-2 h-4 w-4" />
                Save
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Account List */}
      <div className="grid gap-4">
        {portfolios.map((portfolio) => (
          <Card key={portfolio.id}>
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex-1">
                {editingId === portfolio.id ? (
                  <div className="space-y-4">
                    {/* Edit form similar to create form */}
                  </div>
                ) : (
                  <div>
                    <h3 className="text-lg font-semibold">{portfolio.account_name}</h3>
                    <p className="text-sm text-muted-foreground capitalize">
                      {portfolio.account_type.replace('_', ' ')}
                    </p>
                    <p className="text-sm">
                      {formatCurrency(portfolio.total_value)} • {portfolio.position_count} positions
                    </p>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingId(portfolio.id)}
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDelete(portfolio.id)}
                  disabled={portfolios.length === 1}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

---

## Phase 5: Update Existing Pages

### Dashboard Page

**File:** `frontend/app/dashboard/page.tsx`

**Add Account Components:**

```typescript
'use client'

import { AccountSummaryCard } from '@/components/portfolio/AccountSummaryCard'
import { AccountFilter } from '@/components/portfolio/AccountFilter'
import { usePortfolios } from '@/hooks/usePortfolioData'

export default function DashboardPage() {
  // Load portfolios on mount
  const { isLoading } = usePortfolios()

  if (isLoading) return <div>Loading...</div>

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Filter */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <AccountFilter />
      </div>

      {/* Account Summary */}
      <AccountSummaryCard />

      {/* Rest of dashboard content */}
      {/* ... */}
    </div>
  )
}
```

### Navigation

**File:** `frontend/src/components/navigation/NavigationHeader.tsx`

**Add Account Filter to Header:**

```typescript
import { AccountFilter } from '@/components/portfolio/AccountFilter'

export function NavigationHeader() {
  return (
    <header className="border-b">
      <div className="flex items-center justify-between p-4">
        <Logo />

        {/* Add account filter */}
        <AccountFilter />

        <UserDropdown />
      </div>
    </header>
  )
}
```

---

## Phase 6: Cache Invalidation Strategy

### Invalidate Caches on Portfolio Change

```typescript
// In AccountFilter component
const queryClient = useQueryClient()

const handleChange = (value: string) => {
  if (value === 'all') {
    setSelectedPortfolio(null)
  } else {
    setSelectedPortfolio(value)
  }

  // Invalidate all analytics queries when changing filter
  queryClient.invalidateQueries({ queryKey: ['analytics'] })
  queryClient.invalidateQueries({ queryKey: ['positions'] })
  queryClient.invalidateQueries({ queryKey: ['risk-metrics'] })
}
```

### Smart Prefetching

```typescript
// Prefetch analytics for common views
const { portfolios } = usePortfolioStore()

useEffect(() => {
  // Prefetch aggregate analytics
  queryClient.prefetchQuery({
    queryKey: ['analytics', 'aggregate'],
    queryFn: portfolioApi.getAggregateAnalytics
  })

  // Prefetch analytics for each portfolio
  portfolios.forEach(portfolio => {
    queryClient.prefetchQuery({
      queryKey: ['analytics', 'overview', portfolio.id],
      queryFn: () => analyticsApi.getPortfolioOverview(portfolio.id)
    })
  })
}, [portfolios])
```

---

## Phase 7: Testing

### Component Tests

**File:** `frontend/src/components/portfolio/__tests__/AccountSummaryCard.test.tsx`

```typescript
import { render, screen } from '@testing-library/react'
import { AccountSummaryCard } from '../AccountSummaryCard'

describe('AccountSummaryCard', () => {
  it('displays total value across all accounts', () => {
    render(<AccountSummaryCard />)
    expect(screen.getByText(/Total Portfolio Value/i)).toBeInTheDocument()
  })

  it('shows breakdown of each account', () => {
    render(<AccountSummaryCard />)
    expect(screen.getByText(/Fidelity/i)).toBeInTheDocument()
    expect(screen.getByText(/Schwab IRA/i)).toBeInTheDocument()
  })
})
```

### Integration Tests

**File:** `frontend/src/__tests__/integration/multi-portfolio-flow.test.tsx`

```typescript
import { renderWithProviders } from '@/test-utils'
import DashboardPage from '@/app/dashboard/page'

describe('Multi-Portfolio Flow', () => {
  it('loads all portfolios on mount', async () => {
    const { findByText } = renderWithProviders(<DashboardPage />)

    expect(await findByText(/All Accounts/i)).toBeInTheDocument()
  })

  it('filters to single account when selected', async () => {
    const { getByRole, findByText } = renderWithProviders(<DashboardPage />)

    // Click filter dropdown
    const filter = getByRole('combobox')
    fireEvent.click(filter)

    // Select Fidelity
    const fidelityOption = await findByText(/Fidelity/i)
    fireEvent.click(fidelityOption)

    // Verify filtered view
    expect(await findByText(/Fidelity/i)).toBeInTheDocument()
  })
})
```

---

## Phase 8: Performance Optimization

### Memoization

```typescript
import React from 'react'

export const AccountSummaryCard = React.memo(function AccountSummaryCard() {
  // Component implementation
})

export const PositionsTable = React.memo(function PositionsTable({ positions }) {
  // Component implementation
}, (prevProps, nextProps) => {
  return prevProps.positions === nextProps.positions
})
```

### Virtualization for Long Lists

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

export function PositionsTable({ positions }: { positions: Position[] }) {
  const parentRef = React.useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: positions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 10
  })

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const position = positions[virtualRow.index]
          return (
            <TableRow key={virtualRow.key} style={{ transform: `translateY(${virtualRow.start}px)` }}>
              {/* Row content */}
            </TableRow>
          )
        })}
      </div>
    </div>
  )
}
```

---

## Rollout Plan

### Week 1: State & Services
1. Update portfolioStore with migration
2. Add new service methods
3. Create custom hooks
4. Unit tests

### Week 2: UI Components
1. Build AccountSummaryCard
2. Build AccountFilter
3. Build AccountManagementPage
4. Update PositionsTable
5. Component tests

### Week 3: Integration
1. Update Dashboard page
2. Update all analytics pages
3. Add AccountFilter to navigation
4. Integration tests

### Week 4: Polish & Testing
1. Performance optimization
2. E2E testing
3. Bug fixes
4. Documentation

---

## Phase 4.5: Progressive Disclosure for Single-Portfolio Users

### Overview

**Goal:** Ensure clean UX for users with only 1 portfolio (all existing users after migration).

**Approach:** Hide multi-portfolio features until user creates 2nd portfolio.

### Implementation

#### 1. Utility Function

**File:** `frontend/src/lib/utils.ts`

```typescript
/**
 * Check if user has only a single portfolio
 * Used for progressive disclosure of multi-portfolio features
 */
export function isSinglePortfolio(portfolios: PortfolioListItem[]): boolean {
  return portfolios.length === 1
}
```

#### 2. Simplified Account Summary for n=1

**File:** `frontend/src/components/portfolio/AccountSummaryCard.tsx`

```typescript
export function AccountSummaryCard() {
  const { data: breakdown, isLoading } = usePortfolioBreakdown()

  if (isLoading || !breakdown) {
    return <LoadingCard />
  }

  const isSinglePortfolio = breakdown.length === 1

  if (isSinglePortfolio) {
    // Simplified single-portfolio view
    const portfolio = breakdown[0]

    return (
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Value</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="text-3xl font-bold">
                {formatCurrency(portfolio.value)}
              </div>
              <div className="text-sm text-muted-foreground">
                {portfolio.account_name}
              </div>
            </div>

            {/* Discovery: Add Account button */}
            <Button
              onClick={handleAddAccount}
              variant="outline"
              className="w-full"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Another Account
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Full multi-portfolio view (existing implementation)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Total Across All Accounts</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Account breakdown with percentages */}
      </CardContent>
    </Card>
  )
}
```

#### 3. Conditional Account Filter

**File:** `frontend/src/components/portfolio/AccountFilter.tsx`

```typescript
export function AccountFilter() {
  const portfolios = usePortfolioStore(state => state.portfolios)

  // Don't show filter if only 1 portfolio
  if (portfolios.length === 1) {
    return (
      <div className="text-sm text-muted-foreground">
        {portfolios[0].account_name}
      </div>
    )
  }

  // Show full dropdown for n > 1
  return (
    <Select>
      {/* Filter options */}
    </Select>
  )
}
```

#### 4. Conditional Account Column in Positions Table

**File:** `frontend/src/components/portfolio/PositionsTable.tsx`

```typescript
export function PositionsTable({ positions }: { positions: Position[] }) {
  const portfolios = usePortfolioStore(state => state.portfolios)
  const showAccountColumn = portfolios.length > 1

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          {showAccountColumn && <TableHead>Account</TableHead>}
          <TableHead className="text-right">Quantity</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead className="text-right">Weight</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => (
          <TableRow key={position.id}>
            <TableCell>{position.symbol}</TableCell>
            {showAccountColumn && (
              <TableCell className="text-sm text-muted-foreground">
                {position.portfolio_name}
              </TableCell>
            )}
            <TableCell className="text-right">
              {position.quantity.toLocaleString()}
            </TableCell>
            <TableCell className="text-right">
              {formatCurrency(position.current_value)}
            </TableCell>
            <TableCell className="text-right">
              {position.weight.toFixed(2)}%
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### User Experience Scenarios

#### Scenario 1: Existing User After Migration (1 Portfolio)

**What User Sees:**
```
Dashboard:
  ✅ Portfolio Value: $500,000 (Fidelity)
  ✅ Same metrics as before migration
  ✅ Clean, familiar UI (no clutter)
  ✅ "Add Another Account" button (discovery)

Navigation:
  ✅ Account name displayed, no dropdown

Positions Table:
  ✅ No "Account" column (all in same account)
```

**Result:** Feels exactly the same, with optional upgrade path.

#### Scenario 2: User Creates 2nd Portfolio

**User Actions:**
1. Clicks "Add Another Account" button
2. Creates "Schwab IRA" account
3. Adds positions to new account

**UI Automatically Updates:**
```
Dashboard:
  ✅ "Total Across All Accounts" heading
  ✅ Account breakdown appears (Fidelity 60%, Schwab 40%)
  ✅ Aggregate metrics displayed

Navigation:
  ✅ Account filter dropdown appears

Positions Table:
  ✅ "Account" column appears
```

**Result:** Progressive enhancement - features appear when needed.

#### Scenario 3: User Deletes Down to 1 Portfolio

**User Actions:**
1. Has 3 portfolios
2. Deletes 2 portfolios

**UI Automatically Simplifies:**
```
Dashboard:
  ✅ "Portfolio Value" heading (not "Total Across")
  ✅ Account breakdown disappears
  ✅ Shows single portfolio value

Navigation:
  ✅ Account filter disappears, shows account name

Positions Table:
  ✅ "Account" column disappears
```

**Result:** UI complexity scales down with user's needs.

### Testing Checklist

```typescript
// Test progressive disclosure
describe('Progressive Disclosure', () => {
  it('shows simplified UI with 1 portfolio', () => {
    // Setup: User with 1 portfolio
    // Assert: No account filter, no breakdown, no account column
  })

  it('expands UI when 2nd portfolio created', () => {
    // Setup: User with 1 portfolio
    // Action: Create 2nd portfolio
    // Assert: Account filter appears, breakdown appears, account column appears
  })

  it('simplifies UI when deleting to 1 portfolio', () => {
    // Setup: User with 3 portfolios
    // Action: Delete 2 portfolios
    // Assert: UI simplifies to single-portfolio view
  })

  it('handles rapid portfolio additions', () => {
    // Setup: User with 1 portfolio
    // Action: Rapidly add 5 portfolios
    // Assert: UI updates correctly, no flickering
  })
})
```

### Effort Estimate

**Additional Work:** ~4-6 hours in Phase 4

**Components to Update:**
- AccountSummaryCard (1 hour)
- AccountFilter (30 minutes)
- PositionsTable (30 minutes)
- Utility function (15 minutes)
- Testing (2-3 hours)

**Total Added Effort:** Minimal (~5% increase in Phase 4 scope)

---

## Success Criteria

- ✅ Users can view all accounts in aggregate
- ✅ Users can filter to single account
- ✅ Account breakdown displays correctly
- ✅ Positions show account column in aggregate view
- ✅ Account management page functional (CRUD)
- ✅ Performance acceptable (<100ms UI updates)
- ✅ **Single-portfolio users see clean, simple UI** ⭐ NEW
- ✅ **Progressive disclosure works (1→2→1 portfolios)** ⭐ NEW
- ✅ Backward compatible with single-portfolio users
- ✅ All tests passing

---

**Document Version:** 1.1
**Last Updated:** 2025-11-01
**Changes:** Added Phase 4.5 (Progressive Disclosure)
