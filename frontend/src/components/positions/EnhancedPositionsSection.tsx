// src/components/positions/EnhancedPositionsSection.tsx
'use client'

import { useState, useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PositionList } from '@/components/common/PositionList'
import { ResearchPositionCard } from '@/components/positions/ResearchPositionCard'
import { useTheme } from '@/contexts/ThemeContext'
import type { EnhancedPosition } from '@/services/positionResearchService'

interface EnhancedPositionsSectionProps {
  positions: EnhancedPosition[]
  title: string
  aggregateReturnEOY: number
  aggregateReturnNextYear: number
  onTargetPriceUpdate?: () => Promise<void>
}

export function EnhancedPositionsSection({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate
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
    <div className="space-y-4">
      {/* Section Header */}
      <div className={`rounded-lg border p-4 transition-all duration-300 ${
        theme === 'dark'
          ? 'bg-slate-800/30 border-slate-700/50'
          : 'bg-white border-gray-200'
      }`}>
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
          <div className="flex gap-6">
            <div className="text-right">
              <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
              }`}>
                Expected Return EOY
              </div>
              <div className={`text-xl font-bold tabular-nums ${
                aggregateReturnEOY >= 0 ? 'text-emerald-500' : 'text-rose-500'
              }`}>
                {aggregateReturnEOY >= 0 ? '+' : ''}{aggregateReturnEOY.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
              }`}>
                Expected Return Next Year
              </div>
              <div className={`text-xl font-bold tabular-nums ${
                aggregateReturnNextYear >= 0 ? 'text-emerald-500' : 'text-rose-500'
              }`}>
                {aggregateReturnNextYear >= 0 ? '+' : ''}{aggregateReturnNextYear.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>

        {/* Filter and Sort Controls */}
        <div className="flex gap-3 flex-wrap">
          {/* Filter By */}
          <Select value={filterBy} onValueChange={(v: any) => { setFilterBy(v); setFilterValue('all') }}>
            <SelectTrigger className={`w-[180px] transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-900/50 border-slate-600 hover:border-slate-500'
                : 'bg-gray-50 border-gray-300 hover:border-gray-400'
            }`}>
              <SelectValue placeholder="Filter by..." />
            </SelectTrigger>
            <SelectContent className={`${
              theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
            }`}>
              <SelectItem value="all">All Positions</SelectItem>
              <SelectItem value="tag">Filter by Tag</SelectItem>
              <SelectItem value="sector">Filter by Sector</SelectItem>
              <SelectItem value="industry">Filter by Industry</SelectItem>
            </SelectContent>
          </Select>

          {/* Filter Value */}
          {filterBy !== 'all' && filterOptions.length > 0 && (
            <Select value={filterValue} onValueChange={setFilterValue}>
              <SelectTrigger className={`w-[200px] transition-colors duration-300 ${
                theme === 'dark'
                  ? 'bg-slate-900/50 border-slate-600 hover:border-slate-500'
                  : 'bg-gray-50 border-gray-300 hover:border-gray-400'
              }`}>
                <SelectValue placeholder={`Select ${filterBy}...`} />
              </SelectTrigger>
              <SelectContent className={`${
                theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
              }`}>
                <SelectItem value="all">All {filterBy}s</SelectItem>
                {filterOptions.map(option => (
                  <SelectItem key={option} value={option}>{option}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Sort By */}
          <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
            <SelectTrigger className={`w-[180px] transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-900/50 border-slate-600 hover:border-slate-500'
                : 'bg-gray-50 border-gray-300 hover:border-gray-400'
            }`}>
              <SelectValue placeholder="Sort by..." />
            </SelectTrigger>
            <SelectContent className={`${
              theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
            }`}>
              <SelectItem value="percent_of_equity">% of Portfolio</SelectItem>
              <SelectItem value="symbol">Symbol (A-Z)</SelectItem>
              <SelectItem value="target_return_eoy">Return EOY</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort Order */}
          <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
            <SelectTrigger className={`w-[140px] transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-900/50 border-slate-600 hover:border-slate-500'
                : 'bg-gray-50 border-gray-300 hover:border-gray-400'
            }`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className={`${
              theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
            }`}>
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
          />
        )}
        emptyMessage={`No ${title.toLowerCase()} found`}
      />
    </div>
  )
}
