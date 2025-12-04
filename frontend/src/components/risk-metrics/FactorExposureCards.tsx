'use client'

import React from 'react'
import type { FactorExposure } from '@/types/analytics'
import type { SpreadFactor } from '@/services/spreadFactorsApi'

// Factor display order for ridge regression factors (backend names)
const RIDGE_FACTOR_ORDER = [
  'Provider Beta (1Y)',
  'Market Beta (90D)',
  'Momentum',
  'Value',
  'Growth',
  'Quality',
  'Size',
  'Low Volatility',
  'IR Beta'
]

// Spread factor display order
const SPREAD_FACTOR_ORDER = [
  'Growth-Value Spread',
  'Momentum Spread',
  'Size Spread',
  'Quality Spread'
]

interface FactorExposureCardsProps {
  ridgeFactors: FactorExposure[] | null
  spreadFactors: SpreadFactor[] | null
  ridgeLoading: boolean
  spreadLoading: boolean
  ridgeError: string | null
  spreadError: string | null
  ridgeCalculationDate: string | null
  spreadCalculationDate: string | null
  onRefetchRidge?: () => void
  onRefetchSpread?: () => void
}

// Helper: Format beta value
function formatBeta(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--'
  }
  const rounded = Number(value.toFixed(2))
  if (Object.is(rounded, -0)) {
    return '+0.00'
  }
  return `${rounded >= 0 ? '+' : ''}${rounded.toFixed(2)}`
}

// Helper: Get magnitude from beta value
function getMagnitude(beta: number | null | undefined): 'Strong' | 'Moderate' | 'Weak' {
  if (beta === null || beta === undefined) return 'Weak'
  const abs = Math.abs(beta)
  if (abs > 0.5) return 'Strong'
  if (abs > 0.2) return 'Moderate'
  return 'Weak'
}

// Helper: Get direction
function getDirection(beta: number | null | undefined): 'Positive' | 'Negative' | 'Neutral' {
  if (beta === null || beta === undefined) return 'Neutral'
  if (beta > 0.1) return 'Positive'
  if (beta < -0.1) return 'Negative'
  return 'Neutral'
}

// Helper: Get magnitude badge color (Bloomberg style: orange for strong)
function getMagnitudeBadgeColor(magnitude: string): string {
  switch (magnitude) {
    case 'Strong':
      return 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700'
    case 'Moderate':
      return 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-700/30 dark:text-gray-300 dark:border-gray-600'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/20 dark:text-gray-400 dark:border-gray-600'
  }
}

// Helper: Get direction badge color (Bloomberg style: green positive, red negative)
function getDirectionBadgeColor(direction: string): string {
  switch (direction) {
    case 'Positive':
      return 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700'
    case 'Negative':
      return 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/20 dark:text-gray-400 dark:border-gray-600'
  }
}

// Helper: Map backend factor names to display names
function getDisplayName(backendName: string): string {
  const nameMap: Record<string, string> = {
    'Provider Beta (1Y)': '1 Year Beta',
    'Market Beta (90D)': '90 Day Beta',
    'IR Beta': 'Interest Rate Sensitivity'
  }
  return nameMap[backendName] || backendName
}

// Helper: Get factor icon (using backend names)
function getFactorIcon(name: string): string {
  const icons: Record<string, string> = {
    'Provider Beta (1Y)': '📈',
    'Market Beta (90D)': '📈',
    'Momentum': '📊',
    'Value': '💰',
    'Growth': '🚀',
    'Quality': '💎',
    'Size': '📏',
    'Low Volatility': '🛡️',
    'IR Beta': '🏦',
    'Growth-Value Spread': '🎯',
    'Momentum Spread': '📈',
    'Size Spread': '🏢',
    'Quality Spread': '💎'
  }
  return icons[name] || '📊'
}

// Helper: Check if 1Y and 90D betas diverge
function checkBetaDivergence(beta1y: number | null, beta90d: number | null): string | null {
  if (beta1y === null || beta90d === null) return null
  const diff = Math.abs(beta90d - beta1y)
  if (diff > 0.15) {
    if (beta90d > beta1y) {
      return '⚠️ Recent beta HIGHER than 1Y suggests increasing volatility or market exposure. Monitor closely.'
    } else {
      return '⚠️ Recent beta LOWER than 1Y suggests decreasing volatility or market exposure.'
    }
  }
  return null
}

// Helper: Get factor commentary (using backend names)
function getFactorCommentary(name: string, beta: number | null | undefined, beta1y?: number | null): string {
  if (beta === null || beta === undefined) return 'Data not available'

  switch (name) {
    case 'Provider Beta (1Y)':
      return `1-year: Your portfolio has ${beta > 1 ? 'amplified' : beta < 1 ? 'dampened' : 'matched'} market movements. Beta of ${formatBeta(beta)} = ${Math.abs((beta - 1) * 100).toFixed(0)}% ${beta > 1 ? 'more' : 'less'} movement than SPY.`

    case 'Market Beta (90D)': {
      const divergence = checkBetaDivergence(beta1y || null, beta)
      if (divergence) return `90-day: ${formatBeta(beta)}. ${divergence}`
      return `90-day: ${formatBeta(beta)}. ${beta > 1.2 ? 'High volatility - moves significantly more than market.' : beta < 0.8 ? 'Defensive positioning with lower market sensitivity.' : 'Tracking market closely.'}`
    }

    case 'Momentum':
      if (beta > 0.1) return 'Positions with recent upward momentum tend to outperform when trends continue. Risk: Reversal if momentum fades.'
      if (beta < -0.1) return 'Contrarian bet on reversals. May underperform in strong trending markets but capture value during mean reversion.'
      return 'Balanced momentum exposure. Portfolio is neither chasing trends nor betting on reversals.'

    case 'Value':
      if (beta > 0.1) return 'Overweight in undervalued stocks with low P/E, P/B ratios. Performs well when value premiums expand.'
      if (beta < -0.1) return 'Underweight in value stocks. May miss value recovery cycles but avoids value traps.'
      return 'Balanced value exposure. Portfolio has neutral positioning between value and growth characteristics.'

    case 'Growth':
      if (beta > 0.1) return 'Tilted toward high-growth companies. Benefits in bull markets and low-rate environments. Higher valuation risk.'
      if (beta < -0.1) return 'Defensive against growth stock corrections. May underperform in strong risk-on rallies.'
      return 'Balanced growth exposure. Portfolio has neutral positioning between growth and value characteristics.'

    case 'Quality':
      if (beta > 0.1) return 'Overweight in profitable, stable companies with strong balance sheets. Defensive during uncertainty.'
      if (beta < -0.1) return 'Exposure to higher-risk, lower-quality firms. Higher return potential but elevated downside risk.'
      return 'Balanced quality exposure. Portfolio has mix of high-quality and speculative positions.'

    case 'Size':
      if (beta > 0.1) return 'Overweight small caps (IWM vs SPY). Higher growth potential but greater volatility and liquidity risk.'
      if (beta < -0.1) return 'Large cap bias. More stable, liquid, but may underperform in small-cap rallies.'
      return 'Balanced size exposure. Portfolio has mix of large and small cap positions.'

    case 'Low Volatility':
      if (beta > 0.1) return 'Positioned in stable, low-volatility stocks. Defensive during market turbulence. May lag in strong rallies.'
      if (beta < -0.1) return 'Exposure to higher-volatility names. Greater upside capture but increased downside risk.'
      return 'Balanced volatility exposure. Portfolio has mix of stable and volatile positions.'

    case 'IR Beta':
      if (beta > 0.1) return 'Portfolio falls when rates rise (duration risk). Consider hedging if Fed tightening expected.'
      if (beta < -0.1) return 'Benefits from rising rates (financials, value). Vulnerable to rate cuts.'
      return 'Balanced interest rate exposure. Portfolio has neutral sensitivity to rate changes.'

    default:
      return 'Factor exposure analysis'
  }
}

// Helper: Get spread factor commentary
function getSpreadCommentary(name: string, beta: number | null | undefined): string {
  if (beta === null || beta === undefined) return 'Data not available'

  switch (name) {
    case 'Growth-Value Spread':
      return `VUG-VTV: ${formatBeta(beta)}. Your portfolio captures ${Math.abs(beta * 100).toFixed(0)}% of the ${beta > 0 ? 'growth premium over value' : 'value premium over growth'} stocks.`

    case 'Momentum Spread':
      return `MTUM-SPY: ${formatBeta(beta)}. Portfolio ${beta > 0 ? 'tilted toward' : 'underweight in'} stocks with strong recent price momentum.`

    case 'Size Spread':
      return `IWM-SPY: ${formatBeta(beta)}. ${beta > 0 ? 'Positive' : 'Negative'} spread beta means portfolio favors ${beta > 0 ? 'small caps over large caps' : 'large caps over small caps'}.`

    case 'Quality Spread':
      return `QUAL-SPY: ${formatBeta(beta)}. Portfolio captures ${Math.abs(beta * 100).toFixed(0)}% of the quality premium over the broader market.`

    default:
      return 'Spread factor exposure analysis'
  }
}

// Helper: Format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

// Helper: Format date (handles ISO date strings without timezone issues)
function formatDate(value: string | null): string | null {
  if (!value) return null
  // Append T12:00:00 to interpret the date as noon local time, avoiding timezone rollover
  // This fixes the issue where "2025-12-01" was being interpreted as midnight UTC
  // and then displayed as "Nov 30" in US timezones
  const dateString = value.includes('T') ? value : `${value}T12:00:00`
  const parsed = new Date(dateString)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// Individual Factor Card Component
function FactorCard({
  name,
  beta,
  exposureDollar,
  isSpread = false,
  beta1y
}: {
  name: string
  beta: number | null | undefined
  exposureDollar?: number
  isSpread?: boolean
  beta1y?: number | null
}) {
  const magnitude = getMagnitude(beta)
  const direction = getDirection(beta)
  const icon = getFactorIcon(name)
  const commentary = isSpread ? getSpreadCommentary(name, beta) : getFactorCommentary(name, beta, beta1y)
  const magnitudeColor = getMagnitudeBadgeColor(magnitude)
  const directionColor = getDirectionBadgeColor(direction)

  // Get display name: map backend names to friendly names, shorten spread factor names
  const displayName = isSpread ? name.replace(' Spread', '') : getDisplayName(name)

  return (
    <div className="rounded-lg border p-4 transition-all duration-200 hover:shadow-lg cursor-pointer bg-white dark:bg-gray-800 hover:scale-[1.02]">
      {/* Header with name */}
      <div className="mb-2">
        <div className="text-sm font-semibold text-primary">{displayName}</div>
      </div>

      {/* Beta value - large and prominent */}
      <div className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
        {formatBeta(beta)}
      </div>

      {/* Badges: Direction and Magnitude */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${directionColor}`}>
          {direction}
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${magnitudeColor}`}>
          {magnitude}
        </span>
      </div>

      {/* Commentary */}
      <div className="text-xs text-secondary leading-relaxed mb-3 min-h-[60px]">
        {commentary}
      </div>

      {/* Dollar exposure if available */}
      {exposureDollar !== undefined && (
        <div className="text-xs text-tertiary font-mono">
          {formatCurrency(exposureDollar)} exposure
        </div>
      )}
    </div>
  )
}

// Loading skeleton
function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-primary p-4 animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-3"></div>
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-20 mb-2"></div>
      <div className="flex gap-2 mb-3">
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
      </div>
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full mb-1"></div>
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
    </div>
  )
}

// Main component
export function FactorExposureCards({
  ridgeFactors,
  spreadFactors,
  ridgeLoading,
  spreadLoading,
  ridgeError,
  spreadError,
  ridgeCalculationDate,
  spreadCalculationDate,
  onRefetchRidge,
  onRefetchSpread
}: FactorExposureCardsProps) {
  const loading = ridgeLoading || spreadLoading
  const hasRidgeData = Array.isArray(ridgeFactors) && ridgeFactors.length > 0
  const hasSpreadData = Array.isArray(spreadFactors) && spreadFactors.length > 0

  // Sort ridge factors
  const sortedRidgeFactors = hasRidgeData
    ? [...ridgeFactors].sort((a, b) => {
        const indexA = RIDGE_FACTOR_ORDER.indexOf(a.name)
        const indexB = RIDGE_FACTOR_ORDER.indexOf(b.name)
        if (indexA === -1 && indexB === -1) return a.name.localeCompare(b.name)
        if (indexA === -1) return 1
        if (indexB === -1) return -1
        return indexA - indexB
      })
    : []

  // Sort spread factors
  const sortedSpreadFactors = hasSpreadData
    ? [...spreadFactors].sort((a, b) => {
        const indexA = SPREAD_FACTOR_ORDER.indexOf(a.name)
        const indexB = SPREAD_FACTOR_ORDER.indexOf(b.name)
        if (indexA === -1 && indexB === -1) return a.name.localeCompare(b.name)
        if (indexA === -1) return 1
        if (indexB === -1) return -1
        return indexA - indexB
      })
    : []

  // Get beta 1Y for divergence check
  const beta1y = sortedRidgeFactors.find(f => f.name === 'Provider Beta (1Y)')?.beta || null

  const ridgeCalcDate = formatDate(ridgeCalculationDate)
  const spreadCalcDate = formatDate(spreadCalculationDate)

  if (loading) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="mb-3">
            <h2 className="text-sm font-medium text-secondary">Portfolio Factor Analysis</h2>
            <p className="text-xs text-tertiary">Loading factor exposures...</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (!hasRidgeData && !hasSpreadData) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="bg-primary border border-primary rounded-lg p-6 text-center">
            <p className="text-secondary text-sm">
              {ridgeError || spreadError || 'Factor exposure data not yet available. Run batch calculations to generate factor exposures.'}
            </p>
            {(onRefetchRidge || onRefetchSpread) && (
              <button
                onClick={() => {
                  onRefetchRidge?.()
                  onRefetchSpread?.()
                }}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
          {/* Main Section Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-2xl font-bold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                Factor Exposures
              </h2>
              {(ridgeCalcDate || spreadCalcDate) && (
                <span className="text-sm text-secondary">
                  As of {ridgeCalcDate || spreadCalcDate}
                </span>
              )}
            </div>
            <p className="text-sm text-secondary leading-relaxed mb-4">
              Factor exposures measure how your portfolio responds to systematic market forces beyond overall market movements.
              These metrics reveal your portfolio's sensitivity to styles (value vs. growth), characteristics (quality, size),
              and economic conditions (interest rates, momentum). Understanding these exposures helps explain performance,
              identify hidden risks, and manage diversification more effectively.
            </p>

            <div className="pt-4 border-t transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
              <p className="text-sm text-secondary leading-relaxed mb-3">
                <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  SigmaSight takes two approaches to understanding factor risks:
                </strong>
              </p>
              <div className="space-y-3 text-sm text-secondary">
                <div>
                  <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>Ridge Regression Factors:</strong> Uses statistical techniques to disentangle correlated factors and isolate pure factor exposures. This approach controls for the natural correlations between factors (e.g., growth and momentum often move together) to show what happens when you change one factor while holding others constant. This reveals your portfolio's true sensitivities independent of factor interactions.
                </div>
                <div>
                  <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>Long-Short Spread Factors:</strong> Measures portfolio sensitivity through direct regression on tradeable long-short ETF pair returns (e.g., VUG-VTV for growth-value). This approach captures how your portfolio actually responds to realized market factor spreads, providing insight into your exposure to implementable factor strategies and real-world factor performance.
                </div>
              </div>
            </div>
          </div>

          {/* Ridge Regression Factors Section */}
          {hasRidgeData && (
            <>
              <div className="mb-3">
                <h3 className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>Ridge Regression Factors</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {sortedRidgeFactors.map((factor) => (
                <FactorCard
                  key={factor.name}
                  name={factor.name}
                  beta={factor.beta}
                  beta1y={beta1y}
                  isSpread={false}
                />
              ))}
            </div>
          </>
        )}

        {/* Spread Factors Section */}
        {hasSpreadData && (
          <>
            <div className="mb-3">
              <h3 className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>Long-Short Spread Factors</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {sortedSpreadFactors.map((factor) => (
                <FactorCard
                  key={factor.name}
                  name={factor.name}
                  beta={factor.beta}
                  exposureDollar={factor.exposure_dollar}
                  isSpread={true}
                />
              ))}
            </div>
          </>
        )}
        </div>
      </div>
    </section>
  )
}

export default FactorExposureCards
