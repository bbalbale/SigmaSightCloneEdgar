import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PublicPositions } from './PublicPositions'
import { OptionsPositions } from './OptionsPositions'
import { PrivatePositions } from './PrivatePositions'
import type {
  PublicPositionView,
  OptionPositionView,
  PrivatePositionView,
  PositionType
} from '@/types/positions'

interface PortfolioPositionsProps {
  longPositions?: PublicPositionView[]
  shortPositions?: PublicPositionView[]
  publicPositions?: PublicPositionView[]
  optionsPositions?: OptionPositionView[]
  privatePositions?: PrivatePositionView[]
}

const isLongOption = (type?: PositionType) => type === 'LC' || type === 'LP'
const isShortOption = (type?: PositionType) => type === 'SC' || type === 'SP'

export function PortfolioPositions({
  longPositions = [],
  shortPositions = [],
  publicPositions = [],
  optionsPositions = [],
  privatePositions = []
}: PortfolioPositionsProps) {
  const hasInvestmentClassData =
    publicPositions.length > 0 || optionsPositions.length > 0 || privatePositions.length > 0

  const publicPositionsFinal: PublicPositionView[] = hasInvestmentClassData
    ? publicPositions
    : [...longPositions, ...shortPositions]

  const publicLongs = publicPositionsFinal.filter((p) => p.type === 'LONG' || !p.type)
  const publicShorts = publicPositionsFinal.filter((p) => p.type === 'SHORT')

  const optionLongs = optionsPositions.filter((p) => isLongOption(p.type))
  const optionShorts = optionsPositions.filter((p) => isShortOption(p.type))

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
