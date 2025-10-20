/**
 * Custom hook for fetching spread factor exposures
 *
 * Provides loading, error, and data states for spread factors.
 * Automatically fetches data when portfolio ID changes.
 *
 * Created: 2025-10-20
 */

import { useEffect, useState } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  getSpreadFactors,
  hasSpreadFactors,
  type SpreadFactor,
  type SpreadFactorsResponse
} from '@/services/spreadFactorsApi'

interface UseSpreadFactorsReturn {
  spreadFactors: SpreadFactor[] | null
  loading: boolean
  error: any
  available: boolean
  calculationDate: string | null
  metadata: SpreadFactorsResponse['metadata']
  refetch: () => void
}

/**
 * Hook to fetch and manage spread factor data for the current portfolio
 *
 * @returns Spread factors data with loading and error states
 *
 * @example
 * ```typescript
 * function MyComponent() {
 *   const { spreadFactors, loading, error, available } = useSpreadFactors();
 *
 *   if (loading) return <div>Loading...</div>;
 *   if (error) return <div>Error loading spread factors</div>;
 *   if (!available) return <div>No spread factor data available</div>;
 *
 *   return <SpreadFactorCards factors={spreadFactors} />;
 * }
 * ```
 */
export function useSpreadFactors(): UseSpreadFactorsReturn {
  const portfolioId = usePortfolioStore(state => state.portfolioId)

  const [spreadFactors, setSpreadFactors] = useState<SpreadFactor[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<any>(null)
  const [available, setAvailable] = useState(false)
  const [calculationDate, setCalculationDate] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<SpreadFactorsResponse['metadata']>({})
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  useEffect(() => {
    const abortController = new AbortController()

    const fetchSpreadFactors = async () => {
      if (!portfolioId) {
        setSpreadFactors(null)
        setAvailable(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await getSpreadFactors(portfolioId)

        if (hasSpreadFactors(response)) {
          setSpreadFactors(response.factors)
          setAvailable(true)
          setCalculationDate(response.calculation_date || null)
          setMetadata(response.metadata)
        } else {
          setSpreadFactors(null)
          setAvailable(false)
          setCalculationDate(null)
          setMetadata(response.metadata)
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return
        }

        console.error('Failed to load spread factors:', err)
        setError(err)
        setSpreadFactors(null)
        setAvailable(false)
      } finally {
        setLoading(false)
      }
    }

    fetchSpreadFactors()

    return () => {
      abortController.abort()
    }
  }, [portfolioId, refetchTrigger])

  const refetch = () => {
    setRefetchTrigger(prev => prev + 1)
  }

  return {
    spreadFactors,
    loading,
    error,
    available,
    calculationDate,
    metadata,
    refetch
  }
}
