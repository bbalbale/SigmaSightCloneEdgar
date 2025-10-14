'use client'

import React, { useMemo } from 'react'

interface Position {
  id?: string
  symbol: string
  type?: string
  investment_class?: string
  marketValue: number
  tags?: Array<{ id: string; name: string }>
}

interface PositionCategoryExposureCardsProps {
  positions: Position[]
  selectedTagId: string | null
  equityBalance: number
  loading?: boolean
}

// Category definitions - Using standard borders for consistency
const CATEGORIES = [
  { id: 'longs', label: 'Longs' },
  { id: 'shorts', label: 'Shorts' },
  { id: 'longOptions', label: 'Long Options' },
  { id: 'shortOptions', label: 'Short Options' },
  { id: 'private', label: 'Private' }
]

// Helper function to format currency
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

// Helper function to format count
const formatCount = (count: number) => {
  return count === 1 ? '1 position' : `${count} positions`
}

// Skeleton card for loading state
const SkeletonCard = () => (
  <div className="bg-white rounded-lg border border-gray-200 p-2 animate-pulse">
    <div className="h-3 bg-gray-200 rounded w-20 mb-1"></div>
    <div className="h-5 bg-gray-200 rounded w-16 mb-1"></div>
    <div className="h-3 bg-gray-200 rounded w-24"></div>
  </div>
)

// Individual category card
interface CategoryCardProps {
  label: string
  exposure: number
  count: number
  percentOfEquity: number
}

const CategoryCard: React.FC<CategoryCardProps> = ({
  label,
  exposure,
  count,
  percentOfEquity
}) => {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2 transition-all duration-200 hover:shadow-md cursor-pointer">
      <div className="text-xs font-medium text-gray-600 mb-0.5">
        {label}
      </div>
      <div className="text-base font-bold mb-0.5">
        {formatCurrency(exposure)}
      </div>
      <div className="text-xs text-gray-500 mb-0.5">
        {formatCount(count)}
      </div>
      <div className="text-xs font-medium text-gray-700">
        {percentOfEquity.toFixed(1)}% of Equity
      </div>
    </div>
  )
}

export const PositionCategoryExposureCards: React.FC<PositionCategoryExposureCardsProps> = ({
  positions,
  selectedTagId,
  equityBalance,
  loading = false
}) => {
  // Calculate exposures by category with tag filtering
  const categoryData = useMemo(() => {
    // Filter positions by selected tag
    const filteredPositions = selectedTagId
      ? positions.filter(p => p.tags?.some(tag => tag.id === selectedTagId))
      : positions

    // Categorize positions
    const longs = filteredPositions.filter(p => p.type === 'LONG')
    const shorts = filteredPositions.filter(p => p.type === 'SHORT')
    const longOptions = filteredPositions.filter(p => p.type === 'LC' || p.type === 'LP')
    const shortOptions = filteredPositions.filter(p => p.type === 'SC' || p.type === 'SP')
    const privatePos = filteredPositions.filter(p => p.investment_class === 'PRIVATE')

    // Calculate exposures
    const longsExposure = longs.reduce((sum, p) => sum + (p.marketValue || 0), 0)
    const shortsExposure = shorts.reduce((sum, p) => sum + (p.marketValue || 0), 0)
    const longOptionsExposure = longOptions.reduce((sum, p) => sum + (p.marketValue || 0), 0)
    const shortOptionsExposure = shortOptions.reduce((sum, p) => sum + (p.marketValue || 0), 0)
    const privateExposure = privatePos.reduce((sum, p) => sum + (p.marketValue || 0), 0)

    // Calculate percentage of equity for each category
    return {
      longs: {
        exposure: longsExposure,
        count: longs.length,
        percentOfEquity: equityBalance > 0 ? (longsExposure / equityBalance) * 100 : 0
      },
      shorts: {
        exposure: shortsExposure,
        count: shorts.length,
        percentOfEquity: equityBalance > 0 ? (shortsExposure / equityBalance) * 100 : 0
      },
      longOptions: {
        exposure: longOptionsExposure,
        count: longOptions.length,
        percentOfEquity: equityBalance > 0 ? (longOptionsExposure / equityBalance) * 100 : 0
      },
      shortOptions: {
        exposure: shortOptionsExposure,
        count: shortOptions.length,
        percentOfEquity: equityBalance > 0 ? (shortOptionsExposure / equityBalance) * 100 : 0
      },
      private: {
        exposure: privateExposure,
        count: privatePos.length,
        percentOfEquity: equityBalance > 0 ? (privateExposure / equityBalance) * 100 : 0
      }
    }
  }, [positions, selectedTagId, equityBalance])

  // Handle loading state
  if (loading) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-600">Position Category Exposures</h3>
            <span className="text-xs text-gray-500">
              {selectedTagId ? 'Filtered by tag' : 'All positions'}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {CATEGORIES.map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  // Handle no positions
  if (!positions || positions.length === 0) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm">
              No positions available
            </p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-600">Position Category Exposures</h3>
          <span className="text-xs text-gray-500">
            {selectedTagId ? 'Filtered by selected tag' : 'All positions'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {CATEGORIES.map((category) => {
            const data = categoryData[category.id as keyof typeof categoryData]
            return (
              <CategoryCard
                key={category.id}
                label={category.label}
                exposure={data.exposure}
                count={data.count}
                percentOfEquity={data.percentOfEquity}
              />
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default PositionCategoryExposureCards
