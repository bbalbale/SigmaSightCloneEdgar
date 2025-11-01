import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface VolatilityMetricsProps {
  realizedVol21d: number
  realizedVol63d: number | null
  expectedVol21d: number | null
  volTrend: string | null
  volPercentile: number | null
  loading?: boolean
  error?: string | null
}

export function VolatilityMetrics({
  realizedVol21d,
  realizedVol63d,
  expectedVol21d,
  volTrend,
  volPercentile,
  loading = false,
  error = null,
}: VolatilityMetricsProps) {
  const { theme } = useTheme()

  // Don't render if loading or error
  if (loading || error) {
    return null
  }

  const getTrendIcon = () => {
    if (volTrend === 'increasing') return <TrendingUp className="h-5 w-5 text-red-500" />
    if (volTrend === 'decreasing') return <TrendingDown className="h-5 w-5 text-green-500" />
    return <Minus className="h-5 w-5 text-tertiary" />
  }

  const getTrendColor = () => {
    if (volTrend === 'increasing') return 'text-red-500'
    if (volTrend === 'decreasing') return 'text-green-500'
    return 'text-tertiary'
  }

  const getVolatilityLevel = (vol: number): string => {
    if (vol < 0.15) return 'Very Low'
    if (vol < 0.25) return 'Low'
    if (vol < 0.35) return 'Moderate'
    if (vol < 0.50) return 'High'
    return 'Very High'
  }

  const getPercentileDescription = (percentile: number): string => {
    if (percentile >= 0.75) return 'Well above historical'
    if (percentile >= 0.5) return 'Above historical'
    if (percentile >= 0.25) return 'Near historical average'
    return 'Below historical'
  }

  const getPercentileColor = (percentile: number): string => {
    if (percentile >= 0.75) return 'bg-red-500'
    if (percentile >= 0.5) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <Card className="transition-colors duration-300 themed-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Volatility Analysis
          </span>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className={`h-4 w-4 ${theme === 'dark' ? 'text-secondary' : 'text-tertiary'}`} />
              </TooltipTrigger>
              <TooltipContent>
                <p>Historical and forecasted portfolio volatility.</p>
                <p className="text-xs">Lower = more stable returns</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Current Volatility */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-primary">
                Current (21-day)
              </span>
              <span className={`text-2xl font-bold ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {(realizedVol21d * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-tertiary">
              {getVolatilityLevel(realizedVol21d)} volatility
            </p>
          </div>

          {/* Historical Windows */}
          {realizedVol63d !== null && (
            <div className="grid grid-cols-1 gap-4 py-2 border-t border-primary">
              <div>
                <p className="text-xs text-secondary">
                  63-day (~3 months)
                </p>
                <p className={`text-sm font-medium ${
                  theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
                }`}>
                  {(realizedVol63d * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          )}

          {/* Expected Volatility */}
          {expectedVol21d !== null && (
            <div className="border-t pt-4 border-primary">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-primary">
                  Expected (21-day forecast)
                </span>
                <span className={`text-lg font-semibold ${
                  theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
                }`}>
                  {(expectedVol21d * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-xs text-tertiary">
                HAR model forecast
              </p>
            </div>
          )}

          {/* Trend */}
          {volTrend && (
            <div className={`flex items-center justify-between p-3 rounded-lg ${
              theme === 'dark' ? 'bg-slate-700/50' : 'bg-gray-100'
            }`}>
              <div className="flex items-center gap-2">
                {getTrendIcon()}
                <span className={`text-sm font-medium ${getTrendColor()}`}>
                  Volatility {volTrend}
                </span>
              </div>
              {volPercentile !== null && (
                <span className="text-xs text-secondary">
                  {getPercentileDescription(volPercentile)}
                </span>
              )}
            </div>
          )}

          {/* Percentile Bar */}
          {volPercentile !== null && (
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className={theme === 'dark' ? 'text-secondary' : 'text-secondary'}>
                  Volatility Percentile
                </span>
                <span className="font-medium text-primary">
                  {(volPercentile * 100).toFixed(0)}th
                </span>
              </div>
              <div className={`h-2 rounded-full overflow-hidden ${
                theme === 'dark' ? 'bg-slate-700' : 'bg-gray-200'
              }`}>
                <div
                  className={`h-full transition-all ${getPercentileColor(volPercentile)}`}
                  style={{ width: `${volPercentile * 100}%` }}
                />
              </div>
              <p className="text-xs mt-1 text-tertiary">
                vs. 1-year historical distribution
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
