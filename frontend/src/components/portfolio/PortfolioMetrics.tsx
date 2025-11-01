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
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {metrics.map((metric, index) => (
            <ThemedCard
              key={index}
              hover={true}
              className="transition-colors duration-300"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-secondary transition-colors duration-300">
                  {metric.title}
                </div>
              </div>
              <div className={`text-xl font-bold mb-1 ${
                metric.positive ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {metric.value}
              </div>
              {metric.subValue && (
                <div className="text-sm mb-1 text-primary transition-colors duration-300">
                  {metric.subValue}
                </div>
              )}
              {metric.description && (
                <div className="text-xs text-tertiary transition-colors duration-300">
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
