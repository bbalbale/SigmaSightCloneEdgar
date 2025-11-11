# Private Positions Page Implementation Guide

**Purpose**: Step-by-step guide to create the Private Positions page  
**Route**: `/private-positions`  
**Investment Class**: PRIVATE (alternative investments, private equity)  
**Last Updated**: September 29, 2025

---

## Overview

This page displays all private/alternative investment positions with:
- Summary metrics (total value, cost basis, P&L, return %)
- Sortable table of positions
- Custom formatting for illiquid assets
- Same UI as public positions but filtered for PRIVATE class

---

## Service Dependencies

### Services Used (Already Exist)
```typescript
import { apiClient } from '@/services/apiClient'          // HTTP client
import { portfolioResolver } from '@/services/portfolioResolver'  // Portfolio ID
import { useAuth } from '@/app/providers'                // Auth context
```

### Hook Dependency (Created for Public Positions)
```typescript
import { usePositions } from '@/hooks/usePositions'  // Reuse from public positions
```

### API Endpoint Used
```
GET /api/v1/data/positions/details?portfolio_id={id}
```

### Response Format (Filtered for PRIVATE)
```typescript
{
  positions: [
    {
      id: string
      symbol: string
      investment_class: 'PRIVATE'
      position_type: 'LONG'
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

### Step 1: Reuse Existing Hook

**No new file needed!** - The `usePositions` hook created for Public Positions already supports filtering by investment class.

```typescript
// In your container, just change the filter
const { positions, loading, error } = usePositions('PRIVATE')  // ← Changed from 'PUBLIC'
```

**Why this works**:
- ✅ Hook accepts `investmentClass` parameter
- ✅ Filters backend response by investment_class field
- ✅ Same loading/error handling
- ✅ Same data structure

---

### Step 2: Reuse Existing Components

**No new files needed!** - The components created for Public Positions work for all position types:

- ✅ `PositionSummary.tsx` - Works with any position array
- ✅ `PositionsTable.tsx` - Renders any positions

**Why this works**:
- Components are agnostic to investment class
- They work with the Position interface
- Formatting is consistent across all types

---

### Step 3: Create Container Component

**File**: `src/containers/PrivatePositionsContainer.tsx`

```typescript
// src/containers/PrivatePositionsContainer.tsx
'use client'

import { usePositions } from '@/hooks/usePositions'
import { PositionsTable } from '@/components/positions/PositionsTable'
import { PositionSummary } from '@/components/positions/PositionSummary'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function PrivatePositionsContainer() {
  // Just change the filter from 'PUBLIC' to 'PRIVATE'
  const { positions, loading, error } = usePositions('PRIVATE')
  
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
        <h1 className="text-3xl font-bold text-gray-900">Private Positions</h1>
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
          Private Positions
        </h1>
        <p className="text-gray-600 mt-1">
          {positions.length} position{positions.length !== 1 ? 's' : ''}
        </p>
      </div>
      
      {/* Reuse the same components */}
      <PositionSummary positions={positions} />
      <PositionsTable positions={positions} />
    </div>
  )
}
```

**Key Points**:
- ✅ Almost identical to PublicPositionsContainer
- ✅ Only difference: Changed 'PUBLIC' to 'PRIVATE'
- ✅ Changed title to "Private Positions"
- ✅ Reuses all components
- ✅ ~40 lines total

---

### Step 4: Create Thin Page Route

**File**: `app/private-positions/page.tsx`

```typescript
// app/private-positions/page.tsx
'use client'

import { PrivatePositionsContainer } from '@/containers/PrivatePositionsContainer'

export default function PrivatePositionsPage() {
  return <PrivatePositionsContainer />
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
- [ ] `src/containers/PrivatePositionsContainer.tsx` - Page container
- [ ] `app/private-positions/page.tsx` - Thin route wrapper

### Dependencies (Already Created)
- [x] `src/hooks/usePositions.ts` - Already exists, reuse it
- [x] `src/components/positions/PositionSummary.tsx` - Already exists, reuse it
- [x] `src/components/positions/PositionsTable.tsx` - Already exists, reuse it
- [x] `src/services/apiClient.ts` - HTTP client
- [x] `app/providers.tsx` - Auth context

---

## Code Comparison

### What's Different from Public Positions?

```typescript
// PUBLIC POSITIONS
export function PublicPositionsContainer() {
  const { positions, loading, error } = usePositions('PUBLIC')  // ← Here
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Public Positions</h1>  {/* ← Here */}
      {/* ... rest same ... */}
    </div>
  )
}

// PRIVATE POSITIONS
export function PrivatePositionsContainer() {
  const { positions, loading, error } = usePositions('PRIVATE')  // ← Changed
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Private Positions</h1>  {/* ← Changed */}
      {/* ... rest same ... */}
    </div>
  )
}
```

**Only 2 changes**:
1. Hook parameter: `'PUBLIC'` → `'PRIVATE'`
2. Page title: "Public Positions" → "Private Positions"

---

## Testing Steps

1. **Create container** - Copy from PublicPositionsContainer
2. **Change filter** - Update hook parameter to 'PRIVATE'
3. **Change title** - Update heading text
4. **Create page** - Thin wrapper in `/app`
5. **Test navigation** - Go to `/private-positions`
6. **Verify filtering** - Check only PRIVATE positions show
7. **Test components** - Verify table and summary work
8. **Test sorting** - Click table headers
9. **Test loading** - Check skeleton display
10. **Test errors** - Handle API failures gracefully

---

## Common Issues & Solutions

### Issue 1: No private positions show
**Symptom**: Empty state displays even when data exists  
**Cause**: Database may not have positions with investment_class='PRIVATE'  
**Solution**: 
- Check database: `SELECT * FROM positions WHERE investment_class = 'PRIVATE'`
- Seed data if needed
- Verify backend returns investment_class field

### Issue 2: Same data as public positions
**Symptom**: Private page shows same positions as public  
**Cause**: Filter not applied correctly  
**Solution**: 
- Verify hook parameter is 'PRIVATE' (case-sensitive)
- Check backend response structure
- Console log filtered positions

### Issue 3: Components not found
**Symptom**: Import errors for PositionsTable or PositionSummary  
**Cause**: Public positions page not completed yet  
**Solution**: Complete public positions implementation first

---

## Position Type Context

### Private Investment Examples
- Private equity funds
- Hedge funds
- Venture capital investments
- Real estate (non-REIT)
- Alternative assets
- Collectibles with tracked valuations

### Database Schema
```sql
-- Positions table
CREATE TABLE positions (
  id UUID PRIMARY KEY,
  portfolio_id UUID REFERENCES portfolios(id),
  symbol VARCHAR(20),
  investment_class VARCHAR(20),  -- 'PUBLIC', 'PRIVATE', 'OPTIONS'
  position_type VARCHAR(10),     -- Usually 'LONG' for private
  quantity DECIMAL(18, 8),
  current_price DECIMAL(18, 2),
  market_value DECIMAL(18, 2),
  cost_basis DECIMAL(18, 2),
  -- ...
)
```

### Backend Filtering
The backend API already handles filtering by investment_class:
```python
# Backend code (reference only)
positions = db.query(Position).filter(
    Position.portfolio_id == portfolio_id,
    Position.investment_class == 'PRIVATE'  # ← Filtered here
).all()
```

---

## Future Enhancements

### Optional: Private-Specific Features

If you want to add features specific to private investments later:

1. **Illiquidity Indicators**
```typescript
// Add to PositionsTable
<TableCell>
  {position.investment_class === 'PRIVATE' && (
    <Badge variant="secondary">Illiquid</Badge>
  )}
</TableCell>
```

2. **Valuation Dates**
```typescript
// Show last valuation date for private positions
{position.price_updated_at && (
  <p className="text-xs text-gray-500">
    Last valued: {formatDate(position.price_updated_at)}
  </p>
)}
```

3. **Custom Metrics**
```typescript
// Add IRR, multiple, etc. for private equity
interface PrivatePosition extends Position {
  irr?: number
  multiple?: number
  vintage_year?: number
}
```

**For now**: Keep it simple and reuse existing components!

---

## Advantages of This Approach

### Code Reuse Benefits
1. **One hook** serves all investment classes
2. **Same components** for consistent UI
3. **Consistent logic** for calculations
4. **Easier maintenance** - Fix once, fixes everywhere
5. **Less code** - Only 2 new files vs 5+ if duplicated

### Scalability
- Easy to add OPTIONS positions page later
- Can add filters/groupings without duplicating code
- Components can be enhanced without breaking pages

---

## Next Steps

After implementing Private Positions:
1. Test both Public and Private pages together
2. Verify filtering works correctly
3. Check navigation between pages
4. Ensure no data leakage between investment classes
5. Move on to Organize page (strategies and tags)

---

## Summary

**Pattern**: Reuse hook and components, new container and page  
**Services Used**: apiClient (indirect via usePositions hook)  
**New Files**: 2 total (1 container, 1 page)  
**Reused**: Hook + 2 components from Public Positions  
**Key Advantage**: Minimal code duplication, maximum reusability
