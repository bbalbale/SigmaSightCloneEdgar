import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PublicPositions } from './PublicPositions'
import { OptionsPositions } from './OptionsPositions'
import { PrivatePositions } from './PrivatePositions'

interface Position {
  id?: string
  symbol: string
  company_name?: string
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
  // If new investment class arrays are provided, use them
  // Otherwise fall back to legacy long/short grouping
  const hasInvestmentClassData = publicPositions.length > 0 || optionsPositions.length > 0 || privatePositions.length > 0

  // For backward compatibility, if only legacy data is provided, display it in the public column
  const publicPositionsFinal = hasInvestmentClassData ? publicPositions : [...longPositions, ...shortPositions]

  // Split public positions into longs and shorts
  const publicLongs = publicPositionsFinal.filter(p => p.type === 'LONG' || !p.type)
  const publicShorts = publicPositionsFinal.filter(p => p.type === 'SHORT')

  // Split options into longs (LC, LP) and shorts (SC, SP)
  const optionLongs = optionsPositions.filter(p => p.type === 'LC' || p.type === 'LP')
  const optionShorts = optionsPositions.filter(p => p.type === 'SC' || p.type === 'SP')

  return (
    <section className="flex-1 px-4 pb-6">
      <div className="container mx-auto">
        <div className="space-y-8">
          {/* Row 1: Longs (Stocks), Shorts (Stocks), Private Investments */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Longs */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>Longs</h3>
                <Badge variant="secondary" className="transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--color-accent)'
                }}>
                  {publicLongs.length}
                </Badge>
              </div>
              <PublicPositions positions={publicLongs} />
            </div>

            {/* Shorts */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>Shorts</h3>
                <Badge variant="secondary" className="transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--color-accent)'
                }}>
                  {publicShorts.length}
                </Badge>
              </div>
              <PublicPositions positions={publicShorts} />
            </div>

            {/* Private Investments */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>Private Investments</h3>
                <Badge variant="secondary" className="transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--color-accent)'
                }}>
                  {privatePositions.length}
                </Badge>
              </div>
              <PrivatePositions positions={privatePositions} />
            </div>
          </div>

          {/* Row 2: Option Longs and Shorts (3-column layout with empty third column) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Option Longs (LC, LP) */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>Long Options</h3>
                <Badge variant="secondary" className="transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--color-accent)'
                }}>
                  {optionLongs.length}
                </Badge>
              </div>
              <OptionsPositions positions={optionLongs} />
            </div>

            {/* Option Shorts (SC, SP) */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>Short Options</h3>
                <Badge variant="secondary" className="transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--color-accent)'
                }}>
                  {optionShorts.length}
                </Badge>
              </div>
              <OptionsPositions positions={optionShorts} />
            </div>

            {/* Empty third column for alignment */}
            <div></div>
          </div>
        </div>
      </div>
    </section>
  )
}