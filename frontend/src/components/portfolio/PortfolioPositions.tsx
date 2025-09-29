import React from 'react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'
import { PublicPositions } from './PublicPositions'
import { OptionsPositions } from './OptionsPositions'
import { PrivatePositions } from './PrivatePositions'

interface Position {
  id?: string
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_class?: string
  investment_subtype?: string
  quantity?: number
  price?: number
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}

interface PortfolioPositionsProps {
  longPositions?: Position[]       // Legacy - for backward compatibility
  shortPositions?: Position[]      // Legacy - for backward compatibility
  publicPositions?: Position[]     // New - public equity/ETF positions
  optionsPositions?: Position[]    // New - options contracts
  privatePositions?: Position[]    // New - private/alternative investments
}

export function PortfolioPositions({
  longPositions = [],
  shortPositions = [],
  publicPositions = [],
  optionsPositions = [],
  privatePositions = []
}: PortfolioPositionsProps) {
  const { theme } = useTheme()

  // If new investment class arrays are provided, use them
  // Otherwise fall back to legacy long/short grouping
  const hasInvestmentClassData = publicPositions.length > 0 || optionsPositions.length > 0 || privatePositions.length > 0
  const hasLegacyData = longPositions.length > 0 || shortPositions.length > 0

  // For backward compatibility, if only legacy data is provided, display it in the public column
  const publicPositionsFinal = hasInvestmentClassData ? publicPositions : [...longPositions, ...shortPositions]

  return (
    <section className="flex-1 px-4 pb-6">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Public Equity/ETF Column */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Public Equity</h3>
              <Badge variant="secondary" className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
              }`}>
                {publicPositionsFinal.length}
              </Badge>
            </div>
            <PublicPositions positions={publicPositionsFinal} />
          </div>

          {/* Options Column */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Options</h3>
              <Badge variant="secondary" className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
              }`}>
                {optionsPositions.length}
              </Badge>
            </div>
            <OptionsPositions positions={optionsPositions} />
          </div>

          {/* Private/Alternative Column */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Private Investments</h3>
              <Badge variant="secondary" className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
              }`}>
                {privatePositions.length}
              </Badge>
            </div>
            <PrivatePositions positions={privatePositions} />
          </div>
        </div>
      </div>
    </section>
  )
}