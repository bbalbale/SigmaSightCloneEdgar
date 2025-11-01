import React from 'react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/contexts/ThemeContext'

interface ApiErrors {
  overview?: any
  positions?: any
  factorExposures?: any
}

interface PortfolioErrorProps {
  error: string | null
  apiErrors: ApiErrors
  dataLoaded: boolean
  loading: boolean
  onRetry: () => void
}

export function PortfolioError({
  error,
  apiErrors,
  dataLoaded,
  loading,
  onRetry
}: PortfolioErrorProps) {
  // Don't show error banner if loading or no errors
  if (loading || (!error && !apiErrors.positions)) {
    return null
  }

  return (
    <div className="px-4 py-3 transition-colors duration-300" style={{
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      borderBottom: '1px solid var(--color-error)'
    }}>
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span style={{
            fontSize: 'var(--text-sm)',
            color: 'var(--color-error)'
          }}>
            ⚠️ {error || (apiErrors.positions && 'Position data unavailable')}
          </span>
          {dataLoaded && (
            <span style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              (partial data available)
            </span>
          )}
        </div>
        <Button
          onClick={onRetry}
          size="sm"
          variant="outline"
          className="transition-colors duration-300"
          style={{
            fontSize: 'var(--text-xs)',
            borderColor: 'var(--color-error)',
            color: 'var(--color-error)'
          }}
        >
          Retry
        </Button>
      </div>
    </div>
  )
}

// Error State Component (for full-page error)
export function PortfolioErrorState({
  error,
  onRetry
}: {
  error: string
  onRetry: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] px-4 transition-colors duration-300 bg-primary">
      <div className="text-center max-w-md text-secondary">
        <div className="text-6xl mb-4">😵</div>
        <h2 className="font-semibold mb-2 transition-colors duration-300" style={{
          fontSize: 'var(--text-xl)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-display)'
        }}>Unable to Load Portfolio</h2>
        <p className="mb-4">{error}</p>
        <Button
          onClick={onRetry}
          variant="outline"
          className="transition-colors duration-300"
          style={{
            borderColor: 'var(--border-primary)',
            color: 'var(--text-primary)',
            backgroundColor: 'var(--bg-secondary)'
          }}
        >
          Try Again
        </Button>
      </div>
    </div>
  )
}