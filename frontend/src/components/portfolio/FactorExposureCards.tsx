'use client'

import React from 'react'
import type { FactorExposure, DataStalenessInfo, DataQualityInfo } from '@/types/analytics'
import { DataQualityIndicator } from '../DataQualityIndicator'

interface FactorExposureCardsProps {
  factors: FactorExposure[] | null
  loading?: boolean
  error?: any
  dataQuality?: DataStalenessInfo | DataQualityInfo | null
}

// Factor order as specified - names must match backend FactorDefinition names
const FACTOR_ORDER = [
  'Market Beta (90D)',
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
  // All cards use theme colors, intensity indicated by visual bar
  return ''
}

// Skeleton card for loading state
const SkeletonCard = () => (
  <div
    className="animate-pulse"
    style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: 'var(--border-radius)',
      border: '1px solid var(--border-primary)',
      padding: 'var(--card-padding)'
    }}
  >
    <div className="h-3 rounded w-20 mb-1" style={{ backgroundColor: 'var(--bg-tertiary)' }}></div>
    <div className="h-5 rounded w-12 mb-1" style={{ backgroundColor: 'var(--bg-tertiary)' }}></div>
    <div className="h-3 rounded w-24" style={{ backgroundColor: 'var(--bg-tertiary)' }}></div>
  </div>
)

// Individual factor card
const FactorCard = ({ factor }: { factor: FactorExposure }) => {
  return (
    <div
      className="transition-all duration-200 cursor-pointer"
      style={{
        borderRadius: 'var(--border-radius)',
        border: '1px solid var(--border-primary)',
        padding: 'var(--card-padding)',
        backgroundColor: 'var(--bg-secondary)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'
        e.currentTarget.style.borderColor = 'var(--border-accent)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'
        e.currentTarget.style.borderColor = 'var(--border-primary)'
      }}
    >
      <div className="text-xs font-medium mb-0.5" style={{ color: 'var(--text-secondary)' }}>
        {factor.name}
      </div>
      <div className="text-base font-bold mb-0.5" style={{ color: 'var(--text-primary)' }}>
        {formatBeta(factor.beta)}
      </div>
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        {formatCurrency(factor.exposure_dollar)}
      </div>
      {/* Visual indicator bar */}
      <div
        className="mt-1.5 h-1 rounded-full overflow-hidden"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      >
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${Math.min(100, (Math.abs(factor.beta) / 7) * 100)}%`,
            backgroundColor: 'var(--color-accent)',
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
  error,
  dataQuality
}) => {
  // Handle loading state
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7" style={{ gap: 'var(--card-gap)' }}>
        {FACTOR_ORDER.map((_, index) => (
          <SkeletonCard key={index} />
        ))}
      </div>
    )
  }

  // Handle error state
  if (error) {
    return (
      <div
        className="p-4"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--color-error)',
          borderRadius: 'var(--border-radius)'
        }}
      >
        <p className="text-sm" style={{ color: 'var(--color-error)' }}>
          Unable to load factor exposures
        </p>
      </div>
    )
  }

  // Handle no data
  if (!factors || factors.length === 0) {
    return (
      <div
        className="p-4"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--border-radius)'
        }}
      >
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
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
          <div className="flex items-center" style={{ gap: 'var(--card-gap)' }}>
            <h3 className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Factor Exposures</h3>
            <DataQualityIndicator dataQuality={dataQuality} />
          </div>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Beta values and dollar exposures</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7" style={{ gap: 'var(--card-gap)' }}>
          {sortedFactors.map((factor) => (
            <FactorCard key={factor.name} factor={factor} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default FactorExposureCards