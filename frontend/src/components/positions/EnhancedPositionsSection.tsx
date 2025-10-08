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
