import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { loadPortfolioData, PortfolioType } from '@/services/portfolioService'
import type { FactorExposure } from '@/types/analytics'

interface ApiErrors {
  overview?: any
  positions?: any
  factorExposures?: any
}

interface UsePortfolioDataReturn {
  // State
  loading: boolean
  error: string | null
  apiErrors: ApiErrors
  portfolioSummaryMetrics: any[]
  positions: any[]
  shortPositions: any[]
  portfolioName: string
  dataLoaded: boolean
  factorExposures: FactorExposure[] | null
  portfolioType: PortfolioType | null

  // Actions
  handleRetry: () => void
}

export function usePortfolioData(): UsePortfolioDataReturn {
  const searchParams = useSearchParams()
  const portfolioType = searchParams?.get('type') as PortfolioType | null

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiErrors, setApiErrors] = useState<ApiErrors>({})
  const [retryCount, setRetryCount] = useState(0)
  const [portfolioSummaryMetrics, setPortfolioSummaryMetrics] = useState<any[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [shortPositions, setShortPositions] = useState<any[]>([])
  const [portfolioName, setPortfolioName] = useState('Loading...')
  const [dataLoaded, setDataLoaded] = useState(false)
  const [factorExposures, setFactorExposures] = useState<FactorExposure[] | null>(null)

  useEffect(() => {
    const abortController = new AbortController()

    const loadData = async () => {
      if (!portfolioType) {
        // No portfolio type specified - show error
        setError('Please select a portfolio type')
        setPortfolioSummaryMetrics([])
        setPositions([])
        setShortPositions([])
        setPortfolioName('No Portfolio Selected')
        setDataLoaded(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const data = await loadPortfolioData(portfolioType, abortController.signal)

        if (data) {
          console.log('Loaded portfolio data:', data)
          console.log('Portfolio name from backend:', data.portfolioInfo?.name)

          // Handle API errors from individual endpoints
          if (data.errors) {
            setApiErrors(data.errors)

            // Show position error if positions failed but overview succeeded
            if (data.errors.positions && !data.errors.overview) {
              console.error('Position API failed:', data.errors.positions)
            }
            // Log factor exposures error if it failed
            if (data.errors.factorExposures) {
              console.error('Factor exposures API failed:', data.errors.factorExposures)
            }
          } else {
            setApiErrors({})
          }

          // Update all state with real data
          setPortfolioSummaryMetrics(data.exposures || [])
          const allPositions = data.positions || []
          setPositions(allPositions.filter(p => p.type === 'LONG' || !p.type))
          setShortPositions(allPositions.filter(p => p.type === 'SHORT'))
          setFactorExposures(data.factorExposures || null)

          // Use descriptive name if backend returns generic "Demo Portfolio"
          if (data.portfolioInfo?.name === 'Demo Portfolio' && portfolioType === 'individual') {
            setPortfolioName('Demo Individual Investor Portfolio')
          } else {
            setPortfolioName(data.portfolioInfo?.name || 'Portfolio')
          }

          setDataLoaded(true)
          setError(null)
          setRetryCount(0)
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error('Failed to load portfolio:', err)
          const errorMessage = err.message || 'Failed to load portfolio data'
          setError(errorMessage)

          // No fallback - show error state
          if (!dataLoaded) {
            setPortfolioSummaryMetrics([])
            setPositions([])
            setShortPositions([])
            setPortfolioName('Portfolio Unavailable')
          }
        }
      } finally {
        setLoading(false)
      }
    }

    loadData()

    return () => {
      abortController.abort()
    }
  }, [portfolioType, retryCount])

  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
  }

  return {
    // State
    loading,
    error,
    apiErrors,
    portfolioSummaryMetrics,
    positions,
    shortPositions,
    portfolioName,
    dataLoaded,
    factorExposures,
    portfolioType,

    // Actions
    handleRetry
  }
}