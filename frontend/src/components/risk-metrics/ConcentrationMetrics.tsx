'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'
import { Info } from 'lucide-react'
import type { ConcentrationMetricsResponse } from '@/types/analytics'

interface ConcentrationMetricsProps {
  data: ConcentrationMetricsResponse | null
  loading: boolean
  error: string | null
  onRetry?: () => void
}

export function ConcentrationMetrics({ data, loading, error, onRetry }: ConcentrationMetricsProps) {
  const { theme } = useTheme()

  if (loading) {
    return (
      <Card className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardHeader>
          <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Concentration Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-center py-8 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
            Loading concentration data...
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !data?.available || !data?.data) {
    return (
      <Card className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardHeader>
          <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Concentration Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className={`mb-4 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              {error || 'Concentration data not available'}
            </p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  const { hhi, effective_num_positions, top_3_concentration, top_10_concentration } = data.data

  // HHI interpretation
  const getHHILevel = (value: number): { level: string; color: string } => {
    if (value < 1000) return { level: 'Highly Diversified', color: 'text-emerald-400' }
    if (value < 1800) return { level: 'Moderately Concentrated', color: 'text-yellow-400' }
    if (value < 2500) return { level: 'Concentrated', color: 'text-orange-400' }
    return { level: 'Highly Concentrated', color: 'text-red-400' }
  }

  const hhiLevel = getHHILevel(hhi)

  return (
    <Card className={`transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <CardTitle className={`flex items-center gap-2 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Concentration Metrics
          <div className="group relative">
            <Info className={`h-4 w-4 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-400'}`} />
            <div className={`absolute left-0 top-6 w-64 p-2 rounded shadow-lg text-xs hidden group-hover:block z-10 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-200' : 'bg-white text-gray-700'
            }`}>
              Portfolio concentration measures how evenly assets are distributed. Lower concentration = better diversification.
            </div>
          </div>
        </CardTitle>
        <p className={`text-sm mt-1 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
          Portfolio diversification and position concentration
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* HHI Score */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className={`text-sm font-medium ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>
                HHI Score
              </span>
              <div className="group relative">
                <Info className={`h-3 w-3 ${theme === 'dark' ? 'text-slate-500' : 'text-gray-400'}`} />
                <div className={`absolute right-0 top-6 w-56 p-2 rounded shadow-lg text-xs hidden group-hover:block z-10 ${
                  theme === 'dark' ? 'bg-slate-700 text-slate-200' : 'bg-white text-gray-700'
                }`}>
                  Herfindahl-Hirschman Index: Sum of squared weights. Range: 0-10,000. Lower = more diversified.
                </div>
              </div>
            </div>
            <div className={`text-3xl font-bold ${hhiLevel.color}`}>
              {hhi.toFixed(0)}
            </div>
            <div className={`text-sm ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              {hhiLevel.level}
            </div>
          </div>

          {/* Effective Number of Positions */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className={`text-sm font-medium ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>
                Effective Positions
              </span>
              <div className="group relative">
                <Info className={`h-3 w-3 ${theme === 'dark' ? 'text-slate-500' : 'text-gray-400'}`} />
                <div className={`absolute right-0 top-6 w-56 p-2 rounded shadow-lg text-xs hidden group-hover:block z-10 ${
                  theme === 'dark' ? 'bg-slate-700 text-slate-200' : 'bg-white text-gray-700'
                }`}>
                  Number of equal-sized positions that would give the same HHI. Higher = more balanced.
                </div>
              </div>
            </div>
            <div className={`text-3xl font-bold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {effective_num_positions.toFixed(1)}
            </div>
            <div className={`text-sm ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Balanced positions
            </div>
          </div>

          {/* Top 3 Concentration */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className={`text-sm font-medium ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>
                Top 3 Concentration
              </span>
            </div>
            <div className={`text-3xl font-bold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {(top_3_concentration * 100).toFixed(1)}%
            </div>
            {/* Progress bar */}
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  top_3_concentration > 0.5 ? 'bg-red-500' :
                  top_3_concentration > 0.3 ? 'bg-yellow-500' :
                  'bg-emerald-500'
                }`}
                style={{ width: `${top_3_concentration * 100}%` }}
              />
            </div>
          </div>

          {/* Top 10 Concentration */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className={`text-sm font-medium ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>
                Top 10 Concentration
              </span>
            </div>
            <div className={`text-3xl font-bold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {(top_10_concentration * 100).toFixed(1)}%
            </div>
            {/* Progress bar */}
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  top_10_concentration > 0.75 ? 'bg-red-500' :
                  top_10_concentration > 0.5 ? 'bg-yellow-500' :
                  'bg-emerald-500'
                }`}
                style={{ width: `${top_10_concentration * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Guidance */}
        <div className={`mt-6 pt-4 border-t text-xs ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}
          style={{
            borderColor: theme === 'dark' ? 'rgb(51 65 85)' : 'rgb(229 231 235)'
          }}
        >
          <p className="font-medium mb-1">Interpretation Guide:</p>
          <ul className="space-y-1 ml-4 list-disc">
            <li>HHI &lt; 1,000: Highly diversified portfolio</li>
            <li>HHI 1,000-1,800: Moderately concentrated</li>
            <li>HHI &gt; 2,500: Highly concentrated (higher risk)</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
