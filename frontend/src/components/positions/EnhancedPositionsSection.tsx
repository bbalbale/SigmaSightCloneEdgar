// src/components/positions/EnhancedPositionsSection.tsx
'use client'

import { useState, useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PositionList } from '@/components/common/PositionList'
import { ResearchPositionCard } from '@/components/positions/ResearchPositionCard'
import type { EnhancedPosition } from '@/services/positionResearchService'
import type { TargetPriceUpdate } from '@/services/targetPriceUpdateService'

interface EnhancedPositionsSectionProps {
  positions: EnhancedPosition[]
  title: string
  aggregateReturnEOY: number
  aggregateReturnNextYear: number
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
  onPositionClick?: (position: EnhancedPosition) => void
}

export function EnhancedPositionsSection({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate,
  onPositionClick
}: EnhancedPositionsSectionProps) {
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
      return Array.from(new Set(positions.map(p => p.sector).filter((s): s is string => Boolean(s)))).sort()
    }
    if (filterBy === 'industry') {
      return Array.from(new Set(positions.map(p => p.industry).filter((i): i is string => Boolean(i)))).sort()
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
    const sorted = [...filteredPositions].sort((a, b) => {
      const aValue = a[sortBy] as any
      const bValue = b[sortBy] as any

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
      }

      return sortOrder === 'asc'
        ? String(aValue || '').localeCompare(String(bValue || ''))
        : String(bValue || '').localeCompare(String(aValue || ''))
    })

    // DEBUG: Log filtering and sorting results
    console.log(`🔍 EnhancedPositionsSection [${title}]:`, {
      inputPositions: positions.length,
      afterFiltering: filteredPositions.length,
      afterSorting: sorted.length,
      filterBy,
      filterValue,
      sortBy,
      sortOrder,
      samplePosition: positions[0] && {
        symbol: positions[0].symbol,
        percent_of_equity: positions[0].percent_of_equity,
        target_return_eoy: positions[0].target_return_eoy,
        investment_class: positions[0].investment_class
      },
      filteredOutCount: positions.length - filteredPositions.length
    })

    return sorted
  }, [filteredPositions, sortBy, sortOrder, positions, title, filterBy, filterValue])

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="rounded-lg border p-4 transition-all duration-300" style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="transition-colors duration-300" style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 600,
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}>
              {title}
            </h3>
            <Badge variant="secondary" className="transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--color-accent)'
            }}>
              {filteredPositions.length}
            </Badge>
          </div>

          {/* Aggregate Returns */}
          <div className="flex gap-6">
            <div className="text-right">
              <div className="mb-1 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}>
                Expected Return EOY
              </div>
              <div className="tabular-nums" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: aggregateReturnEOY >= 0 ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {aggregateReturnEOY >= 0 ? '+' : ''}{aggregateReturnEOY.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className="mb-1 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}>
                Expected Return Next Year
              </div>
              <div className="tabular-nums" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: aggregateReturnNextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {aggregateReturnNextYear >= 0 ? '+' : ''}{aggregateReturnNextYear.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>

        {/* Filter and Sort Controls */}
        <div className="flex gap-3 flex-wrap">
          {/* Filter By */}
          <Select value={filterBy} onValueChange={(v: any) => { setFilterBy(v); setFilterValue('all') }}>
            <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue placeholder="Filter by..." />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="all">All Positions</SelectItem>
              <SelectItem value="tag">Filter by Tag</SelectItem>
              <SelectItem value="sector">Filter by Sector</SelectItem>
              <SelectItem value="industry">Filter by Industry</SelectItem>
            </SelectContent>
          </Select>

          {/* Filter Value */}
          {filterBy !== 'all' && filterOptions.length > 0 && (
            <Select value={filterValue} onValueChange={setFilterValue}>
              <SelectTrigger className="w-[200px] transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-primary)',
                borderColor: 'var(--border-primary)'
              }}>
                <SelectValue placeholder={`Select ${filterBy}...`} />
              </SelectTrigger>
              <SelectContent className="themed-card">
                <SelectItem value="all">All {filterBy}s</SelectItem>
                {filterOptions.map(option => (
                  <SelectItem key={option} value={option}>{option}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Sort By */}
          <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
            <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue placeholder="Sort by..." />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="percent_of_equity">% of Portfolio</SelectItem>
              <SelectItem value="symbol">Symbol (A-Z)</SelectItem>
              <SelectItem value="target_return_eoy">Return EOY</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort Order */}
          <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
            <SelectTrigger className="w-[140px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="desc">High to Low</SelectItem>
              <SelectItem value="asc">Low to High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Position Cards */}
      <PositionList
        items={sortedPositions}
        renderItem={(position) => (
          <ResearchPositionCard
            key={position.id}
            position={position}
            onTargetPriceUpdate={onTargetPriceUpdate}
            onClick={() => onPositionClick?.(position)}
          />
        )}
        emptyMessage={`No ${title.toLowerCase()} found`}
      />
    </div>
  )
}
