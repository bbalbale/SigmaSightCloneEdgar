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
            <span className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-gray-500'}`}>
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

  // Check if the error is due to no portfolio found
  const isNoPortfolio = error.toLowerCase().includes('could not resolve portfolio') ||
                        error.toLowerCase().includes('no portfolio')

  return (
    <div className={`flex flex-col items-center justify-center min-h-[400px] px-4 transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      <div className={`text-center max-w-md ${
        theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
      }`}>
        <div className="text-6xl mb-4">{isNoPortfolio ? '📊' : '😵'}</div>
        <h2 className={`text-xl font-semibold mb-2 transition-colors duration-300 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          {isNoPortfolio ? 'No Portfolio Found' : 'Unable to Load Portfolio'}
        </h2>
        <p className="mb-6">
          {isNoPortfolio
            ? "You haven't created a portfolio yet. Let's get you started!"
            : error
          }
        </p>
        <div className="flex gap-3 justify-center">
          {isNoPortfolio ? (
            <Button
              onClick={() => window.location.href = '/onboarding/upload'}
              className={`transition-colors duration-300 ${
                theme === 'dark'
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              Create Portfolio
            </Button>
          ) : (
            <Button
              onClick={onRetry}
              variant="outline"
              className={`transition-colors duration-300 ${
                theme === 'dark'
                  ? 'border-slate-600 text-white bg-slate-800 hover:bg-slate-700'
                  : 'border-gray-300 text-gray-900 bg-white hover:bg-gray-50'
              }`}
            >
              Try Again
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}