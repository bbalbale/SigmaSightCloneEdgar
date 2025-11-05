'use client'

import React from 'react'
import type { FactorExposure } from '@/types/analytics'
import type { SpreadFactor } from '@/services/spreadFactorsApi'

const FACTOR_DISPLAY_ORDER = [
  'Market Beta',
  'Momentum',
  'Value',
  'Growth',
  'Quality',
  'Size',
  'Low Volatility'
]

const SPREAD_DISPLAY_ORDER = [
  'Growth-Value Spread',
  'Momentum Spread',
  'Size Spread',
  'Quality Spread'
]

interface MetricCardProps {
  label: string
  value: string
  subValue: string
  valueVariant: 'positive' | 'negative' | 'neutral'
}

interface FactorExposureHeroRowProps {
  factorExposures: FactorExposure[] | null
  factorAvailable: boolean
  factorLoading: boolean
  factorError: string | null
  factorCalculationDate: string | null
  spreadFactors: SpreadFactor[] | null
  spreadAvailable: boolean
  spreadLoading: boolean
  spreadError: string | null
  spreadCalculationDate: string | null
  onRefetchFactors?: () => void
  onRefetchSpreads?: () => void
}

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

function getValueVariant(value: number | null | undefined): 'positive' | 'negative' | 'neutral' {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
    return 'neutral'
  }
  return value > 0 ? 'positive' : 'negative'
}

function MetricCard({ label, value, subValue, valueVariant }: MetricCardProps) {
  const textColor =
    valueVariant === 'positive'
      ? 'text-emerald-400'
      : valueVariant === 'negative'
        ? 'text-red-400'
        : 'text-accent'

  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary">
        {label}
      </div>
      <div className={`text-2xl font-bold tabular-nums mb-0.5 ${textColor}`}>{value}</div>
      <div className="text-xs font-medium tabular-nums text-secondary">{subValue}</div>
    </div>
  )
}

function LoadingCard() {
  return (
    <div className="themed-card p-4 animate-pulse transition-colors duration-300">
      <div className="h-3 rounded w-24 mb-2 bg-tertiary"></div>
      <div className="h-8 rounded w-32 mb-1 bg-tertiary"></div>
      <div className="h-4 rounded w-20 bg-tertiary"></div>
    </div>
  )
}

function EmptyState({
  message,
  onRetry
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="themed-border bg-secondary p-6 text-sm text-secondary flex items-center justify-between gap-4">
      <span>{message}</span>
      {onRetry ? (
        <button
          type="button"
          className="text-xs font-semibold uppercase tracking-wide text-accent hover:text-accent/80"
          onClick={onRetry}
        >
          Retry
        </button>
      ) : null}
    </div>
  )
}

function formatDate(value: string | null): string | null {
  if (!value) {
    return null
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function FactorExposureHeroRow({
  factorExposures,
  factorAvailable,
  factorLoading,
  factorError,
  factorCalculationDate,
  spreadFactors,
  spreadAvailable,
  spreadLoading,
  spreadError,
  spreadCalculationDate,
  onRefetchFactors,
  onRefetchSpreads
}: FactorExposureHeroRowProps) {
  const loading = factorLoading || spreadLoading
  const hasData =
    (factorAvailable && Array.isArray(factorExposures) && factorExposures.length > 0) ||
    (spreadAvailable && Array.isArray(spreadFactors) && spreadFactors.length > 0)

  if (loading) {
    return (
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-medium text-secondary">Factor & Spread Snapshot</h2>
              <p className="text-xs text-tertiary">Loading portfolio betas and spread tilts...</p>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-8 gap-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <LoadingCard key={index} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (!hasData) {
    const errorMessage =
      factorError ||
      spreadError ||
      'Factor exposures are not available yet. Run analytics calculations and try again.'

    return (
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <EmptyState
            message={errorMessage}
            onRetry={() => {
              onRefetchFactors?.()
              onRefetchSpreads?.()
            }}
          />
        </div>
      </section>
    )
  }

  const factorCards: MetricCardProps[] = Array.isArray(factorExposures)
    ? [...factorExposures]
        .sort((a, b) => {
          const indexA = FACTOR_DISPLAY_ORDER.indexOf(a.name)
          const indexB = FACTOR_DISPLAY_ORDER.indexOf(b.name)
          if (indexA === -1 && indexB === -1) return a.name.localeCompare(b.name)
          if (indexA === -1) return 1
          if (indexB === -1) return -1
          return indexA - indexB
        })
        .map(factor => ({
          label: factor.name,
          value: formatBeta(factor.beta),
          subValue: 'Factor beta',
          valueVariant: getValueVariant(factor.beta),
        }))
    : []

  const spreadCards: MetricCardProps[] = Array.isArray(spreadFactors)
    ? [...spreadFactors]
        .sort((a, b) => {
          const indexA = SPREAD_DISPLAY_ORDER.indexOf(a.name)
          const indexB = SPREAD_DISPLAY_ORDER.indexOf(b.name)
          if (indexA === -1 && indexB === -1) return a.name.localeCompare(b.name)
          if (indexA === -1) return 1
          if (indexB === -1) return -1
          return indexA - indexB
        })
        .map(spread => ({
          label: spread.name,
          value: formatBeta(spread.beta),
          subValue: 'Spread beta',
          valueVariant: getValueVariant(spread.beta),
        }))
    : []

  const cards = [...factorCards, ...spreadCards]

  const calcStamp = formatDate(factorCalculationDate ?? spreadCalculationDate ?? null)

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-3 gap-3">
          <div>
            <h2 className="text-sm font-medium text-secondary">Factor & Spread Snapshot</h2>
            <p className="text-xs text-tertiary">
              Portfolio factor betas and long/short spread tilts.
            </p>
          </div>
          {calcStamp ? (
            <span className="text-xs text-tertiary whitespace-nowrap">
              As of {calcStamp}
            </span>
          ) : null}
        </div>
        <div className="themed-border overflow-hidden bg-secondary">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-8">
            {cards.map(card => (
              <MetricCard
                key={card.label}
                label={card.label}
                value={card.value}
                subValue={card.subValue}
                valueVariant={card.valueVariant}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default FactorExposureHeroRow
