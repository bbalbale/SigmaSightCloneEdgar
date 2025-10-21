/**
 * FactorBetaCard - Display factor exposures (betas) for a position
 *
 * Shows both:
 * 1. Calculated factor betas (7-factor model from regression)
 * 2. Company market beta (from financial data provider)
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface FactorBetaCardProps {
  symbol: string
  factorExposures?: Record<string, number> // Calculated factor betas
  companyBeta?: number // Market beta from company profile
  loading?: boolean
  calculationDate?: string | null
}

// Factor descriptions for tooltips
const FACTOR_DESCRIPTIONS: Record<string, string> = {
  'Market Beta': 'Sensitivity to overall market movements (SPY)',
  'Value': 'Exposure to value stocks vs growth stocks (VTV)',
  'Growth': 'Exposure to growth stocks vs value stocks (VUG)',
  'Momentum': 'Exposure to stocks with strong recent performance (MTUM)',
  'Quality': 'Exposure to high-quality, profitable companies (QUAL)',
  'Size': 'Exposure to small-cap vs large-cap stocks (IWM)',
  'Low Volatility': 'Exposure to low-volatility stocks (USMV)'
}

// Preferred display order for factors
const FACTOR_ORDER = [
  'Market Beta',
  'Value',
  'Growth',
  'Momentum',
  'Quality',
  'Size',
  'Low Volatility'
]

export function FactorBetaCard({
  symbol,
  factorExposures,
  companyBeta,
  loading = false,
  calculationDate
}: FactorBetaCardProps) {
  // Format beta value with sign and color
  const formatBeta = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A'
    const formatted = value.toFixed(2)
    return value > 0 ? `+${formatted}` : formatted
  }

  // Get color class based on beta value
  const getBetaColor = (value: number | undefined) => {
    if (value === undefined || value === null) return 'text-gray-400'
    if (Math.abs(value) < 0.1) return 'text-gray-500'
    return value > 0 ? 'text-green-600' : 'text-red-600'
  }

  // Loading state
  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-gray-500">
            {symbol} - Loading factor data...
          </CardTitle>
        </CardHeader>
      </Card>
    )
  }

  // No data available
  if (!factorExposures && !companyBeta) {
    return (
      <Card className="w-full border-gray-200">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-gray-400">
            {symbol} - No factor data available
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-gray-400">
            Factor calculations may not be complete yet. Check back after the next batch processing run.
          </p>
        </CardContent>
      </Card>
    )
  }

  // Sort factors by preferred order
  const sortedFactors = FACTOR_ORDER.filter(name =>
    factorExposures && name in factorExposures
  )

  return (
    <Card className="w-full border-blue-100 bg-blue-50/30">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-gray-700">
            {symbol} Factor Exposures
          </CardTitle>
          {calculationDate && (
            <span className="text-xs text-gray-400">
              {new Date(calculationDate).toLocaleDateString()}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Calculated Factor Betas (7-factor model) */}
        {factorExposures && sortedFactors.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-600 mb-2">
              Calculated Factor Betas
            </h4>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {sortedFactors.map(factorName => {
                const value = factorExposures[factorName]
                return (
                  <TooltipProvider key={factorName}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex justify-between items-center text-xs cursor-help">
                          <span className="text-gray-600 font-medium">
                            {factorName}:
                          </span>
                          <span className={`font-mono font-semibold ${getBetaColor(value)}`}>
                            {formatBeta(value)}
                          </span>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        <p className="text-xs">{FACTOR_DESCRIPTIONS[factorName]}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )
              })}
            </div>
          </div>
        )}

        {/* Company Market Beta (from profile) */}
        {companyBeta !== undefined && companyBeta !== null && (
          <div className="pt-2 border-t border-blue-200">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex justify-between items-center cursor-help">
                    <span className="text-xs text-gray-600 font-medium">
                      Market Beta (Profile):
                    </span>
                    <span className={`text-sm font-mono font-bold ${getBetaColor(companyBeta)}`}>
                      {formatBeta(companyBeta)}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="text-xs">
                    Market beta from company financial profile (independent calculation from data provider)
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* Missing data message */}
        {!factorExposures && companyBeta !== undefined && (
          <p className="text-xs text-gray-400 italic">
            Calculated factor betas not yet available
          </p>
        )}
      </CardContent>
    </Card>
  )
}
