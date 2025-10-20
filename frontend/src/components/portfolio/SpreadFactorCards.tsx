'use client'

import React from 'react'
import type { SpreadFactor } from '@/services/spreadFactorsApi'
import {
  formatBeta,
  getRiskLevelColor,
  getMagnitudeBadgeColor
} from '@/services/spreadFactorsApi'

interface SpreadFactorCardsProps {
  factors: SpreadFactor[] | null
  loading?: boolean
  error?: any
  calculationDate?: string | null
}

// Spread factor order (matches backend display_order)
const SPREAD_FACTOR_ORDER = [
  'Growth-Value Spread',
  'Momentum Spread',
  'Size Spread',
  'Quality Spread'
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

// Skeleton card for loading state
const SkeletonCard = () => (
  <div className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
    <div className="h-4 bg-gray-200 rounded w-32 mb-3"></div>
    <div className="h-6 bg-gray-200 rounded w-20 mb-2"></div>
    <div className="flex gap-2 mb-3">
      <div className="h-5 bg-gray-200 rounded w-16"></div>
      <div className="h-5 bg-gray-200 rounded w-20"></div>
    </div>
    <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
    <div className="h-3 bg-gray-200 rounded w-5/6"></div>
  </div>
)

// Individual spread factor card
const SpreadFactorCard = ({ factor }: { factor: SpreadFactor }) => {
  const riskColorClass = getRiskLevelColor(factor.risk_level)
  const magnitudeColorClass = getMagnitudeBadgeColor(factor.magnitude)

  // Get short factor name for display
  const getShortName = (name: string) => {
    return name.replace(' Spread', '')
  }

  return (
    <div className={`rounded-lg border p-4 transition-all duration-200 hover:shadow-lg cursor-pointer bg-white hover:scale-[1.02]`}>
      {/* Header with factor name */}
      <div className="text-sm font-semibold text-gray-700 mb-2">
        {getShortName(factor.name)}
      </div>

      {/* Beta value - large and prominent */}
      <div className="text-2xl font-bold text-gray-900 mb-3">
        {formatBeta(factor.beta)}
      </div>

      {/* Badges: Direction and Magnitude */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${riskColorClass}`}>
          {factor.direction}
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${magnitudeColorClass}`}>
          {factor.magnitude}
        </span>
      </div>

      {/* Dollar exposure if available */}
      {factor.exposure_dollar && (
        <div className="text-xs text-gray-500 mb-2 font-mono">
          {formatCurrency(factor.exposure_dollar)}
        </div>
      )}

      {/* Explanation text */}
      <div className="text-xs text-gray-600 leading-relaxed line-clamp-3" title={factor.explanation}>
        {factor.explanation}
      </div>

      {/* Visual indicator bar based on magnitude */}
      <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            factor.magnitude === 'Strong' ? 'bg-purple-500' :
            factor.magnitude === 'Moderate' ? 'bg-blue-500' :
            'bg-gray-400'
          }`}
          style={{
            width: `${Math.min(100, (Math.abs(factor.beta) / 2) * 100)}%`
          }}
        />
      </div>
    </div>
  )
}

export const SpreadFactorCards: React.FC<SpreadFactorCardsProps> = ({
  factors,
  loading = false,
  error,
  calculationDate
}) => {
  // Handle loading state
  if (loading) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-600">Spread Factor Exposures</h3>
            <span className="text-xs text-gray-500">180-day regression analysis</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {SPREAD_FACTOR_ORDER.map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  // Handle error state
  if (error) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-600">Spread Factor Exposures</h3>
            <span className="text-xs text-gray-500">180-day regression analysis</span>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600 text-sm">
              Unable to load spread factor exposures
            </p>
          </div>
        </div>
      </section>
    )
  }

  // Handle no data
  if (!factors || factors.length === 0) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-600">Spread Factor Exposures</h3>
            <span className="text-xs text-gray-500">180-day regression analysis</span>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm">
              Spread factor data not yet available. Run batch calculations to generate spread factors.
            </p>
          </div>
        </div>
      </section>
    )
  }

  // Sort factors according to specified order
  const sortedFactors = [...factors].sort((a, b) => {
    const indexA = SPREAD_FACTOR_ORDER.indexOf(a.name)
    const indexB = SPREAD_FACTOR_ORDER.indexOf(b.name)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Spread Factor Exposures</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Long-short factors (VUG-VTV, MTUM-SPY, IWM-SPY, QUAL-SPY) · 180-day window
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-gray-500">
              {sortedFactors.length} of {SPREAD_FACTOR_ORDER.length} factors
            </span>
            {calculationDate && (
              <div className="text-xs text-gray-400 mt-1">
                As of {new Date(calculationDate).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric'
                })}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {sortedFactors.map((factor) => (
            <SpreadFactorCard key={factor.name} factor={factor} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default SpreadFactorCards
