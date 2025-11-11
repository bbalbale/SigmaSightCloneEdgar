# Organize Page Implementation Guide

**Purpose**: Step-by-step guide to create the Organize page  
**Route**: `/organize`  
**Features**: Strategy management and tag organization  
**Last Updated**: September 29, 2025

---

## Overview

This page provides portfolio organization tools:
- **Strategies**: Group positions into trading strategies
- **Tags**: Categorize strategies with custom tags
- Two-column layout for side-by-side management
- Real-time updates when changes are made

---

## Service Dependencies

### Services Used (Already Exist)
```typescript
import strategiesApi from '@/services/strategiesApi'  // Strategy CRUD operations
import tagsApi from '@/services/tagsApi'              // Tag CRUD operations
import { useAuth } from '@/app/providers'             // Auth context
```

### API Endpoints Used

#### Strategy Endpoints
```
GET  /strategies/                           # List all strategies
GET  /data/portfolios/{id}/strategies       # Portfolio strategies with details
POST /strategies/                           # Create strategy
PATCH /strategies/{id}                      # Update strategy
DELETE /strategies/{id}                     # Delete strategy
POST /strategies/{id}/positions             # Add positions to strategy
DELETE /strategies/{id}/positions           # Remove positions
POST /strategies/{id}/tags                  # Assign tags
DELETE /strategies/{id}/tags                # Remove tags
```

#### Tag Endpoints
```
GET  /tags/                                 # List user tags
POST /tags/                                 # Create tag
PATCH /tags/{id}                            # Update tag
DELETE /tags/{id}                           # Archive tag
POST /tags/defaults                         # Create default tags
POST /tags/reorder                          # Reorder tags
```

---

## Implementation Steps

### Step 1: Create Custom Hooks

#### Hook A: Strategies Hook

**File**: `src/hooks/useStrategies.ts`

```typescript
// src/hooks/useStrategies.ts
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/app/providers'
import strategiesApi from '@/services/strategiesApi'

export function useStrategies() {
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { portfolioId } = useAuth()
  
  useEffect(() => {
    if (portfolioId) {
      fetchStrategies()
    }
  }, [portfolioId])
  
  const fetchStrategies = async () => {
    if (!portfolioId) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Use existing strategiesApi service
      const data = await strategiesApi.listByPortfolio({ 
        portfolioId, 
        includeTags: true,
        includePositions: true 
      })
      setStrategies(data.strategies || [])
    } catch (err) {
      console.error('Failed to fetch strategies:', err)
      setError('Failed to load strategies')
    } finally {
      setLoading(false)
    }
  }
  
  return {
    strategies,
    loading,
    error,
    refetch: fetchStrategies
  }
}
```

**Key Points**:
- ✅ Uses existing `strategiesApi` service
- ✅ Fetches strategies with tags and positions
- ✅ Provides refetch for updates
- ✅ Portfolio-scoped via useAuth

#### Hook B: Tags Hook

**File**: `src/hooks/useTags.ts`

```typescript
// src/hooks/useTags.ts
'use client'

import { useState, useEffect } from 'react'
import tagsApi from '@/services/tagsApi'

export function useTags() {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    fetchTags()
  }, [])
  
  const fetchTags = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Use existing tagsApi service
      const data = await tagsApi.list(false)  // false = exclude archived
      setTags(data || [])
    } catch (err) {
      console.error('Failed to fetch tags:', err)
      setError('Failed to load tags')
    } finally {
      setLoading(false)
    }
  }
  
  return {
    tags,
    loading,
    error,
    refetch: fetchTags
  }
}
```

**Key Points**:
- ✅ Uses existing `tagsApi` service
- ✅ User-scoped (no portfolio filter needed)
- ✅ Excludes archived tags
- ✅ Provides refetch for updates

---

### Step 2: Create UI Components

#### Component A: Strategy List

**File**: `src/components/strategies/StrategyList.tsx`

```typescript
// src/components/strategies/StrategyList.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Edit, Trash } from 'lucide-react'
import strategiesApi from '@/services/strategiesApi'
import { useAuth } from '@/app/providers'

interface Strategy {
  id: string
  name: string
  description: string
  strategy_type: string
  positions?: any[]
  tags?: any[]
  net_exposure?: number
  total_cost_basis?: number
}

interface StrategyListProps {
  strategies: Strategy[]
  tags: any[]
  onUpdate: () => void
}

export function StrategyList({ strategies, tags, onUpdate }: StrategyListProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)
  const { portfolioId } = useAuth()
  
  const handleDelete = async (strategyId: string) => {
    if (!confirm('Delete this strategy?')) return
    
    try {
      await strategiesApi.delete(strategyId)
      onUpdate()  // Refresh strategies
    } catch (error) {
      console.error('Failed to delete strategy:', error)
      alert('Failed to delete strategy')
    }
  }
  
  const handleCreateStrategy = () => {
    // Open create dialog (implementation depends on UI library)
    // For now, just placeholder
    console.log('Create strategy clicked')
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Strategies</CardTitle>
          <Button onClick={handleCreateStrategy} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            New Strategy
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {strategies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No strategies yet. Create one to organize your positions.
          </div>
        ) : (
          <div className="space-y-3">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{strategy.name}</h3>
                      <Badge variant="outline" className="text-xs">
                        {strategy.strategy_type}
                      </Badge>
                    </div>
                    
                    {strategy.description && (
                      <p className="text-sm text-gray-600 mt-1">
                        {strategy.description}
                      </p>
                    )}
                    
                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <span className="text-gray-500">
                        {strategy.positions?.length || 0} positions
                      </span>
                      {strategy.net_exposure && (
                        <span className="text-gray-500">
                          Net: ${strategy.net_exposure.toLocaleString()}
                        </span>
                      )}
                    </div>
                    
                    {strategy.tags && strategy.tags.length > 0 && (
                      <div className="flex gap-1 mt-2">
                        {strategy.tags.map((tag: any) => (
                          <Badge
                            key={tag.id}
                            variant="secondary"
                            className="text-xs"
                            style={{ backgroundColor: tag.color }}
                          >
                            {tag.name}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedStrategy(strategy)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(strategy.id)}
                    >
                      <Trash className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

**Key Points**:
- ✅ Uses existing `strategiesApi` service for delete
- ✅ Displays strategy details including positions and tags
- ✅ Color-coded tag badges
- ✅ Edit/Delete actions
- ✅ Empty state handling

#### Component B: Tag List

**File**: `src/components/tags/TagList.tsx`

```typescript
// src/components/tags/TagList.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Plus, Edit, Trash, Check, X } from 'lucide-react'
import tagsApi from '@/services/tagsApi'

interface Tag {
  id: string
  name: string
  color: string
  description?: string
  usage_count?: number
}

interface TagListProps {
  tags: Tag[]
  onUpdate: () => void
}

export function TagList({ tags, onUpdate }: TagListProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState('#3B82F6')
  
  const handleCreate = async () => {
    if (!newTagName.trim()) return
    
    try {
      await tagsApi.create({
        name: newTagName.trim(),
        color: newTagColor,
        description: ''
      })
      setNewTagName('')
      setNewTagColor('#3B82F6')
      setIsCreating(false)
      onUpdate()  // Refresh tags
    } catch (error) {
      console.error('Failed to create tag:', error)
      alert('Failed to create tag')
    }
  }
  
  const handleDelete = async (tagId: string) => {
    if (!confirm('Archive this tag?')) return
    
    try {
      await tagsApi.delete(tagId)
      onUpdate()  // Refresh tags
    } catch (error) {
      console.error('Failed to delete tag:', error)
      alert('Failed to delete tag')
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Tags</CardTitle>
          {!isCreating && (
            <Button onClick={() => setIsCreating(true)} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Tag
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isCreating && (
          <div className="border rounded-lg p-4 mb-4 space-y-3">
            <Input
              placeholder="Tag name"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              autoFocus
            />
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={newTagColor}
                onChange={(e) => setNewTagColor(e.target.value)}
                className="h-10 w-20 rounded border cursor-pointer"
              />
              <div className="flex gap-2 ml-auto">
                <Button onClick={handleCreate} size="sm">
                  <Check className="h-4 w-4" />
                </Button>
                <Button
                  onClick={() => {
                    setIsCreating(false)
                    setNewTagName('')
                  }}
                  variant="ghost"
                  size="sm"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
        
        {tags.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No tags yet. Create one to categorize your strategies.
          </div>
        ) : (
          <div className="space-y-2">
            {tags.map((tag) => (
              <div
                key={tag.id}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: tag.color }}
                  />
                  <div>
                    <p className="font-medium">{tag.name}</p>
                    {tag.usage_count !== undefined && (
                      <p className="text-xs text-gray-500">
                        Used in {tag.usage_count} strateg{tag.usage_count === 1 ? 'y' : 'ies'}
                      </p>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(tag.id)}
                >
                  <Trash className="h-4 w-4 text-red-600" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

**Key Points**:
- ✅ Uses existing `tagsApi` service
- ✅ Inline creation form
- ✅ Color picker for tag colors
- ✅ Usage count display
- ✅ Archive/delete functionality

---

### Step 3: Create Container Component

**File**: `src/containers/OrganizeContainer.tsx`

```typescript
// src/containers/OrganizeContainer.tsx
'use client'

import { useStrategies } from '@/hooks/useStrategies'
import { useTags } from '@/hooks/useTags'
import { StrategyList } from '@/components/strategies/StrategyList'
import { TagList } from '@/components/tags/TagList'
import { Skeleton } from '@/components/ui/skeleton'

export function OrganizeContainer() {
  const { strategies, loading: strategiesLoading, refetch: refetchStrategies } = useStrategies()
  const { tags, loading: tagsLoading, refetch: refetchTags } = useTags()
  
  // Refresh both when either updates
  const handleUpdate = () => {
    refetchStrategies()
    refetchTags()
  }
  
  if (strategiesLoading || tagsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid lg:grid-cols-2 gap-6">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">
        Portfolio Organization
      </h1>
      
      <div className="grid lg:grid-cols-2 gap-6">
        <StrategyList 
          strategies={strategies} 
          tags={tags}
          onUpdate={handleUpdate}
        />
        
        <TagList 
          tags={tags}
          onUpdate={handleUpdate}
        />
      </div>
    </div>
  )
}
```

**Key Points**:
- ✅ Uses both custom hooks
- ✅ Two-column layout (strategies | tags)
- ✅ Shared update handler to refresh both
- ✅ Loading skeletons
- ✅ ~40 lines total

---

### Step 4: Create Thin Page Route

**File**: `app/organize/page.tsx`

```typescript
// app/organize/page.tsx
'use client'

import { OrganizeContainer } from '@/containers/OrganizeContainer'

export default function OrganizePage() {
  return <OrganizeContainer />
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
- [ ] `src/hooks/useStrategies.ts` - Strategy data hook
- [ ] `src/hooks/useTags.ts` - Tag data hook
- [ ] `src/components/strategies/StrategyList.tsx` - Strategy display
- [ ] `src/components/tags/TagList.tsx` - Tag management
- [ ] `src/containers/OrganizeContainer.tsx` - Page container
- [ ] `app/organize/page.tsx` - Thin route wrapper

### Dependencies (Already Exist)
- [x] `src/services/strategiesApi.ts` - Strategy API service
- [x] `src/services/tagsApi.ts` - Tag API service
- [x] `app/providers.tsx` - Auth context
- [x] `src/components/ui/*` - ShadCN UI components

---

## strategiesApi Service Reference

### Available Methods
```typescript
// Already implemented in src/services/strategiesApi.ts
strategiesApi.create(data)                  // Create strategy
strategiesApi.listByPortfolio(params)       // List with filters
strategiesApi.get(id)                       // Get single strategy
strategiesApi.update(id, data)              // Update strategy
strategiesApi.delete(id)                    // Delete strategy
strategiesApi.addPositions(id, positionIds) // Add positions
strategiesApi.removePositions(id, positionIds) // Remove positions
strategiesApi.assignTags(id, tagIds)        // Assign tags
strategiesApi.removeTags(id, tagIds)        // Remove tags
```

## tagsApi Service Reference

### Available Methods
```typescript
// Already implemented in src/services/tagsApi.ts
tagsApi.create(data)                   // Create tag
tagsApi.list(includeArchived)          // List tags
tagsApi.get(id)                        // Get single tag
tagsApi.update(id, data)               // Update tag
tagsApi.delete(id)                     // Archive tag
tagsApi.restore(id)                    // Restore archived tag
tagsApi.createDefaults()               // Create default tags
tagsApi.reorder(tagIds)                // Reorder display
tagsApi.getStrategies(id)              // Get strategies using tag
```

---

## Testing Steps

1. **Create files** in order: Hooks → Components → Container → Page
2. **Test strategy hook** - Verify strategies load
3. **Test tag hook** - Verify tags load
4. **Test strategy component** - Check display and delete
5. **Test tag component** - Check create and delete
6. **Test container** - Verify two-column layout
7. **Test page** - Navigate to `/organize`
8. **Test updates** - Create tag, verify both lists refresh
9. **Test delete** - Delete strategy, verify refresh
10. **Test empty states** - Check when no strategies/tags exist

---

## Common Issues & Solutions

### Issue 1: Strategies not loading
**Symptom**: Empty strategies list  
**Cause**: portfolioId null or API error  
**Solution**: Check auth context, verify backend is running

### Issue 2: Tags not refreshing after create
**Symptom**: New tag doesn't appear  
**Cause**: onUpdate callback not called  
**Solution**: Ensure onUpdate prop is passed and calls refetch

### Issue 3: Service methods not found
**Symptom**: Import errors for strategiesApi or tagsApi  
**Cause**: Services not exported correctly  
**Solution**: Check service files have default exports

---

## Future Enhancements

### Optional Features to Add Later

1. **Drag & Drop**
   - Drag positions into strategies
   - Reorder strategies

2. **Bulk Operations**
   - Select multiple strategies
   - Batch tag assignment

3. **Strategy Templates**
   - Predefined strategy types
   - Quick create from template

4. **Advanced Filters**
   - Filter strategies by tag
   - Search by name/description

5. **Strategy Analytics**
   - Performance metrics per strategy
   - Comparison charts

---

## Next Steps

After implementing Organize page:
1. Test strategy creation and management
2. Test tag creation and assignment
3. Verify data refresh works
4. Check two-column responsive layout
5. Move on to AI Chat page

---

## Summary

**Pattern**: Two hooks → Two components → Container → Page  
**Services Used**: strategiesApi, tagsApi  
**New Files**: 6 total (2 hooks, 2 components, 1 container, 1 page)  
**Layout**: Two-column grid (strategies | tags)  
**Key Feature**: Real-time updates when changes are made
