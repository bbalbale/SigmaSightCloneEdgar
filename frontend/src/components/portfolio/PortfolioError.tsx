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
  const { theme } = useTheme()

  // Don't show error banner if loading or no errors
  if (loading || (!error && !apiErrors.positions)) {
    return null
  }

  return (
    <div className={`px-4 py-3 border-b transition-colors duration-300 ${
      theme === 'dark' ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'
    }`}>
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-sm ${theme === 'dark' ? 'text-red-400' : 'text-red-600'}`}>
            ⚠️ {error || (apiErrors.positions && 'Position data unavailable')}
          </span>
          {dataLoaded && (
            <span className={`text-xs ${theme === 'dark' ? 'text-secondary' : 'text-tertiary'}`}>
              (partial data available)
            </span>
          )}
        </div>
        <Button
          onClick={onRetry}
          size="sm"
          variant="outline"
          className={`text-xs ${
            theme === 'dark'
              ? 'border-red-700 text-red-400 hover:bg-red-900/30'
              : 'border-red-300 text-red-600 hover:bg-red-100'
          }`}
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
  const { theme } = useTheme()

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] px-4 transition-colors duration-300 bg-primary">
      <div className="text-center max-w-md text-secondary">
        <div className="text-6xl mb-4">😵</div>
        <h2 className={`text-xl font-semibold mb-2 transition-colors duration-300 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>Unable to Load Portfolio</h2>
        <p className="mb-4">{error}</p>
        <Button
          onClick={onRetry}
          variant="outline"
          className={`transition-colors duration-300 ${
            theme === 'dark'
              ? 'border-slate-600 text-white bg-slate-800 hover:bg-slate-700'
              : 'border-gray-300 text-gray-900 bg-white hover:bg-primary'
          }`}
        >
          Try Again
        </Button>
      </div>
    </div>
  )
}