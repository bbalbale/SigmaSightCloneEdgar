'use client'

import React, { useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

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
  { id: 'longs', label: 'Longs', positive: true },
  { id: 'shorts', label: 'Shorts', positive: false },
  { id: 'longOptions', label: 'Long Options', positive: true },
  { id: 'shortOptions', label: 'Short Options', positive: false },
  { id: 'private', label: 'Private', positive: true }
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
const SkeletonCard = () => {
  const { theme } = useTheme()
  return (
    <Card className="transition-colors duration-300 themed-card">
      <CardContent className="p-4 animate-pulse">
        <div className="h-3 bg-gray-200 rounded w-20 mb-2"></div>
        <div className="h-6 bg-gray-200 rounded w-16 mb-1"></div>
        <div className="h-4 bg-gray-200 rounded w-24 mb-1"></div>
        <div className="h-3 bg-gray-200 rounded w-28"></div>
      </CardContent>
    </Card>
  )
}

// Individual category card
interface CategoryCardProps {
  label: string
  exposure: number
  count: number
  percentOfEquity: number
  positive: boolean
}

const CategoryCard: React.FC<CategoryCardProps> = ({
  label,
  exposure,
  count,
  percentOfEquity,
  positive
}) => {
  const { theme } = useTheme()

  return (
    <Card className="transition-colors duration-300 themed-card">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs transition-colors duration-300 text-secondary">
            {label}
          </div>
        </div>
        <div className={`text-xl font-bold mb-1 ${
          positive ? 'text-emerald-400' : 'text-red-400'
        }`}>
          {formatCurrency(exposure)}
        </div>
        <div className="text-sm mb-1 transition-colors duration-300 text-primary">
          {formatCount(count)}
        </div>
        <div className="text-xs transition-colors duration-300 text-tertiary">
          {percentOfEquity.toFixed(1)}% of Equity
        </div>
      </CardContent>
    </Card>
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
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
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
    return null
  }

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {CATEGORIES.map((category) => {
            const data = categoryData[category.id as keyof typeof categoryData]
            return (
              <CategoryCard
                key={category.id}
                label={category.label}
                exposure={data.exposure}
                count={data.count}
                percentOfEquity={data.percentOfEquity}
                positive={category.positive}
              />
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default PositionCategoryExposureCards
