import React from 'react'
import { ThemedCard } from '@/components/ui/ThemedCard'

interface Metric {
  title: string
  value: string
  subValue?: string
  description?: string
  positive?: boolean
}

interface PortfolioMetricsProps {
  metrics: Metric[]
  loading: boolean
  error: string | null
}

export function PortfolioMetrics({ metrics, loading, error }: PortfolioMetricsProps) {
  // Don't render if loading or error
  if (loading || error || !metrics || metrics.length === 0) {
    return null
  }

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 mb-8" style={{ gap: 'var(--card-gap)' }}>
          {metrics.map((metric, index) => (
            <ThemedCard
              key={index}
              hover={true}
              className="transition-colors duration-300"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
                  {metric.title}
                </div>
              </div>
              <div className="text-xl font-bold mb-1" style={{
                color: metric.positive ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {metric.value}
              </div>
              {metric.subValue && (
                <div className="text-sm mb-1 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {metric.subValue}
                </div>
              )}
              {metric.description && (
                <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
                  {metric.description}
                </div>
              )}
            </ThemedCard>
          ))}
        </div>
      </div>
    </section>
  )
}
