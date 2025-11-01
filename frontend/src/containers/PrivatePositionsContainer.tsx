// src/containers/PrivatePositionsContainer.tsx
'use client'

import { usePrivatePositions } from '@/hooks/usePrivatePositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'

export function PrivatePositionsContainer() {
  const { positions, loading, error, aggregateReturns, updatePositionTargetOptimistic } = usePrivatePositions()

  if (loading && !positions.length) {
    return (
      <div
        className="min-h-screen flex items-center justify-center transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <div className="text-center">
          <div
            className="inline-block animate-spin rounded-full h-12 w-12 mb-4"
            style={{ borderBottom: '2px solid var(--color-accent)' }}
          ></div>
          <p
            className="font-medium transition-colors duration-300"
            style={{
              fontSize: 'var(--text-lg)',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-body)'
            }}
          >
            Loading positions...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="min-h-screen transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <section className="px-6 py-12">
          <div className="max-w-7xl mx-auto">
            <div
              className="transition-all duration-300"
              style={{
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                border: '1px solid var(--color-error)',
                borderRadius: 'var(--border-radius)',
                padding: 'var(--card-padding)'
              }}
            >
              <h2
                className="font-bold mb-2 transition-colors duration-300"
                style={{
                  fontSize: 'var(--text-2xl)',
                  color: 'var(--color-error)',
                  fontFamily: 'var(--font-display)'
                }}
              >
                Error Loading Positions
              </h2>
              <p
                className="transition-colors duration-300"
                style={{
                  color: 'var(--color-error)',
                  fontFamily: 'var(--font-body)'
                }}
              >
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1
            className="font-bold mb-2 transition-colors duration-300"
            style={{
              fontSize: 'var(--text-2xl)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}
          >
            Private Positions
          </h1>
          <p
            className="transition-colors duration-300"
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-body)'
            }}
          >
            Private equity, venture capital, and alternative investments
          </p>
        </div>
      </section>

      {/* Positions Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <EnhancedPositionsSection
            positions={positions}
            title="Private Investments"
            aggregateReturnEOY={aggregateReturns.eoy}
            aggregateReturnNextYear={aggregateReturns.next_year}
            onTargetPriceUpdate={updatePositionTargetOptimistic}
          />
        </div>
      </section>
    </div>
  )
}
