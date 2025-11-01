import React from 'react'
import { Card, CardContent } from '@/components/ui/card'

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
            <Card key={index} className="themed-card transition-colors duration-300">
              <CardContent className="p-4">
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
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}