import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

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
  const { theme } = useTheme()

  // Don't render if loading or error
  if (loading || error || !metrics || metrics.length === 0) {
    return null
  }

  return (
    <section className="px-4 pb-6">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {metrics.map((metric, index) => (
            <Card key={index} className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
            }`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className={`text-xs transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                  }`}>{metric.title}</div>
                </div>
                <div className={`text-xl font-bold mb-1 ${
                  metric.positive ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {metric.value}
                </div>
                {metric.subValue && (
                  <div className={`text-sm mb-1 transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
                  }`}>{metric.subValue}</div>
                )}
                {metric.description && (
                  <div className={`text-xs transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
                  }`}>{metric.description}</div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}