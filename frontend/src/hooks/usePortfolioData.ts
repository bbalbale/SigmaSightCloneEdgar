import { useEffect, useState } from 'react'
import { loadPortfolioData } from '@/services/portfolioService'
import { usePortfolioStore } from '@/stores/portfolioStore'
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
  publicPositions: any[]
  optionsPositions: any[]
  privatePositions: any[]
  portfolioName: string
  dataLoaded: boolean
  factorExposures: FactorExposure[] | null
  portfolioId: string | null

  // Actions
  handleRetry: () => void
}

export function usePortfolioData(): UsePortfolioDataReturn {
  // Use separate selectors to avoid creating new object references
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const setPortfolio = usePortfolioStore(state => state.setPortfolio)
  const clearPortfolio = usePortfolioStore(state => state.clearPortfolio)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiErrors, setApiErrors] = useState<ApiErrors>({})
  const [retryCount, setRetryCount] = useState(0)
  const [portfolioSummaryMetrics, setPortfolioSummaryMetrics] = useState<any[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [shortPositions, setShortPositions] = useState<any[]>([])
  const [publicPositions, setPublicPositions] = useState<any[]>([])
  const [optionsPositions, setOptionsPositions] = useState<any[]>([])
  const [privatePositions, setPrivatePositions] = useState<any[]>([])
  const [portfolioName, setPortfolioName] = useState('Loading...')
  const [dataLoaded, setDataLoaded] = useState(false)
  const [factorExposures, setFactorExposures] = useState<FactorExposure[] | null>(null)

  useEffect(() => {
    const abortController = new AbortController()

    const loadData = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await loadPortfolioData(abortController.signal, {
          portfolioId,
          forceRefresh: retryCount > 0
        })

        if (!data) {
          setError('Portfolio data unavailable')
          setDataLoaded(false)
          return
        }

        const resolvedId = data.portfolioId
        if (resolvedId) {
          setPortfolio(resolvedId, data.portfolioInfo?.name)
        }

        if (data.errors) {
          setApiErrors(data.errors)
        } else {
          setApiErrors({})
        }

        setPortfolioSummaryMetrics(data.exposures || [])
        const allPositions = data.positions || []

        setPositions(allPositions.filter(p => p.type === 'LONG' || !p.type))
        setShortPositions(allPositions.filter(p => p.type === 'SHORT'))

        const publicPos = allPositions.filter(p => !p.investment_class || p.investment_class === 'PUBLIC')
        const optionsPos = allPositions.filter(p => p.investment_class === 'OPTIONS' || ['LC', 'LP', 'SC', 'SP'].includes(p.type))
        const privatePos = allPositions.filter(p => p.investment_class === 'PRIVATE')

        setPublicPositions(publicPos)
        setOptionsPositions(optionsPos)
        setPrivatePositions(privatePos)
        setFactorExposures(data.factorExposures || null)

        if (data.portfolioInfo?.name) {
          setPortfolioName(data.portfolioInfo.name)
        } else {
          setPortfolioName('Portfolio')
        }

        setDataLoaded(true)
        setError(null)
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return
        }

        console.error('Failed to load portfolio:', err)
        const errorMessage = err.message || 'Failed to load portfolio data'
        setError(errorMessage)
        setDataLoaded(false)
        setPortfolioSummaryMetrics([])
        setPositions([])
        setShortPositions([])
        setPublicPositions([])
        setOptionsPositions([])
        setPrivatePositions([])
        setPortfolioName('Portfolio Unavailable')
        clearPortfolio()
      } finally {
        setLoading(false)
      }
    }

    loadData()

    return () => {
      abortController.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [portfolioId, retryCount])

  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
  }

  return {
    loading,
    error,
    apiErrors,
    portfolioSummaryMetrics,
    positions,
    shortPositions,
    publicPositions,
    optionsPositions,
    privatePositions,
    portfolioName,
    dataLoaded,
    factorExposures,
    portfolioId,
    handleRetry
  }
}


