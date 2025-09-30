'use client'

import React from 'react'
import type { FactorExposure } from '@/types/analytics'

interface FactorExposureCardsProps {
  factors: FactorExposure[] | null
  loading?: boolean
  error?: any
}

// Factor order as specified
const FACTOR_ORDER = [
  'Market Beta',
  'Momentum',
  'Value',
  'Growth',
  'Quality',
  'Size',
  'Low Volatility'
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

// Helper function to format beta value
const formatBeta = (value: number) => {
  return value.toFixed(2)
}

// Helper function to get color based on beta value
const getBetaColor = (beta: number) => {
  const absBeta = Math.abs(beta)
  if (absBeta > 5) return 'text-emerald-700 bg-emerald-50 border-emerald-200'
  if (absBeta > 3) return 'text-emerald-600 bg-emerald-50 border-emerald-200'
  if (absBeta > 1) return 'text-green-600 bg-green-50 border-green-200'
  return 'text-gray-600 bg-gray-50 border-gray-200'
}

// Skeleton card for loading state
const SkeletonCard = () => (
  <div className="bg-white rounded-lg border border-gray-200 p-2 animate-pulse">
    <div className="h-3 bg-gray-200 rounded w-20 mb-1"></div>
    <div className="h-5 bg-gray-200 rounded w-12 mb-1"></div>
    <div className="h-3 bg-gray-200 rounded w-24"></div>
  </div>
)

// Individual factor card
const FactorCard = ({ factor }: { factor: FactorExposure }) => {
  const colorClass = getBetaColor(factor.beta)

  return (
    <div className={`rounded-lg border p-2 transition-all duration-200 hover:shadow-md cursor-pointer ${colorClass}`}>
      <div className="text-xs font-medium text-gray-600 mb-0.5">
        {factor.name}
      </div>
      <div className="text-base font-bold mb-0.5">
        {formatBeta(factor.beta)}
      </div>
      <div className="text-xs text-gray-500">
        {formatCurrency(factor.exposure_dollar)}
      </div>
      {/* Visual indicator bar */}
      <div className="mt-1.5 h-1 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-current transition-all duration-300"
          style={{
            width: `${Math.min(100, (Math.abs(factor.beta) / 7) * 100)}%`,
            opacity: 0.6
          }}
        />
      </div>
    </div>
  )
}

export const FactorExposureCards: React.FC<FactorExposureCardsProps> = ({ 
  factors, 
  loading = false, 
  error 
}) => {
  // Handle loading state
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {FACTOR_ORDER.map((_, index) => (
          <SkeletonCard key={index} />
        ))}
      </div>
    )
  }

  // Handle error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600 text-sm">
          Unable to load factor exposures
        </p>
      </div>
    )
  }

  // Handle no data
  if (!factors || factors.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-gray-600 text-sm">
          Factor exposure data not available
        </p>
      </div>
    )
  }

  // Sort factors according to specified order
  const sortedFactors = [...factors].sort((a, b) => {
    const indexA = FACTOR_ORDER.indexOf(a.name)
    const indexB = FACTOR_ORDER.indexOf(b.name)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-600">Factor Exposures</h3>
          <span className="text-xs text-gray-500">Beta values and dollar exposures</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {sortedFactors.map((factor) => (
            <FactorCard key={factor.name} factor={factor} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default FactorExposureCards