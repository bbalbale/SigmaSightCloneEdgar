import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PublicPositions } from './PublicPositions'
import { OptionsPositions } from './OptionsPositions'
import { PrivatePositions } from './PrivatePositions'

type BasePosition = {
  id?: string
  symbol: string
  marketValue: number
  pnl: number
  quantity: number
  positive?: boolean
  type?: string
  investment_class?: string
  investment_subtype?: string
  price?: number
  account_name?: string
}

type PublicPosition = BasePosition & {
  company_name?: string
}

type OptionPosition = BasePosition & {
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}

type PrivatePosition = BasePosition & {
  name?: string
}

interface PortfolioPositionsProps {
  longPositions?: PublicPosition[]
  shortPositions?: PublicPosition[]
  publicPositions?: PublicPosition[]
  optionsPositions?: OptionPosition[]
  privatePositions?: PrivatePosition[]
}

export function PortfolioPositions({
  longPositions = [],
  shortPositions = [],
  publicPositions = [],
  optionsPositions = [],
  privatePositions = []
}: PortfolioPositionsProps) {
  const hasInvestmentClassData =
    publicPositions.length > 0 || optionsPositions.length > 0 || privatePositions.length > 0

  const publicPositionsFinal: PublicPosition[] = hasInvestmentClassData
    ? publicPositions
    : [...longPositions, ...shortPositions]

  const publicLongs = publicPositionsFinal.filter((p) => p.type === 'LONG' || !p.type)
  const publicShorts = publicPositionsFinal.filter((p) => p.type === 'SHORT')

  const optionLongs = optionsPositions.filter((p) => p.type === 'LC' || p.type === 'LP')
  const optionShorts = optionsPositions.filter((p) => p.type === 'SC' || p.type === 'SP')

  return (
    <section className="flex-1 px-4 pb-6">
      <div className="container mx-auto">
        <div className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3
                  className="transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  Longs
                </h3>
                <Badge
                  variant="secondary"
                  className="transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--color-accent)'
                  }}
                >
                  {publicLongs.length}
                </Badge>
              </div>
              <PublicPositions positions={publicLongs} />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3
                  className="transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  Shorts
                </h3>
                <Badge
                  variant="secondary"
                  className="transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--color-accent)'
                  }}
                >
                  {publicShorts.length}
                </Badge>
              </div>
              <PublicPositions positions={publicShorts} />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3
                  className="transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  Private Investments
                </h3>
                <Badge
                  variant="secondary"
                  className="transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--color-accent)'
                  }}
                >
                  {privatePositions.length}
                </Badge>
              </div>
              <PrivatePositions positions={privatePositions} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3
                  className="transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  Long Options
                </h3>
                <Badge
                  variant="secondary"
                  className="transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--color-accent)'
                  }}
                >
                  {optionLongs.length}
                </Badge>
              </div>
              <OptionsPositions positions={optionLongs} />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3
                  className="transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  Short Options
                </h3>
                <Badge
                  variant="secondary"
                  className="transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--color-accent)'
                  }}
                >
                  {optionShorts.length}
                </Badge>
              </div>
              <OptionsPositions positions={optionShorts} />
            </div>

            <div />
          </div>
        </div>
      </div>
    </section>
  )
}
